from fastapi import APIRouter, Depends
from pymongo import ReturnDocument

from app import database
from app.api.deps import require_role, require_tenant_scope
from app.models.common import utcnow
from app.models.tenant import Tenant
from app.models.user import OrientationIn, ProfileUpdate, User
from app.services import audit, orientation

router = APIRouter(prefix="/candidates", tags=["candidates"])

candidate = require_role(["candidate"])


def _out(user: User, tenant: Tenant) -> dict:
    return {**user.public(), "tenant": {"slug": tenant.slug, "name": tenant.name}}


@router.get("/me")
async def get_me(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return _out(user, tenant)


@router.put("/me")
async def update_me(body: ProfileUpdate, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    changes = body.model_dump(exclude_none=True)
    if changes:
        doc = await database.users().find_one_and_update(
            {"_id": user.id, "tenant_id": tenant.id},
            {"$set": {**changes, "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        user = User.model_validate(doc)
        await audit.record(
            tenant_id=tenant.id, actor_id=user.id, entity_type="user", entity_id=user.id,
            action="user.profile_updated", metadata={"fields": sorted(changes)},
        )
    return _out(user, tenant)


@router.post("/me/orientation")
async def mark_video_watched(body: OrientationIn, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """Simple "mark as watched" for the explainer video (plan v2 Phase 3)."""
    record = await orientation.mark_watched(tenant.id, user.id, body)
    return _out(user.model_copy(update={"orientation": record}), tenant)
