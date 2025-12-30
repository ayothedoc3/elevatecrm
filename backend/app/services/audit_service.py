from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json
from datetime import datetime, timezone

from app.models import (
    AuditLog, TimelineEvent, TimelineEventType, VisibilityScope
)


async def create_audit_log(
    db: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str],
    action: str,
    object_type: str,
    object_id: str,
    before_json: Optional[dict] = None,
    after_json: Optional[dict] = None,
    metadata: Optional[dict] = None,
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """Create an audit log entry."""
    audit_log = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before_json=json.dumps(before_json) if before_json else None,
        after_json=json.dumps(after_json) if after_json else None,
        metadata_json=json.dumps(metadata) if metadata else '{}',
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_log)
    await db.flush()
    return audit_log


async def create_timeline_event(
    db: AsyncSession,
    tenant_id: str,
    event_type: TimelineEventType,
    title: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    company_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
    visibility: VisibilityScope = VisibilityScope.INTERNAL_ONLY,
    due_date: Optional[datetime] = None
) -> TimelineEvent:
    """Create a timeline event."""
    event = TimelineEvent(
        tenant_id=tenant_id,
        contact_id=contact_id,
        deal_id=deal_id,
        company_id=company_id,
        event_type=event_type,
        title=title,
        description=description,
        metadata_json=json.dumps(metadata) if metadata else '{}',
        visibility=visibility,
        actor_id=actor_id,
        actor_name=actor_name,
        due_date=due_date
    )
    db.add(event)
    await db.flush()
    return event
