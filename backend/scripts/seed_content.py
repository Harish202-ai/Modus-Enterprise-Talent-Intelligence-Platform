"""Load the Phase 1 content seed (backend/seed/*.json) into the default tenant. Idempotent.

    python -m scripts.seed_content

Anything a person has edited is never overwritten. Content that only this script has ever
written ("seed-owned") is brought up to date: a changed item, or one whose references have newer
published versions, gets a new version and is republished (earlier versions — and attempts pinned
to them — are untouched). Files marked "publish": true are published straight away (they must
validate); the rest stay drafts for an admin to finish.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict

from app import database
from app.config import get_settings
from app.content.registry import get_type
from app.content.validation import RefLookup, validate
from app.models.tenant import TenantCreate
from app.services import content
from app.services.tenants import create_tenant

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
# Load order matters: references must already be published (values -> higher-order values,
# questions -> sections -> assessments -> products).
SEED_FILES = (
    "competencies.json",
    "values_taxonomy.json",
    "rubrics.json",
    "questions.json",
    "sections.json",
    "assessments.json",
    "prompts.json",
    "prompts_live.json",
    "videos.json",
    "site_content.json",
    "products.json",
    "support_kb.json",
    "interview_questions.json",
)


async def _pins_stale(ctype, tenant_id: str, current: dict) -> bool:
    """Would publishing this data again pin newer versions of what it references?"""
    lookup = RefLookup(tenant_id)
    if await validate(ctype, current["key"], current["data"], lookup):
        return False
    return lookup.pinned() != (current.get("ref_versions") or {})


async def _apply(ctype, tenant_id: str, item: dict, publish: bool, actor_id: str) -> str:
    """created | updated (a draft ready to publish) | skipped. Never touches anything a person has edited."""
    versions = await database.collection(ctype.name).find({"tenant_id": tenant_id, "key": item["key"]}).sort("version", -1).to_list(None)
    if not versions:
        await content.create(ctype, tenant_id, item["key"], item["data"], actor_id)
        return "created"
    seed_owned = all(v["created_by"] == actor_id and v["updated_by"] == actor_id for v in versions)
    latest = versions[0]
    if not (seed_owned and publish):
        return "skipped"
    if latest["status"] == "draft":
        if latest["data"] != item["data"]:
            await content.update_draft(ctype, tenant_id, item["key"], item["data"], actor_id)
        return "updated"
    if latest["data"] == item["data"] and not await _pins_stale(ctype, tenant_id, latest):
        return "skipped"
    await content.new_version(ctype, tenant_id, item["key"], actor_id)
    await content.update_draft(ctype, tenant_id, item["key"], item["data"], actor_id)
    return "updated"


async def seed(actor_id: str = "seed") -> Dict[str, Dict[str, int]]:
    settings = get_settings()
    await database.ensure_indexes()
    tenant, _ = await create_tenant(TenantCreate(slug=settings.default_tenant_slug, name=settings.default_tenant_name))

    summary: Dict[str, Dict[str, int]] = {}
    for filename in SEED_FILES:
        spec = json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))
        ctype = get_type(spec["content_type"])
        counts = summary.setdefault(ctype.name, {"created": 0, "updated": 0, "published": 0, "skipped": 0})
        for item in spec["items"]:
            action = await _apply(ctype, tenant.id, item, bool(spec.get("publish")), actor_id)
            counts[action] += 1
            if action in ("created", "updated") and spec.get("publish"):
                await content.publish(ctype, tenant.id, item["key"], actor_id)
                counts["published"] += 1
    return summary


async def main() -> None:
    summary = await seed()
    print(f"Database '{get_settings().mongo_db}', tenant '{get_settings().default_tenant_slug}':")
    for name, counts in summary.items():
        print(
            f"  {name:24} created={counts['created']:<3} updated={counts['updated']:<3} "
            f"published={counts['published']:<3} skipped(existing)={counts['skipped']}"
        )
    database.close_client()


if __name__ == "__main__":
    asyncio.run(main())
