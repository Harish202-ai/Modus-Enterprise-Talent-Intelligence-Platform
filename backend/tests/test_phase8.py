"""Phase 8 — Composite scores, Reports & AI Explainer (Why / Coach), voice capability."""
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.ai import provider
from app.main import app
from app.models.common import new_id, utcnow
from app.services import composite
from scripts.seed_content import seed
from tests.conftest import default_tenant

SEED_QUESTIONS = json.loads((__import__("pathlib").Path(__file__).resolve().parent.parent / "seed" / "questions.json").read_text(encoding="utf-8"))
QUESTIONS = {q["key"]: q["data"] for q in SEED_QUESTIONS["items"]}

AISCORE = {"reasoning_score": 72, "reasoning_evidence": "clear structure", "knowledge_score": 66, "knowledge_evidence": "sound",
           "communication_score": 80, "communication_evidence": "answer-first", "overall_confidence": 85}


def fake_ai(monkeypatch, *replies):
    queue = list(replies)

    async def _call(system, user, *, temperature, max_tokens):
        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)

    monkeypatch.setattr(provider, "_call", _call)


# --- pure composite --------------------------------------------------------------------------

def test_composite_renormalises_over_present_components():
    only_cap = composite.compute({"capability": {"status": "scored", "overall_pct": 80.0}})
    assert only_cap["readiness"] == 80.0  # single component → its own value
    assert only_cap["readiness_components"] == {"capability": 80.0}

    none = composite.compute({"capability": {"status": "not_submitted"}})
    assert none["readiness"] is None and none["evidence_confidence"] == 0.0


def test_evidence_confidence_scales_with_coverage_and_ai_confidence():
    full = composite.compute({
        "talent_dna": {"status": "scored", "dimensions": [{"normalized": 50.0}]},
        "values": {"status": "scored"}, "capability": {"status": "scored", "overall_pct": 60.0},
        "written_communication": {"status": "scored", "responses": [{"status": "scored", "scores": AISCORE}]},
        "case_study": {"status": "scored", "responses": [{"status": "scored", "scores": AISCORE}]},
    })
    assert full["evidence_coverage"] == 100.0
    assert full["evidence_confidence"] == round((0.5 + 0.5 * 0.85) * 100, 1)  # coverage 1.0 × confidence factor


def test_band_thresholds():
    assert composite.band(80) == "strong" and composite.band(60) == "developing well"
    assert composite.band(40) == "emerging" and composite.band(10) == "early" and composite.band(None) == "not yet scored"


# --- end to end ------------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="report@example.com", upgrade=False):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Remy Report", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    keys = ["bundle", *products["bundle"]["bundled_product_keys"]] + (["detailed_report"] if upgrade else [])
    for key in keys:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


async def submit(client, h, code):
    a = (await client.post(f"/v1/assessments/{code}/attempts", headers=h)).json()
    answers = {}
    for s in a["definition"]["sections"]:
        for q in s["questions"]:
            qd = QUESTIONS[q["key"]]
            keys = [o["key"] for o in qd.get("options", [])]
            answers[q["key"]] = keys[-1] if qd["type"] in ("single_choice", "likert") else keys if qd["type"] == "rank" else " ".join(["evidence"] * 160)
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
    assert (await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)).status_code == 200
    return a["id"]


@pytest.mark.asyncio
async def test_summary_of_findings_after_a_scored_assessment(client, monkeypatch):
    fake_ai(monkeypatch, AISCORE)
    h = await candidate(client)
    await submit(client, h, "capability")
    await submit(client, h, "written_communication")

    report = (await client.get("/v1/me/report", headers=h)).json()["report"]
    assert report["type"] == "summary" and report["scored"] is True
    assert report["readiness"] is not None and report["readiness_band"]
    assert report["strengths"] and report["development_themes"]
    assert report["has_detailed_report"] is False


@pytest.mark.asyncio
async def test_detailed_report_is_gated_by_the_upgrade(client, monkeypatch):
    fake_ai(monkeypatch, AISCORE)
    h = await candidate(client)  # no upgrade
    await submit(client, h, "capability")
    assert (await client.get("/v1/me/report/detailed", headers=h)).status_code == 402

    up = await candidate(client, "up@example.com", upgrade=True)
    await submit(client, up, "capability")
    await submit(client, up, "written_communication")
    detailed = (await client.get("/v1/me/report/detailed", headers=up)).json()["report"]
    assert detailed["type"] == "detailed" and detailed["has_detailed_report"] is True
    assert detailed["composite"]["readiness"] is not None
    assert detailed["capability"]["status"] == "scored" and detailed["written_communication"]["status"] == "scored"


@pytest.mark.asyncio
async def test_explainer_is_grounded_and_degrades_without_ai(client, monkeypatch):
    h = await candidate(client)
    await submit(client, h, "capability")

    # No AI configured → honest "not available", never invented.
    down = (await client.post("/v1/me/explainer", json={"question": "why is this my score?"}, headers=h)).json()
    assert down["available"] is False and "isn't available" in down["answer"]

    # With AI, the answer comes back and the model was given the candidate's own locked context.
    captured = {}

    async def _call(system, user, *, temperature, max_tokens):
        captured["user"] = user
        return json.dumps({"answer": "Your capability score reflects strong structuring."})

    monkeypatch.setattr(provider, "_call", _call)
    ans = (await client.post("/v1/me/explainer", json={"question": "why?", "mode": "why"}, headers=h)).json()
    assert ans["available"] is True and ans["mode"] == "why" and "structuring" in ans["answer"]
    assert "Readiness:" in captured["user"] and "CANDIDATE QUESTION" in captured["user"]

    coach = (await client.post("/v1/me/explainer", json={"question": "what next?", "mode": "coach"}, headers=h)).json()
    assert coach["mode"] == "coach" and coach["available"] is True


@pytest.mark.asyncio
async def test_voice_capability_defaults_to_webspeech(client):
    h = await candidate(client)
    cap = (await client.get("/v1/me/voice", headers=h)).json()
    assert cap["provider"] == "webspeech" and cap["configured"] is True
