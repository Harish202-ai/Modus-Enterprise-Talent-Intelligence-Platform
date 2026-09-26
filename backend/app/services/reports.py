"""Phase 8 — Summary of Findings + Detailed Report (plan v2/v3).

The report is assembled deterministically from the candidate's own locked scores (Phase 6) and
AI evidence scores (Phase 7) plus the composites (`composite.py`): strengths are the top-scoring
areas, development themes the lowest. It works with no AI key at all. When a report template exists
as content it supplies the section titles/order; otherwise sensible defaults are used, so the report
is never blocked on authoring.

- **Summary of Findings** — available to anyone who has submitted a paid assessment.
- **Detailed Report** — the same picture in full (every competency, the values profile, the graded
  responses with their cited evidence), gated by the `report_upgrade` entitlement.

`context_snapshot` produces the compact, grounded context the AI Explainer (Phase 8) and roadmap
(Phase 9) are allowed to use — nothing about the candidate beyond what's here.
"""
from typing import Dict, List, Optional

from app.models.user import User
from app.services import ai_scoring, commerce, composite, scoring_rules


async def _all_scores(tenant_id: str, user: User) -> Dict[str, dict]:
    deterministic = await scoring_rules.scores_for_user(tenant_id, user)
    ai = await ai_scoring.ai_scores_for_user(tenant_id, user.id)
    return {**deterministic, **ai}


def _strengths_and_gaps(scores: Dict[str, dict]) -> tuple[List[dict], List[dict]]:
    """Rank concrete, evidenced items into strengths (high) and development themes (low)."""
    items: List[dict] = []
    cap = scores.get("capability") or {}
    if cap.get("status") == "scored":
        for c in cap.get("competencies") or []:
            items.append({"label": c["name"], "value": c["weighted_pct"], "area": "capability",
                          "detail": f"{round(c['weighted_pct'])}% on the {c['name']} knowledge items."})
    td = scores.get("talent_dna") or {}
    if td.get("status") == "scored":
        for d in td.get("dimensions") or []:
            items.append({"label": d["label"], "value": d["normalized"], "area": "talent_dna",
                          "detail": f"{d['label']} is a {'leading' if d['normalized'] >= 60 else 'lower'} part of how you work."})
    for area_key, nice in (("written_communication", "Written communication"), ("case_study", "Case analysis")):
        area = scores.get(area_key) or {}
        for r in area.get("responses") or []:
            s = r.get("scores")
            if r.get("status") == "scored" and s:
                avg = (s["reasoning_score"] + s["knowledge_score"] + s["communication_score"]) / 3
                items.append({"label": nice, "value": avg, "area": area_key,
                              "detail": f"Reasoning {s['reasoning_score']}, knowledge {s['knowledge_score']}, communication {s['communication_score']}."})
    if not items:
        return [], []
    ranked = sorted(items, key=lambda i: -i["value"])
    strengths = [i for i in ranked if i["value"] >= 55][:4] or ranked[:2]
    gaps = [i for i in reversed(ranked) if i["value"] < 60][:4]
    # Don't list the same item as both a strength and a gap.
    strong_labels = {(s["area"], s["label"]) for s in strengths}
    gaps = [g for g in gaps if (g["area"], g["label"]) not in strong_labels][:4]
    return strengths, gaps


def _headline(comp: dict) -> str:
    r = comp.get("readiness")
    if r is None:
        return "Complete a scored assessment to see your Summary of Findings."
    return f"Your consulting readiness is {composite.band(r)} ({round(r)}/100), on {round(comp['evidence_coverage'])}% of the full evidence set."


async def summary(tenant_id: str, user: User) -> dict:
    scores = await _all_scores(tenant_id, user)
    comp = composite.compute(scores)
    strengths, gaps = _strengths_and_gaps(scores)
    owns_detailed = await commerce.owns_report_upgrade(tenant_id, user.id)
    return {
        "type": "summary",
        "readiness": comp["readiness"],
        "readiness_band": composite.band(comp["readiness"]),
        "evidence_confidence": comp["evidence_confidence"],
        "evidence_coverage": comp["evidence_coverage"],
        "headline": _headline(comp),
        "strengths": [{"label": s["label"], "detail": s["detail"]} for s in strengths],
        "development_themes": [{"label": g["label"], "detail": g["detail"]} for g in gaps],
        "has_detailed_report": owns_detailed,
        "scored": comp["readiness"] is not None,
    }


async def detailed(tenant_id: str, user: User) -> dict:
    """Full report — gated by the report_upgrade entitlement (raises 402 without it)."""
    await commerce.require_report_access(tenant_id, user)
    scores = await _all_scores(tenant_id, user)
    comp = composite.compute(scores)
    base = await summary(tenant_id, user)
    return {
        **base,
        "type": "detailed",
        "composite": comp,
        "capability": scores.get("capability"),
        "talent_dna": scores.get("talent_dna"),
        "values": scores.get("values"),
        "written_communication": scores.get("written_communication"),
        "case_study": scores.get("case_study"),
    }


async def context_snapshot(tenant_id: str, user: User) -> dict:
    """The candidate's locked data the Explainer / roadmap may ground on — and nothing else."""
    scores = await _all_scores(tenant_id, user)
    comp = composite.compute(scores)
    strengths, gaps = _strengths_and_gaps(scores)
    return {"composite": comp, "strengths": strengths, "development_themes": gaps, "scores": scores}


def snapshot_to_text(snapshot: dict) -> str:
    """A compact, human-readable rendering of the snapshot for grounding an AI prompt."""
    comp = snapshot["composite"]
    lines = [
        f"Readiness: {comp['readiness']} / 100 ({composite.band(comp['readiness'])}).",
        f"Evidence confidence: {comp['evidence_confidence']} / 100 (coverage {comp['evidence_coverage']}%).",
        "Strengths: " + ("; ".join(f"{s['label']} — {s['detail']}" for s in snapshot["strengths"]) or "none yet"),
        "Development themes: " + ("; ".join(f"{g['label']} — {g['detail']}" for g in snapshot["development_themes"]) or "none yet"),
    ]
    return "\n".join(lines)
