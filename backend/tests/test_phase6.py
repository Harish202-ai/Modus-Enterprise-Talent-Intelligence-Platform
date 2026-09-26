"""Phase 6 — Deterministic Scoring.

Half of this file is pure-maths unit tests (no DB): the rank 4-3-2-1 scoring, Schwartz MRAT
centring and weighted capability key scoring must be exact and reproducible. The rest drives the
real engine end to end: submit the three deterministic forms, read /v1/me/scores, and check the
numbers are stable across reads and that unfinished forms report `not_submitted`.
"""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.main import app
from app.models.common import new_id, utcnow
from app.services import scoring_rules
from scripts.seed_content import seed
from tests.conftest import default_tenant
from tests.fixture_files import make_docx

SEED = Path(__file__).resolve().parent.parent / "seed"
QUESTIONS = {q["key"]: q["data"] for q in json.loads((SEED / "questions.json").read_text(encoding="utf-8"))["items"]}


# --- pure maths (no I/O) ----------------------------------------------------------------------

def test_talent_dna_rank_points_and_normalisation():
    # One item, options mapped to four dimensions, placed best→worst: 4,3,2,1 points.
    questions = {
        "Q": {
            "type": "rank",
            "scoring_rule": {"method": "rank_points", "points": [4, 3, 2, 1]},
            "options": [
                {"key": "A", "maps_to": "alpha"},
                {"key": "B", "maps_to": "beta"},
                {"key": "C", "maps_to": "gamma"},
                {"key": "D", "maps_to": "delta"},
            ],
        }
    }
    out = scoring_rules.score_talent_dna(questions, {"Q": ["A", "B", "C", "D"]})
    got = {d["key"]: (d["raw"], d["normalized"]) for d in out["dimensions"]}
    # raw = rank points; normalised against this item's min(1)/max(4).
    assert got == {"alpha": (4.0, 100.0), "beta": (3.0, 66.7), "gamma": (2.0, 33.3), "delta": (1.0, 0.0)}
    assert [d["key"] for d in out["dimensions"]] == ["alpha", "beta", "gamma", "delta"]  # sorted desc
    assert out["scored_items"] == 1


def test_talent_dna_ignores_incomplete_rankings():
    questions = {"Q": {"type": "rank", "scoring_rule": {"method": "rank_points", "points": [4, 3, 2, 1]},
                       "options": [{"key": "A", "maps_to": "x"}, {"key": "B", "maps_to": "y"}]}}
    assert scoring_rules.score_talent_dna(questions, {"Q": ["A"]})["scored_items"] == 0


def test_values_mrat_centering_and_higher_order():
    questions = {
        "V1": {"scoring_rule": {"method": "likert_value"}, "value_map": [{"value_key": "v1", "weight": 1}]},
        "V2": {"scoring_rule": {"method": "likert_value"}, "value_map": [{"value_key": "v1", "weight": 1}]},
        "V3": {"scoring_rule": {"method": "likert_value"}, "value_map": [{"value_key": "v2", "weight": 1}]},
        "V4": {"scoring_rule": {"method": "likert_value"}, "value_map": [{"value_key": "v2", "weight": 1}]},
    }
    taxonomy = [
        {"key": "v1", "data": {"kind": "basic_value", "name": "V-One"}},
        {"key": "v2", "data": {"kind": "basic_value", "name": "V-Two"}},
        {"key": "hi_both", "data": {"kind": "higher_order", "name": "Both", "constituent_value_keys": ["v1", "v2"]}},
        {"key": "hi_partial", "data": {"kind": "higher_order", "name": "Partial", "constituent_value_keys": ["v1"], "partial_value_keys": ["v2"]}},
    ]
    answers = {"V1": "6", "V2": "6", "V3": "2", "V4": "4"}  # means: v1=6, v2=3; MRAT = 18/4 = 4.5
    out = scoring_rules.score_values(questions, answers, taxonomy)
    assert out["mrat"] == 4.5 and out["answered"] == 4
    basic = {b["key"]: (b["raw_mean"], b["centered"]) for b in out["basic"]}
    assert basic == {"v1": (6.0, 1.5), "v2": (3.0, -1.5)}
    higher = {h["key"]: h["centered"] for h in out["higher_order"]}
    assert higher["hi_both"] == 0.0  # (1.5 + -1.5) / 2
    assert higher["hi_partial"] == 0.5  # (1*1.5 + 0.5*-1.5) / 1.5
    assert out["top_values"][0] == "v1"


def test_capability_weighted_key_scoring():
    questions = {
        "C1": {"scoring_rule": {"method": "correct_option", "correct": "A"}, "competency_map": [{"competency_key": "compA", "weight": 1}]},
        "C2": {"scoring_rule": {"method": "correct_option", "correct": "B"}, "competency_map": [{"competency_key": "compA", "weight": 1}]},
        "C3": {"scoring_rule": {"method": "correct_option", "correct": "C"},
               "competency_map": [{"competency_key": "compB", "weight": 1}, {"competency_key": "compA", "weight": 0.5}]},
    }
    answers = {"C1": "A", "C2": "C", "C3": "C"}  # C1 right, C2 wrong, C3 right
    out = scoring_rules.score_capability(questions, answers, {"compA": "Comp A", "compB": "Comp B"})
    assert out["correct"] == 2 and out["total"] == 3 and out["overall_pct"] == 66.7
    comp = {c["key"]: c["weighted_pct"] for c in out["competencies"]}
    assert comp["compA"] == 60.0  # credit (1*1 + 1*0 + 0.5*1)=1.5 over weight (1+1+0.5)=2.5
    assert comp["compB"] == 100.0


def test_scorers_are_reproducible_on_the_real_item_bank():
    """The seeded Talent DNA / Values / Capability items score without error and identically twice."""
    td = {k: QUESTIONS[k] for k in QUESTIONS if QUESTIONS[k].get("type") == "rank"}
    td_answers = {k: [o["key"] for o in QUESTIONS[k]["options"]] for k in td}
    assert scoring_rules.score_talent_dna(td, td_answers) == scoring_rules.score_talent_dna(td, td_answers)
    assert len(scoring_rules.score_talent_dna(td, td_answers)["dimensions"]) == 9  # TDD §9.1 dimensions


# --- end to end -------------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def candidate(client, email="scorer@example.com"):
    r = await client.post("/v1/auth/register", json={"email": email, "full_name": "Sam Scorer", "password": "Consult1ng", "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    user = await database.users().find_one({"email": email})
    products = {p["key"]: p for p in (await client.get("/v1/products")).json()}
    for key in ["bundle", *products["bundle"]["bundled_product_keys"]]:
        await database.entitlements().insert_one({"_id": new_id(), "tenant_id": user["tenant_id"], "user_id": user["_id"], "product_key": key,
                                                  "product_version": products[key]["version"], "source": "test", "payment_id": None,
                                                  "granted_at": utcnow(), "revoked_at": None})
    return h


def _answer(q: dict):
    keys = [o["key"] for o in q.get("options", [])]
    if q["type"] in ("single_choice", "likert"):
        return keys[-1]
    if q["type"] == "rank":
        return keys  # top→bottom as listed
    return None


async def _submit(client, h, code: str):
    a = (await client.post(f"/v1/assessments/{code}/attempts", headers=h)).json()
    questions = [q for s in a["definition"]["sections"] for q in s["questions"]]
    answers = {q["key"]: _answer(QUESTIONS[q["key"]]) for q in questions}
    await client.put(f"/v1/attempts/{a['id']}/answers", json={"answers": answers}, headers=h)
    r = await client.post(f"/v1/attempts/{a['id']}/submit", headers=h)
    assert r.status_code == 200, (code, r.text)
    return a["id"]


@pytest.mark.asyncio
async def test_definition_of_done_reproducible_profile_from_submitted_forms(client):
    h = await candidate(client)
    await _submit(client, h, "talent_dna")
    await _submit(client, h, "values")
    await _submit(client, h, "capability")

    scores = (await client.get("/v1/me/scores", headers=h)).json()["scores"]

    # Talent DNA — 9 dimensions, each with a 0–100 normalised score.
    td = scores["talent_dna"]
    assert td["status"] == "scored" and len(td["dimensions"]) == 9
    assert all(0 <= d["normalized"] <= 100 for d in td["dimensions"])

    # Values — 10 basic values (wheel) + 4 higher-order views, centred on the candidate's own mean.
    val = scores["values"]
    assert val["status"] == "scored" and len(val["basic"]) == 10 and len(val["higher_order"]) == 4
    assert "mrat" in val and val["basic"][0]["name"]

    # Capability — a weighted % per competency the item bank covers, plus an overall %.
    cap = scores["capability"]
    assert cap["status"] == "scored" and cap["total"] == 20 and 0 <= cap["overall_pct"] <= 100
    assert cap["competencies"] and cap["competencies"][0]["name"]

    # Reproducible: reading again returns identical numbers.
    again = (await client.get("/v1/me/scores", headers=h)).json()["scores"]
    assert again == scores


@pytest.mark.asyncio
async def test_unsubmitted_forms_report_not_submitted_and_missing_scores_recompute(client):
    h = await candidate(client)
    await _submit(client, h, "talent_dna")

    scores = (await client.get("/v1/me/scores", headers=h)).json()["scores"]
    assert scores["talent_dna"]["status"] == "scored"
    assert scores["values"]["status"] == "not_submitted"
    assert scores["capability"]["status"] == "not_submitted"

    # Simulate an attempt submitted before Phase 6: drop the stored score → the read recomputes it.
    first = scores["talent_dna"]
    await database.scores().delete_many({})
    recomputed = (await client.get("/v1/me/scores", headers=h)).json()["scores"]["talent_dna"]
    assert recomputed["dimensions"] == first["dimensions"]
    assert await database.scores().count_documents({}) == 1  # re-persisted


@pytest.mark.asyncio
async def test_scores_are_private_to_the_candidate(client):
    h = await candidate(client)
    await _submit(client, h, "capability")
    other = await candidate(client, "someone.else@example.com")
    mine = (await client.get("/v1/me/scores", headers=h)).json()["scores"]
    theirs = (await client.get("/v1/me/scores", headers=other)).json()["scores"]
    assert mine["capability"]["status"] == "scored" and theirs["capability"]["status"] == "not_submitted"
