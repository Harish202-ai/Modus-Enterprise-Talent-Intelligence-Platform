"""Phase 11 (v5) admin upgrades — AI content drafting, file import, and the candidate dashboard."""
import io
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
from tests.conftest import default_tenant, make_user

QUESTIONS = {q["key"]: q["data"] for q in json.loads((Path(__file__).resolve().parent.parent / "seed" / "questions.json").read_text(encoding="utf-8"))["items"]}


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


async def candidate(client, email="dash@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Dana Dash", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"]]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h, user


@pytest.mark.asyncio
async def test_ai_drafts_content_for_the_admin(client, monkeypatch):
    _, admin = await make_user("admin@example.com", "admin")
    fake_ai(monkeypatch, {"data": {"title": "Can I get a refund?", "body": "Refunds are handled case by case — contact support.", "tags": ["refund", "billing"]}})
    r = await client.post("/v1/admin/content/support_kb/generate", json={"instruction": "Write a help entry about refunds"}, headers=admin)
    assert r.status_code == 200
    assert r.json()["data"]["title"] == "Can I get a refund?" and "refund" in r.json()["data"]["tags"]

    # The admin can then save it as a draft with the normal create endpoint.
    created = await client.post("/v1/admin/content/support_kb", json={"key": "refunds", "data": r.json()["data"]}, headers=admin)
    assert created.status_code == 201


@pytest.mark.asyncio
async def test_import_content_from_a_json_file(client):
    _, admin = await make_user("admin@example.com", "admin")
    payload = {"items": [
        {"key": "faq-hours", "data": {"title": "Opening hours", "body": "We're online 24/7.", "tags": ["hours"]}},
        {"key": "faq-contact", "data": {"title": "Contact", "body": "Email support.", "tags": ["contact"]}},
        {"key": "what-is-meti", "data": {"title": "dupe", "body": "x", "tags": []}},  # already seeded → skipped
        {"data": {"title": "no key"}},  # invalid → error
    ]}
    files = {"file": ("kb.json", io.BytesIO(json.dumps(payload).encode()), "application/json")}
    r = await client.post("/v1/admin/content/support_kb/import", headers=admin, files=files)
    assert r.status_code == 200
    body = r.json()
    assert set(body["created"]) == {"faq-hours", "faq-contact"} and body["skipped"] == ["what-is-meti"] and len(body["errors"]) == 1


@pytest.mark.asyncio
async def test_admin_candidate_dashboard(client):
    h, user = await candidate(client)
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    answers = {q["key"]: QUESTIONS[q["key"]]["scoring_rule"]["correct"] for s in a["definition"]["sections"] for q in s["questions"]}
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
    await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)

    _, admin = await make_user("admin@example.com", "admin")
    listing = (await client.get("/v1/admin/candidates", headers=admin)).json()["candidates"]
    row = next(c for c in listing if c["email"] == "dash@example.com")
    assert row["submitted_assessments"] == 1

    detail = (await client.get(f"/v1/admin/candidates/{user['_id']}", headers=admin)).json()
    assert detail["user"]["email"] == "dash@example.com"
    assert "bundle" in detail["entitlements"]
    assert detail["scores"]["capability"]["status"] == "scored" and detail["scores"]["capability"]["overall_pct"] == 100.0
    assert detail["report"]["scored"] is True
    assert any(att["assessment_key"] == "capability" and att["status"] == "submitted" for att in detail["attempts"])


@pytest.mark.asyncio
async def test_admin_upgrades_are_admin_only(client):
    h, _ = await candidate(client, "notadmin2@example.com")
    assert (await client.get("/v1/admin/candidates", headers=h)).status_code == 403
    assert (await client.post("/v1/admin/content/support_kb/generate", json={"instruction": "x y z"}, headers=h)).status_code == 403
    files = {"file": ("kb.json", io.BytesIO(b"[]"), "application/json")}
    assert (await client.post("/v1/admin/content/support_kb/import", headers=h, files=files)).status_code == 403
