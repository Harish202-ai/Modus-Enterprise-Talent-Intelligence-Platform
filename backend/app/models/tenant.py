from typing import Any, Dict, Literal

from pydantic import BaseModel, Field

from app.models.common import MongoModel

TenantStatus = Literal["active", "suspended"]


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=200)


class Tenant(MongoModel):
    slug: str
    name: str
    status: TenantStatus = "active"
    # Tenant overlays (branding, locale, price-book reference...) land here later.
    settings: Dict[str, Any] = Field(default_factory=dict)
