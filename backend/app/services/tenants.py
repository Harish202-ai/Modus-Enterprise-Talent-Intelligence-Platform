from typing import Optional, Tuple

from pymongo.errors import DuplicateKeyError

from app import database
from app.models.tenant import Tenant, TenantCreate
from app.services import audit


async def get_by_slug(slug: str) -> Optional[Tenant]:
    doc = await database.tenants().find_one({"slug": slug})
    return Tenant.model_validate(doc) if doc else None


async def create_tenant(data: TenantCreate, actor_id: str = "system") -> Tuple[Tenant, bool]:
    """Create a tenant. Returns (tenant, created); idempotent on slug."""
    existing = await get_by_slug(data.slug)
    if existing:
        return existing, False

    tenant = Tenant(slug=data.slug, name=data.name)
    try:
        await database.tenants().insert_one(tenant.to_mongo())
    except DuplicateKeyError:  # created concurrently
        return await get_by_slug(data.slug), False

    await audit.record(
        tenant_id=tenant.id,
        actor_id=actor_id,
        entity_type="tenant",
        entity_id=tenant.id,
        action="tenant.created",
        metadata={"slug": tenant.slug, "name": tenant.name},
    )
    return tenant, True
