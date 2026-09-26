"""Phase 11 (v5) — admin view of candidates (plan: "admin portal should see the complete user
dashboard performance, video interview record").

Read-only aggregation of one candidate's whole picture for an admin: entitlements, attempts, the
deterministic + AI scores, the report summary, and their uploaded files (including interview videos,
downloadable via the existing owner-or-admin /v1/files/{id} endpoint).
"""
from typing import List, Optional

from app import database
from app.models.user import User
from app.services import ai_scoring, commerce, composite, interview, profile_ai, reports, scoring_rules
from app.services.content import NotFound
from app.services.files import public as file_public


async def list_candidates(tenant_id: str) -> List[dict]:
    users = await database.users().find({"tenant_id": tenant_id, "role": "candidate"}).sort("created_at", -1).to_list(None)
    rows = []
    for u in users:
        user = User.model_validate(u)
        submitted = await database.attempts().count_documents({"tenant_id": tenant_id, "user_id": u["_id"], "status": "submitted"})
        # Overall performance so an admin can see, at a glance, who is doing well.
        readiness = None
        band = None
        try:
            scores = {**await scoring_rules.scores_for_user(tenant_id, user), **await ai_scoring.ai_scores_for_user(tenant_id, u["_id"])}
            comp = composite.compute(scores)
            readiness = comp["readiness"]
            band = composite.band(readiness)
        except Exception:  # noqa: BLE001 — the list must render even if one student can't be scored
            pass
        rows.append({
            "id": u["_id"],
            "email": u["email"],
            "full_name": u.get("full_name"),
            "status": u.get("status"),
            "created_at": u.get("created_at"),
            "last_login_at": u.get("last_login_at"),
            "submitted_assessments": submitted,
            "readiness": readiness,
            "readiness_band": band,
        })
    # Best performers first; students with no score yet go last.
    rows.sort(key=lambda r: (r["readiness"] is None, -(r["readiness"] or 0)))
    return rows


async def _user(tenant_id: str, user_id: str) -> User:
    doc = await database.users().find_one({"_id": user_id, "tenant_id": tenant_id})
    if doc is None:
        raise NotFound("Candidate not found")
    return User.model_validate(doc)


async def candidate_detail(tenant_id: str, user_id: str) -> dict:
    user = await _user(tenant_id, user_id)

    attempts = await database.attempts().find({"tenant_id": tenant_id, "user_id": user_id}).sort("started_at", -1).to_list(None)
    files = await database.files().find({"tenant_id": tenant_id, "user_id": user_id}).sort("created_at", -1).to_list(None)
    deterministic = await scoring_rules.scores_for_user(tenant_id, user)
    ai = await ai_scoring.ai_scores_for_user(tenant_id, user.id)
    try:
        summary = await reports.summary(tenant_id, user)
    except Exception:  # noqa: BLE001 — the dashboard should render even if a candidate has no scores yet
        summary = None
    resume = await profile_ai.latest(tenant_id, user_id)

    return {
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "status": user.status,
                 "created_at": user.created_at, "last_login_at": getattr(user, "last_login_at", None)},
        "entitlements": sorted(await commerce.owned_product_keys(tenant_id, user_id)),
        "attempts": [
            {"id": a["_id"], "assessment_key": a["assessment_key"], "status": a["status"],
             "submitted_at": a.get("submitted_at"), "started_at": a.get("started_at")}
            for a in attempts
        ],
        "scores": {**deterministic, **ai},
        "report": summary,
        "resume": resume,
        "interviews": await interview.for_candidate(tenant_id, user_id),
        "files": [
            {**file_public(f), "purpose": f.get("purpose"), "kind": f.get("kind"), "created_at": f.get("created_at")}
            for f in files
        ],
    }
