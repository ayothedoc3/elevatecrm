from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, normalize_lower, now_utc
from app.core.database import get_db
from app.pg_models.models import (
    Affiliate,
    AffiliateCommission,
    AffiliateEvent,
    AffiliateLink,
    AffiliateProgram,
)

router = APIRouter(prefix="/affiliates", tags=["Affiliates"])


def _require_admin(user: dict) -> None:
    if (user.get("role") or "").lower() not in {"admin", "manager", "owner", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")


class AffiliateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    payout_method: str = "manual"
    payout_details: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class AffiliateProgramCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    product_type: str = "service"
    journey_type: str = "demo_first"
    attribution_type: str = "deal"
    attribution_model: str = "first_touch"
    attribution_window_days: int = Field(default=30, ge=1, le=365)
    commission_type: str = "percentage"
    commission_value: float = Field(default=10, ge=0)
    min_payout_threshold: float = Field(default=50, ge=0)
    cookie_duration_days: int = Field(default=30, ge=1, le=365)
    pipeline_scope: Optional[str] = None
    qualifying_stage_id: Optional[str] = None
    auto_approve: bool = False
    is_active: bool = True


@router.get("")
async def list_affiliates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    where = [Affiliate.tenant_id == user["tenant_id"]]
    if status:
        where.append(Affiliate.status == status)
    if search:
        like = f"%{search.strip()}%"
        where.append(or_(Affiliate.name.ilike(like), Affiliate.email.ilike(like), Affiliate.company.ilike(like)))

    total_res = await db.execute(select(func.count(Affiliate.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(Affiliate).where(and_(*where)).order_by(Affiliate.created_at.desc()).offset(offset).limit(page_size)
    )
    affiliates = res.scalars().all()

    affiliate_ids = [a.id for a in affiliates]
    link_counts: Dict[str, int] = {aid: 0 for aid in affiliate_ids}
    click_sums: Dict[str, int] = {aid: 0 for aid in affiliate_ids}
    links_by_affiliate: Dict[str, List[dict]] = {aid: [] for aid in affiliate_ids}
    commission_stats: Dict[str, Dict[str, dict]] = {aid: {} for aid in affiliate_ids}
    recent_commissions: Dict[str, List[dict]] = {aid: [] for aid in affiliate_ids}

    if affiliate_ids:
        # Links
        links_res = await db.execute(
            select(AffiliateLink).where(and_(AffiliateLink.tenant_id == user["tenant_id"], AffiliateLink.affiliate_id.in_(affiliate_ids)))
        )
        for link in links_res.scalars().all():
            link_counts[link.affiliate_id] = link_counts.get(link.affiliate_id, 0) + 1
            click_sums[link.affiliate_id] = click_sums.get(link.affiliate_id, 0) + int(link.click_count or 0)
            links_by_affiliate.setdefault(link.affiliate_id, []).append(
                {
                    "id": link.id,
                    "referral_code": link.referral_code,
                    "click_count": int(link.click_count or 0),
                    "conversion_count": int(link.conversion_count or 0),
                    "program_id": link.program_id,
                    "landing_page_url": link.landing_page_url,
                    "is_active": bool(link.is_active),
                    "created_at": dt_to_iso(link.created_at),
                }
            )

        # Commission stats grouped by affiliate/status
        stats_res = await db.execute(
            select(
                AffiliateCommission.affiliate_id,
                AffiliateCommission.status,
                func.coalesce(func.sum(AffiliateCommission.amount), 0),
                func.count(AffiliateCommission.id),
            )
            .where(and_(AffiliateCommission.tenant_id == user["tenant_id"], AffiliateCommission.affiliate_id.in_(affiliate_ids)))
            .group_by(AffiliateCommission.affiliate_id, AffiliateCommission.status)
        )
        for affiliate_id, comm_status, total_amt, count_amt in stats_res.all():
            commission_stats.setdefault(str(affiliate_id), {})[str(comm_status)] = {
                "total": float(total_amt or 0),
                "count": int(count_amt or 0),
            }

        # Recent commissions
        comms_res = await db.execute(
            select(AffiliateCommission)
            .where(and_(AffiliateCommission.tenant_id == user["tenant_id"], AffiliateCommission.affiliate_id.in_(affiliate_ids)))
            .order_by(AffiliateCommission.created_at.desc())
            .limit(200)
        )
        for comm in comms_res.scalars().all():
            bucket = recent_commissions.setdefault(comm.affiliate_id, [])
            if len(bucket) >= 10:
                continue
            bucket.append(
                {
                    "id": comm.id,
                    "amount": float(comm.amount or 0),
                    "status": comm.status,
                    "earned_at": dt_to_iso(comm.created_at),
                }
            )

    def _affiliate_to_dict(a: Affiliate) -> dict:
        return {
            "id": a.id,
            "tenant_id": a.tenant_id,
            "name": a.name,
            "email": a.email,
            "phone": a.phone,
            "company": a.company,
            "website": a.website,
            "status": a.status,
            "payout_method": a.payout_method,
            "notes": a.notes,
            "total_earnings": float(a.total_earnings or 0),
            "total_paid": float(a.total_paid or 0),
            "created_at": dt_to_iso(a.created_at),
            "updated_at": dt_to_iso(a.updated_at),
            "link_count": int(link_counts.get(a.id, 0)),
            "total_clicks": int(click_sums.get(a.id, 0)),
            "commission_stats": commission_stats.get(a.id, {}),
            "links": links_by_affiliate.get(a.id, []),
            "recent_commissions": recent_commissions.get(a.id, []),
        }

    return {"affiliates": [_affiliate_to_dict(a) for a in affiliates], "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
async def create_affiliate(
    data: AffiliateCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    existing = await db.execute(
        select(Affiliate).where(and_(Affiliate.tenant_id == user["tenant_id"], Affiliate.email == data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Affiliate with this email already exists")

    now = now_utc()
    affiliate = Affiliate(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        email=str(data.email),
        phone=data.phone,
        company=data.company,
        website=data.website,
        status="pending",
        payout_method=data.payout_method or "manual",
        payout_details=data.payout_details or {},
        notes=data.notes,
        total_earnings=0.0,
        total_paid=0.0,
        created_at=now,
        updated_at=now,
    )
    db.add(affiliate)
    await db.flush()

    return {
        "id": affiliate.id,
        "tenant_id": affiliate.tenant_id,
        "name": affiliate.name,
        "email": affiliate.email,
        "phone": affiliate.phone,
        "company": affiliate.company,
        "website": affiliate.website,
        "status": affiliate.status,
        "payout_method": affiliate.payout_method,
        "notes": affiliate.notes,
        "total_earnings": float(affiliate.total_earnings or 0),
        "total_paid": float(affiliate.total_paid or 0),
        "created_at": dt_to_iso(affiliate.created_at),
        "updated_at": dt_to_iso(affiliate.updated_at),
    }


@router.post("/{affiliate_id}/approve")
async def approve_affiliate(
    affiliate_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    now = now_utc()
    res = await db.execute(
        update(Affiliate)
        .where(and_(Affiliate.id == affiliate_id, Affiliate.tenant_id == user["tenant_id"]))
        .values(status="active", updated_at=now)
    )
    if (res.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    return {"success": True}


# ==================== PROGRAMS ====================


@router.get("/programs")
async def list_programs(
    is_active: Optional[bool] = None,
    journey_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Used by landing pages + affiliate admin UI; keep open to any authenticated user.
    where = [AffiliateProgram.tenant_id == user["tenant_id"]]
    if is_active is not None:
        where.append(AffiliateProgram.is_active.is_(bool(is_active)))
    if journey_type:
        where.append(AffiliateProgram.journey_type == journey_type)

    res = await db.execute(select(AffiliateProgram).where(and_(*where)).order_by(AffiliateProgram.created_at.desc()))
    programs = res.scalars().all()

    program_ids = [p.id for p in programs]
    affiliate_counts: Dict[str, int] = {pid: 0 for pid in program_ids}
    if program_ids:
        counts_res = await db.execute(
            select(AffiliateLink.program_id, func.count(func.distinct(AffiliateLink.affiliate_id)))
            .where(AffiliateLink.program_id.in_(program_ids))
            .group_by(AffiliateLink.program_id)
        )
        for pid, cnt in counts_res.all():
            affiliate_counts[str(pid)] = int(cnt or 0)

    out = []
    for p in programs:
        out.append(
            {
                "id": p.id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "description": p.description,
                "product_type": p.product_type,
                "journey_type": p.journey_type,
                "attribution_type": p.attribution_type,
                "attribution_model": p.attribution_model,
                "attribution_window_days": int(p.attribution_window_days or 0),
                "commission_type": p.commission_type,
                "commission_value": float(p.commission_value or 0),
                "min_payout_threshold": float(p.min_payout_threshold or 0),
                "cookie_duration_days": int(p.cookie_duration_days or 0),
                "pipeline_scope": p.pipeline_scope,
                "qualifying_stage_id": p.qualifying_stage_id,
                "auto_approve": bool(p.auto_approve),
                "is_active": bool(p.is_active),
                "affiliate_count": affiliate_counts.get(p.id, 0),
                "created_at": dt_to_iso(p.created_at),
                "updated_at": dt_to_iso(p.updated_at),
            }
        )
    return {"programs": out}


@router.post("/programs", status_code=201)
async def create_program(
    data: AffiliateProgramCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    name_lower = normalize_lower(data.name)
    existing = await db.execute(
        select(AffiliateProgram).where(and_(AffiliateProgram.tenant_id == user["tenant_id"], AffiliateProgram.name_lower == name_lower))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Program with this name already exists")

    now = now_utc()
    program = AffiliateProgram(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        name_lower=name_lower,
        description=data.description,
        product_type=data.product_type,
        journey_type=data.journey_type,
        attribution_type=data.attribution_type,
        attribution_model=data.attribution_model,
        attribution_window_days=int(data.attribution_window_days),
        commission_type=data.commission_type,
        commission_value=float(data.commission_value),
        min_payout_threshold=float(data.min_payout_threshold),
        cookie_duration_days=int(data.cookie_duration_days),
        pipeline_scope=data.pipeline_scope,
        qualifying_stage_id=data.qualifying_stage_id,
        auto_approve=bool(data.auto_approve),
        is_active=bool(data.is_active),
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(program)
    await db.flush()
    return {"id": program.id, "success": True}


# ==================== COMMISSIONS ====================


@router.get("/commissions")
async def list_commissions(
    affiliate_id: Optional[str] = None,
    program_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    where = [AffiliateCommission.tenant_id == user["tenant_id"]]
    if affiliate_id:
        where.append(AffiliateCommission.affiliate_id == affiliate_id)
    if program_id:
        where.append(AffiliateCommission.program_id == program_id)
    if status:
        where.append(AffiliateCommission.status == status)

    total_res = await db.execute(select(func.count(AffiliateCommission.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    comms_res = await db.execute(
        select(AffiliateCommission)
        .where(and_(*where))
        .order_by(AffiliateCommission.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    commissions = comms_res.scalars().all()

    affiliate_ids = {c.affiliate_id for c in commissions}
    names_by_id: Dict[str, str] = {}
    if affiliate_ids:
        aff_res = await db.execute(select(Affiliate.id, Affiliate.name).where(Affiliate.id.in_(list(affiliate_ids))))
        for aid, nm in aff_res.all():
            names_by_id[str(aid)] = str(nm)

    totals_res = await db.execute(
        select(AffiliateCommission.status, func.coalesce(func.sum(AffiliateCommission.amount), 0), func.count(AffiliateCommission.id))
        .where(AffiliateCommission.tenant_id == user["tenant_id"])
        .group_by(AffiliateCommission.status)
    )
    totals = {s: {"total": float(t or 0), "count": int(c or 0)} for s, t, c in totals_res.all()}

    out = []
    for c in commissions:
        out.append(
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "affiliate_id": c.affiliate_id,
                "affiliate_name": names_by_id.get(c.affiliate_id, "Unknown"),
                "program_id": c.program_id,
                "deal_id": c.deal_id,
                "payment_id": c.payment_id,
                "amount": float(c.amount or 0),
                "currency": c.currency,
                "status": c.status,
                "notes": c.notes,
                "earned_at": dt_to_iso(c.created_at),
                "approved_at": dt_to_iso(c.approved_at),
                "paid_at": dt_to_iso(c.paid_at),
                "created_at": dt_to_iso(c.created_at),
                "updated_at": dt_to_iso(c.updated_at),
            }
        )

    return {"commissions": out, "total": total, "page": page, "page_size": page_size, "totals": totals}


@router.post("/commissions/{commission_id}/approve")
async def approve_commission(
    commission_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    now = now_utc()
    res = await db.execute(
        update(AffiliateCommission)
        .where(and_(AffiliateCommission.id == commission_id, AffiliateCommission.tenant_id == user["tenant_id"]))
        .values(status="approved", approved_at=now, approved_by=user["id"], updated_at=now)
    )
    if (res.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Commission not found")
    return {"success": True}


@router.post("/commissions/{commission_id}/pay")
async def pay_commission(
    commission_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    now = now_utc()
    res = await db.execute(
        update(AffiliateCommission)
        .where(and_(AffiliateCommission.id == commission_id, AffiliateCommission.tenant_id == user["tenant_id"]))
        .values(status="paid", paid_at=now, paid_by=user["id"], updated_at=now)
    )
    if (res.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Commission not found")
    return {"success": True}


# ==================== ANALYTICS ====================


@router.get("/analytics/dashboard")
async def get_affiliate_dashboard(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]
    start_date = now_utc() - timedelta(days=days)

    total_aff_res = await db.execute(select(func.count(Affiliate.id)).where(Affiliate.tenant_id == tenant_id))
    active_aff_res = await db.execute(
        select(func.count(Affiliate.id)).where(and_(Affiliate.tenant_id == tenant_id, Affiliate.status == "active"))
    )

    clicks_res = await db.execute(
        select(func.count(AffiliateEvent.id)).where(
            and_(
                AffiliateEvent.tenant_id == tenant_id,
                AffiliateEvent.event_type == "affiliate_link_clicked",
                AffiliateEvent.created_at >= start_date,
            )
        )
    )

    comm_stats_res = await db.execute(
        select(AffiliateCommission.status, func.coalesce(func.sum(AffiliateCommission.amount), 0), func.count(AffiliateCommission.id))
        .where(and_(AffiliateCommission.tenant_id == tenant_id, AffiliateCommission.created_at >= start_date))
        .group_by(AffiliateCommission.status)
    )
    commission_by_status = {s: {"total": float(t or 0), "count": int(c or 0)} for s, t, c in comm_stats_res.all()}

    total_commission_value = float(sum(v.get("total", 0) for v in commission_by_status.values()))

    return {
        "period_days": days,
        "affiliates": {"total": int(total_aff_res.scalar() or 0), "active": int(active_aff_res.scalar() or 0)},
        "clicks": int(clicks_res.scalar() or 0),
        "commissions": commission_by_status,
        "total_commission_value": total_commission_value,
        "top_affiliates": [],
        "program_stats": [],
    }

