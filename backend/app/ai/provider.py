"""The one LLM abstraction every AI feature goes through (config-swappable, plan v2/v4).

AI_PROVIDER=anthropic → Anthropic Messages API.
AI_PROVIDER=openai    → OpenAI Chat Completions or any compatible server (Ollama, Groq, LM Studio …) via AI_BASE_URL.

`generate(...)` returns a schema-validated pydantic object. Per the TDD rule: on invalid output it
retries once with a repair prompt, then raises AIOutputInvalid — callers route that to review; they
never fake a result.
"""
import json
import re
from typing import Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class AIUnavailable(Exception):
    """No provider configured, or the provider couldn't be reached."""


class AIOutputInvalid(Exception):
    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw[:2000]


async def _call(system: str, user: str, *, temperature: float, max_tokens: int) -> str:
    """Send one prompt, return the model's text. Tests replace this function."""
    s = get_settings()
    if not s.ai_configured:
        raise AIUnavailable("AI isn't configured yet — set AI_PROVIDER, AI_MODEL and AI_API_KEY (or AI_BASE_URL) in backend/.env")
    try:
        async with httpx.AsyncClient(timeout=s.ai_timeout_seconds) as client:
            if s.ai_provider == "anthropic":
                r = await client.post(
                    (s.ai_base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages",
                    headers={"x-api-key": s.ai_api_key, "anthropic-version": "2023-06-01"},
                    json={"model": s.ai_model, "system": system, "max_tokens": max_tokens, "temperature": temperature,
                          "messages": [{"role": "user", "content": user}]},
                )
                r.raise_for_status()
                return "".join(block.get("text", "") for block in r.json().get("content", []))
            if s.ai_provider == "openai":
                headers = {"Authorization": f"Bearer {s.ai_api_key}"} if s.ai_api_key else {}
                r = await client.post(
                    (s.ai_base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
                    headers=headers,
                    json={"model": s.ai_model, "temperature": temperature, "max_tokens": max_tokens,
                          "response_format": {"type": "json_object"},
                          "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"] or ""
    except httpx.HTTPStatusError as exc:
        raise AIUnavailable(f"AI provider returned {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise AIUnavailable(f"Couldn't reach the AI provider: {exc.__class__.__name__}") from exc
    raise AIUnavailable(f"Unknown AI_PROVIDER '{s.ai_provider}' — use anthropic or openai")


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the response")
    return json.loads(text[start : end + 1])


async def generate(system: str, user: str, schema: Type[T], *, temperature: float = 0.1, max_tokens: int = 3000) -> T:
    raw = await _call(system, user, temperature=temperature, max_tokens=max_tokens)
    try:
        return schema.model_validate(_extract_json(raw))
    except (ValueError, ValidationError) as first_error:
        repair = (
            f"{user}\n\nYour previous reply could not be used: {str(first_error)[:600]}\n"
            "Reply again with ONLY one JSON object that matches the required schema exactly — no prose, no code fences."
        )
        raw = await _call(system, repair, temperature=0.0, max_tokens=max_tokens)
        try:
            return schema.model_validate(_extract_json(raw))
        except (ValueError, ValidationError) as exc:
            raise AIOutputInvalid(f"AI output failed validation twice: {str(exc)[:300]}", raw) from exc


def model_label() -> Optional[str]:
    s = get_settings()
    return f"{s.ai_provider}:{s.ai_model}" if s.ai_configured else None
