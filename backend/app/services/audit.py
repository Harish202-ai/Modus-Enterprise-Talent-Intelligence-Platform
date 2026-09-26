from typing import Any, Dict, Optional

from app import database
from app.models.audit import AuditEvent


async def record(
    *,
    tenant_id: str,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    candidate_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        candidate_id=candidate_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata=metadata or {},
    )
    await database.audit_events().insert_one(event.to_mongo())
    return event
