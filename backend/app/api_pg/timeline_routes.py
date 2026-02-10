from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import create_timeline_event
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import TimelineEvent

router = APIRouter(tags=["Timeline"])


class TimelineEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    deal_id: Optional[str] = None
    contact_id: Optional[str] = None
    visibility: str = "internal_only"
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.get("/timeline")
async def list_timeline(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
    deal_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [TimelineEvent.tenant_id == user["tenant_id"]]
    if event_type:
        filters.append(TimelineEvent.event_type == event_type)
    if deal_id:
        filters.append(TimelineEvent.deal_id == deal_id)
    if contact_id:
        filters.append(TimelineEvent.contact_id == contact_id)

    total_res = await db.execute(select(func.count()).select_from(TimelineEvent).where(and_(*filters)))
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(TimelineEvent)
        .where(and_(*filters))
        .order_by(TimelineEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = (await db.execute(stmt)).scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "tenant_id": e.tenant_id,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "actor_id": e.actor_id,
                "actor_name": e.actor_name,
                "deal_id": e.deal_id,
                "contact_id": e.contact_id,
                "visibility": e.visibility,
                "metadata": e.meta or {},
                "created_at": dt_to_iso(e.created_at),
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/timeline", status_code=201)
async def create_timeline_event_endpoint(
    data: TimelineEventCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_timeline_event(
        db=db,
        tenant_id=user["tenant_id"],
        event_type=data.event_type,
        title=data.title,
        description=data.description,
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        deal_id=data.deal_id,
        contact_id=data.contact_id,
        visibility=data.visibility,
        metadata=data.metadata or {},
    )

