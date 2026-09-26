"""Phase 13 — Reassessment & Progress (plan v5, restored).

Retaking is already possible by construction: once an attempt is submitted it's no longer the open
attempt, so starting the assessment again creates a fresh, independently-versioned attempt (the prior
one is immutable and kept). This module adds the **progress view**: a simple before/after of the two
most recent submitted attempts of an assessment, per competency / dimension — not a trend dashboard.
The roadmap regenerates after a reassessment (wired in the submit flow).
"""
from typing import Dict, List, Optional

from app import database
from app.models.user import User

# Which assessments can be compared, and how to pull a {label: (key, value)} metric map from a score.
COMPARABLE = ("talent_dna", "values", "capability", "written_communication", "case_study")


def _metrics(score_doc: Optional[dict]) -> Dict[str, dict]:
    """A flat {key: {name, value}} map for one attempt's score, so two attempts can be diffed."""
    if not score_doc:
        return {}
    area = score_doc.get("area")
    result = score_doc.get("result") or {}
    out: Dict[str, dict] = {}
    if area == "capability":
        out["__overall__"] = {"name": "Overall", "value": result.get("overall_pct")}
        for c in result.get("competencies") or []:
            out[c["key"]] = {"name": c["name"], "value": c["weighted_pct"]}
    elif area == "talent_dna":
        for d in result.get("dimensions") or []:
            out[d["key"]] = {"name": d["label"], "value": d["normalized"]}
    elif area == "values":
        for b in result.get("basic") or []:
            out[b["key"]] = {"name": b["name"], "value": b["centered"]}
    elif area in ("written_communication", "case_study"):
        scored = [r["scores"] for r in result.get("responses") or [] if r.get("status") in ("scored", "overridden") and r.get("scores")]
        if scored:
            for dim in ("reasoning", "knowledge", "communication"):
                out[dim] = {"name": dim.capitalize(), "value": round(sum(s[f"{dim}_score"] for s in scored) / len(scored), 1)}
    return out


async def _submitted_attempts(tenant_id: str, user_id: str, assessment_key: str) -> List[dict]:
    return await database.attempts().find(
        {"tenant_id": tenant_id, "user_id": user_id, "assessment_key": assessment_key, "status": "submitted"}
    ).sort("submitted_at", 1).to_list(None)


async def compare(tenant_id: str, user: User, assessment_key: str) -> dict:
    """Before/after of the two most recent submitted attempts (or just the latest if there's one)."""
    attempts = await _submitted_attempts(tenant_id, user.id, assessment_key)
    if not attempts:
        return {"assessment_key": assessment_key, "attempts": 0, "status": "not_submitted"}
    latest = attempts[-1]
    previous = attempts[-2] if len(attempts) >= 2 else None
    after = _metrics(await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": latest["_id"]}))
    before = _metrics(await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": previous["_id"]})) if previous else {}

    rows = []
    for key in sorted(set(after) | set(before), key=lambda k: (k != "__overall__", k)):
        b = before.get(key, {}).get("value")
        a = after.get(key, {}).get("value")
        rows.append({
            "key": key,
            "name": (after.get(key) or before.get(key) or {}).get("name", key),
            "before": b,
            "after": a,
            "delta": (round(a - b, 1) if a is not None and b is not None else None),
        })
    return {
        "assessment_key": assessment_key,
        "attempts": len(attempts),
        "status": "compared" if previous else "single",
        "latest_at": latest.get("submitted_at"),
        "previous_at": previous.get("submitted_at") if previous else None,
        "rows": rows,
    }


async def overview(tenant_id: str, user: User) -> List[dict]:
    """One row per assessment the candidate has submitted, saying whether a reassessment exists."""
    rows: List[dict] = []
    for key in COMPARABLE:
        attempts = await _submitted_attempts(tenant_id, user.id, key)
        if attempts:
            rows.append({"assessment_key": key, "attempts": len(attempts), "can_compare": len(attempts) >= 2})
    return rows
