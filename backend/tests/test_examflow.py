"""Exam flow — the candidate can Skip questions and still submit; skipped knowledge items score as
wrong. Submitting with an unanswered, un-skipped question is still rejected (unchanged contract)."""
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
CAP_KEYS = [k for k, d in QUESTIONS.items() if k.startswith("CAP-")]


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="exam@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Ed Exam", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"]]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


@pytest.mark.asyncio
async def test_skip_lets_you_submit_and_skipped_questions_score_as_wrong(client):
    h = await candidate(client)
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()

    # Answer the first 5 correctly, leave the other 15 unanswered.
    answered = {k: QUESTIONS[k]["scoring_rule"]["correct"] for k in CAP_KEYS[:5]}
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answered}, headers=h)

    # Without skipping, submit is rejected for the 15 unanswered questions (contract unchanged).
    r = await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)
    assert r.status_code == 422 and len(r.json()["errors"]) == 15

    # Explicitly skipping the rest lets the exam be submitted.
    r = await client.post(f"/v1/attempts/{a['id']}/submit", json={"skipped": CAP_KEYS[5:]}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "submitted"

    # Skipped knowledge questions count as wrong: 5 correct out of 20 = 25%.
    cap = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["capability"]
    assert cap["total"] == 20 and cap["correct"] == 5 and cap["overall_pct"] == 25.0


@pytest.mark.asyncio
async def test_answering_a_question_unskips_it(client):
    # Skipping a question you later answer still records the answer (the skip list only covers blanks).
    h = await candidate(client)
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    answered = {k: QUESTIONS[k]["scoring_rule"]["correct"] for k in CAP_KEYS}  # all correct
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answered}, headers=h)
    # Pass a stale skip for an answered question — submit still records the answer, not a skip.
    r = await client.post(f"/v1/attempts/{a['id']}/submit", json={"skipped": [CAP_KEYS[0]]}, headers=h)
    assert r.status_code == 200
    cap = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["capability"]
    assert cap["correct"] == 20 and cap["overall_pct"] == 100.0
