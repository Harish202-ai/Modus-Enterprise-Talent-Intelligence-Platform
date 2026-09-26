"""Public site content (no sign-in). Only *published* `site_content` versions are ever returned."""
from typing import Optional

from fastapi import APIRouter, Depends, Path

from app.api.deps import current_tenant
from app.content.registry import get_type
from app.content.validation import youtube_id
from app.models.content import KEY_PATTERN, ContentVersion
from app.models.tenant import Tenant
from app.services import content

router = APIRouter(prefix="/site", tags=["site (public)"])


def _video_out(video: ContentVersion) -> dict:
    data = video.data
    embed_url: Optional[str] = None
    if data.get("provider") == "youtube":
        vid = youtube_id(data.get("url", ""))
        embed_url = f"https://www.youtube-nocookie.com/embed/{vid}?rel=0&cc_load_policy=1" if vid else None
    return {
        "key": video.key,
        "version": video.version,
        "title": data.get("title"),
        "description": data.get("description"),
        "provider": data.get("provider"),
        "url": data.get("url"),
        "embed_url": embed_url,
        "captions_url": data.get("captions_url"),
        "transcript": data.get("transcript"),
    }


@router.get("/{key}")
async def get_page(key: str = Path(pattern=KEY_PATTERN), tenant: Tenant = Depends(current_tenant)) -> dict:
    page = await content.get_current(get_type("site_content"), tenant.id, key)
    video = None
    video_key = page.data.get("video_key")
    if video_key:
        # The exact video version pinned when this page version was published.
        version = page.ref_versions["videos"][video_key]
        video = _video_out(await content.get_version(get_type("videos"), tenant.id, video_key, version))
    return {"key": page.key, "version": page.version, **{k: v for k, v in page.data.items() if k != "video_key"}, "video": video}
