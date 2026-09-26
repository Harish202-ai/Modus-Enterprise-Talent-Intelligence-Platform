"""Phase 11 (v5) — AI content drafting for the admin (plan: "instead of admin types everything…").

Given a content type and a short instruction, the AI drafts the `data` object for that type — matching
its field specs — which the admin then reviews and edits before publishing. Nothing is auto-published;
the AI just fills the form. Degrades honestly: with no AI key the caller gets a clear "not available".
"""
import json
import logging
from typing import Optional

from pydantic import BaseModel

from app.ai import provider
from app.content.registry import ContentType

log = logging.getLogger(__name__)


class GeneratedContent(BaseModel):
    data: dict


def _field_guide(ctype: ContentType) -> str:
    lines = []
    for f in ctype.fields:
        bits = [f'"{f.name}" ({f.kind}{"" if not f.required else ", required"})']
        if f.options:
            bits.append(f"one of {list(f.options)}")
        if f.help:
            bits.append(f.help)
        lines.append("- " + " — ".join(bits))
    return "\n".join(lines)


async def draft(ctype: ContentType, instruction: str, existing: Optional[dict] = None) -> dict:
    """Return a drafted `data` dict for one content item. Raises provider.AIUnavailable if no AI."""
    system = (
        f"You draft content for the '{ctype.label}' section of a management-consulting assessment platform. "
        f"Return a JSON object shaped as {{\"data\": {{...}}}} where data has ONLY these fields:\n{_field_guide(ctype)}\n\n"
        "Rules: fill required fields sensibly; omit fields you have no basis for; keep JSON-typed values "
        "(lists as lists, objects as objects); never invent references to other content that may not exist. "
        "Keep copy concise and professional. Reply with ONLY the JSON object."
    )
    user = f"Instruction: {instruction}"
    if existing:
        user += f"\n\nImprove or extend this existing draft (keep good parts):\n{json.dumps(existing)[:4000]}"
    result = await provider.generate(system, user, GeneratedContent, temperature=0.4, max_tokens=2000)
    return result.data
