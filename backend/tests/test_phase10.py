"""Phase 10 — Site-wide support chatbot (public, grounded in support_kb only, no candidate data)."""
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app import database
from app.ai import provider
from app.main import app
from app.services import support_kb
from scripts.seed_content import seed
from tests.conftest import default_tenant


def test_keyword_scoring_prefers_title_and_tag_hits():
    item = {"data": {"title": "How long does the assessment take?", "body": "About an hour.", "tags": ["time", "duration"]}}
    assert support_kb._score(support_kb._tokens("how long does it take"), item) > 0
    assert support_kb._score(support_kb._tokens("banana rocket"), item) == 0


@pytest_asyncio.fixture
async def client():
    await database.ensure_indexes()
    await default_tenant()
    await seed()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_public_bot_answers_from_help_content_without_ai(client):
    # No AI configured → extractive answer straight from the best matching entry, no login needed.
    r = await client.post("/v1/support/chat", json={"question": "how long does the assessment take?"})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True and body["sources"] and "hour" in body["answer"].lower() or "minutes" in body["answer"].lower()
    assert any(s["key"] == "how-long" for s in body["sources"])


@pytest.mark.asyncio
async def test_bot_says_when_it_doesnt_know_and_never_guesses(client):
    r = await client.post("/v1/support/chat", json={"question": "what is the airspeed velocity of a swallow?"})
    body = r.json()
    assert body["grounded"] is False and body["sources"] == []
    assert "don't have an answer" in body["answer"]


@pytest.mark.asyncio
async def test_bot_uses_ai_over_retrieved_chunks_when_configured(client, monkeypatch):
    captured = {}

    async def _call(system, user, *, temperature, max_tokens):
        captured["user"] = user
        return json.dumps({"answer": "It takes roughly 60–90 minutes and saves as you go."})

    monkeypatch.setattr(provider, "_call", _call)
    body = (await client.post("/v1/support/chat", json={"question": "how long does it take?"})).json()
    assert body["mode"] == "ai" and "90 minutes" in body["answer"]
    # The model was given help content only — never a candidate's private answers/scores (there is no
    # candidate in this request, and retrieval only ever queries the public support_kb collection).
    assert "HELP CONTENT" in captured["user"] and "how long" in captured["user"].lower()
