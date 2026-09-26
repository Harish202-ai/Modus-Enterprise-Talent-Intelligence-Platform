"""Phase 9 — Development Roadmap (gated by the upgrade; generated from the candidate's gaps)."""
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


async def candidate(client, email="roadmap@example.com", upgrade=True):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Rory Roadmap", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    keys = ["bundle", *products["bundle"]["bundled_product_keys"]] + (["detailed_report"] if upgrade else [])
    for key in keys:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


async def submit_capability(client, h):
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    # Answer the first option throughout — mostly wrong, so there are real gaps to build a roadmap from.
    answers = {q["key"]: "A" for s in a["definition"]["sections"] for q in s["questions"]}
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
    await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)


@pytest.mark.asyncio
async def test_roadmap_is_gated_and_generated_from_gaps(client):
    no_up = await candidate(client, "noup@example.com", upgrade=False)
    await submit_capability(client, no_up)
    assert (await client.get("/v1/me/roadmap", headers=no_up)).status_code == 402

    h = await candidate(client)
    await submit_capability(client, h)
    roadmap = (await client.get("/v1/me/roadmap", headers=h)).json()["roadmap"]
    assert roadmap["milestones"] and all({"week", "title", "actions", "resource"} <= set(m) for m in roadmap["milestones"])
    assert roadmap["reassessment_schedule"] and "weeks" in roadmap["reassessment_schedule"]
    # Persisted one-per-candidate.
    assert await database.roadmaps().count_documents({"user_id": (await database.users().find_one({"email": "roadmap@example.com"}))["_id"]}) == 1


@pytest.mark.asyncio
async def test_regenerate_rebuilds_from_current_results(client):
    h = await candidate(client)
    await submit_capability(client, h)
    first = (await client.get("/v1/me/roadmap", headers=h)).json()["roadmap"]
    again = (await client.post("/v1/me/roadmap/regenerate", headers=h)).json()["roadmap"]
    assert again["milestones"] and len(again["milestones"]) == len(first["milestones"])


@pytest.mark.asyncio
async def test_coach_explainer_grounds_on_the_roadmap(client, monkeypatch):
    h = await candidate(client)
    await submit_capability(client, h)
    captured = {}

    async def _call(system, user, *, temperature, max_tokens):
        captured["user"] = user
        return json.dumps({"answer": "Start with the first milestone."})

    monkeypatch.setattr(provider, "_call", _call)
    ans = (await client.post("/v1/me/explainer", json={"question": "what should I do first?", "mode": "coach"}, headers=h)).json()
    assert ans["available"] is True and ans["mode"] == "coach"
    assert "ROADMAP:" in captured["user"] and "Week 1" in captured["user"]
