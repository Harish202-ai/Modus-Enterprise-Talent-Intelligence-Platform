"""Phase 7 — AI Scoring Service (plan v5).

One scoring service, not a swarm of agents: it takes a candidate's free-text response (an executive
memo or a case answer — typed, or extracted from an uploaded PDF/DOCX/PPTX), the response's rubric,
and the published `scoring` prompt, and makes **one AI call per response** that returns the three
named dimensions the v5 diagram calls for — Reasoning, Knowledge, Communication — each with a cited
evidence quote, plus an overall confidence.

Per the TDD rule, invalid model output retries once (in `provider.generate`) and then the response
is flagged `needs_review`; a missing key or an unreachable provider leaves it `pending`; a video
answer waits for the transcription that arrives with the Phase 8 voice provider. It never fakes a score.

Scores are stored one document per attempt in the `scores` collection (area = the assessment key),
with a `responses` list so a multi-part case keeps a score per question.
"""
import io
import logging
import re
import zipfile
from typing import Any, Dict, List, Optional

from docx import Document
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

from app import database
from app.ai import provider
from app.content.registry import get_type
from app.models.common import new_id, utcnow
from app.services import audit, files
from app.services.content import NotFound, get_current, get_version

log = logging.getLogger(__name__)

PROMPT_KEY = "scoring"
MAX_RESPONSE_CHARS = 14000
MIN_RESPONSE_CHARS = 20
DOC_KINDS = ("pdf", "docx", "pptx")
VIDEO_KINDS = ("mp4", "mov", "webm")

# Assessments whose responses are AI-scored (free-text with a rubric).
AI_SCORED_ASSESSMENTS = {"written_communication", "case_study"}


class AIScore(BaseModel):
    """The v5 Phase 7 output schema: three named dimensions, each with cited evidence."""

    reasoning_score: int = Field(ge=0, le=100)
    reasoning_evidence: str = Field(default="", max_length=2000)
    knowledge_score: int = Field(ge=0, le=100)
    knowledge_evidence: str = Field(default="", max_length=2000)
    communication_score: int = Field(ge=0, le=100)
    communication_evidence: str = Field(default="", max_length=2000)
    overall_confidence: int = Field(ge=0, le=100)

    @field_validator("reasoning_score", "knowledge_score", "communication_score", "overall_confidence", mode="before")
    @classmethod
    def _clamp(cls, v):
        try:
            return max(0, min(100, round(float(v))))
        except (TypeError, ValueError):
            return v

    @field_validator("reasoning_evidence", "knowledge_evidence", "communication_evidence", mode="before")
    @classmethod
    def _trim(cls, v):
        return " ".join(str(v).split())[:2000] if v is not None else ""


# --- extracting the response text -------------------------------------------------------------

def _pptx_text(data: bytes) -> str:
    parts: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in sorted(n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)):
            xml = z.read(name).decode("utf-8", "ignore")
            parts += re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)
    text = "\n".join(p.strip() for p in parts if p.strip())
    return (
        text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
    )


def extract_text(doc: dict) -> str:
    """Plain text from an uploaded PDF / DOCX / PPTX answer (bounded)."""
    data = files.read_bytes(doc)
    kind = doc["kind"]
    if kind == "pdf":
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:30])
    elif kind == "docx":
        d = Document(io.BytesIO(data))
        rows = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                rows.append(" | ".join(cell.text for cell in row.cells))
        text = "\n".join(rows)
    elif kind == "pptx":
        text = _pptx_text(data)
    else:
        raise ValueError(f"can't extract text from a {kind} file")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())[:MAX_RESPONSE_CHARS]


async def _response_text(tenant_id: str, answer: Any) -> tuple[Optional[str], Optional[str]]:
    """(text, blocking_status): the response's text, or a status ('needs_transcript' | 'empty' |
    'unreadable') when it can't be scored yet."""
    if isinstance(answer, str):
        text = answer.strip()
        return (text, None) if len(text) >= MIN_RESPONSE_CHARS else (None, "empty")
    if isinstance(answer, dict) and isinstance(answer.get("file_id"), str):
        kind = answer.get("kind")
        if kind in VIDEO_KINDS:
            return None, "needs_transcript"  # transcription arrives with the Phase 8 voice provider
        if kind in DOC_KINDS:
            try:
                text = extract_text(await files.get(tenant_id, answer["file_id"]))
            except Exception:  # noqa: BLE001 — a bad upload becomes review, never a crash
                log.exception("response text extraction failed", extra={"file_id": answer.get("file_id")})
                return None, "unreadable"
            return (text, None) if len(text) >= MIN_RESPONSE_CHARS else (None, "unreadable")
    return None, "empty"


# --- prompt assembly --------------------------------------------------------------------------

def _rubric_block(rubric: dict) -> str:
    lines = [f"Rubric: {rubric.get('name', '')}"]
    for dim in rubric.get("dimensions") or []:
        lines.append(f"\n[{dim.get('name', dim.get('key'))}] (weight {dim.get('weight')})")
        for anchor in dim.get("anchors") or []:
            lines.append(f"  {anchor.get('level')}: {anchor.get('descriptor')}")
    return "\n".join(lines)


def _build_user_prompt(question_data: dict, rubric: dict, competency_names: List[str], response_text: str) -> str:
    comp = ", ".join(competency_names) if competency_names else "general consulting capability"
    return (
        f"TASK GIVEN TO THE CANDIDATE:\n{question_data.get('prompt', '')}\n\n"
        f"COMPETENCIES THIS RESPONSE INFORMS: {comp}\n\n"
        f"{_rubric_block(rubric)}\n\n"
        f"CANDIDATE RESPONSE:\n<<<\n{response_text}\n>>>\n\n"
        "Score the response on reasoning, knowledge and communication (0-100 each) using the rubric anchors, "
        "with a short evidence quote from the candidate's own words for each, and an overall_confidence."
    )


# --- scoring one attempt ----------------------------------------------------------------------

async def _score_one(tenant_id: str, prompt, question, competency_names: List[str], answer: Any) -> dict:
    """Score a single response; returns a `responses[]` entry (never raises)."""
    entry: Dict[str, Any] = {"question_key": question.key, "prompt": question.data.get("prompt")}
    text, blocked = await _response_text(tenant_id, answer)
    if blocked:
        messages = {
            "empty": "No written answer to score.",
            "needs_transcript": "This is a video answer — it will be scored once voice transcription is enabled (Phase 8).",
            "unreadable": "We couldn't read text from the uploaded file, so it needs a human review.",
        }
        entry.update(status="needs_review" if blocked == "unreadable" else blocked, message=messages[blocked])
        return entry

    rubric_versions = (question.ref_versions or {}).get("rubrics") or {}
    rubric_key = question.data.get("rubric_key")
    rubric = await get_version(get_type("rubrics"), tenant_id, rubric_key, rubric_versions[rubric_key])
    policy = prompt.data.get("model_policy") or {}
    try:
        score = await provider.generate(
            prompt.data["system_prompt"],
            _build_user_prompt(question.data, rubric.data, competency_names, text),
            AIScore,
            temperature=float(policy.get("temperature", 0.2)),
        )
    except provider.AIUnavailable as exc:
        log.warning("ai scoring unavailable", extra={"question_key": question.key, "reason": str(exc)})
        entry.update(status="pending", message="AI scoring isn't available right now — this will be scored shortly.")
    except provider.AIOutputInvalid:
        log.warning("ai scoring invalid output", extra={"question_key": question.key})
        entry.update(status="needs_review", message="The AI score couldn't be validated, so this needs a human review.")
    else:
        entry.update(status="scored", scores=score.model_dump(), rubric_key=rubric_key, rubric_version=rubric.version)
    return entry


async def run_for_attempt(tenant_id: str, attempt_id: str) -> Optional[dict]:
    """Score every AI-scored response in a submitted attempt (one AI call each) and persist.

    Best-effort and idempotent: re-running rescoring overwrites the attempt's score document.
    """
    from app.services.attempts import load_definition  # lazy: avoids an import cycle

    attempt = await database.attempts().find_one({"_id": attempt_id, "tenant_id": tenant_id})
    if attempt is None or attempt.get("status") != "submitted":
        return None
    if attempt["assessment_key"] not in AI_SCORED_ASSESSMENTS:
        return None
    defn = await load_definition(tenant_id, attempt["assessment_key"], attempt["assessment_version"])
    answers = attempt.get("answers") or {}
    competency_names = await _competency_names(tenant_id)

    try:
        prompt = await get_current(get_type("prompts"), tenant_id, PROMPT_KEY)
    except NotFound:
        prompt = None

    responses: List[dict] = []
    for section in defn["sections"]:
        for question in section["questions"]:
            if not question.data.get("rubric_key"):
                continue
            if prompt is None:
                responses.append({"question_key": question.key, "prompt": question.data.get("prompt"), "status": "pending",
                                  "message": "AI scoring isn't set up yet — the scoring prompt hasn't been published."})
                continue
            names = [competency_names.get(m["competency_key"], m["competency_key"]) for m in question.data.get("competency_map") or []]
            responses.append(await _score_one(tenant_id, prompt, question, names, answers.get(question.key)))

    statuses = {r["status"] for r in responses}
    overall = (
        "scored" if statuses == {"scored"}
        else "pending" if "pending" in statuses
        else "needs_review" if "needs_review" in statuses
        else "partial" if "scored" in statuses
        else (next(iter(statuses)) if len(statuses) == 1 else "needs_review")
    )
    now = utcnow()
    doc = {
        "tenant_id": tenant_id,
        "user_id": attempt["user_id"],
        "assessment_key": attempt["assessment_key"],
        "attempt_id": attempt_id,
        "assessment_version": attempt["assessment_version"],
        "area": attempt["assessment_key"],
        "method": "ai",
        "model": provider.model_label(),
        "prompt_version": prompt.version if prompt else None,
        "result": {"status": overall, "responses": responses},
        "computed_at": now,
        "updated_at": now,
    }
    await database.scores().update_one(
        {"tenant_id": tenant_id, "attempt_id": attempt_id},
        {"$set": doc, "$setOnInsert": {"_id": new_id(), "created_at": now}},
        upsert=True,
    )
    await audit.record(
        tenant_id=tenant_id, actor_id="system", candidate_id=attempt["user_id"], entity_type="score", entity_id=attempt_id,
        action="score.ai_computed", metadata={"area": attempt["assessment_key"], "status": overall, "model": doc["model"]},
    )
    return await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt_id})


async def _competency_names(tenant_id: str) -> Dict[str, str]:
    rows = (
        await database.collection(get_type("competencies").name)
        .find({"tenant_id": tenant_id, "status": "published"})
        .sort([("key", 1), ("version", -1)])
        .to_list(None)
    )
    names: Dict[str, str] = {}
    for row in rows:
        names.setdefault(row["key"], (row.get("data") or {}).get("name", row["key"]))
    return names


async def ai_scores_for_user(tenant_id: str, user_id: str) -> Dict[str, dict]:
    """The AI-scored areas for the candidate's latest submitted memo / case attempts.

    Read-only: unlike the deterministic scorers, AI scores are produced on submit (or by an explicit
    rescore), never recomputed on read. A submitted-but-not-yet-scored attempt reports `pending`.
    """
    out: Dict[str, dict] = {}
    for assessment_key in sorted(AI_SCORED_ASSESSMENTS):
        attempt = await database.attempts().find_one(
            {"tenant_id": tenant_id, "user_id": user_id, "assessment_key": assessment_key, "status": "submitted"},
            sort=[("submitted_at", -1)],
        )
        if attempt is None:
            out[assessment_key] = {"status": "not_submitted"}
            continue
        score = await database.scores().find_one({"tenant_id": tenant_id, "attempt_id": attempt["_id"]})
        if score is None:
            out[assessment_key] = {"status": "pending", "attempt_id": attempt["_id"], "submitted_at": attempt.get("submitted_at")}
            continue
        out[assessment_key] = {
            "attempt_id": attempt["_id"],
            "assessment_key": assessment_key,
            "submitted_at": attempt.get("submitted_at"),
            "computed_at": score["computed_at"],
            "model": score.get("model"),
            **score["result"],
        }
    return out


async def rescore(tenant_id: str, user_id: str, assessment_key: str) -> dict:
    """Owner-triggered re-run for the candidate's latest submitted attempt of an AI-scored form."""
    if assessment_key not in AI_SCORED_ASSESSMENTS:
        raise NotFound("That assessment isn't AI-scored")
    attempt = await database.attempts().find_one(
        {"tenant_id": tenant_id, "user_id": user_id, "assessment_key": assessment_key, "status": "submitted"},
        sort=[("submitted_at", -1)],
    )
    if attempt is None:
        raise NotFound("No submitted attempt to score")
    await run_for_attempt(tenant_id, attempt["_id"])
    return (await ai_scores_for_user(tenant_id, user_id))[assessment_key]
