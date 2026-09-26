"""Phase 6 — Deterministic Scoring (Talent DNA, Values, Consulting Capability).

Everything here is computed in code, not by an LLM, so the same answers always produce
exactly the same profile (TDD §9). Three deterministic scorers:

- **Talent DNA** — rank-order items scored 4-3-2-1 (TDD §9.1). Each placed option adds its
  rank points to the dimension it `maps_to`; a dimension's total is normalised against the
  best/worst it could have scored on the items where it appeared.
- **Values** — Schwartz portrait items on a 6-point scale (TDD §9.2). Each basic value is the
  mean of its items, then **MRAT-centred**: the candidate's own mean across all value items is
  subtracted, which removes individual scale-use bias and turns the ratings into a relative
  value *priority* profile. Higher-order views (TDD §9.3) aggregate their constituent values.
- **Consulting Capability** — single-choice knowledge items with a correct option; each item's
  correctness is credited to its competency (weighted), giving a per-competency % for the radar.

The pure functions (`score_talent_dna`, `score_values`, `score_capability`) take resolved
question/answer data and return plain dicts — no I/O — so the maths is exactly unit-testable.
`score_attempt` / `scores_for_user` wrap them with persistence to the `scores` collection.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from app import database
from app.content.registry import get_type
from app.models.common import new_id, utcnow
from app.models.user import User
from app.services import audit
from app.services.content import get_current, get_version

log = logging.getLogger(__name__)

# Bump when a formula changes so stored scores can be recomputed knowingly.
RULES_VERSION = 1

# Each scored assessment maps to one deterministic scoring "area".
SCORED_AREAS = {"talent_dna": "talent_dna", "values": "values", "capability": "capability"}

# Display labels for the fixed Talent DNA dimensions (TDD §9.1). Numbers are data-driven from
# the questions' `maps_to`; only these human labels live in code, and unknown keys fall back to
# a title-cased version so a new dimension still renders.
_TALENT_LABELS = {
    "purpose_motivation": "Purpose & Motivation",
    "learning_curiosity": "Learning & Curiosity",
    "systems_thinking": "Systems Thinking",
    "innovation": "Innovation",
    "communication_collaboration": "Communication & Collaboration",
    "leadership_judgement": "Leadership & Judgement",
    "teamwork_relationships": "Teamwork & Relationships",
    "consulting_dna": "Consulting DNA",
    "future_global": "Future & Global Thinking",
}


def _talent_label(key: str) -> str:
    return _TALENT_LABELS.get(key, key.replace("_", " ").title())


def _round(value: float, ndigits: int = 1) -> float:
    return round(value, ndigits)


# --- pure scorers -----------------------------------------------------------------------------

def score_talent_dna(questions: Dict[str, dict], answers: Dict[str, Any]) -> dict:
    """Rank-order items 4-3-2-1 → normalised score per Talent DNA dimension.

    `questions` is {question_key: question.data}; only `rank` items with a `rank_points` rule
    are scored. `normalized` is 0–100 against the min/max the dimension could reach on the items
    where it actually appeared, so dimensions that occur on different numbers of items compare fairly.
    """
    totals: Dict[str, float] = defaultdict(float)
    dim_min: Dict[str, float] = defaultdict(float)
    dim_max: Dict[str, float] = defaultdict(float)
    counts: Dict[str, int] = defaultdict(int)
    scored_items = 0

    for qkey, data in questions.items():
        rule = data.get("scoring_rule") or {}
        if data.get("type") != "rank" or rule.get("method") != "rank_points":
            continue
        points = [float(p) for p in (rule.get("points") or [])]
        options = {str(o["key"]): o for o in data.get("options") or []}
        order = answers.get(qkey)
        if not isinstance(order, list) or sorted(map(str, order)) != sorted(options):
            continue
        scored_items += 1
        p_lo, p_hi = min(points), max(points)
        for i, opt_key in enumerate(order):
            dim = options[str(opt_key)].get("maps_to")
            if dim is None:
                continue
            totals[dim] += points[i] if i < len(points) else 0.0
            dim_min[dim] += p_lo
            dim_max[dim] += p_hi
            counts[dim] += 1

    dimensions = []
    for dim, total in totals.items():
        span = dim_max[dim] - dim_min[dim]
        normalized = _round((total - dim_min[dim]) / span * 100) if span > 0 else 0.0
        dimensions.append(
            {"key": dim, "label": _talent_label(dim), "raw": _round(total, 2), "normalized": normalized, "items": counts[dim]}
        )
    dimensions.sort(key=lambda d: (-d["normalized"], d["key"]))
    return {"dimensions": dimensions, "scored_items": scored_items}


def score_values(questions: Dict[str, dict], answers: Dict[str, Any], taxonomy: List[dict]) -> dict:
    """6-point portrait items → MRAT-centred value priorities + higher-order views.

    `taxonomy` is the resolved values_taxonomy items ({key, data}) — basic values give the wheel
    order, higher-order items give the aggregation. MRAT = the candidate's mean rating across all
    answered value items; each value's centred score is its mean minus MRAT (a relative priority).
    """
    per_value: Dict[str, List[float]] = defaultdict(list)
    all_ratings: List[float] = []

    for qkey, data in questions.items():
        rule = data.get("scoring_rule") or {}
        if rule.get("method") != "likert_value":
            continue
        raw = answers.get(qkey)
        if not (isinstance(raw, str) and raw.isdigit()):
            continue
        rating = float(raw)
        all_ratings.append(rating)
        for m in data.get("value_map") or []:
            per_value[m["value_key"]].append(rating)

    mrat = sum(all_ratings) / len(all_ratings) if all_ratings else 0.0
    value_mean = {v: sum(rs) / len(rs) for v, rs in per_value.items() if rs}
    centered = {v: mean - mrat for v, mean in value_mean.items()}

    basics = [t for t in taxonomy if (t.get("data") or {}).get("kind") == "basic_value"]
    highers = [t for t in taxonomy if (t.get("data") or {}).get("kind") == "higher_order"]

    basic_out = [
        {
            "key": t["key"],
            "name": t["data"].get("name", t["key"]),
            "raw_mean": _round(value_mean[t["key"]], 2),
            "centered": _round(centered[t["key"]], 2),
        }
        for t in basics
        if t["key"] in value_mean
    ]

    higher_out = []
    for t in highers:
        parts: List[tuple] = [(k, 1.0) for k in (t["data"].get("constituent_value_keys") or [])]
        parts += [(k, 0.5) for k in (t["data"].get("partial_value_keys") or [])]
        num = sum(w * centered[k] for k, w in parts if k in centered)
        den = sum(w for k, w in parts if k in centered)
        if den > 0:
            higher_out.append({"key": t["key"], "name": t["data"].get("name", t["key"]), "centered": _round(num / den, 2)})

    ranked = sorted(basic_out, key=lambda b: -b["centered"])
    return {
        "mrat": _round(mrat, 2),
        "answered": len(all_ratings),
        "basic": basic_out,  # taxonomy (circumplex) order — the values-wheel order
        "higher_order": higher_out,
        "top_values": [b["key"] for b in ranked[:3]],
    }


def score_capability(questions: Dict[str, dict], answers: Dict[str, Any], names: Optional[Dict[str, str]] = None) -> dict:
    """Correct-option knowledge items → per-competency %, weighted by each item's competency_map."""
    names = names or {}
    comp_credit: Dict[str, float] = defaultdict(float)
    comp_weight: Dict[str, float] = defaultdict(float)
    comp_items: Dict[str, int] = defaultdict(int)
    correct = 0
    total = 0

    for qkey, data in questions.items():
        rule = data.get("scoring_rule") or {}
        if rule.get("method") != "correct_option":
            continue
        # Every knowledge question counts toward the exam score; a skipped/blank answer is simply wrong.
        total += 1
        answer = answers.get(qkey)
        is_correct = 1.0 if isinstance(answer, str) and answer == rule.get("correct") else 0.0
        correct += int(is_correct)
        for m in data.get("competency_map") or []:
            w = float(m.get("weight", 1))
            comp_weight[m["competency_key"]] += w
            comp_credit[m["competency_key"]] += w * is_correct
            comp_items[m["competency_key"]] += 1

    competencies = [
        {
            "key": key,
            "name": names.get(key, key.replace("_", " ").title()),
            "items": comp_items[key],
            "weighted_pct": _round(comp_credit[key] / comp_weight[key] * 100) if comp_weight[key] else 0.0,
        }
        for key in comp_weight
    ]
    competencies.sort(key=lambda c: (-c["weighted_pct"], c["key"]))
    return {
        "correct": correct,
        "total": total,
        "overall_pct": _round(correct / total * 100) if total else 0.0,
        "competencies": competencies,
    }


# --- resolving content + persistence ----------------------------------------------------------

def _questions_of(defn: dict) -> Dict[str, dict]:
    """{question_key: question.data} for every question in the pinned definition."""
    return {q.key: q.data for section in defn["sections"] for q in section["questions"]}


async def _load_taxonomy(tenant_id: str) -> List[dict]:
    """The published values_taxonomy items as [{key, data}] — basic values then higher-order."""
    ctype = get_type("values_taxonomy")
    rows = (
        await database.collection(ctype.name)
        .find({"tenant_id": tenant_id, "status": "published"})
        .sort([("key", 1), ("version", -1)])
        .to_list(None)
    )
    latest: Dict[str, dict] = {}
    for row in rows:
        latest.setdefault(row["key"], row)  # highest version first
    return [{"key": r["key"], "data": r["data"]} for r in latest.values()]


async def _competency_names(tenant_id: str) -> Dict[str, str]:
    ctype = get_type("competencies")
    rows = (
        await database.collection(ctype.name)
        .find({"tenant_id": tenant_id, "status": "published"})
        .sort([("key", 1), ("version", -1)])
        .to_list(None)
    )
    names: Dict[str, str] = {}
    for row in rows:
        names.setdefault(row["key"], (row.get("data") or {}).get("name", row["key"]))
    return names


async def compute_area(tenant_id: str, area: str, defn: dict, answers: Dict[str, Any]) -> dict:
    """Run the deterministic scorer for one area against a resolved definition + answers."""
    questions = _questions_of(defn)
    if area == "talent_dna":
        return score_talent_dna(questions, answers)
    if area == "values":
        return score_values(questions, answers, await _load_taxonomy(tenant_id))
    if area == "capability":
        return score_capability(questions, answers, await _competency_names(tenant_id))
    raise ValueError(f"no deterministic scorer for area '{area}'")


async def score_attempt(tenant_id: str, attempt: dict, defn: dict) -> Optional[dict]:
    """Compute + persist the deterministic score for a submitted attempt (idempotent).

    Returns the stored score document, or None if the assessment isn't deterministically scored.
    Safe to call more than once — it upserts on (tenant_id, attempt_id).
    """
    area = SCORED_AREAS.get(attempt["assessment_key"])
    if area is None:
        return None
    result = await compute_area(tenant_id, area, defn, attempt.get("answers") or {})
    now = utcnow()
    doc = {
        "tenant_id": tenant_id,
        "user_id": attempt["user_id"],
        "assessment_key": attempt["assessment_key"],
        "attempt_id": attempt["_id"],
        "assessment_version": attempt["assessment_version"],
        "area": area,
        "method": "deterministic",
        "rules_version": RULES_VERSION,
        "result": result,
        "computed_at": now,
        "updated_at": now,
    }
    await database.scores().update_one(
        {"tenant_id": tenant_id, "attempt_id": attempt["_id"]},
        {"$set": doc, "$setOnInsert": {"_id": new_id(), "created_at": now}},
        upsert=True,
    )
    await audit.record(
        tenant_id=tenant_id, actor_id="system", candidate_id=attempt["user_id"], entity_type="score", entity_id=attempt["_id"],
        action="score.computed", metadata={"area": area, "rules_version": RULES_VERSION},
    )
    return await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt["_id"]})


async def score_on_submit(tenant_id: str, attempt: dict, defn: dict) -> None:
    """Best-effort scoring hook for submit — never lets a scoring error fail the submission."""
    try:
        await score_attempt(tenant_id, attempt, defn)
    except Exception:  # noqa: BLE001 — a submitted attempt must lock even if scoring hiccups
        log.exception("deterministic scoring failed on submit", extra={"attempt_id": attempt.get("_id")})


async def scores_for_user(tenant_id: str, user: User) -> Dict[str, dict]:
    """Every deterministic score for the candidate's latest submitted attempts, computing any
    that are missing (e.g. attempts submitted before Phase 6)."""
    from app.services.attempts import load_definition  # lazy: avoids an import cycle

    out: Dict[str, dict] = {}
    for assessment_key, area in SCORED_AREAS.items():
        attempt = await database.attempts().find_one(
            {"tenant_id": tenant_id, "user_id": user.id, "assessment_key": assessment_key, "status": "submitted"},
            sort=[("submitted_at", -1)],
        )
        if attempt is None:
            out[area] = {"status": "not_submitted"}
            continue
        score = await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt["_id"]})
        if score is None or score.get("rules_version") != RULES_VERSION:
            defn = await load_definition(tenant_id, assessment_key, attempt["assessment_version"])
            score = await score_attempt(tenant_id, attempt, defn)
        out[area] = {
            "status": "scored",
            "attempt_id": attempt["_id"],
            "assessment_key": assessment_key,
            "submitted_at": attempt.get("submitted_at"),
            "computed_at": score["computed_at"],
            **score["result"],
        }
    return out
