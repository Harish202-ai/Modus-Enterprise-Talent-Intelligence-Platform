"""Phase 8 — Composite scores (plan v2/v3).

Two composite scores, computed deterministically from the Phase 6 (Talent DNA / Values / Capability)
and Phase 7 (AI Reasoning / Knowledge / Communication) outputs — never by an LLM:

- **Readiness (0-100)** — a weighted blend of consulting capability, demonstrated reasoning /
  knowledge / communication, and the Talent DNA profile. Values are *descriptive* (development
  context, not pass/fail per the TDD) and deliberately don't move Readiness.
- **Evidence Confidence (0-100)** — how well-evidenced the picture is: how many of the expected
  inputs the candidate actually completed, weighted by the AI's own confidence in the graded
  responses. A strong Readiness on thin evidence is reported with low confidence.

Both degrade gracefully: only the components that exist contribute, and the weights are renormalised
over what's present, so a candidate who bought one assessment still gets a meaningful (if lower-
confidence) composite.
"""
from typing import Dict, List, Optional, Tuple

# Readiness component weights (renormalised over whatever is present).
READINESS_WEIGHTS = {
    "capability": 0.35,
    "reasoning": 0.20,
    "knowledge": 0.15,
    "communication": 0.15,
    "talent_dna": 0.15,
}

# What "fully evidenced" looks like — each present input adds its share to coverage.
EVIDENCE_INPUTS = ("talent_dna", "values", "capability", "written_communication", "case_study")


def _round(v: float, n: int = 1) -> float:
    return round(v, n)


def _mean(xs: List[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def _ai_dimension_means(*ai_areas: dict) -> Dict[str, Optional[float]]:
    """Mean reasoning / knowledge / communication across every *scored* AI response."""
    buckets: Dict[str, List[float]] = {"reasoning": [], "knowledge": [], "communication": [], "confidence": []}
    for area in ai_areas:
        if not area or area.get("status") == "not_submitted":
            continue
        for r in area.get("responses") or []:
            s = r.get("scores")
            if r.get("status") == "scored" and s:
                buckets["reasoning"].append(s["reasoning_score"])
                buckets["knowledge"].append(s["knowledge_score"])
                buckets["communication"].append(s["communication_score"])
                buckets["confidence"].append(s["overall_confidence"])
    return {k: _mean(v) for k, v in buckets.items()}


def compute(scores: Dict[str, dict]) -> dict:
    """Given the merged score areas (as returned by the score read API), return the composites."""
    talent = scores.get("talent_dna") or {}
    capability = scores.get("capability") or {}
    ai_means = _ai_dimension_means(scores.get("written_communication"), scores.get("case_study"))

    components: Dict[str, float] = {}
    if capability.get("status") == "scored":
        components["capability"] = float(capability.get("overall_pct", 0.0))
    if talent.get("status") == "scored" and talent.get("dimensions"):
        components["talent_dna"] = _mean([d["normalized"] for d in talent["dimensions"]]) or 0.0
    for dim in ("reasoning", "knowledge", "communication"):
        if ai_means.get(dim) is not None:
            components[dim] = float(ai_means[dim])

    readiness = _weighted(components, READINESS_WEIGHTS)

    # Evidence Confidence: coverage of expected inputs × the AI's confidence where it graded.
    present = [k for k in EVIDENCE_INPUTS if (scores.get(k) or {}).get("status") not in (None, "not_submitted")]
    coverage = len(present) / len(EVIDENCE_INPUTS)
    ai_conf = ai_means.get("confidence")
    graded_any = ai_conf is not None
    # If nothing was AI-graded yet, confidence rests on coverage alone (capped so it can't read "certain").
    evidence_confidence = coverage * (0.5 + 0.5 * (ai_conf / 100)) * 100 if graded_any else coverage * 80

    return {
        "readiness": _round(readiness) if components else None,
        "readiness_components": {k: _round(v) for k, v in components.items()},
        "evidence_confidence": _round(evidence_confidence),
        "evidence_coverage": _round(coverage * 100),
        "inputs_present": present,
        "ai_means": {k: (_round(v) if v is not None else None) for k, v in ai_means.items()},
    }


def _weighted(components: Dict[str, float], weights: Dict[str, float]) -> float:
    pairs: List[Tuple[float, float]] = [(components[k], weights[k]) for k in components if k in weights]
    total_w = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total_w if total_w > 0 else 0.0


def band(readiness: Optional[float]) -> str:
    """A plain-language band for the Readiness score (display + report narrative)."""
    if readiness is None:
        return "not yet scored"
    if readiness >= 75:
        return "strong"
    if readiness >= 55:
        return "developing well"
    if readiness >= 35:
        return "emerging"
    return "early"
