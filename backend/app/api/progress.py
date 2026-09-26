"""Reassessment & Progress API (plan v5 Phase 13). Retaking uses the normal start endpoint; this
exposes the before/after comparison."""
from fastapi import APIRouter, Depends, Path

from app.api.deps import require_role, require_tenant_scope
from app.models.content import KEY_PATTERN
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reassessment

router = APIRouter(tags=["progress"])
candidate = require_role(["candidate"])


@router.get("/me/progress")
async def my_progress(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """Which assessments the candidate has submitted, and which can show a before/after."""
    return {"progress": await reassessment.overview(tenant.id, user)}


@router.get("/me/progress/{assessment_key}")
async def compare(
    assessment_key: str = Path(pattern=KEY_PATTERN),
    user: User = Depends(candidate),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    """Before/after of the two most recent submitted attempts of one assessment, per competency."""
    return await reassessment.compare(tenant.id, user, assessment_key)
