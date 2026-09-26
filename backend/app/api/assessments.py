"""Read-only view of published assessments, resolved exactly as they were published.

Candidates need a paid entitlement that includes the assessment and only ever get the sanitised
questions (no correct answers, scoring maps or rubrics); admins get the full definition to preview.
Each published version pins the versions of what it references, so republishing a question never
changes an already-published assessment.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_tenant_scope
from app.content.registry import get_type
from app.models.content import ContentVersion
from app.models.tenant import Tenant
from app.models.user import User
from app.services import attempts, commerce, content

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _full(item: ContentVersion) -> dict:
    return {"key": item.key, "version": item.version, "published_at": item.published_at, **item.data}


@router.get("/{code}")
async def get_assessment(code: str, user: User = Depends(get_current_user), tenant: Tenant = Depends(require_tenant_scope)) -> dict:
    await commerce.require_assessment_access(tenant.id, user, code)  # 402 for candidates who haven't bought it
    current = await content.get_current(get_type("assessments"), tenant.id, code)
    defn = await attempts.load_definition(tenant.id, code, current.version)
    if user.role != "admin":
        return attempts.public_definition(defn)
    return {
        **_full(defn["assessment"]),
        "sections": [{**_full(s["section"]), "questions": [_full(q) for q in s["questions"]]} for s in defn["sections"]],
    }
