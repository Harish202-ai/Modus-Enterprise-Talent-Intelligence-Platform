"""Admin authoring API for every versioned content type. Admin only."""
import json
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.ai import content_gen, provider
from app.api.deps import require_role, require_tenant_scope
from app.content.registry import CONTENT_TYPES, ContentType, get_type
from app.models.content import KEY_PATTERN, ContentCreate, ContentVersion, DraftUpdate
from app.models.tenant import Tenant
from app.models.user import User
from app.services import content

admin = require_role(["admin"])
router = APIRouter(prefix="/admin/content", tags=["admin: content"], dependencies=[Depends(admin)])

KeyParam = Path(pattern=KEY_PATTERN)


def content_type(type_name: str) -> ContentType:
    ctype = get_type(type_name)
    if ctype is None:
        raise HTTPException(404, f"Unknown content type '{type_name}'. Known: {', '.join(CONTENT_TYPES)}")
    return ctype


def _out(item: ContentVersion) -> dict:
    return item.model_dump(by_alias=False)


@router.get("/types")
async def list_types() -> List[dict]:
    return [t.to_api() for t in CONTENT_TYPES.values()]


@router.get("/{type_name}")
async def list_items(
    ctype: ContentType = Depends(content_type),
    status_filter: Optional[Literal["draft", "published"]] = Query(None, alias="status"),
    tenant: Tenant = Depends(require_tenant_scope),
) -> List[dict]:
    return await content.list_items(ctype, tenant.id, status_filter)


@router.post("/{type_name}", status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ContentCreate,
    ctype: ContentType = Depends(content_type),
    tenant: Tenant = Depends(require_tenant_scope),
    user: User = Depends(admin),
) -> dict:
    return _out(await content.create(ctype, tenant.id, body.key, body.data, user.id))


@router.get("/{type_name}/{key}")
async def get_history(
    key: str = KeyParam, ctype: ContentType = Depends(content_type), tenant: Tenant = Depends(require_tenant_scope)
) -> dict:
    history = await content.versions(ctype, tenant.id, key)
    return {"key": key, "content_type": ctype.name, "versions": [_out(v) for v in history]}


@router.get("/{type_name}/{key}/current")
async def get_current(
    key: str = KeyParam, ctype: ContentType = Depends(content_type), tenant: Tenant = Depends(require_tenant_scope)
) -> dict:
    return _out(await content.get_current(ctype, tenant.id, key))


@router.get("/{type_name}/{key}/versions/{version}")
async def get_version(
    version: int, key: str = KeyParam, ctype: ContentType = Depends(content_type), tenant: Tenant = Depends(require_tenant_scope)
) -> dict:
    return _out(await content.get_version(ctype, tenant.id, key, version))


@router.put("/{type_name}/{key}/draft")
async def update_draft(
    body: DraftUpdate,
    key: str = KeyParam,
    ctype: ContentType = Depends(content_type),
    tenant: Tenant = Depends(require_tenant_scope),
    user: User = Depends(admin),
) -> dict:
    return _out(await content.update_draft(ctype, tenant.id, key, body.data, user.id))


@router.post("/{type_name}/{key}/draft", status_code=status.HTTP_201_CREATED)
async def create_new_version(
    key: str = KeyParam,
    ctype: ContentType = Depends(content_type),
    tenant: Tenant = Depends(require_tenant_scope),
    user: User = Depends(admin),
) -> dict:
    return _out(await content.new_version(ctype, tenant.id, key, user.id))


@router.delete("/{type_name}/{key}/draft")
async def discard_draft(
    key: str = KeyParam,
    ctype: ContentType = Depends(content_type),
    tenant: Tenant = Depends(require_tenant_scope),
    user: User = Depends(admin),
) -> dict:
    return _out(await content.discard_draft(ctype, tenant.id, key, user.id))


@router.post("/{type_name}/{key}/validate")
async def validate_draft(
    key: str = KeyParam, ctype: ContentType = Depends(content_type), tenant: Tenant = Depends(require_tenant_scope)
) -> dict:
    errors = await content.validate_draft(ctype, tenant.id, key)
    return {"ok": not errors, "errors": errors}


@router.post("/{type_name}/{key}/publish")
async def publish(
    key: str = KeyParam,
    ctype: ContentType = Depends(content_type),
    tenant: Tenant = Depends(require_tenant_scope),
    user: User = Depends(admin),
) -> dict:
    return _out(await content.publish(ctype, tenant.id, key, user.id))


# --- AI drafting + file import (v5 Phase 11: "instead of admin types everything") ----------------

class GenerateIn(BaseModel):
    instruction: str = Field(min_length=3, max_length=2000)
    existing: Optional[dict] = None


@router.post("/{type_name}/generate")
async def generate_with_ai(
    body: GenerateIn, ctype: ContentType = Depends(content_type), tenant: Tenant = Depends(require_tenant_scope), user: User = Depends(admin)
) -> dict:
    """Draft a content item's `data` with AI from a plain-English instruction. The admin reviews and
    edits it, then saves/publishes as usual — nothing is auto-published."""
    try:
        data = await content_gen.draft(ctype, body.instruction, body.existing)
    except provider.AIUnavailable:
        raise HTTPException(503, "AI drafting isn't configured — set AI_PROVIDER/AI_MODEL/AI_API_KEY in backend/.env, or fill the form manually.")
    except provider.AIOutputInvalid:
        raise HTTPException(502, "The AI couldn't produce a usable draft — try rephrasing your instruction.")
    return {"data": data}


@router.post("/{type_name}/import")
async def import_from_file(
    file: UploadFile = File(...), ctype: ContentType = Depends(content_type), tenant: Tenant = Depends(require_tenant_scope), user: User = Depends(admin)
) -> dict:
    """Bulk-create items from an uploaded JSON file — either a list of `{key, data}` (or `{items: [...]}`)
    or a single `{key, data}`. New keys are created as drafts; existing keys are skipped (edit them in place)."""
    raw = await file.read()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "That file isn't valid JSON.")
    items = parsed.get("items") if isinstance(parsed, dict) and "items" in parsed else parsed
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items:
        raise HTTPException(422, 'Expected a JSON list of {"key": ..., "data": {...}} objects.')
    created, skipped, errors = [], [], []
    for i, item in enumerate(items):
        key = (item or {}).get("key")
        data = (item or {}).get("data")
        if not isinstance(key, str) or not isinstance(data, dict):
            errors.append({"index": i, "message": 'each item needs a string "key" and an object "data"'})
            continue
        try:
            await content.create(ctype, tenant.id, key, data, user.id)
            created.append(key)
        except content.Conflict:
            skipped.append(key)
        except content.ContentError as exc:
            errors.append({"index": i, "key": key, "message": exc.message})
    return {"created": created, "skipped": skipped, "errors": errors}
