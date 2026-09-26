"""Admin score governance API (plan v2 Phase 9 / v5 Phase 11). Admin role only."""
from fastapi import APIRouter, Depends, Path

from app.api.deps import require_role, require_tenant_scope
from app.models.content import KEY_PATTERN
from app.models.tenant import Tenant
from app.models.user import User
from app.services import admin_scores

router = APIRouter(tags=["admin scores"], prefix="/admin/scores")
admin = require_role(["admin"])


@router.get("/review")
async def review_queue(user: User = Depends(admin), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """AI-scored responses that need a human look (needs_review / pending / partial)."""
    return {"queue": await admin_scores.review_queue(tenant.id)}


@router.get("/{attempt_id}")
async def get_scored(attempt_id: str, user: User = Depends(admin), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await admin_scores.get_scored_attempt(tenant.id, attempt_id)


@router.post("/{attempt_id}/responses/{question_key}/override")
async def override(
    body: admin_scores.Override,
    attempt_id: str,
    question_key: str = Path(pattern=KEY_PATTERN),
    user: User = Depends(admin),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    """Replace one response's dimension scores with the admin's, with a required reason (audited)."""
    return await admin_scores.override_response(tenant.id, user.id, attempt_id, question_key, body)


@router.post("/{attempt_id}/approve")
async def approve(attempt_id: str, user: User = Depends(admin), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await admin_scores.approve_attempt(tenant.id, user.id, attempt_id)
