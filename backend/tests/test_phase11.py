"""Phase 11 — Admin score governance (review queue + per-response override with a reason)."""
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.ai import provider
from app.main import app
from app.models.common import new_id, utcnow
from scripts.seed_content import seed
from tests.conftest import default_tenant, make_user


def fake_ai(monkeypatch, reply):
    async def _call(system, user, *, temperature, max_tokens):
        return reply if isinstance(reply, str) else json.dumps(reply)

    monkeypatch.setattr(provider, "_call", _call)


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="cand@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Cass Cand", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"]]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


async def submit_memo(client, h):
    a = (await client.post("/v1/assessments/written_communication/attempts", headers=h)).json()
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": {"WC-01": " ".join(["evidence"] * 160)}}, headers=h)
    await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)
    return a["id"]


@pytest.mark.asyncio
async def test_review_queue_and_override_with_reason(client, monkeypatch):
    fake_ai(monkeypatch, {"not": "valid"})  # invalid AI output both times → response goes to needs_review
    h = await candidate(client)
    attempt_id = await submit_memo(client, h)

    _, admin = await make_user("admin@example.com", "admin")
    queue = (await client.get("/v1/admin/scores/review", headers=admin)).json()["queue"]
    assert any(row["attempt_id"] == attempt_id for row in queue)

    override = {"reasoning_score": 70, "knowledge_score": 65, "communication_score": 80, "overall_confidence": 90, "reason": "Rescored after manual read — the memo is solid."}
    r = await client.post(f"/v1/admin/scores/{attempt_id}/responses/WC-01/override", json=override, headers=admin)
    assert r.status_code == 200
    resp = next(x for x in r.json()["result"]["responses"] if x["question_key"] == "WC-01")
    assert resp["status"] == "overridden" and resp["scores"]["reasoning_score"] == 70 and resp["override"]["reason"].startswith("Rescored")

    # The candidate now sees the overridden score on their report/scores.
    wc = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["written_communication"]
    assert wc["responses"][0]["scores"]["communication_score"] == 80

    approved = await client.post(f"/v1/admin/scores/{attempt_id}/approve", headers=admin)
    assert approved.status_code == 200
    # Audit trail records the override + approval.
    actions = [e["action"] async for e in database.audit_events().find({"entity_id": attempt_id, "action": {"$regex": "^score"}})]
    assert "score.overridden" in actions and "score.approved" in actions


@pytest.mark.asyncio
async def test_score_governance_is_admin_only(client):
    h = await candidate(client, "notadmin@example.com")
    assert (await client.get("/v1/admin/scores/review", headers=h)).status_code == 403
    assert (await client.post("/v1/admin/scores/x/approve", headers=h)).status_code == 403
