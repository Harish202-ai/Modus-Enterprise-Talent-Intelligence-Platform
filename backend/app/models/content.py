from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from app.models.common import TenantScoped

ContentStatus = Literal["draft", "published"]
KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"


class ContentVersion(TenantScoped):
    """One version of one content item. Published versions are never modified."""

    content_type: str
    key: str  # stable logical id across versions, e.g. "F06", "C13"
    version: int
    status: ContentStatus = "draft"
    data: Dict[str, Any] = Field(default_factory=dict)
    # Filled at publish: the exact published version of every item this one references.
    ref_versions: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    based_on_version: Optional[int] = None
    created_by: str = "system"
    updated_by: str = "system"
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None


class ContentCreate(BaseModel):
    key: str = Field(pattern=KEY_PATTERN)
    data: Dict[str, Any] = Field(default_factory=dict)


class DraftUpdate(BaseModel):
    data: Dict[str, Any]
