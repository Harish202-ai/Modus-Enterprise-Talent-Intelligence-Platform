"""Give a candidate a product without payment (sponsored / complimentary access). Audited.

    python -m scripts.grant_product --email candidate@example.com --product bundle

Grants the product at its current published version (and each bundled product), exactly as a
paid purchase would, but with source "admin_grant" and no payment record.
"""
import argparse
import asyncio

from app import database
from app.config import get_settings
from app.models.common import new_id, utcnow
from app.services import audit, commerce
from app.services.tenants import get_by_slug


async def main(email: str, product_key: str) -> None:
    tenant = await get_by_slug(get_settings().default_tenant_slug)
    user = await database.users().find_one({"tenant_id": tenant.id, "email": email.strip().lower()})
    if not user or user.get("role", "candidate") != "candidate":
        raise SystemExit(f"No candidate account for {email}")
    products = await commerce.published_products(tenant.id)
    if product_key not in products:
        raise SystemExit(f"No published product '{product_key}'. Available: {', '.join(products)}")
    keys = [product_key] + list(products[product_key]["data"].get("bundled_product_keys") or [])
    for key in keys:
        if key not in products:
            continue
        if await database.entitlements().find_one({"tenant_id": tenant.id, "user_id": user["_id"], "product_key": key}):
            print(f"  {key}: already owned")
            continue
        await database.entitlements().insert_one(
            {
                "_id": new_id(), "tenant_id": tenant.id, "user_id": user["_id"], "product_key": key,
                "product_version": products[key]["version"], "source": "admin_grant", "payment_id": None,
                "granted_at": utcnow(), "revoked_at": None,
            }
        )
        await audit.record(
            tenant_id=tenant.id, actor_id="system", candidate_id=user["_id"], entity_type="entitlement",
            entity_id=key, action="entitlement.granted", metadata={"source": "admin_grant"},
        )
        print(f"  {key}: granted")
    database.close_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--product", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.email, args.product))
