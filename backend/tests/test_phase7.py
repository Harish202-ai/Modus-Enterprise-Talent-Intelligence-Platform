"""Phase 7 — AI Scoring Service (Reasoning / Knowledge / Communication with cited evidence).

Pure tests cover the response-text extraction and the output schema; the rest drives a real submit
with the LLM faked (as everywhere in the suite) and checks that every scored response returns all
three named dimensions with evidence — and that a video answer, an unreachable provider and a
rescore all behave.
"""
import io
import json
import zipfile

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.ai import provider
from app.main import app
from app.models.common import new_id, utcnow
from app.services import ai_scoring
from scripts.seed_content import seed
from tests.conftest import default_tenant
from tests.fixture_files import MP4_BYTES, make_docx

# A valid AI reply matching the v5 Phase 7 schema.
SCORE = {
    "reasoning_score": 78,
    "reasoning_evidence": "Breaks the late-delivery rise into root causes tied to the new system.",
    "knowledge_score": 71,
    "knowledge_evidence": "Correctly links the 11% failure rate to the warehouse go-live.",
    "communication_score": 85,
    "communication_evidence": "Leads with a clear 90-day recommendation, then three supporting points.",
    "overall_confidence": 88,
}


def fake_ai(monkeypatch, *replies):
    calls = []
    queue = list(replies)

    async def _call(system, user, *, temperature, max_tokens):
        calls.append({"system": system, "user": user})
        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)

    monkeypatch.setattr(provider, "_call", _call)
    return calls


def words(n: int, token: str = "structured") -> str:
    return " ".join([token] * n)


# --- pure ------------------------------------------------------------------------------------

def test_pptx_text_extraction():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ppt/slides/slide1.xml", "<p:sld><a:t>Recommendation:</a:t><a:t>close 20 branches</a:t></p:sld>")
        z.writestr("ppt/slides/slide2.xml", "<p:sld><a:t>Risk &amp; mitigation</a:t></p:sld>")
        z.writestr("docProps/app.xml", "<props/>")  # ignored — not a slide
    text = ai_scoring._pptx_text(buf.getvalue())
    assert text == "Recommendation:\nclose 20 branches\nRisk & mitigation"


def test_ai_score_schema_clamps_and_trims():
    s = ai_scoring.AIScore.model_validate(
        {**SCORE, "reasoning_score": 150, "knowledge_score": -5, "communication_score": "83", "reasoning_evidence": "  spaced\n\nout  "}
    )
    assert s.reasoning_score == 100 and s.knowledge_score == 0 and s.communication_score == 83
    assert s.reasoning_evidence == "spaced out"


def test_user_prompt_carries_the_rubric_and_response():
    rubric = {"name": "Executive Memo", "dimensions": [{"key": "communication", "name": "Communication", "weight": 0.5,
              "anchors": [{"level": 75, "descriptor": "Leads with a clear recommendation."}]}]}
    prompt = ai_scoring._build_user_prompt({"prompt": "Write a memo"}, rubric, ["Executive Communication"], "My recommendation is…")
    assert "Write a memo" in prompt and "Executive Communication" in prompt
    assert "Leads with a clear recommendation." in prompt and "My recommendation is…" in prompt


# --- end to end ------------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="writer@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Wren Writer", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"]]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


async def _start(client, h, code):
    return (await client.post(f"/v1/assessments/{code}/attempts", headers=h)).json()["id"]


@pytest.mark.asyncio
async def test_seed_publishes_rubrics_and_pins_them_on_the_free_text_questions(client):
    from app.content.registry import get_type
    from app.services import content

    tenant = await default_tenant()
    assert (await content.get_current(get_type("rubrics"), tenant.id, "memo")).data["dimensions"][0]["key"] == "communication"
    assert (await content.get_current(get_type("prompts"), tenant.id, "scoring")).data["system_prompt"].startswith("You are an assessor")
    wc = await content.get_current(get_type("questions"), tenant.id, "WC-01")
    assert wc.data["rubric_key"] == "memo" and wc.ref_versions["rubrics"]["memo"] >= 1


@pytest.mark.asyncio
async def test_definition_of_done_three_named_dimensions_with_evidence(client, monkeypatch):
    calls = fake_ai(monkeypatch, SCORE)
    h = await candidate(client)
    a = await _start(client, h, "written_communication")
    await client.put(f"/v1/attempts/{a}/answers", json={"answers": {"WC-01": words(160)}}, headers=h)
    assert (await client.post(f"/v1/attempts/{a}/submit", headers=h)).json()["status"] == "submitted"

    scores = (await client.get("/v1/me/scores", headers=h)).json()["scores"]
    wc = scores["written_communication"]
    assert wc["status"] == "scored" and len(wc["responses"]) == 1
    r = wc["responses"][0]
    assert r["question_key"] == "WC-01" and r["status"] == "scored"
    # All three named dimensions, each with cited evidence — not one opaque number.
    for dim in ("reasoning", "knowledge", "communication"):
        assert isinstance(r["scores"][f"{dim}_score"], int) and r["scores"][f"{dim}_evidence"]
    assert r["scores"]["overall_confidence"] == 88 and r["rubric_key"] == "memo"
    # One AI call for one response, fed the rubric + the candidate's words.
    assert len(calls) == 1 and "Executive Memo" in calls[0]["user"] and "CANDIDATE RESPONSE" in calls[0]["user"]


@pytest.mark.asyncio
async def test_case_scores_each_response_typed_or_uploaded(client, monkeypatch):
    calls = fake_ai(monkeypatch, SCORE)
    h = await candidate(client)
    a = await _start(client, h, "case_study")
    await client.put(f"/v1/attempts/{a}/answers", json={"answers": {"CASE-01": words(130, "hypothesis")}}, headers=h)
    await client.post(f"/v1/attempts/{a}/files", params={"question_key": "CASE-02"}, headers=h,
                      files={"file": ("recommendation.docx", make_docx("Option A: keep branches. Option B: go digital. I recommend B because " + words(40)), "application/octet-stream")})
    assert (await client.post(f"/v1/attempts/{a}/submit", headers=h)).json()["status"] == "submitted"

    case = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["case_study"]
    assert case["status"] == "scored" and {r["question_key"] for r in case["responses"]} == {"CASE-01", "CASE-02"}
    assert all(r["scores"]["reasoning_score"] == 78 for r in case["responses"])
    assert len(calls) == 2  # one AI call per response


@pytest.mark.asyncio
async def test_video_answer_waits_for_transcription(client, monkeypatch):
    calls = fake_ai(monkeypatch, SCORE)
    h = await candidate(client)
    a = await _start(client, h, "written_communication")
    await client.post(f"/v1/attempts/{a}/files", params={"question_key": "WC-01"}, headers=h, files={"file": ("pitch.mp4", MP4_BYTES, "video/mp4")})
    await client.post(f"/v1/attempts/{a}/submit", headers=h)

    wc = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["written_communication"]
    assert wc["status"] == "needs_transcript"
    assert wc["responses"][0]["status"] == "needs_transcript" and "Phase 8" in wc["responses"][0]["message"]
    assert calls == []  # a video is never sent to the text scorer


@pytest.mark.asyncio
async def test_provider_outage_leaves_pending_then_rescore_recovers(client, monkeypatch):
    h = await candidate(client)  # AI_PROVIDER empty in tests → real _call raises AIUnavailable
    a = await _start(client, h, "written_communication")
    await client.put(f"/v1/attempts/{a}/answers", json={"answers": {"WC-01": words(160)}}, headers=h)
    await client.post(f"/v1/attempts/{a}/submit", headers=h)

    wc = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["written_communication"]
    assert wc["status"] == "pending" and wc["responses"][0]["status"] == "pending"

    fake_ai(monkeypatch, SCORE)
    rescored = (await client.post("/v1/me/scores/written_communication/rescore", headers=h)).json()
    assert rescored["status"] == "scored" and rescored["responses"][0]["scores"]["overall_confidence"] == 88
    assert (await client.post("/v1/me/scores/talent_dna/rescore", headers=h)).status_code == 404  # not an AI-scored form


@pytest.mark.asyncio
async def test_ai_scores_are_private_and_unsubmitted_reports_not_submitted(client, monkeypatch):
    fake_ai(monkeypatch, SCORE)
    h = await candidate(client)
    a = await _start(client, h, "written_communication")
    await client.put(f"/v1/attempts/{a}/answers", json={"answers": {"WC-01": words(160)}}, headers=h)
    await client.post(f"/v1/attempts/{a}/submit", headers=h)

    other = await candidate(client, "nosy2@example.com")
    mine = (await client.get("/v1/me/scores", headers=h)).json()["scores"]
    theirs = (await client.get("/v1/me/scores", headers=other)).json()["scores"]
    assert mine["written_communication"]["status"] == "scored"
    assert theirs["written_communication"]["status"] == "not_submitted"
    assert theirs["case_study"]["status"] == "not_submitted"
