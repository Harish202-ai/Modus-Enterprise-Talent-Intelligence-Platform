"""Score read API (plan v2/v3 Phase 6 deterministic · plan v5 Phase 7 AI).

Read-only for the candidate: their Talent DNA, Values (MRAT-centred) and Consulting Capability
profiles computed in code, plus the AI-scored Written Communication and Case Study responses
(Reasoning / Knowledge / Communication with cited evidence). Deterministic scores are produced at
submit time and back-filled on read; AI scores are produced on submit (or by an explicit rescore).
The composite scores and the report/explainer arrive in Phase 8.
"""
from fastapi import APIRouter, Depends, Path

from app.api.deps import require_role, require_tenant_scope
from app.models.content import KEY_PATTERN
from app.models.tenant import Tenant
from app.models.user import User
from app.services import ai_scoring, scoring_rules

router = APIRouter(tags=["scores"])
candidate = require_role(["candidate"])


@router.get("/me/scores")
async def my_scores(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    """All of the candidate's scores by area: deterministic (`talent_dna`, `values`, `capability`)
    and AI (`written_communication`, `case_study`). Each is `{status: 'not_submitted'}` until done,
    and an AI area is `{status: 'pending'}` while its scoring is still running."""
    deterministic = await scoring_rules.scores_for_user(tenant.id, user)
    ai = await ai_scoring.ai_scores_for_user(tenant.id, user.id)
    return {"scores": {**deterministic, **ai}}


@router.post("/me/scores/{assessment_key}/rescore")
async def rescore(
    assessment_key: str = Path(pattern=KEY_PATTERN),
    user: User = Depends(candidate),
    tenant: Tenant = Depends(require_tenant_scope),
) -> dict:
    """Re-run AI scoring for the candidate's latest submitted memo / case attempt (e.g. after a
    provider outage left it `pending`)."""
    return await ai_scoring.rescore(tenant.id, user.id, assessment_key)
