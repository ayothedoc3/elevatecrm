from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import (
    create_timeline_event,
    get_default_pipeline_and_stage,
    resolve_account,
    resolve_partner_and_product,
    upsert_open_next_step_task_for_deal,
)
from app.api_pg.utils import (
    MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE,
    VALID_LEAD_TIERS,
    calculate_tier,
    compute_universal_score,
    dt_to_iso,
    is_non_empty,
    now_utc,
    parse_iso_datetime,
    scoring_inputs_complete,
)
from app.core.database import get_db
from app.pg_models.models import Contact, Deal, Lead, PipelineStage, User

router = APIRouter(prefix="/leads", tags=["Leads"])


class LeadCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    source: Optional[str] = None
    score: int = Field(default=0, ge=0, le=100)
    tier: Optional[str] = None
    sales_motion_type: str = "partnership_sales"
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    source: Optional[str] = None
    score: Optional[int] = Field(default=None, ge=0, le=100)
    tier: Optional[str] = None
    sales_motion_type: Optional[str] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    owner_id: Optional[str] = None
    tags: Optional[List[str]] = None


class LeadAssignRequest(BaseModel):
    owner_id: str


class LeadScoreRequest(BaseModel):
    score: Optional[int] = Field(default=None, ge=0, le=100)
    scoring_data: Optional[Dict[str, Any]] = None


class LeadPushToSalesRequest(BaseModel):
    deal_name: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    next_step_at: str = Field(..., min_length=1)
    next_step_note: Optional[str] = None
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None


class LeadTouchpointRequest(BaseModel):
    activity_type: str = "call"
    notes: Optional[str] = None
    got_response: bool = False


def _lead_to_dict(lead: Lead, owner_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": lead.id,
        "tenant_id": lead.tenant_id,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "full_name": (lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}").strip(),
        "email": lead.email,
        "phone": lead.phone,
        "company_name": lead.company_name,
        "source": lead.source,
        "score": int(lead.score or 0),
        "tier": (lead.tier or "D").strip().upper(),
        "sales_motion_type": lead.sales_motion_type,
        "partner_id": lead.partner_id,
        "product_id": lead.product_id,
        "partner_name": lead.partner_name,
        "product_name": lead.product_name,
        "status": lead.status,
        "notes": lead.notes,
        "tags": lead.tags or [],
        "owner_id": lead.owner_id,
        "owner_name": owner_name,
        "assigned_at": dt_to_iso(lead.assigned_at),
        "converted_at": dt_to_iso(lead.converted_at),
        "contact_id": lead.contact_id,
        "touchpoints_count": int(lead.touchpoints_count or 0),
        "last_touchpoint_at": dt_to_iso(lead.last_touchpoint_at),
        "scoring_data": lead.scoring_data or {},
        "created_at": dt_to_iso(lead.created_at),
        "updated_at": dt_to_iso(lead.updated_at),
    }


@router.get("")
async def get_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    tier: Optional[str] = None,
    source: Optional[str] = None,
    owner_id: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    filters = [Lead.tenant_id == tenant_id]
    if status:
        filters.append(Lead.status == status)
    if tier:
        filters.append(Lead.tier == tier)
    if source:
        filters.append(Lead.source == source)
    if owner_id:
        filters.append(Lead.owner_id == owner_id)
    if min_score is not None:
        filters.append(Lead.score >= min_score)
    if max_score is not None:
        filters.append(Lead.score <= max_score)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Lead.first_name.ilike(pattern),
                Lead.last_name.ilike(pattern),
                Lead.email.ilike(pattern),
                Lead.company_name.ilike(pattern),
            )
        )

    total_res = await db.execute(select(func.count()).select_from(Lead).where(and_(*filters)))
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Lead, User)
        .outerjoin(User, and_(Lead.owner_id == User.id, User.tenant_id == tenant_id))
        .where(and_(*filters))
        .order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()

    leads: List[Dict[str, Any]] = []
    for lead, owner in rows:
        owner_name = None
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip()
        leads.append(_lead_to_dict(lead, owner_name=owner_name))

    return {"leads": leads, "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
async def create_lead(
    data: LeadCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    now = now_utc()

    tier = (data.tier or calculate_tier(int(data.score or 0))).strip().upper()
    if tier not in VALID_LEAD_TIERS:
        tier = calculate_tier(int(data.score or 0))

    resolved = await resolve_partner_and_product(
        db=db,
        tenant_id=tenant_id,
        sales_motion_type=data.sales_motion_type,
        partner_id=data.partner_id,
        product_id=data.product_id,
        partner_name=data.partner_name,
        product_name=data.product_name,
        actor_id=user["id"],
    )

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name=data.first_name,
        last_name=data.last_name,
        full_name=f"{data.first_name} {data.last_name}".strip(),
        email=data.email,
        phone=data.phone,
        company_name=data.company_name,
        source=data.source or "manual",
        score=int(data.score or 0),
        tier=tier,
        sales_motion_type=(data.sales_motion_type or "partnership_sales").strip(),
        partner_id=resolved.get("partner_id"),
        product_id=resolved.get("product_id"),
        partner_name=resolved.get("partner_name"),
        product_name=resolved.get("product_name"),
        status="new",
        notes=data.notes,
        tags=list(data.tags or []),
        owner_id=None,
        assigned_at=None,
        converted_at=None,
        contact_id=None,
        touchpoints_count=0,
        last_touchpoint_at=None,
        scoring_data={},
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    await db.flush()

    return _lead_to_dict(lead, owner_name=None)


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == user["tenant_id"])))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    owner_name = None
    if lead.owner_id:
        owner_res = await db.execute(
            select(User).where(and_(User.id == lead.owner_id, User.tenant_id == user["tenant_id"]))
        )
        owner = owner_res.scalar_one_or_none()
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip()

    return _lead_to_dict(lead, owner_name=owner_name)


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    data: LeadUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == user["tenant_id"])))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.status in {"disqualified", "converted"}:
        raise HTTPException(status_code=400, detail="Cannot assign a disqualified or converted lead")

    now = now_utc()

    if data.first_name is not None:
        lead.first_name = data.first_name
    if data.last_name is not None:
        lead.last_name = data.last_name
    if data.email is not None:
        lead.email = data.email
    if data.phone is not None:
        lead.phone = data.phone
    if data.company_name is not None:
        lead.company_name = data.company_name
    if data.source is not None:
        lead.source = data.source
    if data.score is not None:
        lead.score = int(data.score or 0)
        lead.tier = (data.tier or calculate_tier(int(data.score or 0))).strip().upper()
    if data.tier is not None:
        lead.tier = data.tier

    if data.status is not None:
        allowed = {
            "new",
            "assigned",
            "working",
            "info_collected",
            "unresponsive",
            "disqualified",
            "qualified",
            "converted",
        }
        if data.status not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(sorted(allowed))}")

        if data.status in {"info_collected", "qualified"}:
            if not scoring_inputs_complete(lead.scoring_data or {}):
                raise HTTPException(
                    status_code=400,
                    detail="Scoring inputs must be completed before moving to Info Collected or Qualified",
                )

        if data.status == "unresponsive":
            if int(lead.touchpoints_count or 0) < MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE:
                raise HTTPException(
                    status_code=400,
                    detail=f"At least {MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE} touchpoints are required before marking Unresponsive",
                )

        lead.status = data.status

    if data.notes is not None:
        lead.notes = data.notes

    if data.owner_id is not None:
        lead.owner_id = data.owner_id
        if not lead.assigned_at:
            lead.assigned_at = now

    if data.tags is not None:
        lead.tags = list(data.tags or [])

    motion_update_requested = any(
        [
            data.sales_motion_type is not None,
            data.partner_id is not None,
            data.product_id is not None,
            data.partner_name is not None,
            data.product_name is not None,
        ]
    )
    if motion_update_requested:
        resolved = await resolve_partner_and_product(
            db=db,
            tenant_id=user["tenant_id"],
            sales_motion_type=data.sales_motion_type or lead.sales_motion_type,
            partner_id=data.partner_id if data.partner_id is not None else lead.partner_id,
            product_id=data.product_id if data.product_id is not None else lead.product_id,
            partner_name=data.partner_name if data.partner_name is not None else lead.partner_name,
            product_name=data.product_name if data.product_name is not None else lead.product_name,
            actor_id=user["id"],
        )
        lead.sales_motion_type = (data.sales_motion_type or lead.sales_motion_type or "partnership_sales").strip()
        lead.partner_id = resolved.get("partner_id")
        lead.product_id = resolved.get("product_id")
        lead.partner_name = resolved.get("partner_name")
        lead.product_name = resolved.get("product_name")

    lead.full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
    lead.updated_at = now
    await db.flush()

    owner_name = None
    if lead.owner_id:
        owner_res = await db.execute(select(User).where(and_(User.id == lead.owner_id, User.tenant_id == user["tenant_id"])))
        owner = owner_res.scalar_one_or_none()
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip()

    return _lead_to_dict(lead, owner_name=owner_name)


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == user["tenant_id"])))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    return None


@router.post("/{lead_id}/assign")
async def assign_lead(
    lead_id: str,
    data: LeadAssignRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    owner_res = await db.execute(select(User).where(and_(User.id == data.owner_id, User.tenant_id == tenant_id)))
    owner = owner_res.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=400, detail="Assigned user not found")

    now = now_utc()
    lead.owner_id = data.owner_id
    lead.assigned_at = now
    lead.status = "working"
    lead.updated_at = now
    await db.flush()

    return _lead_to_dict(lead, owner_name=f"{owner.first_name} {owner.last_name}".strip())


@router.post("/{lead_id}/touchpoint")
async def log_lead_touchpoint(
    lead_id: str,
    data: LeadTouchpointRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.status in {"disqualified", "converted"}:
        raise HTTPException(status_code=400, detail="Cannot log touchpoints for a disqualified or converted lead")

    now = now_utc()
    lead.touchpoints_count = int(lead.touchpoints_count or 0) + 1
    lead.last_touchpoint_at = now
    lead.updated_at = now

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="lead_touchpoint",
        title=f"Lead touchpoint: {data.activity_type}",
        description=data.notes,
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        metadata={
            "lead_id": lead_id,
            "activity_type": data.activity_type,
            "got_response": bool(data.got_response),
        },
    )

    await db.flush()

    owner_name = None
    if lead.owner_id:
        owner_res = await db.execute(select(User).where(and_(User.id == lead.owner_id, User.tenant_id == tenant_id)))
        owner = owner_res.scalar_one_or_none()
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip()

    return _lead_to_dict(lead, owner_name=owner_name)


@router.post("/{lead_id}/score")
async def score_lead(
    lead_id: str,
    data: LeadScoreRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    scoring_data = data.scoring_data if data.scoring_data is not None else (lead.scoring_data or {})

    if data.scoring_data is not None:
        score = compute_universal_score(scoring_data, lead.source or "manual")
    elif data.score is not None:
        score = int(data.score or 0)
    else:
        raise HTTPException(status_code=400, detail="Provide scoring_data to compute score or score to set manually")

    tier = calculate_tier(score)
    lead.score = score
    lead.tier = tier
    if data.scoring_data is not None:
        lead.scoring_data = scoring_data
    lead.updated_at = now_utc()

    await db.flush()

    owner_name = None
    if lead.owner_id:
        owner_res = await db.execute(select(User).where(and_(User.id == lead.owner_id, User.tenant_id == tenant_id)))
        owner = owner_res.scalar_one_or_none()
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip()

    return _lead_to_dict(lead, owner_name=owner_name)


@router.post("/{lead_id}/convert")
async def convert_lead_to_contact(
    lead_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.converted_at:
        raise HTTPException(status_code=400, detail="Lead already converted")

    now = now_utc()

    company_name = lead.company_name
    account_name_input = company_name or (lead.full_name or "").strip()
    resolved_account = None
    if account_name_input:
        resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])

    contact_id = str(uuid.uuid4())
    contact = Contact(
        id=contact_id,
        tenant_id=tenant_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        full_name=(lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}").strip(),
        email=lead.email,
        phone=lead.phone,
        company_name=company_name,
        account_id=(resolved_account or {}).get("account_id"),
        account_name=(resolved_account or {}).get("account_name"),
        source=lead.source,
        lifecycle_stage="lead",
        lead_score=int(lead.score or 0),
        lead_tier=(lead.tier or "D").strip().upper(),
        owner_id=lead.owner_id,
        tags=list(lead.tags or []),
        status="active",
        converted_from_lead_id=lead_id,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(contact)

    lead.status = "converted"
    lead.converted_at = now
    lead.contact_id = contact_id
    lead.updated_at = now

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="contact_created",
        title=f"Contact created: {contact.full_name}",
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        contact_id=contact_id,
        metadata={"converted_from_lead_id": lead_id},
    )

    await db.flush()

    contact_dict = {
        "id": contact.id,
        "tenant_id": contact.tenant_id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "full_name": contact.full_name,
        "email": contact.email,
        "phone": contact.phone,
        "company_name": contact.company_name,
        "company": contact.company_name,
        "account_id": contact.account_id,
        "account_name": contact.account_name,
        "source": contact.source,
        "lifecycle_stage": contact.lifecycle_stage,
        "lead_score": contact.lead_score,
        "lead_tier": contact.lead_tier,
        "owner_id": contact.owner_id,
        "tags": contact.tags or [],
        "status": contact.status,
        "converted_from_lead_id": contact.converted_from_lead_id,
        "created_by": contact.created_by,
        "created_at": dt_to_iso(contact.created_at),
        "updated_at": dt_to_iso(contact.updated_at),
    }

    return {"lead_id": lead_id, "contact_id": contact_id, "contact": contact_dict, "message": "Lead successfully converted to contact"}


@router.post("/{lead_id}/push-to-sales")
async def push_lead_to_sales(
    lead_id: str,
    data: LeadPushToSalesRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.status != "qualified":
        raise HTTPException(status_code=400, detail="Lead must be Qualified before pushing to Sales Pipeline")

    if not scoring_inputs_complete(lead.scoring_data or {}):
        raise HTTPException(status_code=400, detail="Scoring inputs must be completed before pushing to Sales Pipeline")

    now = now_utc()

    # Contact
    contact: Optional[Contact] = None
    if lead.contact_id:
        contact_res = await db.execute(
            select(Contact).where(and_(Contact.id == lead.contact_id, Contact.tenant_id == tenant_id))
        )
        contact = contact_res.scalar_one_or_none()

    if not contact:
        company_name = lead.company_name
        account_name_input = company_name or (lead.full_name or "").strip()
        resolved_account = None
        if account_name_input:
            resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])

        contact = Contact(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            full_name=(lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}").strip(),
            email=lead.email,
            phone=lead.phone,
            company_name=company_name,
            account_id=(resolved_account or {}).get("account_id"),
            account_name=(resolved_account or {}).get("account_name"),
            source=lead.source,
            lifecycle_stage="lead",
            lead_score=int(lead.score or 0),
            lead_tier=(lead.tier or "D").strip().upper(),
            owner_id=lead.owner_id,
            tags=list(lead.tags or []),
            status="active",
            converted_from_lead_id=lead_id,
            created_by=user["id"],
            created_at=now,
            updated_at=now,
        )
        db.add(contact)
        await db.flush()
    else:
        # Ensure account link
        if not contact.account_id:
            account_name_input = contact.account_name or contact.company_name or contact.full_name
            if account_name_input:
                resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])
                contact.account_id = resolved_account.get("account_id")
                contact.account_name = resolved_account.get("account_name")
                contact.updated_at = now

    # Pipeline/Stage
    chosen = await get_default_pipeline_and_stage(db, tenant_id, data.pipeline_id, data.stage_id)
    pipeline = chosen["pipeline"]
    stage: PipelineStage = chosen["stage"]

    deal_name = (data.deal_name or "").strip() or (lead.company_name or lead.full_name or "New Deal").strip()
    amount = float(data.amount or 0.0)
    lead_score = int(lead.score or 0)
    lead_tier = (lead.tier or calculate_tier(lead_score)).strip().upper()
    if lead_tier not in VALID_LEAD_TIERS:
        lead_tier = calculate_tier(lead_score)

    next_step_at_dt = parse_iso_datetime(data.next_step_at)
    if not next_step_at_dt:
        raise HTTPException(status_code=400, detail="next_step_at must be a valid ISO datetime")

    deal = Deal(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=deal_name,
        amount=amount,
        currency="USD",
        status="open",
        contact_id=contact.id,
        account_id=contact.account_id,
        account_name=contact.account_name,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        next_step_at=next_step_at_dt,
        next_step_note=data.next_step_note,
        lead_score=lead_score,
        lead_tier=lead_tier,
        sales_motion_type=lead.sales_motion_type or "partnership_sales",
        partner_id=lead.partner_id,
        product_id=lead.product_id,
        partner_name=lead.partner_name,
        product_name=lead.product_name,
        owner_id=lead.owner_id or user["id"],
        last_override={},
        handoff_status="pending",
        created_at=now,
        updated_at=now,
    )

    missing = []
    for field in list(stage.required_fields or []):
        value = getattr(deal, field, None) if hasattr(deal, field) else None
        if not is_non_empty(value):
            missing.append(field)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields for stage '{stage.name}': {', '.join(missing)}",
        )

    db.add(deal)
    await db.flush()

    await upsert_open_next_step_task_for_deal(
        db=db,
        tenant_id=tenant_id,
        deal_id=deal.id,
        due_at=deal.next_step_at,
        owner_id=deal.owner_id or user["id"],
        created_by=user["id"],
        note=deal.next_step_note,
    )

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="deal_created",
        title=f"Deal created: {deal_name}",
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        deal_id=deal.id,
        contact_id=contact.id,
        metadata={"converted_from_lead_id": lead_id},
    )

    lead.status = "converted"
    lead.converted_at = now
    lead.contact_id = contact.id
    lead.updated_at = now

    await db.flush()

    contact_dict = {
        "id": contact.id,
        "tenant_id": contact.tenant_id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "full_name": contact.full_name,
        "email": contact.email,
        "phone": contact.phone,
        "company_name": contact.company_name,
        "company": contact.company_name,
        "account_id": contact.account_id,
        "account_name": contact.account_name,
        "source": contact.source,
        "lifecycle_stage": contact.lifecycle_stage,
        "lead_score": contact.lead_score,
        "lead_tier": contact.lead_tier,
        "owner_id": contact.owner_id,
        "tags": contact.tags or [],
        "status": contact.status,
        "converted_from_lead_id": contact.converted_from_lead_id,
        "created_by": contact.created_by,
        "created_at": dt_to_iso(contact.created_at),
        "updated_at": dt_to_iso(contact.updated_at),
    }
    deal_dict = {
        "id": deal.id,
        "tenant_id": deal.tenant_id,
        "name": deal.name,
        "amount": float(deal.amount or 0),
        "currency": deal.currency,
        "status": deal.status,
        "contact_id": deal.contact_id,
        "account_id": deal.account_id,
        "account_name": deal.account_name,
        "pipeline_id": deal.pipeline_id,
        "stage_id": deal.stage_id,
        "next_step_at": dt_to_iso(deal.next_step_at),
        "next_step_note": deal.next_step_note,
        "lead_score": deal.lead_score,
        "lead_tier": deal.lead_tier,
        "sales_motion_type": deal.sales_motion_type,
        "partner_id": deal.partner_id,
        "product_id": deal.product_id,
        "partner_name": deal.partner_name,
        "product_name": deal.product_name,
        "owner_id": deal.owner_id,
        "created_at": dt_to_iso(deal.created_at),
        "updated_at": dt_to_iso(deal.updated_at),
    }

    return {
        "lead_id": lead_id,
        "contact_id": contact.id,
        "deal_id": deal.id,
        "contact": contact_dict,
        "deal": deal_dict,
        "message": "Lead pushed to Sales Pipeline",
    }


@router.get("/stats/summary")
async def get_lead_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    total = int((await db.execute(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id))).scalar_one() or 0)

    async def _count(where_extra):
        res = await db.execute(
            select(func.count()).select_from(Lead).where(and_(Lead.tenant_id == tenant_id, where_extra))
        )
        return int(res.scalar_one() or 0)

    by_status = {
        "new": await _count(Lead.status == "new"),
        "assigned": await _count(Lead.status == "assigned"),
        "working": await _count(Lead.status == "working"),
        "info_collected": await _count(Lead.status == "info_collected"),
        "unresponsive": await _count(Lead.status == "unresponsive"),
        "disqualified": await _count(Lead.status == "disqualified"),
        "qualified": await _count(Lead.status == "qualified"),
        "converted": await _count(Lead.status == "converted"),
    }

    def _tier_count(t: str):
        return select(func.count()).select_from(Lead).where(
            and_(Lead.tenant_id == tenant_id, Lead.tier == t, Lead.status != "converted")
        )

    tier_counts = {}
    for t in ["A", "B", "C", "D"]:
        tier_counts[t] = int((await db.execute(_tier_count(t))).scalar_one() or 0)

    avg_res = await db.execute(
        select(func.avg(Lead.score)).where(and_(Lead.tenant_id == tenant_id, Lead.status != "converted"))
    )
    avg_score = avg_res.scalar_one()

    return {
        "total": total,
        "by_status": by_status,
        "by_tier": tier_counts,
        "average_score": round(float(avg_score or 0), 1) if avg_score else 0,
    }

