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
from tests.fixture_files import make_docx

SEED = Path(__file__).resolve().parent.parent / "seed"
QUESTIONS = {q["key"]: q["data"] for q in json.loads((SEED / "questions.json").read_text(encoding="utf-8"))["items"]}
FORMS = {a["key"]: a["data"]["section_keys"] for a in json.loads((SEED / "assessments.json").read_text(encoding="utf-8"))["items"]}


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="runner@example.com", product="bundle"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Rae Runner", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if product:  # grant the product directly (payment itself is covered by the Phase 4 tests)
        user = await database.users().find_one({"email": email})
        products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
        for key in [product, *products[product]["bundled_product_keys"]]:
            await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                      "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                      "granted_at": utcnow(), "revoked_at": None})
    return h


def valid_answer(q: dict):
    keys = [o["key"] for o in q.get("options", [])]
    if q["type"] in ("single_choice", "likert"):
        return keys[-1]
    if q["type"] == "multi_select":
        return keys[: q.get("min_selections") or 1]
    if q["type"] == "rank":
        return list(reversed(keys))
    return " ".join(["evidence"] * max(q.get("min_words") or 1, 5))


@pytest.mark.asyncio
async def test_definition_of_done_all_seven_forms_run_through_one_engine(client):
    h = await candidate(client)
    home = (await client.get("/v1/me/assessments", headers=h)).json()
    assert [r["key"] for r in home] == ["profile", "motivation", "capability", "written_communication", "case_study", "talent_dna", "values"]
    assert {r["status"] for r in home} == {"not_started"}

    for form in FORMS:
        attempt = (await client.post(f"/v1/assessments/{form}/attempts", headers=h)).json()
        questions = [q for s in attempt["definition"]["sections"] for q in s["questions"]]
        # Candidates never see answer keys or scoring maps.
        for q in questions:
            assert not {"scoring_rule", "competency_map", "value_map", "rubric_key"} & set(q)
            assert all(set(o) == {"key", "label"} for o in q.get("options", []))
        for q in questions:
            if q["type"] == "file_upload":
                r = await client.post(f"/v1/attempts/{attempt['id']}/files", params={"question_key": q["key"]}, headers=h,
                                      files={"file": ("cv.docx", make_docx("Consultant\n" * 60), "application/octet-stream")})
                assert r.status_code == 200, r.text
        answers = {q["key"]: valid_answer(QUESTIONS[q["key"]]) for q in questions if q["type"] != "file_upload"}
        saved = (await client.put(f"/v1/attempts/{attempt['id']}/answers", json={"answers": answers}, headers=h)).json()
        assert saved["progress"]["answered"] == saved["progress"]["total"] == len(questions)
        r = await client.post(f"/v1/attempts/{attempt['id']}/submit", headers=h)
        assert r.status_code == 200 and r.json()["status"] == "submitted", (form, r.text)

    assert {r["status"] for r in (await client.get("/v1/me/assessments", headers=h)).json()} == {"submitted"}


@pytest.mark.asyncio
async def test_autosave_and_resume_from_another_device(client):
    h = await candidate(client)
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    r = await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": {"CAP-01": "B", "CAP-02": "C"}, "current_section_key": "cap_strategy"}, headers=h)
    assert r.status_code == 200 and r.json()["progress"] == {"answered": 2, "total": 20, "skipped_sections": []}

    # "Another device": sign in again (new token), start again -> the same attempt, answers intact.
    login = await client.post("/v1/auth/login", json={"email": "runner@example.com", "password": "Consult1ng"})
    h2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
    again = (await client.post("/v1/assessments/capability/attempts", headers=h2)).json()
    assert again["id"] == a["id"] and again["answers"] == {"CAP-01": "B", "CAP-02": "C"} and again["current_section_key"] == "cap_strategy"

    # Partial free text autosaves before it meets the word count; clearing an answer works.
    wc = (await client.post("/v1/assessments/written_communication/attempts", headers=h)).json()
    assert (await client.put(f"/v1/attempts/{wc['id']}/answers", json={"answers": {"WC-01": "Draft opening…"}}, headers=h)).status_code == 200
    r = await client.post(f"/v1/attempts/{wc['id']}/submit", headers=h)
    assert r.status_code == 422 and r.json()["errors"][0]["message"].startswith("write at least 150 words")
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": {"CAP-02": None}}, headers=h)
    assert (await client.get(f"/v1/attempts/{a['id']}", headers=h)).json()["answers"] == {"CAP-01": "B"}


@pytest.mark.asyncio
async def test_answer_validation_for_the_five_types(client):
    h = await candidate(client)
    prof = (await client.post("/v1/assessments/profile/attempts", headers=h)).json()["id"]
    td = (await client.post("/v1/assessments/talent_dna/attempts", headers=h)).json()["id"]

    bad = [
        (prof, {"PRF-01": "Z"}, "choose one of the options"),
        (prof, {"PRF-03": ["fin", "fin"]}, "contains an unknown or repeated option"),
        (prof, {"PRF-07": 42}, "must be text"),
        (prof, {"NOPE": "A"}, "is not a question in this assessment"),
        (td, {"TD-01": ["A", "X"]}, "contains an unknown or repeated option"),
    ]
    for attempt_id, answers, message in bad:
        r = await client.put(f"/v1/attempts/{attempt_id}/answers", json={"answers": answers}, headers=h)
        assert r.status_code == 422 and r.json()["errors"][0]["message"] == message, (answers, r.text)

    # Shape-valid but incomplete answers are saved, then reported at submit.
    await client.put(f"/v1/attempts/{prof}/answers", json={"answers": {"PRF-03": ["fin", "tech", "mfg", "retail"]}}, headers=h)
    await client.put(f"/v1/attempts/{td}/answers", json={"answers": {"TD-01": ["A", "B"]}}, headers=h)
    errors = {e["field"]: e["message"] for e in (await client.post(f"/v1/attempts/{prof}/submit", headers=h)).json()["errors"]}
    assert errors["PRF-03"] == "choose between 1 and 3 options" and errors["PRF-01"] == "not answered yet"
    errors = {e["field"]: e["message"] for e in (await client.post(f"/v1/attempts/{td}/submit", headers=h)).json()["errors"]}
    assert errors["TD-01"] == "rank every option exactly once"


@pytest.mark.asyncio
async def test_skip_rule_removes_programme_section_for_people_without_experience(client):
    h = await candidate(client)
    a = (await client.post("/v1/assessments/profile/attempts", headers=h)).json()
    base = {"PRF-01": "A", "PRF-03": ["tech"], "PRF-04": "A", "PRF-06": "A"}
    cv = {"file": ("cv.docx", make_docx("Analyst\n" * 60), "application/octet-stream")}
    await client.post(f"/v1/attempts/{a['id']}/files", params={"question_key": "PRF-00"}, headers=h, files=cv)

    r = await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": {**base, "PRF-02": "A"}}, headers=h)
    assert r.json()["progress"] == {"answered": 6, "total": 6, "skipped_sections": ["prf_programme"]}
    done = (await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)).json()
    assert done["status"] == "submitted"  # PRF-05 / PRF-07 not required once skipped

    h2 = await candidate(client, "experienced@example.com")
    b = (await client.post("/v1/assessments/profile/attempts", headers=h2)).json()
    await client.post(f"/v1/attempts/{b['id']}/files", params={"question_key": "PRF-00"}, headers=h2, files=cv)
    r = await client.put(f"/v1/attempts/{b['id']}/answers", json={"answers": {**base, "PRF-02": "C"}}, headers=h2)
    assert r.json()["progress"]["total"] == 8 and r.json()["progress"]["skipped_sections"] == []
    fields = {e["field"] for e in (await client.post(f"/v1/attempts/{b['id']}/submit", headers=h2)).json()["errors"]}
    assert fields == {"PRF-05", "PRF-07"}


@pytest.mark.asyncio
async def test_submitted_attempts_are_locked_and_attempts_are_private(client):
    h = await candidate(client)
    a = (await client.post("/v1/assessments/talent_dna/attempts", headers=h)).json()
    answers = {q: valid_answer(QUESTIONS[q]) for q in ("TD-01", "TD-02", "TD-03", "TD-04", "TD-05", "TD-06")}
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
    assert (await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)).status_code == 200
    assert (await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": {"TD-01": ["A", "B", "C", "D"]}}, headers=h)).status_code == 409
    assert (await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)).status_code == 409

    other = await candidate(client, "nosy@example.com")
    assert (await client.get(f"/v1/attempts/{a['id']}", headers=other)).status_code == 404
    assert (await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": {}}, headers=other)).status_code == 404


@pytest.mark.asyncio
async def test_unpaid_or_unowned_forms_cannot_be_started(client):
    h = await candidate(client, "cons@example.com", product="consulting_assessment")
    assert (await client.post("/v1/assessments/capability/attempts", headers=h)).status_code == 200
    assert (await client.post("/v1/assessments/values/attempts", headers=h)).status_code == 402
    none = await candidate(client, "none@example.com", product=None)
    assert (await client.post("/v1/assessments/profile/attempts", headers=none)).status_code == 402
    assert (await client.get("/v1/me/assessments", headers=none)).json() == []


@pytest.mark.asyncio
async def test_attempt_is_pinned_to_the_version_it_started_on(client):
    from tests.conftest import make_user

    h = await candidate(client)
    a = (await client.post("/v1/assessments/capability/attempts", headers=h)).json()
    _, admin = await make_user("admin@example.com", "admin")
    base = "/v1/admin/content/questions/CAP-01"
    await client.post(f"{base}/draft", headers=admin)
    data = (await client.get(base, headers=admin)).json()["versions"][0]["data"]
    await client.put(f"{base}/draft", json={"data": {**data, "prompt": "Reworded question"}}, headers=admin)
    await client.post(f"{base}/publish", headers=admin)

    resumed = (await client.get(f"/v1/attempts/{a['id']}", headers=h)).json()
    assert resumed["definition"]["sections"][0]["questions"][0]["prompt"] == QUESTIONS["CAP-01"]["prompt"]
