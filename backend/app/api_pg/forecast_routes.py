from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import VALID_LEAD_TIERS, calculate_tier, now_utc, tier_probability
from app.core.database import get_db
from app.pg_models.models import Deal, OutreachActivity, PipelineStage

router = APIRouter(tags=["Forecast"])


@router.get("/forecast/summary")
async def get_forecast_summary(
    sales_motion_type: Optional[str] = None,
    partner_id: Optional[str] = None,
    product_id: Optional[str] = None,
    client_name: Optional[str] = None,
    lead_tier: Optional[str] = None,
    owner_id: Optional[str] = None,
    include_closed: bool = False,
    stale_days: int = Query(3, ge=1, le=90),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    if (user.get("role") or "").strip().lower() == "finance":
        include_closed = True

    filters = [Deal.tenant_id == tenant_id]
    if (user.get("role") or "").strip().lower() == "finance":
        filters.append(Deal.status == "won")
    elif not include_closed:
        filters.append(Deal.status == "open")
    if sales_motion_type:
        filters.append(Deal.sales_motion_type == sales_motion_type)
    if partner_id:
        filters.append(Deal.partner_id == partner_id)
    if product_id:
        filters.append(Deal.product_id == product_id)
    if client_name:
        filters.append(Deal.client_name == client_name)
    if owner_id:
        filters.append(Deal.owner_id == owner_id)
    if lead_tier:
        tier_norm = lead_tier.strip().upper()
        if tier_norm not in VALID_LEAD_TIERS:
            raise HTTPException(status_code=400, detail="Invalid lead_tier. Must be one of: A, B, C, D")
        filters.append(Deal.lead_tier == tier_norm)

    deals = (await db.execute(select(Deal).where(and_(*filters)))).scalars().all()
    deal_ids = [d.id for d in deals]
    stage_ids = [d.stage_id for d in deals if d.stage_id]
    stages_map: Dict[str, PipelineStage] = {}
    if stage_ids:
        stages = (await db.execute(select(PipelineStage).where(PipelineStage.id.in_(stage_ids)))).scalars().all()
        stages_map = {s.id: s for s in stages}

    last_activity_map: Dict[str, Any] = {}
    if deal_ids:
        rows = (
            await db.execute(
                select(OutreachActivity.deal_id, func.max(OutreachActivity.created_at))
                .where(and_(OutreachActivity.tenant_id == tenant_id, OutreachActivity.deal_id.in_(deal_ids)))
                .group_by(OutreachActivity.deal_id)
            )
        ).all()
        last_activity_map = {deal_id: last_dt for deal_id, last_dt in rows}

    now_dt = now_utc()
    stage_probability_defaults = {
        "demo scheduled": 0.25,
        "demo completed": 0.40,
        "decision pending": 0.60,
        "verbal agreement": 0.85,
        "contract sent": 0.90,
        "closed won": 1.0,
        "closed lost": 0.0,
    }

    totals: Dict[str, Any] = {
        "deal_count": 0,
        "pipeline_value": 0.0,
        "weighted_value": 0.0,
        "overdue_next_steps": 0,
        "missing_next_steps": 0,
        "stale_no_activity": 0,
    }

    by_tier: Dict[str, Dict[str, Any]] = {
        t: {"deal_count": 0, "pipeline_value": 0.0, "weighted_value": 0.0, "probability": tier_probability(t)}
        for t in VALID_LEAD_TIERS
    }
    by_stage: Dict[str, Dict[str, Any]] = {}
    forecast_by_month: Dict[str, Dict[str, Any]] = {}

    for d in deals:
        amount = float(d.amount or 0.0)
        tier = (d.lead_tier or "").strip().upper()
        if tier not in VALID_LEAD_TIERS:
            tier = calculate_tier(int(d.lead_score or 0))

        stage = stages_map.get(d.stage_id) if d.stage_id else None
        stage_name = (stage.name or "").strip() if stage else "Unstaged"
        stage_name_l = stage_name.lower()
        prob = stage_probability_defaults.get(stage_name_l)
        if prob is None:
            prob = float((stage.probability or 0.0) / 100.0) if stage else 0.0
        prob = max(0.0, min(1.0, prob))
        weighted = amount * prob

        totals["deal_count"] += 1
        totals["pipeline_value"] += amount
        totals["weighted_value"] += weighted

        by_tier[tier]["deal_count"] += 1
        by_tier[tier]["pipeline_value"] += amount
        by_tier[tier]["weighted_value"] += weighted
        stage_bucket = by_stage.setdefault(stage_name, {"deal_count": 0, "pipeline_value": 0.0, "weighted_value": 0.0, "probability": prob})
        stage_bucket["deal_count"] += 1
        stage_bucket["pipeline_value"] += amount
        stage_bucket["weighted_value"] += weighted

        month_key = None
        if d.estimated_close_date:
            month_key = d.estimated_close_date.strftime("%Y-%m")
        elif d.next_step_at:
            month_key = d.next_step_at.strftime("%Y-%m")
        if month_key:
            m = forecast_by_month.setdefault(month_key, {"pipeline_value": 0.0, "weighted_value": 0.0, "deal_count": 0})
            m["pipeline_value"] += amount
            m["weighted_value"] += weighted
            m["deal_count"] += 1

        if (d.status or "open").lower() == "open":
            if not d.next_step_at:
                totals["missing_next_steps"] += 1
            elif d.next_step_at <= now_dt:
                totals["overdue_next_steps"] += 1

        baseline = last_activity_map.get(d.id) or d.updated_at or d.created_at
        if baseline:
            if (now_dt - baseline).days >= stale_days:
                totals["stale_no_activity"] += 1

    return {
        "filters": {
            "sales_motion_type": sales_motion_type,
            "partner_id": partner_id,
            "product_id": product_id,
            "client_name": client_name,
            "lead_tier": lead_tier,
            "owner_id": owner_id,
            "include_closed": include_closed,
            "stale_days": stale_days,
        },
        "totals": {
            **totals,
            "pipeline_value": round(float(totals["pipeline_value"]), 2),
            "weighted_value": round(float(totals["weighted_value"]), 2),
        },
        "by_tier": {
            t: {
                **by_tier[t],
                "pipeline_value": round(float(by_tier[t]["pipeline_value"]), 2),
                "weighted_value": round(float(by_tier[t]["weighted_value"]), 2),
            }
            for t in sorted(by_tier.keys())
        },
        "by_stage": {
            k: {
                **v,
                "pipeline_value": round(float(v["pipeline_value"]), 2),
                "weighted_value": round(float(v["weighted_value"]), 2),
                "probability": round(float(v["probability"]), 4),
            }
            for k, v in by_stage.items()
        },
        "forecast_by_month": {
            month: {
                **vals,
                "pipeline_value": round(float(vals["pipeline_value"]), 2),
                "weighted_value": round(float(vals["weighted_value"]), 2),
            }
            for month, vals in sorted(forecast_by_month.items())
        },
    }

