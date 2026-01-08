"""
Elev8 CRM - KPI & Forecasting Routes

Provides forecasting calculations and KPI metrics.
Per Elev8 specification sections 6.4 and 10.

GOVERNANCE:
- All calculations are deterministic (CRM is source of truth)
- AI may analyze but never modify forecast values
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.db.mongodb import get_database
from app.api.elev8.auth import get_current_user
from app.api.elev8.scoring import get_tier_probability

router = APIRouter(tags=["KPIs & Forecasting"])


@router.get("/forecasting/summary")
async def get_forecasting_summary(
    period: str = Query("month", description="Forecast period: week, month, quarter"),
    user = Depends(get_current_user)
):
    """
    Get forecasting summary with weighted pipeline values.
    Uses tier-based probabilities as per PRD Section 6.4.
    """
    db = get_database()
    tenant_id = user["tenant_id"]
    
    # Get sales pipeline
    sales_pipeline = await db.pipelines.find_one(
        {"tenant_id": tenant_id, "pipeline_type": "sales"},
        {"_id": 0}
    )
    
    if not sales_pipeline:
        return {"error": "Sales pipeline not configured"}
    
    # Get all open deals
    deals = await db.deals.find(
        {"tenant_id": tenant_id, "pipeline_id": sales_pipeline["id"], "status": "open"},
        {"_id": 0}
    ).to_list(length=1000)
    
    # Calculate forecast by tier
    forecast_by_tier = {
        "A": {"count": 0, "total_value": 0, "weighted_value": 0, "probability": 0.70},
        "B": {"count": 0, "total_value": 0, "weighted_value": 0, "probability": 0.475},
        "C": {"count": 0, "total_value": 0, "weighted_value": 0, "probability": 0.225},
        "D": {"count": 0, "total_value": 0, "weighted_value": 0, "probability": 0.0}
    }
    
    total_pipeline = 0
    total_weighted = 0
    
    for deal in deals:
        tier = deal.get("tier", "D")
        amount = deal.get("amount", 0)
        probability = get_tier_probability(tier)
        weighted = amount * probability
        
        if tier in forecast_by_tier:
            forecast_by_tier[tier]["count"] += 1
            forecast_by_tier[tier]["total_value"] += amount
            forecast_by_tier[tier]["weighted_value"] += weighted
        
        total_pipeline += amount
        total_weighted += weighted
    
    # Calculate best/worst case
    best_case = sum(f["total_value"] for f in forecast_by_tier.values())
    worst_case = forecast_by_tier["A"]["total_value"] * 0.6  # Only high-confidence A deals
    
    # Get closed won this period
    now = datetime.now(timezone.utc)
    if period == "week":
        period_start = now - timedelta(days=7)
    elif period == "quarter":
        period_start = now - timedelta(days=90)
    else:  # month
        period_start = now - timedelta(days=30)
    
    closed_won = await db.deals.find({
        "tenant_id": tenant_id,
        "status": "won",
        "closed_at": {"$gte": period_start.isoformat()}
    }, {"_id": 0}).to_list(length=1000)
    
    closed_won_value = sum(d.get("amount", 0) for d in closed_won)
    closed_won_count = len(closed_won)
    
    # Get closed lost this period
    closed_lost = await db.deals.find({
        "tenant_id": tenant_id,
        "status": "lost",
        "closed_at": {"$gte": period_start.isoformat()}
    }, {"_id": 0}).to_list(length=1000)
    
    closed_lost_value = sum(d.get("amount", 0) for d in closed_lost)
    closed_lost_count = len(closed_lost)
    
    # Win rate
    total_closed = closed_won_count + closed_lost_count
    win_rate = (closed_won_count / max(total_closed, 1)) * 100
    
    return {
        "period": period,
        "pipeline_summary": {
            "total_deals": len(deals),
            "total_pipeline_value": total_pipeline,
            "weighted_forecast": total_weighted,
            "best_case": best_case,
            "worst_case": worst_case,
            "commit_forecast": forecast_by_tier["A"]["weighted_value"] + forecast_by_tier["B"]["weighted_value"]
        },
        "forecast_by_tier": forecast_by_tier,
        "closed_this_period": {
            "won": {"count": closed_won_count, "value": closed_won_value},
            "lost": {"count": closed_lost_count, "value": closed_lost_value},
            "win_rate": round(win_rate, 1)
        },
        "forecast_confidence": {
            "high": forecast_by_tier["A"]["weighted_value"],
            "medium": forecast_by_tier["B"]["weighted_value"],
            "low": forecast_by_tier["C"]["weighted_value"],
            "excluded": forecast_by_tier["D"]["total_value"]
        }
    }


@router.get("/kpis/overview")
async def get_kpis_overview(
    period: str = Query("month", description="KPI period: week, month, quarter"),
    user = Depends(get_current_user)
):
    """
    Get KPI overview metrics as per PRD Section 10.
    """
    db = get_database()
    tenant_id = user["tenant_id"]
    
    now = datetime.now(timezone.utc)
    if period == "week":
        period_start = now - timedelta(days=7)
    elif period == "quarter":
        period_start = now - timedelta(days=90)
    else:
        period_start = now - timedelta(days=30)
    
    # Activity KPIs
    leads_created = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": period_start.isoformat()}
    })
    
    leads_qualified = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "status": "qualified",
        "qualified_at": {"$gte": period_start.isoformat()}
    })
    
    # Pipeline KPIs
    deals_created = await db.deals.count_documents({
        "tenant_id": tenant_id,
        "created_at": {"$gte": period_start.isoformat()}
    })
    
    deals_won = await db.deals.count_documents({
        "tenant_id": tenant_id,
        "status": "won",
        "updated_at": {"$gte": period_start.isoformat()}
    })
    
    deals_lost = await db.deals.count_documents({
        "tenant_id": tenant_id,
        "status": "lost",
        "updated_at": {"$gte": period_start.isoformat()}
    })
    
    # Get won deal values
    won_deals = await db.deals.find({
        "tenant_id": tenant_id,
        "status": "won",
        "updated_at": {"$gte": period_start.isoformat()}
    }, {"_id": 0, "amount": 1}).to_list(length=1000)
    
    total_won_value = sum(d.get("amount", 0) for d in won_deals)
    avg_deal_size = total_won_value / max(deals_won, 1)
    
    # Conversion rates
    qualification_rate = (leads_qualified / max(leads_created, 1)) * 100
    win_rate = (deals_won / max(deals_won + deals_lost, 1)) * 100
    
    # Tier distribution of current pipeline
    tier_pipeline = await db.deals.aggregate([
        {"$match": {"tenant_id": tenant_id, "status": "open"}},
        {"$group": {"_id": "$tier", "count": {"$sum": 1}, "value": {"$sum": "$amount"}}}
    ]).to_list(length=10)
    
    tier_stats = {item["_id"]: {"count": item["count"], "value": item["value"]} for item in tier_pipeline}
    
    # SPICED completion rate
    total_open_deals = await db.deals.count_documents({"tenant_id": tenant_id, "status": "open"})
    spiced_complete = await db.deals.count_documents({
        "tenant_id": tenant_id,
        "status": "open",
        "spiced_situation": {"$exists": True, "$ne": None, "$ne": ""},
        "spiced_pain": {"$exists": True, "$ne": None, "$ne": ""}
    })
    spiced_rate = (spiced_complete / max(total_open_deals, 1)) * 100
    
    return {
        "period": period,
        "activity_kpis": {
            "leads_created": leads_created,
            "leads_qualified": leads_qualified,
            "qualification_rate": round(qualification_rate, 1),
            "deals_created": deals_created
        },
        "pipeline_kpis": {
            "deals_won": deals_won,
            "deals_lost": deals_lost,
            "win_rate": round(win_rate, 1),
            "total_won_value": total_won_value,
            "avg_deal_size": round(avg_deal_size, 2)
        },
        "quality_kpis": {
            "spiced_completion_rate": round(spiced_rate, 1),
            "tier_distribution": tier_stats
        },
        "targets": {
            "leads_target": 50,
            "qualification_target": 30,
            "win_rate_target": 25,
            "spiced_target": 80
        }
    }


@router.get("/kpis/sales-motion")
async def get_kpis_by_sales_motion(
    period: str = Query("month", description="KPI period"),
    user = Depends(get_current_user)
):
    """
    Get KPIs segmented by sales motion type.
    """
    db = get_database()
    tenant_id = user["tenant_id"]
    
    now = datetime.now(timezone.utc)
    if period == "week":
        period_start = now - timedelta(days=7)
    elif period == "quarter":
        period_start = now - timedelta(days=90)
    else:
        period_start = now - timedelta(days=30)
    
    # Partnership Sales metrics
    partnership_leads = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "sales_motion_type": "partnership_sales",
        "created_at": {"$gte": period_start.isoformat()}
    })
    
    partnership_deals = await db.deals.find({
        "tenant_id": tenant_id,
        "sales_motion_type": "partnership_sales",
        "status": "open"
    }, {"_id": 0, "amount": 1, "tier": 1}).to_list(length=1000)
    
    partnership_pipeline = sum(d.get("amount", 0) for d in partnership_deals)
    partnership_weighted = sum(
        d.get("amount", 0) * get_tier_probability(d.get("tier", "D"))
        for d in partnership_deals
    )
    
    # Partner Sales metrics
    partner_leads = await db.leads.count_documents({
        "tenant_id": tenant_id,
        "sales_motion_type": "partner_sales",
        "created_at": {"$gte": period_start.isoformat()}
    })
    
    partner_deals = await db.deals.find({
        "tenant_id": tenant_id,
        "sales_motion_type": "partner_sales",
        "status": "open"
    }, {"_id": 0, "amount": 1, "tier": 1}).to_list(length=1000)
    
    partner_pipeline = sum(d.get("amount", 0) for d in partner_deals)
    partner_weighted = sum(
        d.get("amount", 0) * get_tier_probability(d.get("tier", "D"))
        for d in partner_deals
    )
    
    return {
        "period": period,
        "partnership_sales": {
            "leads_created": partnership_leads,
            "deals_count": len(partnership_deals),
            "pipeline_value": partnership_pipeline,
            "weighted_forecast": partnership_weighted
        },
        "partner_sales": {
            "leads_created": partner_leads,
            "deals_count": len(partner_deals),
            "pipeline_value": partner_pipeline,
            "weighted_forecast": partner_weighted
        }
    }


@router.get("/kpis/leaderboard")
async def get_sales_leaderboard(
    period: str = Query("month", description="Period for leaderboard"),
    user = Depends(get_current_user)
):
    """
    Get sales leaderboard by owner.
    """
    db = get_database()
    tenant_id = user["tenant_id"]
    
    now = datetime.now(timezone.utc)
    if period == "week":
        period_start = now - timedelta(days=7)
    elif period == "quarter":
        period_start = now - timedelta(days=90)
    else:
        period_start = now - timedelta(days=30)
    
    # Aggregate deals by owner
    pipeline_agg = await db.deals.aggregate([
        {
            "$match": {
                "tenant_id": tenant_id,
                "status": {"$in": ["open", "won"]},
                "owner_id": {"$exists": True, "$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$owner_id",
                "total_deals": {"$sum": 1},
                "open_deals": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
                "won_deals": {"$sum": {"$cond": [{"$eq": ["$status", "won"]}, 1, 0]}},
                "pipeline_value": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, "$amount", 0]}},
                "won_value": {"$sum": {"$cond": [{"$eq": ["$status", "won"]}, "$amount", 0]}}
            }
        },
        {"$sort": {"won_value": -1}}
    ]).to_list(length=20)
    
    # Enrich with user names
    leaderboard = []
    for item in pipeline_agg:
        user_doc = await db.users.find_one({"id": item["_id"]}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
        if user_doc:
            leaderboard.append({
                "user_id": item["_id"],
                "name": f"{user_doc.get('first_name', '')} {user_doc.get('last_name', '')}".strip() or user_doc.get("email"),
                "total_deals": item["total_deals"],
                "open_deals": item["open_deals"],
                "won_deals": item["won_deals"],
                "pipeline_value": item["pipeline_value"],
                "won_value": item["won_value"]
            })
    
    return {
        "period": period,
        "leaderboard": leaderboard
    }
