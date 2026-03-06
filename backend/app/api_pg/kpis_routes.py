from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import now_utc
from app.core.database import get_db
from app.pg_models.models import Affiliate, AffiliateCommission, AffiliateProgram, Contact, Deal, Lead, Pipeline, PipelineStage, TimelineEvent, User

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


def _is_finance_role(user: Dict[str, Any]) -> bool:
    return (user.get("role") or "").strip().lower() == "finance"


async def _build_agent_dashboard_rows(
    *,
    db: AsyncSession,
    tenant_id: str,
    start_dt,
    days_window: int,
) -> List[Dict[str, Any]]:
    users = (
        await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.is_active.is_(True))))
    ).scalars().all()
    if not users:
        return []

    user_ids = [u.id for u in users if u.id]
    touch_event_types = ["call_log", "email_sent", "email_received", "meeting", "lead_touchpoint"]

    activity_rows = (
        await db.execute(
            select(TimelineEvent.actor_id, func.count(TimelineEvent.id))
            .where(
                and_(
                    TimelineEvent.tenant_id == tenant_id,
                    TimelineEvent.actor_id.in_(user_ids),
                    TimelineEvent.created_at >= start_dt,
                    TimelineEvent.event_type.in_(touch_event_types),
                )
            )
            .group_by(TimelineEvent.actor_id)
        )
    ).all()
    activities_by_owner = {str(owner_id): int(count or 0) for owner_id, count in activity_rows if owner_id}

    lead_rows = (
        await db.execute(
            select(Lead.owner_id, func.count(Lead.id))
            .where(
                and_(
                    Lead.tenant_id == tenant_id,
                    Lead.owner_id.in_(user_ids),
                    Lead.last_touchpoint_at >= start_dt,
                )
            )
            .group_by(Lead.owner_id)
        )
    ).all()
    leads_by_owner = {str(owner_id): int(count or 0) for owner_id, count in lead_rows if owner_id}

    deal_adv_rows = (
        await db.execute(
            select(TimelineEvent.actor_id, func.count(TimelineEvent.id))
            .where(
                and_(
                    TimelineEvent.tenant_id == tenant_id,
                    TimelineEvent.actor_id.in_(user_ids),
                    TimelineEvent.event_type == "stage_changed",
                    TimelineEvent.created_at >= start_dt,
                )
            )
            .group_by(TimelineEvent.actor_id)
        )
    ).all()
    deals_advanced_by_owner = {str(owner_id): int(count or 0) for owner_id, count in deal_adv_rows if owner_id}

    deal_outcome_rows = (
        await db.execute(
            select(
                Deal.owner_id,
                func.count(Deal.id).filter(Deal.status == "won").label("won_count"),
                func.count(Deal.id).filter(Deal.status.in_(["won", "lost"])).label("closed_count"),
            )
            .where(
                and_(
                    Deal.tenant_id == tenant_id,
                    Deal.owner_id.in_(user_ids),
                )
            )
            .group_by(Deal.owner_id)
        )
    ).all()
    won_closed_by_owner: Dict[str, Dict[str, int]] = {
        str(owner_id): {"won": int(won_count or 0), "closed": int(closed_count or 0)}
        for owner_id, won_count, closed_count in deal_outcome_rows
        if owner_id
    }

    cycle_rows = (
        await db.execute(
            select(
                Deal.owner_id,
                func.avg(func.extract("epoch", Deal.closed_won_at - Deal.created_at)),
            )
            .where(
                and_(
                    Deal.tenant_id == tenant_id,
                    Deal.owner_id.in_(user_ids),
                    Deal.status == "won",
                    Deal.closed_won_at.is_not(None),
                    Deal.created_at.is_not(None),
                )
            )
            .group_by(Deal.owner_id)
        )
    ).all()
    cycle_by_owner = {str(owner_id): float(avg_cycle_seconds or 0.0) for owner_id, avg_cycle_seconds in cycle_rows if owner_id}

    rows: List[Dict[str, Any]] = []
    safe_days = max(1, int(days_window or 1))
    for u in users:
        owner_id = str(u.id)
        outcome = won_closed_by_owner.get(owner_id, {"won": 0, "closed": 0})
        closed_count = int(outcome.get("closed", 0) or 0)
        rows.append(
            {
                "user_id": owner_id,
                "name": f"{u.first_name} {u.last_name}".strip() or u.email,
                "activities_per_day": round(float(activities_by_owner.get(owner_id, 0)) / float(safe_days), 2),
                "leads_worked": int(leads_by_owner.get(owner_id, 0)),
                "deals_advanced": int(deals_advanced_by_owner.get(owner_id, 0)),
                "win_rate": round((float(outcome.get("won", 0) or 0) / float(closed_count) * 100.0), 2) if closed_count > 0 else 0.0,
                "average_sales_cycle_days": round(float(cycle_by_owner.get(owner_id, 0.0)) / 86400.0, 2)
                if cycle_by_owner.get(owner_id) is not None
                else 0.0,
            }
        )
    return rows


@router.get("/kpis/summary")
async def get_kpi_summary(
    time_range: str = Query("30d"),
    pipeline_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    tenant_id = user["tenant_id"]
    is_finance = _is_finance_role(user)
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
    agents: List[Dict[str, Any]] = []
    if not is_finance:
        agents = await _build_agent_dashboard_rows(
            db=db,
            tenant_id=tenant_id,
            start_dt=start_dt,
            days_window=max(1, days),
        )

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
            "agents": agents,
        },
    }


@router.get("/kpis/agent-dashboard")
async def get_agent_dashboard(
    time_range: str = Query("30d"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if _is_finance_role(user):
        raise HTTPException(status_code=403, detail="Finance users do not have access to agent productivity dashboards")

    tenant_id = user["tenant_id"]
    days = _parse_time_range_days(time_range)
    start_dt = now_utc() - timedelta(days=days)
    agents = await _build_agent_dashboard_rows(
        db=db,
        tenant_id=tenant_id,
        start_dt=start_dt,
        days_window=max(1, days),
    )
    return {"meta": {"time_range": time_range, "days": days}, "agents": agents}


@router.get("/kpis/finance/commissions")
async def get_finance_commission_report(
    status: Optional[str] = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    role = (user.get("role") or "").strip().lower()
    if role not in {"finance", "manager", "admin"}:
        raise HTTPException(status_code=403, detail="Finance, manager, or admin access required")

    tenant_id = user["tenant_id"]
    filters = [AffiliateCommission.tenant_id == tenant_id]
    if status:
        filters.append(AffiliateCommission.status == status)

    total = int(
        (
            await db.execute(
                select(func.count(AffiliateCommission.id)).where(and_(*filters))
            )
        ).scalar_one()
        or 0
    )

    rows = (
        await db.execute(
            select(
                AffiliateCommission,
                Affiliate.name,
                Affiliate.email,
                AffiliateProgram.name,
                Deal.name,
            )
            .select_from(AffiliateCommission)
            .outerjoin(
                Affiliate,
                and_(
                    Affiliate.id == AffiliateCommission.affiliate_id,
                    Affiliate.tenant_id == tenant_id,
                ),
            )
            .outerjoin(
                AffiliateProgram,
                and_(
                    AffiliateProgram.id == AffiliateCommission.program_id,
                    AffiliateProgram.tenant_id == tenant_id,
                ),
            )
            .outerjoin(
                Deal,
                and_(
                    Deal.id == AffiliateCommission.deal_id,
                    Deal.tenant_id == tenant_id,
                ),
            )
            .where(and_(*filters))
            .order_by(AffiliateCommission.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    totals_by_status_rows = (
        await db.execute(
            select(
                AffiliateCommission.status,
                func.coalesce(func.sum(AffiliateCommission.amount), 0.0),
                func.count(AffiliateCommission.id),
            )
            .where(AffiliateCommission.tenant_id == tenant_id)
            .group_by(AffiliateCommission.status)
        )
    ).all()
    totals_by_status = {
        str(stat or "unknown"): {
            "total_amount": round(float(total_amount or 0.0), 2),
            "count": int(count or 0),
        }
        for stat, total_amount, count in totals_by_status_rows
    }

    total_amount = round(float(sum(item["total_amount"] for item in totals_by_status.values())), 2)
    pending_amount = round(float(totals_by_status.get("pending", {}).get("total_amount", 0.0)), 2)
    approved_amount = round(float(totals_by_status.get("approved", {}).get("total_amount", 0.0)), 2)
    paid_amount = round(float(totals_by_status.get("paid", {}).get("total_amount", 0.0)), 2)

    return {
        "meta": {
            "status": status,
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        "summary": {
            "total_amount": total_amount,
            "pending_amount": pending_amount,
            "approved_amount": approved_amount,
            "paid_amount": paid_amount,
            "totals_by_status": totals_by_status,
        },
        "commissions": [
            {
                "id": commission.id,
                "affiliate_id": commission.affiliate_id,
                "affiliate_name": affiliate_name,
                "affiliate_email": affiliate_email,
                "program_id": commission.program_id,
                "program_name": program_name,
                "deal_id": commission.deal_id,
                "deal_name": deal_name,
                "amount": round(float(commission.amount or 0.0), 2),
                "currency": commission.currency,
                "status": commission.status,
                "notes": commission.notes,
                "approved_at": commission.approved_at.isoformat() if commission.approved_at else None,
                "approved_by": commission.approved_by,
                "paid_at": commission.paid_at.isoformat() if commission.paid_at else None,
                "paid_by": commission.paid_by,
                "created_at": commission.created_at.isoformat() if commission.created_at else None,
                "updated_at": commission.updated_at.isoformat() if commission.updated_at else None,
            }
            for commission, affiliate_name, affiliate_email, program_name, deal_name in rows
        ],
    }
