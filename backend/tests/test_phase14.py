"""Phase 14 — end-to-end smoke test: register → pay (granted) → assess → score → report → roadmap,
plus the public support bot never touches candidate data. One pass through the whole journey."""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.ai import provider
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


@pytest.mark.asyncio
async def test_health_reports_stores_up(client):
    health = (await client.get("/health")).json()
    assert health["status"] == "ok" and health["checks"]["mongo"] == "up" and health["checks"]["redis"] == "up"


@pytest.mark.asyncio
async def test_full_candidate_journey(client, monkeypatch):
    async def _call(system, user, *, temperature, max_tokens):
        return json.dumps({"reasoning_score": 75, "reasoning_evidence": "structured", "knowledge_score": 70,
                           "knowledge_evidence": "sound", "communication_score": 82, "communication_evidence": "clear",
                           "overall_confidence": 88})

    monkeypatch.setattr(provider, "_call", _call)

    # Register + grant the bundle and the report upgrade (payment itself is covered by the Phase 4 tests).
    r = await client.post("/v1/auth/register", json={"email": "journey@example.com", "full_name": "Jo Journey", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": "journey@example.com"})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"], "detailed_report"]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})

    # Assess: capability (deterministic) + the memo (AI).
    for code, choose in (("capability", lambda k: QUESTIONS[k]["scoring_rule"]["correct"]), ("written_communication", lambda k: " ".join(["evidence"] * 160))):
        a = (await client.post(f"/v1/assessments/{code}/attempts", headers=h)).json()
        answers = {q["key"]: choose(q["key"]) for s in a["definition"]["sections"] for q in s["questions"]}
        await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
        assert (await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)).status_code == 200

    # Scores, report, detailed report, roadmap all resolve.
    scores = (await client.get("/v1/me/scores", headers=h)).json()["scores"]
    assert scores["capability"]["overall_pct"] == 100.0 and scores["written_communication"]["status"] == "scored"

    report = (await client.get("/v1/me/report", headers=h)).json()["report"]
    assert report["scored"] and report["readiness"] is not None and report["has_detailed_report"]

    detailed = (await client.get("/v1/me/report/detailed", headers=h)).json()["report"]
    assert detailed["type"] == "detailed"

    roadmap = (await client.get("/v1/me/roadmap", headers=h)).json()["roadmap"]
    assert roadmap["milestones"]

    # Public support bot answers a general question and never needs a login or candidate data.
    support = (await client.post("/v1/support/chat", json={"question": "how is my data used?"})).json()
    assert support["grounded"] and support["sources"]
