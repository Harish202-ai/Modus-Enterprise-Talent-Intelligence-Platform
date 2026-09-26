"""Assessment engine API (candidate)."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import require_role, require_tenant_scope
from app.models.content import KEY_PATTERN
from app.models.tenant import Tenant
from app.models.user import User
from app.services import ai_scoring, attempts, profile_ai, roadmap

router = APIRouter(tags=["assessment engine"])
candidate = require_role(["candidate"])


class AnswersIn(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict, max_length=200)
    current_section_key: Optional[str] = Field(None, pattern=KEY_PATTERN)


class SubmitIn(BaseModel):
    # Questions the candidate explicitly skipped (the exam "Skip" button). Optional/back-compatible.
    skipped: list[str] = Field(default_factory=list, max_length=200)


@router.get("/me/assessments")
async def my_assessments(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> list:
    return await attempts.my_assessments(tenant.id, user)


@router.post("/assessments/{code}/attempts")
async def start(code: str, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """Start the assessment, or resume the open attempt (any device)."""
    return await attempts.start_or_resume(tenant.id, user, code)


@router.get("/attempts/{attempt_id}")
async def get(attempt_id: str, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await attempts.get_attempt(tenant.id, user, attempt_id)


@router.put("/attempts/{attempt_id}/answers")
async def autosave(attempt_id: str, body: AnswersIn, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return await attempts.save_answers(tenant.id, user, attempt_id, body.answers, body.current_section_key)


@router.post("/attempts/{attempt_id}/submit")
async def submit(
    attempt_id: str,
    background: BackgroundTasks,
    body: SubmitIn | None = None,
    user: User = Depends(candidate),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    result = await attempts.submit(tenant.id, user, attempt_id, (body.skipped if body else None))
    # Deterministic forms are scored inline on submit; AI-scored forms (memo, case) are slow, so
    # they run in the background — the candidate's Results page shows "pending" until they land.
    if result["assessment_key"] in ai_scoring.AI_SCORED_ASSESSMENTS:
        background.add_task(ai_scoring.run_for_attempt, tenant.id, attempt_id)
    # Phase 13: if the candidate already has a roadmap, a reassessment refreshes it to the new gaps.
    background.add_task(roadmap.regenerate_if_exists, tenant.id, user)
    return result


@router.post("/attempts/{attempt_id}/files")
async def upload_file(
    attempt_id: str,
    background: BackgroundTasks,
    question_key: str = Query(pattern=KEY_PATTERN),
    file: UploadFile = File(...),
    user: User = Depends(candidate),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    """Upload a file as a question's answer (resume, case document, communication video)."""
    result = await attempts.upload_answer_file(tenant.id, user, attempt_id, question_key, file)
    if result["resume_claim"]:
        background.add_task(profile_ai.run, tenant.id, result["resume_claim"]["id"])
    return result
