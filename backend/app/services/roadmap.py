"""Phase 9 — Development Roadmap (plan v3/v5).

A roadmap is generated from the candidate's own composite score and gap analysis (`reports`), not
from static copy: each development theme becomes a milestone with concrete actions and a suggested
resource, plus a couple of consolidation milestones from their strengths. It's gated by the
report_upgrade entitlement (same commercial line as the Detailed Report) and stored one-per-candidate,
regenerated after a reassessment (Phase 13). The Coach-mode Explainer grounds on `roadmap_text`.
"""
from typing import Dict, List, Optional

from app.models.common import new_id, utcnow
from app.models.user import User
from app.services import commerce, reports
from app.services.content import NotFound
from app import database

# Deterministic action templates per assessment area — concrete, MVP-sized.
_ACTIONS = {
    "capability": [
        "Work two consulting cases a week, writing the issue tree before any analysis.",
        "Review the frameworks behind the questions you missed (MECE, value chain, TOM, benefits realisation).",
    ],
    "written_communication": [
        "Draft one answer-first executive memo a week; cut it by 20% on the second pass.",
        "Get feedback on structure: recommendation → three supports → one risk with a mitigation.",
    ],
    "case_study": [
        "Practise structuring an ambiguous case end to end: question, hypotheses, prioritised analyses, recommendation.",
        "Compare at least two options every time and state how you'd measure success.",
    ],
    "talent_dna": [
        "Deliberately practise the working style this dimension reflects on a real task this week.",
    ],
}
_RESOURCES = {
    "capability": {"type": "reading", "title": "Consulting problem-solving frameworks refresher"},
    "written_communication": {"type": "exercise", "title": "Executive memo structure — worked examples"},
    "case_study": {"type": "exercise", "title": "Case interview structuring drills"},
    "talent_dna": {"type": "reflection", "title": "Applying your working-style strengths on the job"},
}
_DEFAULT_ACTIONS = ["Set one specific, measurable goal for this area and review progress weekly."]


def _milestones(snapshot: dict) -> List[dict]:
    themes = snapshot["development_themes"]
    strengths = snapshot["strengths"]
    milestones: List[dict] = []
    week = 1
    for theme in themes[:5]:
        area = theme["area"]
        milestones.append({
            "week": week,
            "title": f"Develop: {theme['label']}",
            "focus": theme["detail"],
            "actions": _ACTIONS.get(area, _DEFAULT_ACTIONS),
            "resource": _RESOURCES.get(area, {"type": "reading", "title": f"{theme['label']} — development resource"}),
        })
        week += 2
    # Consolidate a top strength so the roadmap isn't only deficits.
    if strengths:
        s = strengths[0]
        milestones.append({
            "week": week,
            "title": f"Consolidate: {s['label']}",
            "focus": f"Turn a strength into a differentiator. {s['detail']}",
            "actions": ["Take on a task that stretches this strength and mentor a peer in it."],
            "resource": {"type": "stretch", "title": f"Lead with {s['label']}"},
        })
    return milestones


def _weakest_area(snapshot: dict) -> Optional[str]:
    themes = snapshot["development_themes"]
    return themes[0]["label"] if themes else None


async def generate(tenant_id: str, user: User) -> dict:
    """Build + persist the candidate's roadmap from their current results (idempotent upsert)."""
    await commerce.require_report_access(tenant_id, user)
    snapshot = await reports.context_snapshot(tenant_id, user)
    milestones = _milestones(snapshot)
    weakest = _weakest_area(snapshot)
    now = utcnow()
    doc = {
        "tenant_id": tenant_id,
        "user_id": user.id,
        "readiness": snapshot["composite"]["readiness"],
        "milestones": milestones,
        "reassessment_schedule": (
            f"Retake the assessment covering {weakest} in about 8 weeks to see your progress." if weakest
            else "Retake your assessments in about 8 weeks to see your progress."
        ),
        "generated_at": now,
        "updated_at": now,
    }
    await database.roadmaps().update_one(
        {"tenant_id": tenant_id, "user_id": user.id},
        {"$set": doc, "$setOnInsert": {"_id": new_id(), "created_at": now}},
        upsert=True,
    )
    return await database.roadmaps().find_one({"tenant_id": tenant_id, "user_id": user.id})


async def get(tenant_id: str, user: User, create: bool = True) -> Optional[dict]:
    """The candidate's roadmap, generating it on first read. Raises 402 without the upgrade."""
    await commerce.require_report_access(tenant_id, user)
    doc = await database.roadmaps().find_one({"tenant_id": tenant_id, "user_id": user.id})
    if doc is None and create:
        doc = await generate(tenant_id, user)
    return _public(doc) if doc else None


def _public(doc: dict) -> dict:
    return {
        "readiness": doc.get("readiness"),
        "milestones": doc.get("milestones") or [],
        "reassessment_schedule": doc.get("reassessment_schedule"),
        "generated_at": doc.get("generated_at"),
    }


async def roadmap_text(tenant_id: str, user: User) -> Optional[str]:
    """Compact text of the roadmap for grounding the Coach-mode Explainer (None if not unlocked)."""
    try:
        doc = await database.roadmaps().find_one({"tenant_id": tenant_id, "user_id": user.id})
        if doc is None and await commerce.owns_report_upgrade(tenant_id, user.id):
            doc = await generate(tenant_id, user)
    except NotFound:
        return None
    if not doc:
        return None
    lines = [doc.get("reassessment_schedule", "")]
    for m in doc.get("milestones") or []:
        lines.append(f"Week {m['week']}: {m['title']} — {m['focus']} Actions: {'; '.join(m['actions'])}")
    return "\n".join(l for l in lines if l)


async def regenerate_if_exists(tenant_id: str, user: User) -> None:
    """After a reassessment (Phase 13): refresh an existing roadmap to the new gaps. Best-effort."""
    if await database.roadmaps().find_one({"tenant_id": tenant_id, "user_id": user.id}):
        try:
            await generate(tenant_id, user)
        except commerce.PaymentRequired:
            pass
