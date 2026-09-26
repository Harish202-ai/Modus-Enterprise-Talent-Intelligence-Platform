"""Phase 13 — Reassessment & Progress (retake without losing the prior attempt; before/after)."""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.main import app
from app.models.common import new_id, utcnow
from scripts.seed_content import seed
from tests.conftest import default_tenant

QUESTIONS = {q["key"]: q["data"] for q in json.loads((Path(__file__).resolve().parent.parent / "seed" / "questions.json").read_text(encoding="utf-8"))["items"]}


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="again@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Ada Again", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"]]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


async def submit_capability(client, h, choose):
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    answers = {q["key"]: choose(q["key"]) for s in a["definition"]["sections"] for q in s["questions"]}
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
    r = await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)
    assert r.status_code == 200
    return a["id"]


@pytest.mark.asyncio
async def test_retake_creates_a_new_attempt_and_progress_shows_before_after(client):
    h = await candidate(client)
    # First attempt: everything "A" (mostly wrong).
    first = await submit_capability(client, h, lambda k: "A")
    prog = (await client.get("/v1/me/progress/capability", headers=h)).json()
    assert prog["attempts"] == 1 and prog["status"] == "single"

    # Retake: the correct option for each question → a higher score, prior attempt preserved.
    second = await submit_capability(client, h, lambda k: QUESTIONS[k]["scoring_rule"]["correct"])
    assert first != second
    user = await database.users().find_one({"email": "again@example.com"})
    assert await database.attempts().count_documents({"user_id": user["_id"], "assessment_key": "capability", "status": "submitted"}) == 2

    prog = (await client.get("/v1/me/progress/capability", headers=h)).json()
    assert prog["attempts"] == 2 and prog["status"] == "compared"
    overall = next(r for r in prog["rows"] if r["key"] == "__overall__")
    assert overall["after"] == 100.0 and overall["before"] < overall["after"] and overall["delta"] > 0

    # /me/scores reflects the latest (improved) attempt.
    assert (await client.get("/v1/me/scores", headers=h)).json()["scores"]["capability"]["overall_pct"] == 100.0


@pytest.mark.asyncio
async def test_progress_overview_lists_submitted_assessments(client):
    h = await candidate(client)
    await submit_capability(client, h, lambda k: "A")
    overview = (await client.get("/v1/me/progress", headers=h)).json()["progress"]
    cap = next(r for r in overview if r["assessment_key"] == "capability")
    assert cap["attempts"] == 1 and cap["can_compare"] is False
