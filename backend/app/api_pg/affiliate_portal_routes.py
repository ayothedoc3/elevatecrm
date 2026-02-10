from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_password_hash, verify_password
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Affiliate, AffiliateCommission, AffiliateEvent, AffiliateLink, AffiliateProgram, MarketingMaterial, Tenant
from app.services.storage_service import get_storage

router = APIRouter(prefix="/affiliate-portal", tags=["Affiliate Portal"])

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.environ.get("SECRET_KEY", "elevate-crm-secret-key-change-in-production")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
AFFILIATE_TOKEN_EXPIRE_HOURS = 24


class AffiliateLogin(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str = "demo"


class AffiliateRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    company: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    tenant_slug: str = "demo"


class AffiliateProfileUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None


class AffiliateLinkGenerate(BaseModel):
    program_id: str
    landing_page_url: Optional[str] = None
    custom_slug: Optional[str] = None


def _create_affiliate_token(affiliate_id: str, tenant_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=AFFILIATE_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": affiliate_id, "tenant_id": tenant_id, "type": "affiliate", "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _generate_referral_code(affiliate_id: str, length: int = 8) -> str:
    hash_input = f"{affiliate_id}{secrets.token_hex(4)}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:length].upper()


async def get_current_affiliate(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Affiliate:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        affiliate_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        token_type = payload.get("type")
        if not affiliate_id or token_type != "affiliate" or not tenant_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    res = await db.execute(select(Affiliate).where(and_(Affiliate.id == affiliate_id, Affiliate.tenant_id == tenant_id)))
    affiliate = res.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(status_code=401, detail="Affiliate not found")
    if affiliate.status != "active":
        raise HTTPException(status_code=403, detail="Account not active")
    return affiliate


@router.post("/register", status_code=201)
async def register_affiliate(
    data: AffiliateRegister,
    db: AsyncSession = Depends(get_db),
):
    tenant_res = await db.execute(select(Tenant).where(Tenant.slug == data.tenant_slug))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Invalid tenant")

    existing = await db.execute(select(Affiliate).where(and_(Affiliate.tenant_id == tenant.id, Affiliate.email == str(data.email))))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    now = now_utc()
    affiliate = Affiliate(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        name=data.name,
        email=str(data.email),
        password_hash=get_password_hash(data.password),
        phone=data.phone,
        company=data.company,
        website=data.website,
        status="pending",
        payout_method="manual",
        payout_details={},
        notes=None,
        total_earnings=0.0,
        total_paid=0.0,
        created_at=now,
        updated_at=now,
    )
    db.add(affiliate)
    await db.flush()

    return {
        "success": True,
        "message": "Registration successful! Your account is pending approval. You'll receive an email once approved.",
    }


@router.post("/login")
async def login_affiliate(
    data: AffiliateLogin,
    db: AsyncSession = Depends(get_db),
):
    tenant_res = await db.execute(select(Tenant).where(Tenant.slug == data.tenant_slug))
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    res = await db.execute(select(Affiliate).where(and_(Affiliate.tenant_id == tenant.id, Affiliate.email == str(data.email))))
    affiliate = res.scalar_one_or_none()
    if not affiliate or not affiliate.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, affiliate.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if affiliate.status == "pending":
        raise HTTPException(status_code=403, detail="Your account is pending approval")
    if affiliate.status == "banned":
        raise HTTPException(status_code=403, detail="Your account has been suspended")
    if affiliate.status == "paused":
        raise HTTPException(status_code=403, detail="Your account is paused")

    token = _create_affiliate_token(affiliate.id, tenant.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "affiliate": {"id": affiliate.id, "name": affiliate.name, "email": affiliate.email, "company": affiliate.company, "status": affiliate.status},
    }


@router.get("/me")
async def get_affiliate_profile(affiliate: Affiliate = Depends(get_current_affiliate)):
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


@router.put("/me")
async def update_affiliate_profile(
    data: AffiliateProfileUpdate,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        update_data["updated_at"] = now_utc()
        await db.execute(update(Affiliate).where(Affiliate.id == affiliate.id).values(**update_data))
    return {"success": True}


@router.get("/dashboard")
async def get_affiliate_dashboard(
    days: int = Query(30, ge=1, le=365),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    start_date = now_utc() - timedelta(days=days)

    links_res = await db.execute(
        select(AffiliateLink).where(and_(AffiliateLink.affiliate_id == affiliate.id, AffiliateLink.is_active.is_(True)))
    )
    links = links_res.scalars().all()

    total_clicks = sum(int(l.click_count or 0) for l in links)
    total_conversions = sum(int(l.conversion_count or 0) for l in links)

    comm_res = await db.execute(
        select(AffiliateCommission.status, func.coalesce(func.sum(AffiliateCommission.amount), 0), func.count(AffiliateCommission.id))
        .where(AffiliateCommission.affiliate_id == affiliate.id)
        .group_by(AffiliateCommission.status)
    )
    commissions_by_status = {s: {"total": float(t or 0), "count": int(c or 0)} for s, t, c in comm_res.all()}

    # Click history
    events_res = await db.execute(
        select(func.date_trunc("day", AffiliateEvent.created_at), func.count(AffiliateEvent.id))
        .where(
            and_(
                AffiliateEvent.affiliate_id == affiliate.id,
                AffiliateEvent.event_type == "affiliate_link_clicked",
                AffiliateEvent.created_at >= start_date,
            )
        )
        .group_by(func.date_trunc("day", AffiliateEvent.created_at))
        .order_by(func.date_trunc("day", AffiliateEvent.created_at))
        .limit(30)
    )
    click_history = [{"date": d.date().isoformat(), "clicks": int(c or 0)} for d, c in events_res.all()]

    program_ids = list({l.program_id for l in links if l.program_id})
    programs = []
    if program_ids:
        prog_res = await db.execute(
            select(AffiliateProgram).where(and_(AffiliateProgram.id.in_(program_ids), AffiliateProgram.is_active.is_(True)))
        )
        for p in prog_res.scalars().all():
            programs.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "commission_type": p.commission_type,
                    "commission_value": float(p.commission_value or 0),
                    "journey_type": p.journey_type,
                }
            )

    return {
        "affiliate": {
            "id": affiliate.id,
            "name": affiliate.name,
            "email": affiliate.email,
            "total_earnings": float(affiliate.total_earnings or 0),
            "total_paid": float(affiliate.total_paid or 0),
        },
        "stats": {
            "total_links": len(links),
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "conversion_rate": round((total_conversions / total_clicks * 100), 2) if total_clicks > 0 else 0,
        },
        "commissions": commissions_by_status,
        "pending_payout": commissions_by_status.get("approved", {}).get("total", 0),
        "click_history": click_history,
        "programs": programs,
        "period_days": days,
    }


@router.get("/links")
async def get_affiliate_links(
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(AffiliateLink).where(AffiliateLink.affiliate_id == affiliate.id).order_by(AffiliateLink.created_at.desc()))
    links = res.scalars().all()

    program_ids = list({l.program_id for l in links if l.program_id})
    programs_by_id = {}
    if program_ids:
        prog_res = await db.execute(
            select(AffiliateProgram).where(and_(AffiliateProgram.id.in_(program_ids), AffiliateProgram.tenant_id == affiliate.tenant_id))
        )
        for p in prog_res.scalars().all():
            programs_by_id[p.id] = p

    out = []
    for link in links:
        program = programs_by_id.get(link.program_id) if link.program_id else None
        base_url = link.landing_page_url or f"/ref/{link.referral_code}"
        out.append(
            {
                "id": link.id,
                "tenant_id": link.tenant_id,
                "affiliate_id": link.affiliate_id,
                "program_id": link.program_id,
                "referral_code": link.referral_code,
                "landing_page_url": link.landing_page_url,
                "utm_source": link.utm_source,
                "utm_medium": link.utm_medium,
                "utm_campaign": link.utm_campaign,
                "click_count": int(link.click_count or 0),
                "conversion_count": int(link.conversion_count or 0),
                "is_active": bool(link.is_active),
                "created_at": dt_to_iso(link.created_at),
                "program": {
                    "name": program.name,
                    "commission_type": program.commission_type,
                    "commission_value": float(program.commission_value or 0),
                }
                if program
                else None,
                "full_url": f"{base_url}?ref={link.referral_code}",
            }
        )
    return {"links": out}


@router.post("/links", status_code=201)
async def generate_affiliate_link(
    data: AffiliateLinkGenerate,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    program_res = await db.execute(
        select(AffiliateProgram).where(
            and_(AffiliateProgram.id == data.program_id, AffiliateProgram.tenant_id == affiliate.tenant_id, AffiliateProgram.is_active.is_(True))
        )
    )
    program = program_res.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found or inactive")

    referral_code = data.custom_slug or _generate_referral_code(affiliate.id)
    existing = await db.execute(select(AffiliateLink.id).where(AffiliateLink.referral_code == referral_code))
    if existing.scalar_one_or_none():
        if data.custom_slug:
            raise HTTPException(status_code=400, detail="This slug is already taken")
        referral_code = _generate_referral_code(affiliate.id, 10)

    now = now_utc()
    link = AffiliateLink(
        id=str(uuid.uuid4()),
        tenant_id=affiliate.tenant_id,
        affiliate_id=affiliate.id,
        program_id=data.program_id,
        referral_code=referral_code,
        landing_page_url=data.landing_page_url,
        utm_source="affiliate",
        utm_medium="referral",
        utm_campaign=(program.name or "").lower().replace(" ", "_"),
        click_count=0,
        conversion_count=0,
        is_active=True,
        created_at=now,
    )
    db.add(link)
    await db.flush()

    base_url = data.landing_page_url or f"/ref/{referral_code}"
    return {
        "id": link.id,
        "tenant_id": link.tenant_id,
        "affiliate_id": link.affiliate_id,
        "program_id": link.program_id,
        "referral_code": link.referral_code,
        "landing_page_url": link.landing_page_url,
        "utm_source": link.utm_source,
        "utm_medium": link.utm_medium,
        "utm_campaign": link.utm_campaign,
        "click_count": 0,
        "conversion_count": 0,
        "is_active": True,
        "created_at": dt_to_iso(link.created_at),
        "full_url": f"{base_url}?ref={referral_code}",
        "program": {"name": program.name, "commission_type": program.commission_type, "commission_value": float(program.commission_value or 0)},
    }


@router.get("/programs")
async def get_available_programs(
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(AffiliateProgram)
        .where(and_(AffiliateProgram.tenant_id == affiliate.tenant_id, AffiliateProgram.is_active.is_(True)))
        .order_by(AffiliateProgram.created_at.desc())
        .limit(50)
    )
    programs = res.scalars().all()

    # Whether affiliate already has a link for each program
    program_ids = [p.id for p in programs]
    has_link = set()
    if program_ids:
        links_res = await db.execute(
            select(AffiliateLink.program_id)
            .where(and_(AffiliateLink.affiliate_id == affiliate.id, AffiliateLink.program_id.in_(program_ids)))
            .distinct()
        )
        has_link = {pid for (pid,) in links_res.all()}

    return {
        "programs": [
            {
                "id": p.id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "description": p.description,
                "journey_type": p.journey_type,
                "commission_type": p.commission_type,
                "commission_value": float(p.commission_value or 0),
                "is_active": bool(p.is_active),
                "has_link": p.id in has_link,
            }
            for p in programs
        ]
    }


@router.get("/commissions")
async def get_affiliate_commissions(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    where = [AffiliateCommission.affiliate_id == affiliate.id]
    if status:
        where.append(AffiliateCommission.status == status)

    total_res = await db.execute(select(func.count(AffiliateCommission.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)
    offset = (page - 1) * page_size

    res = await db.execute(
        select(AffiliateCommission)
        .where(and_(*where))
        .order_by(AffiliateCommission.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    commissions = res.scalars().all()

    return {
        "commissions": [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "affiliate_id": c.affiliate_id,
                "program_id": c.program_id,
                "deal_id": c.deal_id,
                "payment_id": c.payment_id,
                "amount": float(c.amount or 0),
                "currency": c.currency,
                "status": c.status,
                "earned_at": dt_to_iso(c.created_at),
                "approved_at": dt_to_iso(c.approved_at),
                "paid_at": dt_to_iso(c.paid_at),
            }
            for c in commissions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/materials")
async def get_portal_materials(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: AsyncSession = Depends(get_db),
):
    where = [MarketingMaterial.tenant_id == affiliate.tenant_id, MarketingMaterial.is_active.is_(True)]
    total_res = await db.execute(select(func.count(MarketingMaterial.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)
    offset = (page - 1) * page_size

    res = await db.execute(
        select(MarketingMaterial)
        .where(and_(*where))
        .order_by(MarketingMaterial.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    materials = res.scalars().all()

    storage = get_storage()
    out = []
    for m in materials:
        file_url = await storage.get_url(m.file_path) if m.file_path else m.url
        out.append(
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "category": m.category,
                "material_type": m.material_type,
                "file_url": file_url,
                "file_name": m.file_name,
                "file_size": int(m.file_size or 0),
                "tags": list(m.tags or []),
                "created_at": dt_to_iso(m.created_at),
            }
        )

    return {"materials": out, "total": total, "page": page, "page_size": page_size}

