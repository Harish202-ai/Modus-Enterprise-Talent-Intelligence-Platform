"""AI video interview (plan v5 — proctored video interview).

The interviewer asks a set of timed questions (admin-editable `interview_questions` content). The
candidate's webcam records their answers in the browser; the browser also runs face-away detection
and, after too many warnings, auto-submits. This service serves the questions + config and stores the
uploaded recording with its proctoring metadata (warnings, whether it auto-submitted) for admin review.

The recording itself is a normal uploaded file (owner-or-admin download via /v1/files/{id}); the
`interviews` collection holds the metadata that ties a recording to its proctoring events.
"""
from typing import List, Optional

from app import database
from app.content.registry import get_type
from app.models.common import new_id, utcnow
from app.models.user import User
from app.services import audit, commerce, files

MAX_WARNINGS = 5
INTERVIEW_KINDS = ("mp4", "webm", "mov")
INTERVIEW_MAX_MB = 200
# The interview is part of the Written Communication assessment's product line.
GATE_ASSESSMENT = "written_communication"


async def get_questions(tenant_id: str) -> List[dict]:
    rows = (
        await database.collection(get_type("interview_questions").name)
        .find({"tenant_id": tenant_id, "status": "published"})
        .sort([("key", 1), ("version", -1)])
        .to_list(None)
    )
    latest = {}
    for r in rows:
        latest.setdefault(r["key"], r)
    items = [{"key": r["key"], "prompt": r["data"].get("prompt"), "seconds": int(r["data"].get("seconds", 90)),
              "order": int(r["data"].get("order", 0))} for r in latest.values()]
    items.sort(key=lambda q: (q["order"], q["key"]))
    return items


async def config(tenant_id: str, user: User) -> dict:
    await commerce.require_assessment_access(tenant_id, user, GATE_ASSESSMENT)
    return {"questions": await get_questions(tenant_id), "max_warnings": MAX_WARNINGS}


def _out(doc: dict) -> dict:
    return {
        "id": doc["_id"],
        "file": doc.get("file"),
        "warnings": doc.get("warnings", 0),
        "auto_submitted": doc.get("auto_submitted", False),
        "answered": doc.get("answered", 0),
        "questions_total": doc.get("questions_total", 0),
        "duration_seconds": doc.get("duration_seconds"),
        "created_at": doc["created_at"],
    }


async def submit(tenant_id: str, user: User, upload, warnings: int, auto_submitted: bool, answered: int, duration_seconds: Optional[int]) -> dict:
    await commerce.require_assessment_access(tenant_id, user, GATE_ASSESSMENT)
    doc = await files.save(tenant_id, user.id, upload, INTERVIEW_KINDS, "interview", INTERVIEW_MAX_MB)
    questions = await get_questions(tenant_id)
    record = {
        "_id": new_id(), "tenant_id": tenant_id, "user_id": user.id,
        "file_id": doc["_id"], "file": files.public(doc),
        "warnings": max(0, int(warnings)), "auto_submitted": bool(auto_submitted),
        "answered": max(0, int(answered)), "questions_total": len(questions),
        "duration_seconds": duration_seconds, "created_at": utcnow(), "updated_at": utcnow(),
    }
    await database.interviews().insert_one(record)
    await audit.record(
        tenant_id=tenant_id, actor_id=user.id, candidate_id=user.id, entity_type="interview", entity_id=record["_id"],
        action="interview.submitted", metadata={"warnings": record["warnings"], "auto_submitted": record["auto_submitted"]},
    )
    return _out(record)


async def latest(tenant_id: str, user_id: str) -> Optional[dict]:
    doc = await database.interviews().find_one({"tenant_id": tenant_id, "user_id": user_id}, sort=[("created_at", -1)])
    return _out(doc) if doc else None


async def for_candidate(tenant_id: str, user_id: str) -> List[dict]:
    docs = await database.interviews().find({"tenant_id": tenant_id, "user_id": user_id}).sort("created_at", -1).to_list(None)
    return [_out(d) for d in docs]
