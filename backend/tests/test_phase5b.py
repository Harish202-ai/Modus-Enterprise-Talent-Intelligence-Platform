"""Phase 5 (v5 additions: uploads) + Phase 5b (AI Profile Understanding)."""
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
from tests.fixture_files import EMPTY_PDF, MP4_BYTES, make_docx

CV_TEXT = "\n".join(
    [
        "Priya Nair — Business Analyst",
        "Experience",
        "Senior Business Analyst, Northwind Bank, 2021 – Present",
        "Led process redesign of mortgage onboarding, cutting cycle time by 30%.",
        "Business Analyst, Contoso Retail, 2018 – 2021",
        "Mapped the order-to-cash value chain across 40 stores.",
        "Education: MBA, Institute of Management, 2018",
        "Skills: process mapping, stakeholder management, SQL, Power BI",
    ]
    * 2
)
PARSED = {
    "summary": "Business analyst with banking and retail experience.",
    "total_years_experience": 6,
    "roles": [
        {"title": "Senior Business Analyst", "organisation": "Northwind Bank", "start": "2021", "end": "Present", "highlights": ["Cut onboarding cycle time by 30%"]},
        {"title": "Business Analyst", "organisation": "Contoso Retail", "start": "2018", "end": "2021", "highlights": []},
    ],
    "industries": ["Banking", "Retail", "banking"],
    "skills": ["Process mapping", "Stakeholder management", "SQL", "Power BI"],
    "education": [{"qualification": "MBA", "institution": "Institute of Management", "year": 2018}],
}


def fake_ai(monkeypatch, *replies):
    """Replace the LLM call; each call returns the next reply (a dict → JSON, a string → raw text, an exception → raised)."""
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


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="cv@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Priya Nair", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ("bundle", "consulting_assessment", "personality_values"):
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h, user


def upload(name, data, ctype="application/octet-stream"):
    return {"file": (name, data, ctype)}


@pytest.mark.asyncio
async def test_definition_of_done_resume_upload_parse_review_confirm(client, monkeypatch):
    calls = fake_ai(monkeypatch, PARSED)
    h, user = await candidate(client)
    attempt = (await client.post("/v1/assessments/profile/attempts", headers=h)).json()
    first_q = attempt["definition"]["sections"][0]["questions"][0]
    assert first_q["key"] == "PRF-00" and first_q["type"] == "file_upload" and first_q["upload_role"] == "resume"

    r = await client.post(f"/v1/attempts/{attempt['id']}/files", params={"question_key": "PRF-00"}, headers=h, files=upload("Priya CV.docx", make_docx(CV_TEXT)))
    assert r.status_code == 200, r.text
    assert r.json()["answer"]["filename"] == "Priya CV.docx" and r.json()["resume_claim"]["status"] == "processing"
    assert (await database.users().find_one({"_id": user["_id"]}))["resume_file_id"] == r.json()["answer"]["file_id"]

    # The background parse has run: one AI call, fed the resume text, using the published prompt.
    claim = (await client.get("/v1/me/resume", headers=h)).json()["claim"]
    assert claim["status"] == "parsed" and claim["evidence_tier"] == "self_reported"
    assert claim["parsed"]["industries"] == ["Banking", "Retail"]  # de-duplicated
    assert claim["parsed"]["roles"][0]["organisation"] == "Northwind Bank" and claim["prompt_version"] == 1
    assert len(calls) == 1 and "Northwind Bank" in calls[0]["user"] and "protected or sensitive characteristics" in calls[0]["system"]

    # The candidate corrects it; the confirmed version is kept alongside what the AI parsed.
    edited = {**claim["parsed"], "total_years_experience": 7, "skills": claim["parsed"]["skills"] + ["Change management"]}
    r = await client.put(f"/v1/me/resume/{claim['id']}", json=edited, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "confirmed" and r.json()["confirmed"]["total_years_experience"] == 7
    stored = await database.evidence_claims().find_one({"_id": claim["id"]})
    assert stored["parsed"]["total_years_experience"] == 6 and stored["edited_by_candidate"] is True
    actions = [e["action"] async for e in database.audit_events().find({"candidate_id": user["_id"], "action": {"$regex": "^resume"}}).sort("timestamp", 1)]
    assert actions == ["resume.uploaded", "resume.parsed", "resume.confirmed"]


@pytest.mark.asyncio
async def test_ai_output_is_repaired_once_then_sent_to_review(client, monkeypatch):
    h, _ = await candidate(client)
    fake_ai(monkeypatch, "Sure! Here is the profile: not json", PARSED)  # bad, then repaired
    claim = (await client.post("/v1/me/resume", headers=h, files=upload("cv.docx", make_docx(CV_TEXT)))).json()
    assert (await client.get("/v1/me/resume", headers=h)).json()["claim"]["status"] == "parsed"

    calls = fake_ai(monkeypatch, {"roles": "not a list"})  # invalid both times
    claim = (await client.post("/v1/me/resume", headers=h, files=upload("cv2.docx", make_docx(CV_TEXT)))).json()
    got = (await client.get("/v1/me/resume", headers=h)).json()["claim"]
    assert got["id"] == claim["id"] and got["status"] == "needs_review" and got["parsed"] is None
    assert len(calls) == 2 and "could not be used" in calls[1]["user"]  # exactly one repair attempt


@pytest.mark.asyncio
async def test_without_ai_the_candidate_fills_it_in_and_can_retry(client, monkeypatch):
    h, _ = await candidate(client)  # AI_PROVIDER is empty in tests -> real _call raises AIUnavailable
    claim = (await client.post("/v1/me/resume", headers=h, files=upload("cv.docx", make_docx(CV_TEXT)))).json()
    got = (await client.get("/v1/me/resume", headers=h)).json()["claim"]
    assert got["status"] == "unavailable" and "fill in your details" in got["message"]

    fake_ai(monkeypatch, PARSED)
    assert (await client.post(f"/v1/me/resume/{claim['id']}/retry", headers=h)).status_code == 200
    assert (await client.get("/v1/me/resume", headers=h)).json()["claim"]["status"] == "parsed"

    manual = {"summary": None, "total_years_experience": 2, "roles": [{"title": "Analyst", "highlights": []}], "industries": ["Energy"], "skills": [], "education": []}
    r = await client.put(f"/v1/me/resume/{claim['id']}", json=manual, headers=h)
    assert r.json()["status"] == "confirmed" and r.json()["confirmed"]["industries"] == ["Energy"]
    assert (await client.put(f"/v1/me/resume/{claim['id']}", json={**manual, "total_years_experience": 99}, headers=h)).status_code == 422


@pytest.mark.asyncio
async def test_scanned_pdf_is_reported_as_unreadable(client, monkeypatch):
    calls = fake_ai(monkeypatch, PARSED)
    h, _ = await candidate(client)
    await client.post("/v1/me/resume", headers=h, files=upload("scan.pdf", EMPTY_PDF))
    got = (await client.get("/v1/me/resume", headers=h)).json()["claim"]
    assert got["status"] == "unreadable" and calls == []


@pytest.mark.asyncio
async def test_uploads_are_checked_by_content_type_and_size(client):
    h, _ = await candidate(client)
    bad = [
        ("cv.txt", b"plain text", "upload a PDF / DOCX file"),
        ("cv.pdf", b"MZ\x90\x00 this is an exe", "file content doesn't match its type"),
        ("cv.docx", b"%PDF-1.4 pretending", "file content doesn't match its type"),
        ("cv.pdf", b"%PDF-1.4 " + b"x" * (5 * 1024 * 1024 + 1), "must be under 5 MB"),
    ]
    for name, data, message in bad:
        r = await client.post("/v1/me/resume", headers=h, files=upload(name, data))
        assert r.status_code == 422 and r.json()["errors"][0]["message"] == message, (name, r.text)
    assert await database.files().count_documents({}) == 0


@pytest.mark.asyncio
async def test_communication_video_and_case_document_answers(client):
    h, _ = await candidate(client)
    wc = (await client.post("/v1/assessments/written_communication/attempts", headers=h)).json()
    q = wc["definition"]["sections"][0]["questions"][0]
    assert q["type"] == "free_text" and q["upload_kinds"] == ["mp4", "mov", "webm"]

    # A document isn't accepted where a video is expected; a video is.
    r = await client.post(f"/v1/attempts/{wc['id']}/files", params={"question_key": "WC-01"}, headers=h, files=upload("memo.docx", make_docx("memo")))
    assert r.status_code == 422
    r = await client.post(f"/v1/attempts/{wc['id']}/files", params={"question_key": "WC-01"}, headers=h, files=upload("pitch.mp4", MP4_BYTES))
    assert r.status_code == 200 and r.json()["progress"]["answered"] == 1
    # File answers can't be forged through autosave.
    forged = {"WC-01": {"file_id": "someone-elses-file", "filename": "x.mp4", "kind": "mp4", "size": 1}}
    assert (await client.put(f"/v1/attempts/{wc['id']}/answers", json={"answers": forged}, headers=h)).status_code == 422
    assert (await client.post(f"/v1/attempts/{wc['id']}/submit", headers=h)).json()["status"] == "submitted"

    case = (await client.post("/v1/assessments/case_study/attempts", headers=h)).json()
    await client.put(f"/v1/attempts/{case['id']}/answers", json={"answers": {"CASE-01": " ".join(["issue tree"] * 70)}}, headers=h)
    r = await client.post(f"/v1/attempts/{case['id']}/files", params={"question_key": "CASE-02"}, headers=h, files=upload("recommendation.docx", make_docx("Option A vs B")))
    assert r.status_code == 200
    assert (await client.post(f"/v1/attempts/{case['id']}/submit", headers=h)).json()["status"] == "submitted"
    # Questions without uploads refuse files.
    cap = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    assert (await client.post(f"/v1/attempts/{cap['id']}/files", params={"question_key": "CAP-01"}, headers=h, files=upload("x.pdf", EMPTY_PDF))).status_code == 422


@pytest.mark.asyncio
async def test_files_are_private_to_owner_and_admin(client):
    h, _ = await candidate(client)
    claim = (await client.post("/v1/me/resume", headers=h, files=upload("cv.docx", make_docx(CV_TEXT)))).json()
    file_id = claim["file"]["id"]
    r = await client.get(f"/v1/files/{file_id}", headers=h)
    assert r.status_code == 200 and r.content[:2] == b"PK" and "cv.docx" in r.headers["content-disposition"]
    other, _ = await candidate(client, "other@example.com")
    assert (await client.get(f"/v1/files/{file_id}", headers=other)).status_code == 404
    _, admin = await make_user("admin@example.com", "admin")
    assert (await client.get(f"/v1/files/{file_id}", headers=admin)).status_code == 200


@pytest.mark.asyncio
async def test_seed_republishes_seed_owned_content_when_references_move(client):
    from app.content.registry import get_type
    from app.services import content

    tenant = await default_tenant()
    qtype = get_type("questions")
    # A newer published version of a question the seed owns (as if a previous release changed it)…
    await content.new_version(qtype, tenant.id, "PRF-01", "seed")
    await content.publish(qtype, tenant.id, "PRF-01", "seed")
    summary = await seed()
    # …so the section pinning it and the assessment pinning that section are republished.
    assert summary["sections"]["updated"] == 1 and summary["assessments"]["updated"] == 1
    current = await content.get_current(get_type("assessments"), tenant.id, "profile")
    section = await content.get_version(get_type("sections"), tenant.id, "prf_background", current.ref_versions["sections"]["prf_background"])
    assert section.ref_versions["questions"]["PRF-01"] == 2
    assert (await seed())["sections"]["updated"] == 0  # stable afterwards
