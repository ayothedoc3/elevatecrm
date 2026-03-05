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
from app.pg_models.models import Contact, Deal, Lead, Pipeline, PipelineStage, TimelineEvent, User

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
    is_finance = (user.get("role") or "").strip().lower() == "finance"
    days = _parse_time_range_days(time_range)
    start_dt = now_utc() - timedelta(days=days)

    # Deals (all-time, current snapshot)
    deal_filters = [Deal.tenant_id == tenant_id]
    if is_finance:
        deal_filters.append(Deal.status == "won")
    deals_row = (
        await db.execute(
            select(
                func.count(Deal.id).label("total"),
                func.count(Deal.id).filter(Deal.status == "won").label("won"),
                func.count(Deal.id).filter(Deal.status == "lost").label("lost"),
                func.count(Deal.id).filter(Deal.status == "open").label("open"),
                func.coalesce(func.sum(Deal.amount), 0.0).label("value"),
                func.coalesce(func.sum(Deal.amount).filter(Deal.status == "won"), 0.0).label("won_value"),
            ).where(and_(*deal_filters))
        )
    ).one()

    deals_total = int(deals_row.total or 0)
    deals_won = int(deals_row.won or 0)
    deals_lost = int(deals_row.lost or 0)
    deals_open = int(deals_row.open or 0)
    deals_value = float(deals_row.value or 0.0)
    deals_won_value = float(deals_row.won_value or 0.0)

    # Contacts (new in range)
    if is_finance:
        contacts_total = 0
        contacts_new = 0
    else:
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
    if pipeline and not is_finance:
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
    if is_finance:
        calls = 0
        emails = 0
        meetings = 0
        total_touchpoints = 0
    else:
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

    # Qualification dashboard
    leads_in_range = []
    if not is_finance:
        leads_in_range = (
            await db.execute(
                select(Lead).where(
                    and_(
                        Lead.tenant_id == tenant_id,
                        Lead.created_at >= start_dt,
                    )
                )
            )
        ).scalars().all()
    lead_count = len(leads_in_range)
    contacted_count = sum(1 for l in leads_in_range if int(l.touchpoints_count or 0) > 0)
    qualified_count = sum(1 for l in leads_in_range if (l.status or "").strip().lower() in {"qualified", "converted"})
    speed_minutes = []
    for l in leads_in_range:
        if l.first_touchpoint_at and l.created_at:
            speed_minutes.append(max(0.0, (l.first_touchpoint_at - l.created_at).total_seconds() / 60.0))
    disq_rows = []
    if not is_finance:
        disq_rows = (
            await db.execute(
                select(Lead.disqualification_reason, func.count(Lead.id))
                .where(
                    and_(
                        Lead.tenant_id == tenant_id,
                        Lead.status == "disqualified",
                    )
                )
                .group_by(Lead.disqualification_reason)
            )
        ).all()
    disqualification_reasons = {
        (reason or "Unspecified"): int(count or 0)
        for reason, count in disq_rows
    }

    # Sales dashboard
    open_deals = []
    if not is_finance:
        open_deals = (await db.execute(select(Deal).where(and_(Deal.tenant_id == tenant_id, Deal.status == "open")))).scalars().all()
    open_stage_ids = [d.stage_id for d in open_deals if d.stage_id]
    stages_map: Dict[str, PipelineStage] = {}
    if open_stage_ids:
        stages = (await db.execute(select(PipelineStage).where(PipelineStage.id.in_(open_stage_ids)))).scalars().all()
        stages_map = {s.id: s for s in stages}

    default_probabilities = {
        "demo scheduled": 0.25,
        "demo completed": 0.40,
        "decision pending": 0.60,
        "verbal agreement": 0.85,
        "contract sent": 0.90,
        "closed won": 1.0,
        "closed lost": 0.0,
    }
    weighted_pipeline = 0.0
    for d in open_deals:
        stage = stages_map.get(d.stage_id) if d.stage_id else None
        stage_name = (stage.name or "").strip().lower() if stage else ""
        prob = default_probabilities.get(stage_name)
        if prob is None:
            prob = float((stage.probability or 0.0) / 100.0) if stage else 0.0
        weighted_pipeline += float(d.amount or 0.0) * max(0.0, min(1.0, float(prob)))

    conversion_rows = []
    if not is_finance:
        conversion_rows = (
            await db.execute(
                select(TimelineEvent.meta["to_stage"].astext, func.count(TimelineEvent.id))
                .where(
                    and_(
                        TimelineEvent.tenant_id == tenant_id,
                        TimelineEvent.event_type == "stage_changed",
                        TimelineEvent.created_at >= start_dt,
                    )
                )
                .group_by(TimelineEvent.meta["to_stage"].astext)
            )
        ).all()
    total_stage_changes = sum(int(c or 0) for _, c in conversion_rows) or 1
    stage_conversion = {
        (stage_name or "Unknown"): round((int(count or 0) / total_stage_changes) * 100.0, 2)
        for stage_name, count in conversion_rows
    }

    forecast_by_month: Dict[str, float] = {}
    for d in open_deals:
        base_dt = d.estimated_close_date or d.next_step_at
        if not base_dt:
            continue
        month_key = base_dt.strftime("%Y-%m")
        forecast_by_month[month_key] = round(float(forecast_by_month.get(month_key, 0.0) + float(d.amount or 0.0)), 2)

    won_rows_motion = (
        await db.execute(
            select(Deal.sales_motion_type, func.coalesce(func.sum(Deal.amount), 0.0))
            .where(and_(Deal.tenant_id == tenant_id, Deal.status == "won"))
            .group_by(Deal.sales_motion_type)
        )
    ).all()
    revenue_by_sales_motion = {str(k or "unknown"): round(float(v or 0.0), 2) for k, v in won_rows_motion}

    won_rows_client = (
        await db.execute(
            select(Deal.client_name, func.coalesce(func.sum(Deal.amount), 0.0))
            .where(and_(Deal.tenant_id == tenant_id, Deal.status == "won"))
            .group_by(Deal.client_name)
        )
    ).all()
    revenue_by_client = {str(k or "Unspecified"): round(float(v or 0.0), 2) for k, v in won_rows_client}

    # Agent dashboard
    users = []
    if not is_finance:
        users = (await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.is_active.is_(True))))).scalars().all()
    days_window = max(1, days)
    touch_event_types = ["call_log", "email_sent", "email_received", "meeting", "lead_touchpoint"]
    agents: Dict[str, Any] = {}
    for u in users:
        activities = int(
            (
                await db.execute(
                    select(func.count(TimelineEvent.id)).where(
                        and_(
                            TimelineEvent.tenant_id == tenant_id,
                            TimelineEvent.actor_id == u.id,
                            TimelineEvent.created_at >= start_dt,
                            TimelineEvent.event_type.in_(touch_event_types),
                        )
                    )
                )
            ).scalar_one()
            or 0
        )
        leads_worked = int(
            (
                await db.execute(
                    select(func.count(Lead.id)).where(
                        and_(
                            Lead.tenant_id == tenant_id,
                            Lead.owner_id == u.id,
                            Lead.last_touchpoint_at >= start_dt,
                        )
                    )
                )
            ).scalar_one()
            or 0
        )
        deals_advanced = int(
            (
                await db.execute(
                    select(func.count(TimelineEvent.id)).where(
                        and_(
                            TimelineEvent.tenant_id == tenant_id,
                            TimelineEvent.actor_id == u.id,
                            TimelineEvent.event_type == "stage_changed",
                            TimelineEvent.created_at >= start_dt,
                        )
                    )
                )
            ).scalar_one()
            or 0
        )
        won_count = int(
            (
                await db.execute(select(func.count(Deal.id)).where(and_(Deal.tenant_id == tenant_id, Deal.owner_id == u.id, Deal.status == "won")))
            ).scalar_one()
            or 0
        )
        closed_count = int(
            (
                await db.execute(select(func.count(Deal.id)).where(and_(Deal.tenant_id == tenant_id, Deal.owner_id == u.id, Deal.status.in_(["won", "lost"]))))
            ).scalar_one()
            or 0
        )
        avg_cycle_seconds = (
            await db.execute(
                select(func.avg(func.extract("epoch", Deal.closed_won_at - Deal.created_at))).where(
                    and_(
                        Deal.tenant_id == tenant_id,
                        Deal.owner_id == u.id,
                        Deal.status == "won",
                        Deal.closed_won_at.is_not(None),
                        Deal.created_at.is_not(None),
                    )
                )
            )
        ).scalar_one_or_none()

        agents[u.id] = {
            "user_id": u.id,
            "name": f"{u.first_name} {u.last_name}".strip() or u.email,
            "activities_per_day": round(float(activities) / float(days_window), 2),
            "leads_worked": leads_worked,
            "deals_advanced": deals_advanced,
            "win_rate": round((float(won_count) / float(closed_count) * 100.0), 2) if closed_count > 0 else 0.0,
            "average_sales_cycle_days": round((float(avg_cycle_seconds or 0.0) / 86400.0), 2) if avg_cycle_seconds else 0.0,
        }

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
        "qualification_dashboard": {
            "speed_to_lead_minutes": round(sum(speed_minutes) / len(speed_minutes), 1) if speed_minutes else 0.0,
            "contact_rate": round((float(contacted_count) / float(lead_count) * 100.0), 2) if lead_count > 0 else 0.0,
            "qualification_rate": round((float(qualified_count) / float(lead_count) * 100.0), 2) if lead_count > 0 else 0.0,
            "disqualification_reasons": disqualification_reasons,
        },
        "sales_dashboard": {
            "stage_conversion_percent": stage_conversion,
            "weighted_pipeline": round(float(weighted_pipeline), 2),
            "forecast_by_month": dict(sorted(forecast_by_month.items())),
            "revenue_by_sales_motion": revenue_by_sales_motion,
            "revenue_by_client": revenue_by_client,
        },
        "agent_dashboard": {
            "agents": list(agents.values()),
        },
    }
