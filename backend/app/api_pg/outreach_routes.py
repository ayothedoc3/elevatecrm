from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import (
    complete_open_next_step_tasks_for_deal,
    create_timeline_event,
    upsert_open_next_step_task_for_deal,
)
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Deal, OutreachActivity

router = APIRouter(tags=["Outreach"])


class OutreachCreate(BaseModel):
    deal_id: str = Field(..., min_length=1)
    activity_type: str = Field(..., min_length=1, max_length=50)
    direction: str = "outbound"
    status: str = "completed"
    subject: Optional[str] = None
    notes: Optional[str] = None
    got_response: bool = False


@router.post("/outreach", status_code=201)
async def create_outreach_activity(
    payload: OutreachCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    now = now_utc()

    deal = (
        await db.execute(select(Deal).where(and_(Deal.id == payload.deal_id, Deal.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    activity = OutreachActivity(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        deal_id=payload.deal_id,
        user_id=user["id"],
        activity_type=payload.activity_type,
        direction=payload.direction,
        status=payload.status,
        subject=payload.subject,
        notes=payload.notes,
        got_response=bool(payload.got_response),
        created_at=now,
    )
    db.add(activity)

    # Timeline event types aligned to ActivityPage config + ReportsPage rollups
    type_map = {
        "call": "call_log",
        "email": "email_sent",
        "sms": "sms_sent",
        "meeting": "meeting",
        "demo": "meeting",
        "note": "note",
    }
    evt_type = type_map.get((payload.activity_type or "").lower(), "note")
    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type=evt_type,
        title=(payload.subject or f"{payload.activity_type}").strip(),
        description=payload.notes,
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        deal_id=payload.deal_id,
    )

    # Discipline: after every interaction, complete current Next Step task and ensure a fresh one exists.
    if (deal.status or "open") == "open":
        await complete_open_next_step_tasks_for_deal(db, tenant_id, payload.deal_id, user["id"])
        if deal.next_step_at:
            await upsert_open_next_step_task_for_deal(
                db=db,
                tenant_id=tenant_id,
                deal_id=payload.deal_id,
                due_at=deal.next_step_at,
                owner_id=deal.owner_id or user["id"],
                created_by=user["id"],
                note=deal.next_step_note,
            )

    await db.flush()

    return {
        "id": activity.id,
        "tenant_id": activity.tenant_id,
        "deal_id": activity.deal_id,
        "user_id": activity.user_id,
        "activity_type": activity.activity_type,
        "direction": activity.direction,
        "status": activity.status,
        "subject": activity.subject,
        "notes": activity.notes,
        "got_response": activity.got_response,
        "created_at": dt_to_iso(activity.created_at),
    }


@router.get("/outreach/deal/{deal_id}")
async def list_deal_outreach(
    deal_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    activities = (
        await db.execute(
            select(OutreachActivity)
            .where(and_(OutreachActivity.deal_id == deal_id, OutreachActivity.tenant_id == tenant_id))
            .order_by(OutreachActivity.created_at.desc())
            .limit(100)
        )
    ).scalars().all()

    touchpoint_count = len([a for a in activities if (a.status or "") in ["completed", "no_answer", "voicemail"]])

    return {
        "activities": [
            {
                "id": a.id,
                "tenant_id": a.tenant_id,
                "deal_id": a.deal_id,
                "user_id": a.user_id,
                "activity_type": a.activity_type,
                "direction": a.direction,
                "status": a.status,
                "subject": a.subject,
                "notes": a.notes,
                "got_response": a.got_response,
                "created_at": dt_to_iso(a.created_at),
            }
            for a in activities
        ],
        "total": len(activities),
        "touchpoint_count": touchpoint_count,
    }


@router.get("/outreach/deal/{deal_id}/summary")
async def get_deal_outreach_summary(
    deal_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    activities = (
        await db.execute(
            select(OutreachActivity)
            .where(and_(OutreachActivity.deal_id == deal_id, OutreachActivity.tenant_id == tenant_id))
            .order_by(OutreachActivity.created_at.desc())
        )
    ).scalars().all()

    calls = len([a for a in activities if a.activity_type == "call"])
    emails = len([a for a in activities if a.activity_type == "email"])
    sms = len([a for a in activities if a.activity_type == "sms"])
    meetings = len([a for a in activities if a.activity_type == "meeting"])
    responses = len([a for a in activities if bool(a.got_response)])

    last_activity = activities[0] if activities else None
    days_since = None
    if last_activity and last_activity.created_at:
        days_since = (now_utc() - last_activity.created_at).days

    return {
        "deal_id": deal_id,
        "total_touchpoints": len(activities),
        "calls": calls,
        "emails": emails,
        "sms": sms,
        "meetings": meetings,
        "responses": responses,
        "last_activity_at": dt_to_iso(last_activity.created_at) if last_activity else None,
        "days_since_last_contact": days_since,
    }

