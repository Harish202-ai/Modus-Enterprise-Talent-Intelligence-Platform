"""Orientation: the one explainer video and its "mark as watched" completion (plan v2 Phase 3).

No milestone tracking and no knowledge-check gate — just which published video version
a candidate marked as watched, and when.
"""
from app import database
from app.content.registry import get_type
from app.models.common import utcnow
from app.models.user import Orientation, OrientationIn
from app.services import audit
from app.services.content import Invalid, NotFound, get_version


async def check_video(tenant_id: str, body: OrientationIn) -> None:
    """The referenced video version must exist and be published."""
    try:
        video = await get_version(get_type("videos"), tenant_id, body.video_key, body.video_version)
    except NotFound:
        video = None
    if video is None or video.status != "published":
        raise Invalid("That video isn't available", [{"field": "orientation", "message": "unknown or unpublished video version"}])


async def mark_watched(tenant_id: str, user_id: str, body: OrientationIn) -> Orientation:
    await check_video(tenant_id, body)
    record = Orientation(**body.model_dump(), watched_at=utcnow())
    await database.users().update_one(
        {"_id": user_id, "tenant_id": tenant_id}, {"$set": {"orientation": record.model_dump(), "updated_at": record.watched_at}}
    )
    await audit.record(
        tenant_id=tenant_id, actor_id=user_id, candidate_id=user_id, entity_type="video", entity_id=body.video_key,
        action="orientation.video_watched", metadata={"version": body.video_version},
    )
    return record
