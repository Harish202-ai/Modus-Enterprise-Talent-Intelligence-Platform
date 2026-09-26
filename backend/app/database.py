"""MongoDB access (Motor) + index bootstrap.

Every collection name lives in `Collections`; every index lives in `INDEXES`.
Later phases register their collections here so one bootstrap call keeps the
whole database consistent.
"""
import logging
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.config import get_settings
from app.content.registry import CONTENT_TYPES

log = logging.getLogger(__name__)


class Collections:
    TENANTS = "tenants"
    USERS = "users"
    AUDIT_EVENTS = "audit_events"
    AUTH_SESSIONS = "auth_sessions"
    PAYMENTS = "payments"
    ENTITLEMENTS = "entitlements"
    ATTEMPTS = "attempts"
    FILES = "files"
    EVIDENCE_CLAIMS = "evidence_claims"
    SCORES = "scores"
    ROADMAPS = "roadmaps"
    INTERVIEWS = "interviews"
    # Versioned content collections (Phase 1) are listed in app.content.registry.


def _content_indexes() -> List[IndexModel]:
    return [
        IndexModel([("tenant_id", ASCENDING), ("key", ASCENDING), ("version", ASCENDING)], unique=True, name="uq_tenant_key_version"),
        # One open draft per key.
        IndexModel(
            [("tenant_id", ASCENDING), ("key", ASCENDING)],
            unique=True,
            partialFilterExpression={"status": "draft"},
            name="uq_tenant_key_draft",
        ),
        IndexModel([("tenant_id", ASCENDING), ("status", ASCENDING), ("key", ASCENDING)], name="ix_tenant_status_key"),
    ]


# tenant_id leads every tenant-scoped index so tenant isolation stays cheap.
INDEXES: Dict[str, List[IndexModel]] = {
    Collections.TENANTS: [
        IndexModel([("slug", ASCENDING)], unique=True, name="uq_slug"),
        IndexModel([("status", ASCENDING)], name="ix_status"),
    ],
    Collections.USERS: [
        IndexModel([("tenant_id", ASCENDING), ("email", ASCENDING)], unique=True, name="uq_tenant_email"),
        IndexModel([("tenant_id", ASCENDING), ("role", ASCENDING)], name="ix_tenant_role"),
    ],
    Collections.AUDIT_EVENTS: [
        IndexModel([("tenant_id", ASCENDING), ("timestamp", DESCENDING)], name="ix_tenant_time"),
        IndexModel([("tenant_id", ASCENDING), ("entity_type", ASCENDING), ("entity_id", ASCENDING)], name="ix_tenant_entity"),
        IndexModel([("actor_id", ASCENDING), ("timestamp", DESCENDING)], name="ix_actor_time"),
    ],
    # Phase 2. Expired sessions are removed by Mongo TTL (expireAfterSeconds=0 -> at expires_at).
    Collections.AUTH_SESSIONS: [
        IndexModel([("user_id", ASCENDING), ("revoked_at", ASCENDING)], name="ix_user_revoked"),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expires_at"),
    ],
    # Phase 4
    Collections.PAYMENTS: [
        IndexModel([("stripe_session_id", ASCENDING)], unique=True, sparse=True, name="uq_stripe_session"),
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_tenant_user_time"),
    ],
    Collections.ENTITLEMENTS: [
        # One entitlement per product per user — makes fulfilment idempotent.
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("product_key", ASCENDING)], unique=True, name="uq_tenant_user_product"),
    ],
    # Phase 5 — one in-progress attempt per candidate per assessment.
    Collections.ATTEMPTS: [
        IndexModel(
            [("tenant_id", ASCENDING), ("user_id", ASCENDING), ("assessment_key", ASCENDING)],
            unique=True,
            partialFilterExpression={"status": "in_progress"},
            name="uq_open_attempt",
        ),
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("started_at", DESCENDING)], name="ix_tenant_user_started"),
    ],
    Collections.FILES: [IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_tenant_user_time")],
    # Phase 5b — structured claims parsed from the resume (self-reported evidence).
    Collections.EVIDENCE_CLAIMS: [
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_tenant_user_time"),
    ],
    # Phase 6 — one deterministic score document per attempt (upserted, so recompute is idempotent).
    Collections.SCORES: [
        IndexModel([("tenant_id", ASCENDING), ("attempt_id", ASCENDING)], unique=True, name="uq_tenant_attempt"),
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("area", ASCENDING), ("computed_at", DESCENDING)], name="ix_tenant_user_area"),
    ],
    # Phase 9 — one current roadmap per candidate (regenerated after a reassessment).
    Collections.ROADMAPS: [
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="uq_tenant_user"),
    ],
    # v5 — AI video interview submissions (one per recording), newest first.
    Collections.INTERVIEWS: [
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_tenant_user_time"),
    ],
    **{name: _content_indexes() for name in CONTENT_TYPES},
}

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        kwargs = dict(serverSelectionTimeoutMS=5000, tz_aware=True)
        # Use certifi's CA bundle for the TLS handshake to Atlas. Without this, some
        # container/cloud hosts (e.g. slim images) fail with SSL CERTIFICATE_VERIFY_FAILED
        # even though the same URI connects fine locally — surfacing as "mongo: down".
        if settings.mongo_uri.startswith("mongodb+srv://") or "tls=true" in settings.mongo_uri.lower() or "ssl=true" in settings.mongo_uri.lower():
            try:
                import certifi

                kwargs["tlsCAFile"] = certifi.where()
            except Exception:  # noqa: BLE001 - certifi missing shouldn't block startup
                pass
        _client = AsyncIOMotorClient(settings.mongo_uri, **kwargs)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongo_db]


def collection(name: str) -> AsyncIOMotorCollection:
    return get_db()[name]


def tenants() -> AsyncIOMotorCollection:
    return collection(Collections.TENANTS)


def users() -> AsyncIOMotorCollection:
    return collection(Collections.USERS)


def audit_events() -> AsyncIOMotorCollection:
    return collection(Collections.AUDIT_EVENTS)


def auth_sessions() -> AsyncIOMotorCollection:
    return collection(Collections.AUTH_SESSIONS)


def payments() -> AsyncIOMotorCollection:
    return collection(Collections.PAYMENTS)


def entitlements() -> AsyncIOMotorCollection:
    return collection(Collections.ENTITLEMENTS)


def attempts() -> AsyncIOMotorCollection:
    return collection(Collections.ATTEMPTS)


def files() -> AsyncIOMotorCollection:
    return collection(Collections.FILES)


def evidence_claims() -> AsyncIOMotorCollection:
    return collection(Collections.EVIDENCE_CLAIMS)


def scores() -> AsyncIOMotorCollection:
    return collection(Collections.SCORES)


def roadmaps() -> AsyncIOMotorCollection:
    return collection(Collections.ROADMAPS)


def interviews() -> AsyncIOMotorCollection:
    return collection(Collections.INTERVIEWS)



async def ensure_indexes() -> Dict[str, List[str]]:
    """Create every collection + index in INDEXES. Idempotent."""
    db = get_db()
    existing = set(await db.list_collection_names())
    created: Dict[str, List[str]] = {}
    for name, models in INDEXES.items():
        if name not in existing:
            await db.create_collection(name)
        created[name] = await db[name].create_indexes(models)
    log.info("indexes ensured", extra={"collections": list(created)})
    return created


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:  # noqa: BLE001 - health check must never raise
        log.exception("mongo ping failed")
        return False


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
