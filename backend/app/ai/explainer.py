"""Phase 8 — AI Results Explainer (plan v3/v5): one grounded chat agent, two framings.

Same underlying agent and the same locked context; only the system framing changes:
- **"why" mode** (report page) — explains *why* a score is what it is, from the evidence.
- **"coach" mode** (roadmap page) — answers "what should I do next", grounded in the gap analysis /
  roadmap, not free-form advice.

The answer is grounded strictly in the candidate's own snapshot (`reports.context_snapshot`) plus,
in coach mode, their roadmap. If the AI isn't configured or is unreachable, the caller gets an honest
"not available" answer — never an invented one.
"""
import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.ai import provider
from app.content.registry import get_type
from app.services.content import NotFound, get_current

log = logging.getLogger(__name__)

PROMPT_KEY = "results_explainer"
MODES = ("why", "coach")

_MODE_FRAMING = {
    "why": (
        "You are explaining a candidate's own assessment results to them. Answer WHY their scores are "
        "what they are, using only the evidence in the context. Be encouraging, specific and honest."
    ),
    "coach": (
        "You are a development coach for this candidate. Answer what they should learn, practise or "
        "improve next, grounded in their development themes and roadmap. Be concrete and actionable."
    ),
}


class ExplainerAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


def _fallback_prompt(mode: str) -> str:
    return (
        f"{_MODE_FRAMING[mode]}\n\n"
        "Rules:\n"
        "- Use ONLY the CONTEXT below (the candidate's own locked results). Never invent scores, evidence or facts.\n"
        "- If the answer isn't supported by the context, say you don't have that information rather than guessing.\n"
        "- Do not discuss other candidates, the platform's commercials, or anything outside this candidate's results.\n"
        "- 2-4 short paragraphs, plain language, second person (\"you\").\n\n"
        'Reply with ONLY this JSON object: {"answer": "..."}'
    )


async def answer(tenant_id: str, question: str, context_text: str, mode: str = "why", roadmap_text: Optional[str] = None) -> dict:
    """Return {answer, mode, grounded, available}. Never raises for an AI outage."""
    if mode not in MODES:
        mode = "why"
    try:
        prompt = await get_current(get_type("prompts"), tenant_id, PROMPT_KEY)
        system = prompt.data.get("system_prompt") or _fallback_prompt(mode)
        # The published prompt is mode-agnostic; prepend the mode framing so one prompt serves both.
        system = f"{_MODE_FRAMING[mode]}\n\n{system}"
        version = prompt.version
    except NotFound:
        system = _fallback_prompt(mode)
        version = None

    context = f"CONTEXT (the candidate's own locked results):\n{context_text}"
    if mode == "coach" and roadmap_text:
        context += f"\n\nROADMAP:\n{roadmap_text}"
    user = f"{context}\n\nCANDIDATE QUESTION: {question}\n\nAnswer grounded only in the context above."

    try:
        result = await provider.generate(system, user, ExplainerAnswer, temperature=0.3, max_tokens=1200)
    except provider.AIUnavailable:
        return {
            "mode": mode,
            "available": False,
            "answer": "The AI Explainer isn't available right now. Your report above shows your scores and the "
            "evidence behind them — please try the chat again shortly.",
        }
    except provider.AIOutputInvalid:
        log.warning("explainer output invalid", extra={"mode": mode})
        return {"mode": mode, "available": False, "answer": "I couldn't put that answer together just now — please rephrase or try again."}
    return {"mode": mode, "available": True, "answer": result.answer, "prompt_version": version}
