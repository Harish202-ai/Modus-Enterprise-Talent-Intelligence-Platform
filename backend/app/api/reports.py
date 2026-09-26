"""Report + AI Explainer API (plan v3/v5 Phase 8).

- Summary of Findings — any candidate who has submitted a paid assessment.
- Detailed Report — gated by the report_upgrade entitlement (402 otherwise).
- Explainer chat — grounded strictly in the candidate's own locked results; "why" mode on the report,
  "coach" mode on the roadmap.
- Voice capability — tells the frontend whether to offer the browser mic / speaker (Web Speech API).
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.ai import explainer, voice_provider
from app.api.deps import require_role, require_tenant_scope
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reports

router = APIRouter(tags=["reports & explainer"])
candidate = require_role(["candidate"])


class ExplainerIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    mode: str = Field(default="why", pattern="^(why|coach)$")


@router.get("/me/report")
async def my_summary(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return {"report": await reports.summary(tenant.id, user)}


@router.get("/me/report/detailed")
async def my_detailed_report(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return {"report": await reports.detailed(tenant.id, user)}


@router.post("/me/explainer")
async def ask_explainer(body: ExplainerIn, user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    snapshot = await reports.context_snapshot(tenant.id, user)
    context_text = reports.snapshot_to_text(snapshot)
    roadmap_text: Optional[str] = None
    if body.mode == "coach":
        try:
            from app.services import roadmap  # roadmap module (Phase 9)

            roadmap_text = await roadmap.roadmap_text(tenant.id, user)
        except ImportError:
            roadmap_text = None
    return await explainer.answer(tenant.id, body.question, context_text, mode=body.mode, roadmap_text=roadmap_text)


@router.get("/me/voice")
async def voice_capability(user: User = Depends(candidate), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    return voice_provider.capability()
