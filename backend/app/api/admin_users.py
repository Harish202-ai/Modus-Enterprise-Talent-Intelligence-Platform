"""Admin candidate dashboard API (plan v5 Phase 11). Admin role only."""
from fastapi import APIRouter, Depends

from app.api.deps import require_role, require_tenant_scope
from app.models.tenant import Tenant
from app.models.user import User
from app.services import admin_users

router = APIRouter(prefix="/admin/candidates", tags=["admin: candidates"])
admin = require_role(["admin"])


@router.get("")
async def list_candidates(user: User = Depends(admin), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return {"candidates": await admin_users.list_candidates(tenant.id)}


@router.get("/{user_id}")
async def candidate_detail(user_id: str, user: User = Depends(admin), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await admin_users.candidate_detail(tenant.id, user_id)
