"""Phase 10 — Site-wide support chatbot retrieval (plan v4).

HARD BOUNDARY: this bot's knowledge is the published `support_kb` content and nothing else. It never
touches any candidate's scores, answers or evidence — the retrieval query only ever runs against
support_kb, enforced here at the query layer, not just by prompt wording. So it's safe to expose to
anyone, signed in or not.

Retrieval is a lightweight keyword-overlap ranker (title/tags weighted above body) — real, and sized
to MVP scale, with no embeddings dependency so it works with no AI key. When an AI provider *is*
configured, the retrieved chunks are handed to the published `support_chatbot` prompt for a fluent
answer; without one, the best-matching entry is returned directly (extractive). If nothing matches
with confidence, the bot says so and points to the contact / sign-in path — it never guesses.
"""
import logging
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app import database
from app.ai import provider
from app.content.registry import get_type
from app.services.content import NotFound, get_current

log = logging.getLogger(__name__)

PROMPT_KEY = "support_chatbot"
_STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "i", "my", "me", "you", "your", "to", "of", "for", "and", "or",
    "how", "what", "when", "where", "can", "will", "it", "in", "on", "with", "about", "this", "that", "get", "am",
}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOPWORDS and len(t) > 1]


async def _published_kb(tenant_id: str) -> List[dict]:
    rows = (
        await database.collection(get_type("support_kb").name)
        .find({"tenant_id": tenant_id, "status": "published"})
        .sort([("key", 1), ("version", -1)])
        .to_list(None)
    )
    latest: Dict[str, dict] = {}
    for row in rows:
        latest.setdefault(row["key"], row)
    return list(latest.values())


def _score(query_tokens: List[str], item: dict) -> float:
    data = item.get("data") or {}
    title_tokens = set(_tokens(data.get("title", "")))
    tag_tokens = set(_tokens(" ".join(data.get("tags") or [])))
    body_tokens = set(_tokens(data.get("body", "")))
    q = set(query_tokens)
    if not q:
        return 0.0
    hits = len(q & title_tokens) * 3 + len(q & tag_tokens) * 3 + len(q & body_tokens)
    return hits / len(q)  # normalise by query length so short and long questions compare


async def retrieve(tenant_id: str, query: str, k: int = 3, threshold: float = 0.5) -> List[dict]:
    query_tokens = _tokens(query)
    scored = [(item, _score(query_tokens, item)) for item in await _published_kb(tenant_id)]
    scored = [(i, s) for i, s in scored if s >= threshold]
    scored.sort(key=lambda pair: -pair[1])
    return [{"key": i["key"], "title": i["data"].get("title"), "body": i["data"].get("body"), "score": round(s, 2)} for i, s in scored[:k]]


class SupportAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=1500)


_NO_MATCH = (
    "I don't have an answer to that in our help content. For anything about your own results, please sign in and "
    "use the AI Results Explainer on your report; for billing or account help, contact the support team from your account page."
)


async def answer(tenant_id: str, query: str) -> dict:
    """Answer a general platform question from public help content only."""
    chunks = await retrieve(tenant_id, query)
    if not chunks:
        return {"answer": _NO_MATCH, "sources": [], "grounded": False}

    sources = [{"key": c["key"], "title": c["title"]} for c in chunks]
    context = "\n\n".join(f"[{c['title']}]\n{c['body']}" for c in chunks)

    try:
        prompt = await get_current(get_type("prompts"), tenant_id, PROMPT_KEY)
        system = prompt.data.get("system_prompt") or ""
    except NotFound:
        system = ""
    if not system:
        # No AI prompt published (or none needed) → extractive answer straight from the best chunk.
        return {"answer": chunks[0]["body"], "sources": sources, "grounded": True, "mode": "extractive"}

    try:
        result = await provider.generate(
            system,
            f"HELP CONTENT (the only thing you may use):\n{context}\n\nVISITOR QUESTION: {query}\n\nAnswer from the help content only.",
            SupportAnswer,
            temperature=0.2,
            max_tokens=600,
        )
    except (provider.AIUnavailable, provider.AIOutputInvalid):
        # AI down → still helpful: return the best matching entry.
        return {"answer": chunks[0]["body"], "sources": sources, "grounded": True, "mode": "extractive"}
    return {"answer": result.answer, "sources": sources, "grounded": True, "mode": "ai"}
