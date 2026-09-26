"""Assessment engine (plan v2 Phase 5): one generic runner for every form, driven by question data.

- An attempt pins the assessment version it started on; sections/questions resolve through that version's
  pinned refs, so a candidate always sees — and is later scored on — exactly what they started.
- Autosave merges answers into the attempt (server-side, so it resumes on any device).
- Skip logic: a section is skipped when any `skip_if` rule matches an earlier answer.
- Submitted attempts are immutable.
- Candidates only ever receive a *sanitised* question (no scoring keys, maps or rubrics).
"""
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app import database
from app.content.registry import get_type
from app.models.common import new_id, utcnow
from app.models.user import User
from app.services import audit, commerce, files, profile_ai
from app.services.content import Conflict, ContentError, Invalid, NotFound, get_current, get_version

CANDIDATE_QUESTION_FIELDS = (
    "type", "prompt", "min_selections", "max_selections", "min_words", "max_length", "upload_kinds", "upload_max_mb", "upload_role",
)


class AnswerError(ContentError):
    status_code = 422


# --- definition -------------------------------------------------------------------------------

async def load_definition(tenant_id: str, assessment_key: str, version: int) -> dict:
    """The pinned assessment tree: {assessment, sections: [{section, questions: [...]}]} (full, unsanitised)."""
    assessment = await get_version(get_type("assessments"), tenant_id, assessment_key, version)
    sections = []
    for s_key in assessment.data.get("section_keys", []):
        section = await get_version(get_type("sections"), tenant_id, s_key, assessment.ref_versions["sections"][s_key])
        questions = [
            await get_version(get_type("questions"), tenant_id, q_key, section.ref_versions["questions"][q_key])
            for q_key in section.data.get("question_keys", [])
        ]
        sections.append({"section": section, "questions": questions})
    return {"assessment": assessment, "sections": sections}


def _public_question(q) -> dict:
    data = q.data
    out = {"key": q.key, **{f: data[f] for f in CANDIDATE_QUESTION_FIELDS if data.get(f) is not None}}
    if data.get("options"):
        out["options"] = [{"key": o["key"], "label": o["label"]} for o in data["options"]]  # never scoring metadata
    return out


def public_definition(defn: dict) -> dict:
    a = defn["assessment"]
    return {
        "key": a.key,
        "version": a.version,
        "name": a.data.get("name"),
        "purpose": a.data.get("purpose"),
        "time_limit_minutes": a.data.get("time_limit_minutes"),
        "sections": [
            {
                "key": s["section"].key,
                "title": s["section"].data.get("title"),
                "instructions": s["section"].data.get("instructions"),
                "skip_if": s["section"].data.get("skip_if") or [],
                "questions": [_public_question(q) for q in s["questions"]],
            }
            for s in defn["sections"]
        ],
    }


# --- skip logic + answer validation -----------------------------------------------------------

def _matches(answer: Any, expected: Any) -> bool:
    if isinstance(answer, list):
        return str(expected) in map(str, answer)
    return answer is not None and str(answer) == str(expected)


def skipped_sections(defn: dict, answers: Dict[str, Any]) -> List[str]:
    return [
        s["section"].key
        for s in defn["sections"]
        if any(_matches(answers.get(rule.get("question_key")), rule.get("answer")) for rule in s["section"].data.get("skip_if") or [])
    ]


def validate_answer(question, value: Any) -> Optional[str]:
    """Return an error message, or None if `value` is a valid (complete) answer."""
    data = question.data
    qtype = data.get("type")
    option_keys = [str(o["key"]) for o in data.get("options") or []]
    if qtype in ("single_choice", "likert"):
        return None if isinstance(value, str) and value in option_keys else "choose one of the options"
    if qtype == "multi_select":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value) or len(set(value)) != len(value):
            return "choose options without repeats"
        if any(v not in option_keys for v in value):
            return "contains an unknown option"
        lo, hi = data.get("min_selections") or 1, data.get("max_selections") or len(option_keys)
        if not lo <= len(value) <= hi:
            return f"choose between {lo} and {hi} options" if lo != hi else f"choose exactly {lo}"
        return None
    if qtype == "rank":
        if not isinstance(value, list) or sorted(map(str, value)) != sorted(option_keys):
            return "rank every option exactly once"
        return None
    if qtype == "file_upload":
        return None if _is_file(value) else "upload a file"
    if qtype == "free_text":
        if _is_file(value) and data.get("upload_kinds"):
            return None
        if not isinstance(value, str) or not value.strip():
            return "write an answer" + (" or upload a file" if data.get("upload_kinds") else "")
        if len(value) > (data.get("max_length") or 5000):
            return f"keep it under {data.get('max_length') or 5000} characters"
        words = len(value.split())
        if data.get("min_words") and words < data["min_words"]:
            return f"write at least {data['min_words']} words (currently {words})"
        return None
    return "unsupported question type"


def _is_file(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("file_id"), str)


def _question_index(defn: dict) -> Dict[str, Any]:
    return {q.key: q for s in defn["sections"] for q in s["questions"]}


def progress(defn: dict, answers: Dict[str, Any]) -> dict:
    skipped = set(skipped_sections(defn, answers))
    visible = [q for s in defn["sections"] if s["section"].key not in skipped for q in s["questions"]]
    answered = sum(1 for q in visible if q.key in answers and validate_answer(q, answers[q.key]) is None)
    return {"answered": answered, "total": len(visible), "skipped_sections": sorted(skipped)}


# --- attempts ---------------------------------------------------------------------------------

def _attempt_out(attempt: dict, defn: dict) -> dict:
    return {
        "id": attempt["_id"],
        "assessment_key": attempt["assessment_key"],
        "assessment_version": attempt["assessment_version"],
        "status": attempt["status"],
        "answers": attempt.get("answers") or {},
        "current_section_key": attempt.get("current_section_key"),
        "started_at": attempt["started_at"],
        "updated_at": attempt["updated_at"],
        "submitted_at": attempt.get("submitted_at"),
        "progress": progress(defn, attempt.get("answers") or {}),
        "definition": public_definition(defn),
    }


async def start_or_resume(tenant_id: str, user: User, assessment_key: str) -> dict:
    await commerce.require_assessment_access(tenant_id, user, assessment_key)
    existing = await database.attempts().find_one(
        {"tenant_id": tenant_id, "user_id": user.id, "assessment_key": assessment_key, "status": "in_progress"}
    )
    if existing:
        return _attempt_out(existing, await load_definition(tenant_id, assessment_key, existing["assessment_version"]))
    assessment = await get_current(get_type("assessments"), tenant_id, assessment_key)  # 404 until published
    now = utcnow()
    attempt = {
        "_id": new_id(),
        "tenant_id": tenant_id,
        "user_id": user.id,
        "assessment_key": assessment_key,
        "assessment_version": assessment.version,
        "status": "in_progress",
        "answers": {},
        "current_section_key": None,
        "started_at": now,
        "updated_at": now,
        "submitted_at": None,
    }
    try:
        await database.attempts().insert_one(attempt)
    except DuplicateKeyError:  # started concurrently in another tab
        return await start_or_resume(tenant_id, user, assessment_key)
    await audit.record(
        tenant_id=tenant_id, actor_id=user.id, candidate_id=user.id, entity_type="attempt", entity_id=attempt["_id"],
        action="attempt.started", metadata={"assessment_key": assessment_key, "version": assessment.version},
    )
    return _attempt_out(attempt, await load_definition(tenant_id, assessment_key, assessment.version))


async def _own_attempt(tenant_id: str, user: User, attempt_id: str) -> dict:
    attempt = await database.attempts().find_one({"_id": attempt_id, "tenant_id": tenant_id, "user_id": user.id})
    if attempt is None:
        raise NotFound("Attempt not found")
    return attempt


async def get_attempt(tenant_id: str, user: User, attempt_id: str) -> dict:
    attempt = await _own_attempt(tenant_id, user, attempt_id)
    return _attempt_out(attempt, await load_definition(tenant_id, attempt["assessment_key"], attempt["assessment_version"]))


async def save_answers(tenant_id: str, user: User, attempt_id: str, answers: Dict[str, Any], current_section_key: Optional[str]) -> dict:
    """Autosave: merge answers. Partial answers are stored as given (validated for shape only at submit),
    except obviously wrong keys/types which are rejected so bad data never lands."""
    attempt = await _own_attempt(tenant_id, user, attempt_id)
    if attempt["status"] != "in_progress":
        raise Conflict("This assessment has been submitted and can't be changed")
    defn = await load_definition(tenant_id, attempt["assessment_key"], attempt["assessment_version"])
    questions = _question_index(defn)
    errors = []
    updates: Dict[str, Any] = {}
    for key, value in answers.items():
        question = questions.get(key)
        if question is None:
            errors.append({"field": key, "message": "is not a question in this assessment"})
            continue
        if value is None:
            updates[f"answers.{key}"] = None  # cleared
            continue
        problem = _shape_error(question, value)
        if problem:
            errors.append({"field": key, "message": problem})
        else:
            updates[f"answers.{key}"] = value
    if errors:
        raise AnswerError("Some answers couldn't be saved", errors)
    section_keys = {s["section"].key for s in defn["sections"]}
    if current_section_key is not None:
        if current_section_key not in section_keys:
            raise AnswerError("Unknown section", [{"field": "current_section_key", "message": "is not a section of this assessment"}])
        updates["current_section_key"] = current_section_key
    updates["updated_at"] = utcnow()
    unset = {k: "" for k, v in updates.items() if k.startswith("answers.") and v is None}
    sets = {k: v for k, v in updates.items() if k not in unset}
    doc = await database.attempts().find_one_and_update(
        {"_id": attempt_id, "status": "in_progress"},
        {"$set": sets, **({"$unset": unset} if unset else {})},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise Conflict("This assessment has been submitted and can't be changed")
    return {"id": doc["_id"], "updated_at": doc["updated_at"], "progress": progress(defn, doc.get("answers") or {})}


def _shape_error(question, value: Any) -> Optional[str]:
    """Autosave accepts work in progress (e.g. a half-written text) but not wrong kinds of value."""
    qtype = question.data.get("type")
    option_keys = {str(o["key"]) for o in question.data.get("options") or []}
    if isinstance(value, dict):
        return "attach files with the upload button"  # only the upload endpoint may set a file answer
    if qtype == "file_upload":
        return "attach files with the upload button"
    if qtype in ("single_choice", "likert"):
        return None if isinstance(value, str) and value in option_keys else "choose one of the options"
    if qtype in ("multi_select", "rank"):
        if not isinstance(value, list) or not all(isinstance(v, str) and v in option_keys for v in value) or len(set(value)) != len(value):
            return "contains an unknown or repeated option"
        return None
    if qtype == "free_text":
        if not isinstance(value, str):
            return "must be text"
        limit = question.data.get("max_length") or 5000
        return f"keep it under {limit} characters" if len(value) > limit else None
    return "unsupported question type"


async def submit(tenant_id: str, user: User, attempt_id: str, skipped_questions: Optional[List[str]] = None) -> dict:
    """Lock the attempt. Every non-skipped-section question must be answered, unless the candidate
    has **explicitly skipped** it (its key in `skipped_questions`) — that's how the exam "Skip"
    button works. Without skips, an unanswered question still blocks submit (unchanged contract)."""
    attempt = await _own_attempt(tenant_id, user, attempt_id)
    if attempt["status"] != "in_progress":
        raise Conflict("Already submitted")
    defn = await load_definition(tenant_id, attempt["assessment_key"], attempt["assessment_version"])
    answers = attempt.get("answers") or {}
    skipped = set(skipped_sections(defn, answers))
    all_question_keys = {q.key for s in defn["sections"] for q in s["questions"]}
    skipped_q = {k for k in (skipped_questions or []) if k in all_question_keys}
    errors = []
    for s in defn["sections"]:
        if s["section"].key in skipped:
            continue
        for q in s["questions"]:
            if q.key in skipped_q and q.key not in answers:
                continue  # candidate chose to skip this one
            problem = validate_answer(q, answers.get(q.key)) if q.key in answers else "not answered yet"
            if problem:
                errors.append({"field": q.key, "message": problem, "section_key": s["section"].key})
    if errors:
        raise Invalid(f"{len(errors)} question{'s' if len(errors) != 1 else ''} still need an answer", errors)
    now = utcnow()
    doc = await database.attempts().find_one_and_update(
        {"_id": attempt_id, "status": "in_progress", "updated_at": attempt["updated_at"]},
        {"$set": {"status": "submitted", "submitted_at": now, "updated_at": now,
                  "skipped_sections": sorted(skipped), "skipped_questions": sorted(skipped_q)}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise Conflict("Answers changed while submitting — please submit again")
    await audit.record(
        tenant_id=tenant_id, actor_id=user.id, candidate_id=user.id, entity_type="attempt", entity_id=attempt_id,
        action="attempt.submitted", metadata={"assessment_key": attempt["assessment_key"], "version": attempt["assessment_version"]},
    )
    # Phase 6: deterministic assessments (Talent DNA, Values, Capability) are scored the moment
    # they lock — best-effort, so a scoring hiccup never blocks the submission itself.
    from app.services import scoring_rules  # local import avoids an import cycle

    await scoring_rules.score_on_submit(tenant_id, doc, defn)
    return _attempt_out(doc, defn)


async def my_assessments(tenant_id: str, user: User) -> List[dict]:
    """Every assessment the candidate has bought, with status and progress — the candidate's home list."""
    unlocked = await commerce.accessible_assessments(tenant_id, user.id)
    names = await commerce._assessment_names(tenant_id)
    attempts = await database.attempts().find({"tenant_id": tenant_id, "user_id": user.id}).sort("started_at", -1).to_list(None)
    latest: Dict[str, dict] = {}
    for a in attempts:
        latest.setdefault(a["assessment_key"], a)
    rows = []
    # Order = the order products list their assessments (admin-controlled), not code.
    order: List[str] = []
    for product in await commerce.catalogue(tenant_id):
        order += [k for k in product["assessment_keys"] if k not in order]
    for key in sorted(unlocked, key=lambda k: (order.index(k) if k in order else len(order), k)):
        a = latest.get(key)
        row = {"key": key, "name": names.get(key, key), "status": "not_started", "attempt_id": None, "progress": None}
        try:
            current = await get_current(get_type("assessments"), tenant_id, key)
        except NotFound:
            row["status"] = "coming_soon"
            current = None
        if a:
            defn = await load_definition(tenant_id, key, a["assessment_version"])
            row.update(status=a["status"], attempt_id=a["_id"], progress=progress(defn, a.get("answers") or {}), submitted_at=a.get("submitted_at"))
        elif current:
            row["purpose"] = current.data.get("purpose")
        rows.append(row)
    return rows


async def upload_answer_file(tenant_id: str, user: User, attempt_id: str, question_key: str, upload) -> dict:
    """Store a file as the answer to one question. A resume question also starts AI Profile Understanding."""
    attempt = await _own_attempt(tenant_id, user, attempt_id)
    if attempt["status"] != "in_progress":
        raise Conflict("This assessment has been submitted and can't be changed")
    defn = await load_definition(tenant_id, attempt["assessment_key"], attempt["assessment_version"])
    question = _question_index(defn).get(question_key)
    if question is None:
        raise NotFound("Question not found in this assessment")
    kinds = question.data.get("upload_kinds") or []
    if not kinds:
        raise AnswerError("This question doesn't accept files", [{"field": question_key, "message": "no uploads here"}])
    is_resume = question.data.get("upload_role") == "resume"
    doc = await files.save(tenant_id, user.id, upload, kinds, "resume" if is_resume else f"answer:{question_key}", question.data.get("upload_max_mb"))
    answer = {"file_id": doc["_id"], "filename": doc["filename"], "kind": doc["kind"], "size": doc["size"]}
    updated = await database.attempts().find_one_and_update(
        {"_id": attempt_id, "status": "in_progress"},
        {"$set": {f"answers.{question_key}": answer, "updated_at": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise Conflict("This assessment has been submitted and can't be changed")
    claim = await profile_ai.start(tenant_id, user.id, doc) if is_resume else None
    return {"answer": answer, "progress": progress(defn, updated.get("answers") or {}), "resume_claim": claim}
