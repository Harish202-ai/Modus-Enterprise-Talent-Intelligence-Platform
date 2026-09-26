"""Shared model pieces. Every tenant-scoped document carries `tenant_id`."""
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoModel(BaseModel):
    """Base for documents stored in Mongo; `id` <-> `_id`."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_id, alias="_id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class TenantScoped(MongoModel):
    tenant_id: str
