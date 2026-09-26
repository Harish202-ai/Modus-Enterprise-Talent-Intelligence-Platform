import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.content.registry import CONTENT_TYPES
from app.main import app
from scripts.seed_content import seed
from tests.conftest import make_user

BASE = "/v1/admin/content"


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    _, headers = await make_user("author@example.com", "admin")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c


async def create_published(client, type_name, key, data):
    r = await client.post(f"{BASE}/{type_name}", json={"key": key, "data": data})
    assert r.status_code == 201, r.text
    r = await client.post(f"{BASE}/{type_name}/{key}/publish")
    assert r.status_code == 200, r.text
    return r.json()


QUESTION = {
    "type": "single_choice",
    "prompt": "What is the first step in structuring an ambiguous client problem?",
    "options": [{"key": "A", "label": "Define the key question"}, {"key": "B", "label": "Build the deck"}],
}


@pytest.mark.asyncio
async def test_types_endpoint_lists_all_phase1_collections(client):
    r = await client.get(f"{BASE}/types")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    assert names == {
        "assessments", "sections", "questions", "rubrics", "competencies", "values_taxonomy",
        "videos", "products", "prompts", "site_content", "interview_questions", "support_kb", "report_templates",
    }
    q = next(t for t in r.json() if t["name"] == "questions")
    assert any(f["name"] == "prompt" and f["required"] for f in q["fields"])
    assert next(f for f in q["fields"] if f["name"] == "type")["options"] == ["single_choice", "multi_select", "likert", "rank", "free_text", "file_upload"]


@pytest.mark.asyncio
async def test_indexes_enforce_versioning(client):
    for name in CONTENT_TYPES:
        ix = await database.collection(name).index_information()
        assert ix["uq_tenant_key_version"]["unique"] is True
        assert ix["uq_tenant_key_draft"]["partialFilterExpression"] == {"status": "draft"}


@pytest.mark.asyncio
async def test_draft_publish_is_immutable_and_edits_create_new_version(client):
    r = await client.post(f"{BASE}/questions", json={"key": "Q1", "data": {**QUESTION, "prompt": "draft"}})
    assert r.status_code == 201 and r.json()["version"] == 1 and r.json()["status"] == "draft"
    assert (await client.post(f"{BASE}/questions", json={"key": "Q1", "data": QUESTION})).status_code == 409

    r = await client.put(f"{BASE}/questions/Q1/draft", json={"data": QUESTION})
    assert r.status_code == 200 and r.json()["data"]["prompt"] == QUESTION["prompt"]

    published = (await client.post(f"{BASE}/questions/Q1/publish")).json()
    assert published["status"] == "published" and published["published_at"]

    # Published versions cannot be edited in place.
    r = await client.put(f"{BASE}/questions/Q1/draft", json={"data": {**QUESTION, "prompt": "sneaky edit"}})
    assert r.status_code == 409

    # Editing = new draft version seeded from the published one.
    r = await client.post(f"{BASE}/questions/Q1/draft")
    assert r.status_code == 201 and r.json()["version"] == 2 and r.json()["based_on_version"] == 1
    assert (await client.post(f"{BASE}/questions/Q1/draft")).status_code == 409  # one draft at a time
    await client.put(f"{BASE}/questions/Q1/draft", json={"data": {**QUESTION, "prompt": "v2 prompt"}})

    v1 = (await client.get(f"{BASE}/questions/Q1/versions/1")).json()
    assert v1["data"]["prompt"] == QUESTION["prompt"] and v1["status"] == "published"
    assert (await client.get(f"{BASE}/questions/Q1/current")).json()["version"] == 1

    await client.post(f"{BASE}/questions/Q1/publish")
    assert (await client.get(f"{BASE}/questions/Q1/current")).json()["data"]["prompt"] == "v2 prompt"
    history = (await client.get(f"{BASE}/questions/Q1")).json()["versions"]
    assert [(v["version"], v["status"]) for v in history] == [(2, "published"), (1, "published")]

    rows = (await client.get(f"{BASE}/questions")).json()
    assert rows == [
        {**rows[0], "key": "Q1", "latest_version": 2, "latest_status": "published", "published_version": 2, "has_draft": False}
    ]


@pytest.mark.asyncio
async def test_publish_rejects_missing_required_fields_and_bad_types(client):
    await client.post(f"{BASE}/questions", json={"key": "Q1", "data": {"type": "single_choice", "options": "nope", "extra": 1}})
    r = await client.post(f"{BASE}/questions/Q1/validate")
    errors = {(e["field"], e["message"]) for e in r.json()["errors"]}
    assert r.json()["ok"] is False
    assert ("prompt", "is required") in errors
    assert ("extra", "is not a field of this content type") in errors
    assert ("options", "must be a list of objects") in errors

    r = await client.post(f"{BASE}/questions/Q1/publish")
    assert r.status_code == 422 and r.json()["errors"]
    assert (await client.get(f"{BASE}/questions/Q1/versions/1")).json()["status"] == "draft"

    # Products carry one flat price.
    await client.post(f"{BASE}/products", json={"key": "P1", "data": {"name": "X", "kind": "assessment", "currency": "usd", "price": -5}})
    fields = {e["field"] for e in (await client.post(f"{BASE}/products/P1/validate")).json()["errors"]}
    assert {"currency", "price", "assessment_keys"} <= fields


@pytest.mark.asyncio
async def test_section_skip_rule_needs_a_published_earlier_question(client):
    await create_published(client, "questions", "Q2", QUESTION)
    section = {"title": "Deep dive", "question_keys": ["Q2"], "skip_if": [{"question_key": "Q1", "answer": "A"}]}
    await client.post(f"{BASE}/sections", json={"key": "S2", "data": section})
    r = await client.post(f"{BASE}/sections/S2/publish")
    assert r.status_code == 422
    assert r.json()["errors"] == [{"field": "skip_if", "message": "'Q1' is not a published item in Questions"}]

    await create_published(client, "questions", "Q1", QUESTION)
    r = await client.post(f"{BASE}/sections/S2/publish")
    assert r.status_code == 200
    assert r.json()["ref_versions"] == {"questions": {"Q1": 1, "Q2": 1}}

    bad = {"title": "Bad", "question_keys": ["Q2"], "skip_if": [{"question_key": "Q1", "answer": "Z"}, {"question_key": "Q2", "answer": "A"}]}
    await client.post(f"{BASE}/sections", json={"key": "S3", "data": bad})
    messages = {e["message"] for e in (await client.post(f"{BASE}/sections/S3/validate")).json()["errors"]}
    assert messages == {"answer 'Z' is not an option of 'Q1'", "'Q2' is in this section — skip rules must depend on an earlier section"}


@pytest.mark.asyncio
async def test_definition_of_done_admin_publishes_assessment_and_reads_it_via_api(client):
    await create_published(client, "competencies", "research_structuring", {"name": "Research & Problem Structuring", "definition": "Issue trees."})
    await create_published(
        client, "questions", "Q1", {**QUESTION, "competency_map": [{"competency_key": "research_structuring", "weight": 1.0}]}
    )
    await create_published(client, "sections", "S1", {"title": "Structuring", "question_keys": ["Q1"]})

    await client.post(f"{BASE}/assessments", json={"key": "case_study", "data": {
        "name": "Case Study", "category": "Demonstrated", "purpose": "Case.", "section_keys": ["S1"],
    }})
    r = await client.post(f"{BASE}/assessments/case_study/publish")
    assert r.status_code == 200 and r.json()["ref_versions"] == {"sections": {"S1": 1}}

    r = await client.get("/v1/assessments/case_study")
    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "case_study" and body["version"] == 1
    assert body["sections"][0]["questions"][0]["prompt"] == QUESTION["prompt"]

    # Republishing the question does not change the already-published assessment.
    await client.post(f"{BASE}/questions/Q1/draft")
    await client.put(f"{BASE}/questions/Q1/draft", json={"data": {**QUESTION, "prompt": "changed later"}})
    await client.post(f"{BASE}/questions/Q1/publish")
    body = (await client.get("/v1/assessments/case_study")).json()
    assert body["sections"][0]["questions"][0]["prompt"] == QUESTION["prompt"]
    assert body["sections"][0]["questions"][0]["version"] == 1

    assert (await client.get("/v1/assessments/nope")).status_code == 404


@pytest.mark.asyncio
async def test_discard_draft_and_audit_trail(client):
    await create_published(client, "competencies", "strategy_enterprise", {"name": "Strategy", "definition": "Strategy."})
    await client.post(f"{BASE}/competencies/strategy_enterprise/draft")
    r = await client.delete(f"{BASE}/competencies/strategy_enterprise/draft")
    assert r.status_code == 200 and r.json()["version"] == 2
    assert [v["version"] for v in (await client.get(f"{BASE}/competencies/strategy_enterprise")).json()["versions"]] == [1]
    assert (await client.delete(f"{BASE}/competencies/strategy_enterprise/draft")).status_code == 404

    actions = [e["action"] async for e in database.audit_events().find({"entity_type": "competencies"}).sort("timestamp", 1)]
    assert actions == ["content.created", "content.published", "content.version_created", "content.draft_discarded"]


@pytest.mark.asyncio
async def test_unknown_type_and_bad_key(client):
    assert (await client.get(f"{BASE}/widgets")).status_code == 404
    assert (await client.post(f"{BASE}/questions", json={"key": "bad key!", "data": {}})).status_code == 422


@pytest.mark.asyncio
async def test_values_higher_order_must_reference_basic_values(client):
    await create_published(client, "values_taxonomy", "achievement", {"name": "Achievement", "kind": "basic_value", "definition": "x"})
    await create_published(client, "values_taxonomy", "power", {"name": "Power", "kind": "basic_value", "definition": "x"})
    await create_published(client, "values_taxonomy", "self_enhancement", {
        "name": "Self-Enhancement", "kind": "higher_order", "definition": "x", "constituent_value_keys": ["achievement", "power"],
    })
    await client.post(f"{BASE}/values_taxonomy", json={"key": "nested", "data": {
        "name": "Nested", "kind": "higher_order", "definition": "x", "constituent_value_keys": ["self_enhancement"],
    }})
    errors = (await client.post(f"{BASE}/values_taxonomy/nested/validate")).json()["errors"]
    assert errors == [{"field": "constituent_value_keys", "message": "'self_enhancement' must be a basic value"}]


@pytest.mark.asyncio
async def test_seed_content_is_idempotent(client):
    first = await seed()
    assert first["competencies"] == {"created": 8, "updated": 0, "published": 8, "skipped": 0}
    assert first["values_taxonomy"] == {"created": 14, "updated": 0, "published": 14, "skipped": 0}
    assert first["questions"] == {"created": 63, "updated": 0, "published": 63, "skipped": 0}
    assert first["sections"] == {"created": 13, "updated": 0, "published": 13, "skipped": 0}
    assert first["assessments"] == {"created": 7, "updated": 0, "published": 7, "skipped": 0}
    # prompts: report_generator (draft) + 4 live (scoring, results_explainer, support_chatbot, profile_parser).
    assert first["prompts"] == {"created": 5, "updated": 0, "published": 4, "skipped": 0}
    assert first["rubrics"] == {"created": 2, "updated": 0, "published": 2, "skipped": 0}  # memo + case (Phase 7)
    assert first["support_kb"] == {"created": 10, "updated": 0, "published": 10, "skipped": 0}  # help content (Phase 10)

    again = await seed()
    assert all(c["created"] == c["updated"] == 0 and c["skipped"] > 0 for c in again.values())

    rows = (await client.get(f"{BASE}/values_taxonomy", params={"status": "published"})).json()
    assert len(rows) == 14
    higher = (await client.get(f"{BASE}/values_taxonomy/conservation/current")).json()
    assert higher["ref_versions"] == {"values_taxonomy": {"conformity": 1, "security": 1, "tradition": 1}}

    # The 7 forms are published with their sections, pinned at publish time.
    capability = (await client.get(f"{BASE}/assessments/capability/current")).json()
    assert capability["ref_versions"]["sections"] == {"cap_data_ai": 1, "cap_operations": 1, "cap_strategy": 1, "cap_transformation": 1}


@pytest.mark.asyncio
async def test_seed_completes_its_own_untouched_drafts_but_never_admin_edits(client):
    from app.content.registry import get_type
    from app.services import content
    from tests.conftest import default_tenant

    tenant = await default_tenant()
    ctype = get_type("assessments")
    # An old skeleton draft left by an earlier seed run, and one an admin has edited.
    await content.create(ctype, tenant.id, "profile", {"name": "Profile", "category": "Profile", "purpose": "old", "section_keys": []}, "seed")
    await content.create(ctype, tenant.id, "motivation", {"name": "Mine", "category": "Potential", "purpose": "x", "section_keys": []}, "seed")
    await content.update_draft(ctype, tenant.id, "motivation", {"name": "Admin edit", "category": "Potential", "purpose": "x", "section_keys": []}, "admin-1")
    summary = await seed()
    assert summary["assessments"] == {"created": 5, "updated": 1, "published": 6, "skipped": 1}
    assert (await content.get_current(ctype, tenant.id, "profile")).data["section_keys"] == ["prf_background", "prf_programme", "prf_international"]
    assert (await content.get_draft(ctype, tenant.id, "motivation")).data["name"] == "Admin edit"
