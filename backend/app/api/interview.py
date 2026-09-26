"""AI video interview API (plan v5). Candidate records; admin reviews via the candidate dashboard."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import require_role, require_tenant_scope
from app.models.tenant import Tenant
from app.models.user import User
from app.services import interview

router = APIRouter(tags=["video interview"])
candidate = require_role(["candidate"])


@router.get("/me/interview")
async def interview_config(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """The timed questions to ask and the proctoring config (max warnings before auto-submit)."""
    return await interview.config(tenant.id, user)


@router.get("/me/interview/latest")
async def my_latest_interview(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return {"interview": await interview.latest(tenant.id, user.id)}


@router.post("/me/interview")
async def submit_interview(
    file: UploadFile = File(...),
    warnings: int = Form(0),
    auto_submitted: bool = Form(False),
    answered: int = Form(0),
    duration_seconds: Optional[int] = Form(None),
    user: User = Depends(candidate),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    """Upload the recording plus its proctoring metadata (warnings, whether it auto-submitted)."""
    return await interview.submit(tenant.id, user, file, warnings, auto_submitted, answered, duration_seconds)
