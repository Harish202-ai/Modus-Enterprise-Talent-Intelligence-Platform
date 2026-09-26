"""Phase 11 — Admin score governance (plan v2 Phase 9, light governance, single admin role).

No separate reviewer sub-app: just a review queue of AI-scored responses and a per-response override
with a required reason. Overriding replaces a response's dimension scores in place, marks it
`overridden`, and records who did it and why (audited). Approving a whole attempt marks it reviewed.
Deterministic scores aren't overridable — they're reproducible by definition; only AI scores are.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app import database
from app.models.common import utcnow
from app.services import audit
from app.services.content import NotFound


class Override(BaseModel):
    reasoning_score: int = Field(ge=0, le=100)
    knowledge_score: int = Field(ge=0, le=100)
    communication_score: int = Field(ge=0, le=100)
    overall_confidence: int = Field(ge=0, le=100)
    reason: str = Field(min_length=3, max_length=1000)


async def _candidate_email(tenant_id: str, user_id: str) -> Optional[str]:
    u = await database.users().find_one({"_id": user_id, "tenant_id": tenant_id}, {"email": 1})
    return u["email"] if u else None


async def review_queue(tenant_id: str, only_pending: bool = False) -> List[dict]:
    """AI score documents, newest first. Every row carries `needs_review` so the UI can split
    'needs a human look' from 'already marked by AI'. `only_pending=True` returns just the former."""
    query: Dict = {"tenant_id": tenant_id, "method": "ai"}
    rows = await database.scores().find(query).sort("computed_at", -1).to_list(None)
    out: List[dict] = []
    for row in rows:
        responses = (row.get("result") or {}).get("responses") or []
        overall = (row.get("result") or {}).get("status")
        needs = any(r.get("status") in ("needs_review", "pending", "partial") for r in responses) or overall in ("needs_review", "pending", "partial")
        if only_pending and not needs:
            continue
        out.append({
            "attempt_id": row["attempt_id"],
            "assessment_key": row["assessment_key"],
            "candidate_email": await _candidate_email(tenant_id, row["user_id"]),
            "status": overall,
            "needs_review": needs,
            "model": row.get("model"),
            "computed_at": row.get("computed_at"),
            "responses": responses,
        })
    return out


async def get_scored_attempt(tenant_id: str, attempt_id: str) -> dict:
    row = await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt_id, "method": "ai"})
    if row is None:
        raise NotFound("No AI score for that attempt")
    return {
        "attempt_id": row["attempt_id"],
        "assessment_key": row["assessment_key"],
        "candidate_email": await _candidate_email(tenant_id, row["user_id"]),
        "result": row.get("result"),
        "model": row.get("model"),
    }


async def override_response(tenant_id: str, admin_id: str, attempt_id: str, question_key: str, override: Override) -> dict:
    """Replace one response's dimension scores with an admin's, keeping the evidence, and audit it."""
    row = await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt_id, "method": "ai"})
    if row is None:
        raise NotFound("No AI score for that attempt")
    responses = (row.get("result") or {}).get("responses") or []
    target = next((r for r in responses if r.get("question_key") == question_key), None)
    if target is None:
        raise NotFound(f"Response '{question_key}' not found on that attempt")

    existing = target.get("scores") or {}
    target["scores"] = {
        "reasoning_score": override.reasoning_score,
        "reasoning_evidence": existing.get("reasoning_evidence", ""),
        "knowledge_score": override.knowledge_score,
        "knowledge_evidence": existing.get("knowledge_evidence", ""),
        "communication_score": override.communication_score,
        "communication_evidence": existing.get("communication_evidence", ""),
        "overall_confidence": override.overall_confidence,
    }
    target["status"] = "overridden"
    target["override"] = {"by": admin_id, "reason": override.reason, "at": utcnow()}

    result = row["result"]
    result["responses"] = responses
    statuses = {r["status"] for r in responses}
    result["status"] = "scored" if statuses <= {"scored", "overridden"} else next(iter(statuses)) if len(statuses) == 1 else "partial"
    await database.scores().update_one({"_id": row["_id"]}, {"$set": {"result": result, "updated_at": utcnow()}})
    await audit.record(
        tenant_id=tenant_id, actor_id=admin_id, candidate_id=row["user_id"], entity_type="score", entity_id=attempt_id,
        action="score.overridden", metadata={"question_key": question_key, "reason": override.reason},
    )
    return await get_scored_attempt(tenant_id, attempt_id)


async def approve_attempt(tenant_id: str, admin_id: str, attempt_id: str) -> dict:
    row = await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt_id, "method": "ai"})
    if row is None:
        raise NotFound("No AI score for that attempt")
    await database.scores().update_one(
        {"_id": row["_id"]}, {"$set": {"reviewed_by": admin_id, "reviewed_at": utcnow(), "updated_at": utcnow()}}
    )
    await audit.record(
        tenant_id=tenant_id, actor_id=admin_id, candidate_id=row["user_id"], entity_type="score", entity_id=attempt_id,
        action="score.approved", metadata={"assessment_key": row["assessment_key"]},
    )
    return await get_scored_attempt(tenant_id, attempt_id)
