from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import now_utc
from app.core.database import get_db
from app.pg_models.models import Contact, Deal, Pipeline, PipelineStage, TimelineEvent

router = APIRouter(tags=["KPIs"])


def _parse_time_range_days(value: Optional[str]) -> int:
    raw = (value or "").strip().lower()
    if not raw:
        return 30
    m = re.match(r"^(\d+)", raw)
    if not m:
        return 30
    days = int(m.group(1))
    return max(1, min(days, 3650))


@router.get("/kpis/summary")
async def get_kpi_summary(
    time_range: str = Query("30d"),
    pipeline_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    tenant_id = user["tenant_id"]
    days = _parse_time_range_days(time_range)
    start_dt = now_utc() - timedelta(days=days)

    # Deals (all-time, current snapshot)
    deals_row = (
        await db.execute(
            select(
                func.count(Deal.id).label("total"),
                func.count(Deal.id).filter(Deal.status == "won").label("won"),
                func.count(Deal.id).filter(Deal.status == "lost").label("lost"),
                func.count(Deal.id).filter(Deal.status == "open").label("open"),
                func.coalesce(func.sum(Deal.amount), 0.0).label("value"),
                func.coalesce(func.sum(Deal.amount).filter(Deal.status == "won"), 0.0).label("won_value"),
            ).where(Deal.tenant_id == tenant_id)
        )
    ).one()

    deals_total = int(deals_row.total or 0)
    deals_won = int(deals_row.won or 0)
    deals_lost = int(deals_row.lost or 0)
    deals_open = int(deals_row.open or 0)
    deals_value = float(deals_row.value or 0.0)
    deals_won_value = float(deals_row.won_value or 0.0)

    # Contacts (new in range)
    contacts_row = (
        await db.execute(
            select(
                func.count(Contact.id).label("total"),
                func.count(Contact.id).filter(Contact.created_at >= start_dt).label("new"),
            ).where(Contact.tenant_id == tenant_id)
        )
    ).one()

    contacts_total = int(contacts_row.total or 0)
    contacts_new = int(contacts_row.new or 0)

    # Pipeline distribution (current snapshot)
    pipeline: Optional[Pipeline] = None
    if pipeline_id:
        pipeline = (
            await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
        ).scalar_one_or_none()
    if not pipeline:
        pipeline = (
            await db.execute(
                select(Pipeline)
                .where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)))
                .order_by(Pipeline.display_order.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
    if not pipeline:
        pipeline = (
            await db.execute(select(Pipeline).where(Pipeline.tenant_id == tenant_id).order_by(Pipeline.display_order.asc()).limit(1))
        ).scalar_one_or_none()

    pipeline_stages: list[Dict[str, Any]] = []
    if pipeline:
        stage_rows = (
            await db.execute(
                select(
                    PipelineStage.id,
                    PipelineStage.name,
                    func.count(Deal.id).label("deal_count"),
                    func.coalesce(func.sum(Deal.amount), 0.0).label("deal_value"),
                )
                .select_from(PipelineStage)
                .outerjoin(
                    Deal,
                    and_(
                        Deal.tenant_id == tenant_id,
                        Deal.pipeline_id == pipeline.id,
                        Deal.stage_id == PipelineStage.id,
                    ),
                )
                .where(PipelineStage.pipeline_id == pipeline.id)
                .group_by(PipelineStage.id, PipelineStage.name, PipelineStage.display_order)
                .order_by(PipelineStage.display_order.asc())
            )
        ).all()

        pipeline_stages = [
            {
                "name": name,
                "count": int(deal_count or 0),
                "value": float(deal_value or 0.0),
            }
            for _id, name, deal_count, deal_value in stage_rows
        ]

    pipeline_velocity = round((deals_won_value / deals_total), 2) if deals_total > 0 else 0.0

    # Outreach (in range, based on timeline event types created by outreach logging)
    touch_types = ["call_log", "email_sent", "email_received", "meeting"]
    touch_rows = (
        await db.execute(
            select(TimelineEvent.event_type, func.count(TimelineEvent.id))
            .where(
                and_(
                    TimelineEvent.tenant_id == tenant_id,
                    TimelineEvent.created_at >= start_dt,
                    TimelineEvent.event_type.in_(touch_types),
                )
            )
            .group_by(TimelineEvent.event_type)
        )
    ).all()
    touch_map = {t: int(c or 0) for t, c in touch_rows}

    calls = touch_map.get("call_log", 0)
    emails = touch_map.get("email_sent", 0) + touch_map.get("email_received", 0)
    meetings = touch_map.get("meeting", 0)
    total_touchpoints = calls + emails + meetings

    # Conversion (all-time snapshot)
    total_closed = deals_won + deals_lost
    conversion_rate = (deals_won / total_closed * 100.0) if total_closed > 0 else 0.0
    avg_deal_size = (deals_won_value / deals_won) if deals_won > 0 else 0.0

    avg_close_seconds = (
        await db.execute(
            select(func.avg(func.extract("epoch", Deal.closed_won_at - Deal.created_at)))
            .where(
                and_(
                    Deal.tenant_id == tenant_id,
                    Deal.status == "won",
                    Deal.closed_won_at.is_not(None),
                    Deal.created_at.is_not(None),
                )
            )
        )
    ).scalar_one_or_none()
    avg_days_to_close = float(avg_close_seconds or 0.0) / 86400.0 if avg_close_seconds else 0.0

    return {
        "meta": {"time_range": time_range, "days": days},
        "deals": {
            "total": deals_total,
            "won": deals_won,
            "lost": deals_lost,
            "open": deals_open,
            "value": round(deals_value, 2),
            "wonValue": round(deals_won_value, 2),
        },
        "contacts": {"total": contacts_total, "new": contacts_new},
        "pipeline": {
            "pipeline_id": pipeline.id if pipeline else None,
            "stages": pipeline_stages,
            "velocity": pipeline_velocity,
        },
        "outreach": {
            "calls": calls,
            "emails": emails,
            "meetings": meetings,
            "totalTouchpoints": total_touchpoints,
        },
        "conversion": {
            "rate": conversion_rate,
            "avgDealSize": round(avg_deal_size, 2),
            "avgDaysToClose": round(avg_days_to_close, 2),
        },
    }

