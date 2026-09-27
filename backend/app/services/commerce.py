"""Products, checkout, entitlements (plan v2 Phase 4).

- Products + flat prices are published content (`products`); nothing about price lives in code.
- Checkout creates a `payments` row (pending) and a Stripe Checkout Session.
- An entitlement is granted only when Stripe says the session is paid — from the webhook, or from
  the success page asking the backend to verify the session with Stripe. Both paths call `fulfill`,
  which is idempotent (atomic pending -> paid + unique entitlement per product).
- Access checks read entitlements server-side, so a direct API call can't skip payment.
"""
from typing import Dict, List, Optional, Set

from pymongo.errors import DuplicateKeyError

from app import database, payments as gateway
from app.config import get_settings
from app.content.registry import get_type
from app.content.validation import RefLookup
from app.models.common import new_id, utcnow
from app.models.user import User
from app.services import audit
from app.services.content import Conflict, ContentError, NotFound, get_version

# ISO 4217 currencies Stripe treats as having no minor unit.
ZERO_DECIMAL = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}


class PaymentRequired(ContentError):
    status_code = 402


def to_minor(amount: float, currency: str) -> int:
    return int(round(amount)) if currency.upper() in ZERO_DECIMAL else int(round(amount * 100))


async def published_products(tenant_id: str) -> Dict[str, dict]:
    return await RefLookup(tenant_id).published("products")


def product_out(doc: dict) -> dict:
    d = doc["data"]
    return {
        "key": doc["key"],
        "version": doc["version"],
        "name": d.get("name"),
        "kind": d.get("kind"),
        "description": d.get("description"),
        "price": d.get("price"),
        "currency": d.get("currency"),
        "assessment_keys": d.get("assessment_keys") or [],
        "bundled_product_keys": d.get("bundled_product_keys") or [],
        "requires_product_keys": d.get("requires_product_keys") or [],
        "sort_order": d.get("sort_order") or 0,
    }


async def _assessment_names(tenant_id: str) -> Dict[str, str]:
    """Latest name of every assessment (drafts included — products may list forms still being authored)."""
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$sort": {"key": 1, "version": -1}},
        {"$group": {"_id": "$key", "name": {"$first": "$data.name"}}},
    ]
    return {d["_id"]: d["name"] for d in await database.collection("assessments").aggregate(pipeline).to_list(None)}


async def catalogue(tenant_id: str) -> List[dict]:
    names = await _assessment_names(tenant_id)
    products = []
    for doc in (await published_products(tenant_id)).values():
        p = product_out(doc)
        p["assessments"] = [{"key": k, "name": names.get(k, k)} for k in p["assessment_keys"]]
        products.append(p)
    return sorted(products, key=lambda p: (p["sort_order"], p["price"] or 0, p["key"]))


async def active_entitlements(tenant_id: str, user_id: str) -> List[dict]:
    cursor = database.entitlements().find({"tenant_id": tenant_id, "user_id": user_id, "revoked_at": None}).sort("granted_at", 1)
    return await cursor.to_list(None)


async def owned_product_keys(tenant_id: str, user_id: str) -> Set[str]:
    return {e["product_key"] for e in await active_entitlements(tenant_id, user_id)}


async def all_assessment_keys(tenant_id: str) -> Set[str]:
    """Every assessment offered by any published product — used when the paywall is off."""
    keys: Set[str] = set()
    for product in await catalogue(tenant_id):
        keys.update(product["assessment_keys"])
    return keys


async def accessible_assessments(tenant_id: str, user_id: str) -> Set[str]:
    """Assessments unlocked by the product *versions* the candidate actually bought."""
    if get_settings().free_access:
        return await all_assessment_keys(tenant_id)
    keys: Set[str] = set()
    ptype = get_type("products")
    for ent in await active_entitlements(tenant_id, user_id):
        product = await get_version(ptype, tenant_id, ent["product_key"], ent["product_version"])
        keys.update(product.data.get("assessment_keys") or [])
    return keys


async def require_assessment_access(tenant_id: str, user: User, assessment_key: str) -> None:
    if user.role == "admin" or get_settings().free_access:
        return
    if assessment_key in await accessible_assessments(tenant_id, user.id):
        return
    offering = [p["name"] for p in await catalogue(tenant_id) if assessment_key in p["assessment_keys"]]
    hint = f" — it's included in: {', '.join(offering)}" if offering else ""
    raise PaymentRequired(f"Purchase required to open this assessment{hint}")


# Phase 8/9: the detailed report + roadmap unlock (report_upgrade product).
async def owns_report_upgrade(tenant_id: str, user_id: str) -> bool:
    if get_settings().free_access:
        return True
    ptype = get_type("products")
    for ent in await active_entitlements(tenant_id, user_id):
        product = await get_version(ptype, tenant_id, ent["product_key"], ent["product_version"])
        if product.data.get("kind") == "report_upgrade":
            return True
    return False


async def require_report_access(tenant_id: str, user: User) -> None:
    if user.role == "admin" or await owns_report_upgrade(tenant_id, user.id):
        return
    raise PaymentRequired("The Detailed Report & Development Roadmap is a paid upgrade — buy it from the pricing page.")


async def start_checkout(tenant_id: str, user: User, product_key: str) -> dict:
    products = await published_products(tenant_id)
    product = products.get(product_key)
    if product is None:
        raise NotFound(f"No product '{product_key}' is on sale")
    owned = await owned_product_keys(tenant_id, user.id)
    if product_key in owned:
        raise Conflict("You already own this")
    if product["data"].get("kind") == "bundle" and set(product["data"].get("bundled_product_keys") or []) <= owned:
        raise Conflict("You already own everything in this bundle")
    requires = product["data"].get("requires_product_keys") or []
    if requires and not owned.intersection(requires):
        names = [products[k]["data"]["name"] for k in requires if k in products] or requires
        raise Conflict(f"Buy {' or '.join(names)} first")

    # Free access (FREE_ACCESS=true, any environment) or local/dev without Stripe: enrol for free
    # instead of failing checkout, so the app is fully usable end to end without payment keys.
    settings = get_settings()
    if settings.free_access or (not settings.payments_configured and settings.is_dev):
        return await _free_enroll(tenant_id, user, product_key, product)

    data = product["data"]
    currency = data["currency"].upper()
    payment = {
        "_id": new_id(),
        "tenant_id": tenant_id,
        "user_id": user.id,
        "product_key": product_key,
        "product_version": product["version"],
        "amount": data["price"],
        "amount_minor": to_minor(data["price"], currency),
        "currency": currency,
        "provider": "stripe",
        "status": "pending",
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    session = await gateway.create_checkout_session(
        payment_id=payment["_id"],
        product_name=data["name"],
        description=data.get("description"),
        amount_minor=payment["amount_minor"],
        currency=currency,
        customer_email=user.email,
        metadata={"payment_id": payment["_id"], "tenant_id": tenant_id, "user_id": user.id, "product_key": product_key},
    )
    payment["stripe_session_id"] = session["id"]
    await database.payments().insert_one(payment)
    await audit.record(
        tenant_id=tenant_id, actor_id=user.id, candidate_id=user.id, entity_type="payment", entity_id=payment["_id"],
        action="payment.checkout_started", metadata={"product_key": product_key, "amount": data["price"], "currency": currency},
    )
    return {"payment_id": payment["_id"], "checkout_url": session["url"]}


async def _free_enroll(tenant_id: str, user: User, product_key: str, product: dict) -> dict:
    """Grant a product (and its bundled products) immediately, no payment — dev-only convenience."""
    data = product["data"]
    now = utcnow()
    payment = {
        "_id": new_id(), "tenant_id": tenant_id, "user_id": user.id, "product_key": product_key,
        "product_version": product["version"], "amount": data["price"], "amount_minor": 0,
        "currency": data["currency"].upper(), "provider": "free", "status": "paid",
        "created_at": now, "updated_at": now, "paid_at": now,
    }
    await database.payments().insert_one(payment)
    await _grant(payment, product_key, product["version"], "free")
    current = await published_products(tenant_id)
    for key in data.get("bundled_product_keys") or []:
        if key in current:
            await _grant(payment, key, current[key]["version"], f"bundle:{product_key}")
    await audit.record(
        tenant_id=tenant_id, actor_id=user.id, candidate_id=user.id, entity_type="payment", entity_id=payment["_id"],
        action="payment.free_enrolled", metadata={"product_key": product_key},
    )
    return {"free": True, "checkout_url": None, "product_key": product_key}


async def _grant(payment: dict, product_key: str, product_version: int, source: str) -> bool:
    try:
        await database.entitlements().insert_one(
            {
                "_id": new_id(),
                "tenant_id": payment["tenant_id"],
                "user_id": payment["user_id"],
                "product_key": product_key,
                "product_version": product_version,
                "source": source,
                "payment_id": payment["_id"],
                "granted_at": utcnow(),
                "revoked_at": None,
            }
        )
    except DuplicateKeyError:
        return False  # already owned (e.g. bought separately before a bundle)
    await audit.record(
        tenant_id=payment["tenant_id"], actor_id="system", candidate_id=payment["user_id"], entity_type="entitlement",
        entity_id=product_key, action="entitlement.granted", metadata={"payment_id": payment["_id"], "source": source},
    )
    return True


async def fulfill(session: dict) -> Optional[dict]:
    """Mark the payment paid and grant entitlements — only for a paid session whose amount matches. Idempotent."""
    payment = await database.payments().find_one({"stripe_session_id": session.get("id")})
    if payment is None:
        return None
    if session.get("payment_status") != "paid":
        return payment
    if session.get("amount_total") != payment["amount_minor"] or (session.get("currency") or "").upper() != payment["currency"]:
        await database.payments().update_one({"_id": payment["_id"]}, {"$set": {"status": "amount_mismatch", "updated_at": utcnow()}})
        await audit.record(
            tenant_id=payment["tenant_id"], actor_id="system", candidate_id=payment["user_id"], entity_type="payment",
            entity_id=payment["_id"], action="payment.amount_mismatch",
            metadata={"expected": payment["amount_minor"], "got": session.get("amount_total"), "currency": session.get("currency")},
        )
        return await database.payments().find_one({"_id": payment["_id"]})
    now = utcnow()
    claimed = await database.payments().find_one_and_update(
        {"_id": payment["_id"], "status": {"$in": ["pending", "expired"]}},
        {"$set": {"status": "paid", "paid_at": now, "updated_at": now, "stripe_payment_intent": session.get("payment_intent")}},
    )
    if claimed is None:  # already fulfilled by the other path
        return await database.payments().find_one({"_id": payment["_id"]})
    await audit.record(
        tenant_id=payment["tenant_id"], actor_id="system", candidate_id=payment["user_id"], entity_type="payment",
        entity_id=payment["_id"], action="payment.paid", metadata={"product_key": payment["product_key"], "amount": payment["amount"]},
    )
    await _grant(payment, payment["product_key"], payment["product_version"], "stripe")
    # Bundles also grant each bundled product (at its current published version).
    product = await get_version(get_type("products"), payment["tenant_id"], payment["product_key"], payment["product_version"])
    current = await published_products(payment["tenant_id"])
    for key in product.data.get("bundled_product_keys") or []:
        if key in current:
            await _grant(payment, key, current[key]["version"], f"bundle:{payment['product_key']}")
    return await database.payments().find_one({"_id": payment["_id"]})


async def confirm(tenant_id: str, user: User, session_id: str) -> dict:
    """Success page: verify the session with Stripe (works even when webhooks can't reach this machine)."""
    payment = await database.payments().find_one({"stripe_session_id": session_id, "tenant_id": tenant_id})
    if payment is None or payment["user_id"] != user.id:
        raise NotFound("Payment not found")
    if payment["status"] != "paid":
        try:
            session = await gateway.retrieve_checkout_session(session_id)
        except LookupError:
            raise NotFound("Payment not found")
        payment = await fulfill(session) or payment
    return payment_out(payment)


async def handle_event(event: dict) -> str:
    kind = event.get("type")
    session = (event.get("data") or {}).get("object") or {}
    if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        await fulfill(session)
    elif kind in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        status = "expired" if kind.endswith("expired") else "failed"
        await database.payments().update_one(
            {"stripe_session_id": session.get("id"), "status": "pending"}, {"$set": {"status": status, "updated_at": utcnow()}}
        )
    return kind or "unknown"


def payment_out(p: dict) -> dict:
    return {k: p.get(k) for k in ("product_key", "product_version", "amount", "currency", "status", "created_at", "paid_at")} | {"id": p["_id"]}
