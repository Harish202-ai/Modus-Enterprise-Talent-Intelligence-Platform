"""Site-wide support chatbot API (plan v4 Phase 10). PUBLIC — no auth, and by construction no access
to any candidate data: it only ever reads the published support_kb help content."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import current_tenant
from app.models.tenant import Tenant
from app.services import support_kb

router = APIRouter(tags=["support chatbot"])


class SupportIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.post("/support/chat")
async def support_chat(body: SupportIn, tenant: Tenant = Depends(current_tenant)) -> dict:
    """Answer a general platform question from public help content only (grounded, never guesses)."""
    return await support_kb.answer(tenant.id, body.question)
