"""Development Roadmap API (plan v3/v5 Phase 9). Gated by the report_upgrade entitlement."""
from fastapi import APIRouter, Depends

from app.api.deps import require_role, require_tenant_scope
from app.models.tenant import Tenant
from app.models.user import User
from app.services import roadmap

router = APIRouter(tags=["roadmap"])
candidate = require_role(["candidate"])


@router.get("/me/roadmap")
async def my_roadmap(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """The candidate's development roadmap (generated on first read from their current results)."""
    return {"roadmap": await roadmap.get(tenant.id, user)}


@router.post("/me/roadmap/regenerate")
async def regenerate(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """Rebuild the roadmap from the latest results (e.g. after a reassessment)."""
    return {"roadmap": roadmap._public(await roadmap.generate(tenant.id, user))}
