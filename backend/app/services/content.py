"""Versioned content: draft -> validate -> publish (immutable); edits create a new version.

Invariants (enforced by queries + indexes, not just by the API):
- (tenant_id, key, version) is unique.
- At most one draft per key (partial unique index on status == "draft").
- Writes only ever match `status: "draft"`, so a published version cannot change.
"""
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app import database
from app.content.registry import ContentType
from app.content.validation import Error, RefLookup, validate
from app.models.common import utcnow
from app.models.content import ContentVersion
from app.services import audit


class ContentError(Exception):
    status_code = 400

    def __init__(self, message: str, errors: Optional[List[Error]] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []


class NotFound(ContentError):
    status_code = 404


class Conflict(ContentError):
    status_code = 409


class Invalid(ContentError):
    status_code = 422


def _coll(ctype: ContentType):
    return database.collection(ctype.name)


def _model(doc: dict) -> ContentVersion:
    return ContentVersion.model_validate(doc)


async def _audit(ctype: ContentType, item: ContentVersion, action: str, actor_id: str) -> None:
    await audit.record(
        tenant_id=item.tenant_id,
        actor_id=actor_id,
        entity_type=ctype.name,
        entity_id=item.id,
        action=f"content.{action}",
        metadata={"key": item.key, "version": item.version},
    )


async def list_items(ctype: ContentType, tenant_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """One row per key: its latest version plus the latest published version number."""
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$sort": {"key": 1, "version": -1}},
        {
            "$group": {
                "_id": "$key",
                "latest": {"$first": "$$ROOT"},
                "published_version": {"$max": {"$cond": [{"$eq": ["$status", "published"]}, "$version", None]}},
                "has_draft": {"$max": {"$eq": ["$status", "draft"]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = []
    for row in await _coll(ctype).aggregate(pipeline).to_list(None):
        latest = row["latest"]
        if status == "published" and row["published_version"] is None:
            continue
        if status == "draft" and not row["has_draft"]:
            continue
        rows.append(
            {
                "key": row["_id"],
                "title": latest["data"].get(ctype.title_field),
                "latest_version": latest["version"],
                "latest_status": latest["status"],
                "published_version": row["published_version"],
                "has_draft": row["has_draft"],
                "updated_at": latest["updated_at"],
            }
        )
    return rows


async def versions(ctype: ContentType, tenant_id: str, key: str) -> List[ContentVersion]:
    docs = await _coll(ctype).find({"tenant_id": tenant_id, "key": key}).sort("version", -1).to_list(None)
    if not docs:
        raise NotFound(f"{ctype.label}: '{key}' not found")
    return [_model(d) for d in docs]


async def get_version(ctype: ContentType, tenant_id: str, key: str, version: int) -> ContentVersion:
    doc = await _coll(ctype).find_one({"tenant_id": tenant_id, "key": key, "version": version})
    if not doc:
        raise NotFound(f"{ctype.label}: '{key}' v{version} not found")
    return _model(doc)


async def get_current(ctype: ContentType, tenant_id: str, key: str) -> ContentVersion:
    """Latest published version."""
    doc = await _coll(ctype).find_one({"tenant_id": tenant_id, "key": key, "status": "published"}, sort=[("version", -1)])
    if not doc:
        raise NotFound(f"{ctype.label}: '{key}' has no published version")
    return _model(doc)


async def get_draft(ctype: ContentType, tenant_id: str, key: str) -> ContentVersion:
    doc = await _coll(ctype).find_one({"tenant_id": tenant_id, "key": key, "status": "draft"})
    if not doc:
        raise NotFound(f"{ctype.label}: '{key}' has no draft")
    return _model(doc)


async def create(ctype: ContentType, tenant_id: str, key: str, data: dict, actor_id: str) -> ContentVersion:
    if await _coll(ctype).find_one({"tenant_id": tenant_id, "key": key}, projection={"_id": 1}):
        raise Conflict(f"{ctype.label}: '{key}' already exists — edit it or create a new version")
    item = ContentVersion(
        tenant_id=tenant_id, content_type=ctype.name, key=key, version=1, data=data, created_by=actor_id, updated_by=actor_id
    )
    try:
        await _coll(ctype).insert_one(item.to_mongo())
    except DuplicateKeyError:
        raise Conflict(f"{ctype.label}: '{key}' already exists")
    await _audit(ctype, item, "created", actor_id)
    return item


async def update_draft(ctype: ContentType, tenant_id: str, key: str, data: dict, actor_id: str) -> ContentVersion:
    doc = await _coll(ctype).find_one_and_update(
        {"tenant_id": tenant_id, "key": key, "status": "draft"},
        {"$set": {"data": data, "updated_at": utcnow(), "updated_by": actor_id}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        await versions(ctype, tenant_id, key)  # 404 if the key doesn't exist at all
        raise Conflict(f"{ctype.label}: '{key}' has no draft — published versions are immutable; create a new version")
    item = _model(doc)
    await _audit(ctype, item, "draft_updated", actor_id)
    return item


async def new_version(ctype: ContentType, tenant_id: str, key: str, actor_id: str) -> ContentVersion:
    """Start a new draft version from the latest published one."""
    history = await versions(ctype, tenant_id, key)
    if any(v.status == "draft" for v in history):
        raise Conflict(f"{ctype.label}: '{key}' already has a draft (v{next(v.version for v in history if v.status == 'draft')})")
    base = next(v for v in history if v.status == "published")
    item = ContentVersion(
        tenant_id=tenant_id,
        content_type=ctype.name,
        key=key,
        version=history[0].version + 1,
        data=base.data,
        based_on_version=base.version,
        created_by=actor_id,
        updated_by=actor_id,
    )
    try:
        await _coll(ctype).insert_one(item.to_mongo())
    except DuplicateKeyError:  # concurrent draft creation
        raise Conflict(f"{ctype.label}: '{key}' already has a draft")
    await _audit(ctype, item, "version_created", actor_id)
    return item


async def discard_draft(ctype: ContentType, tenant_id: str, key: str, actor_id: str) -> ContentVersion:
    draft = await get_draft(ctype, tenant_id, key)
    await _coll(ctype).delete_one({"_id": draft.id, "status": "draft"})
    await _audit(ctype, draft, "draft_discarded", actor_id)
    return draft


async def validate_draft(ctype: ContentType, tenant_id: str, key: str) -> List[Error]:
    draft = await get_draft(ctype, tenant_id, key)
    return await validate(ctype, key, draft.data, RefLookup(tenant_id))


async def publish(ctype: ContentType, tenant_id: str, key: str, actor_id: str) -> ContentVersion:
    draft = await get_draft(ctype, tenant_id, key)
    lookup = RefLookup(tenant_id)
    errors = await validate(ctype, key, draft.data, lookup)
    if errors:
        raise Invalid(f"{ctype.label}: '{key}' v{draft.version} failed validation", errors)
    now = utcnow()
    doc = await _coll(ctype).find_one_and_update(
        {"_id": draft.id, "status": "draft", "updated_at": draft.updated_at},  # nobody edited it since we validated
        {
            "$set": {
                "status": "published",
                "ref_versions": lookup.pinned(),
                "published_at": now,
                "published_by": actor_id,
                "updated_at": now,
                "updated_by": actor_id,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise Conflict(f"{ctype.label}: '{key}' draft changed while publishing — validate and publish again")
    item = _model(doc)
    await _audit(ctype, item, "published", actor_id)
    return item
