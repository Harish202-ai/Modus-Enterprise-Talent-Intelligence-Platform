from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from app.models.common import TenantScoped, utcnow


class AuditEvent(TenantScoped):
    actor_id: str  # user id, or "system" for scripts/jobs
    candidate_id: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utcnow)
