from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import (
    complete_open_next_step_tasks_for_deal,
    create_mention_tasks_from_text,
    create_timeline_event,
    get_active_calculation_definition,
    get_calculation_result,
    get_or_create_deal_handoff,
    handoff_complete,
    resolve_account,
    resolve_partner_and_product,
    sync_deal_handoff_status,
    upsert_open_next_step_task_for_deal,
)
from app.api_pg.utils import (
    VALID_LEAD_TIERS,
    calculate_tier,
    dt_to_iso,
    is_non_empty,
    now_utc,
    parse_iso_datetime,
)
from app.core.database import get_db
from app.pg_models.models import Contact, Deal, DealHandoff, Pipeline, PipelineStage, User

router = APIRouter(tags=["Deals"])


class DealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    amount: float = 0
    contact_id: Optional[str] = None
    pipeline_id: str
    stage_id: str
    next_step_at: Optional[str] = None
    next_step_note: Optional[str] = None
    spiced: Optional[Dict[str, Any]] = None
    demo_title: Optional[str] = None
    demo_type: Optional[str] = None
    demo_status: Optional[str] = None
    demo_scheduled_at: Optional[str] = None
    demo_duration_minutes: Optional[int] = Field(default=None, ge=5, le=480)
    demo_meet_url: Optional[str] = None
    demo_calendar_url: Optional[str] = None
    demo_completed_at: Optional[str] = None
    demo_notes: Optional[str] = None
    lead_score: Optional[int] = Field(default=None, ge=0, le=100)
    lead_tier: Optional[str] = None
    sales_motion_type: str = "partnership_sales"
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None


class DealUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    contact_id: Optional[str] = None
    next_step_at: Optional[str] = None
    next_step_note: Optional[str] = None
    spiced: Optional[Dict[str, Any]] = None
    demo_title: Optional[str] = None
    demo_type: Optional[str] = None
    demo_status: Optional[str] = None
    demo_scheduled_at: Optional[str] = None
    demo_duration_minutes: Optional[int] = Field(default=None, ge=5, le=480)
    demo_meet_url: Optional[str] = None
    demo_calendar_url: Optional[str] = None
    demo_completed_at: Optional[str] = None
    demo_notes: Optional[str] = None
    lead_score: Optional[int] = Field(default=None, ge=0, le=100)
    lead_tier: Optional[str] = None
    sales_motion_type: Optional[str] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None


class MoveDealStageRequest(BaseModel):
    stage_id: str
    override: bool = False
    override_reason: Optional[str] = None


class DealHandoffUpdate(BaseModel):
    delivery_owner_id: Optional[str] = None
    kickoff_at: Optional[str] = None
    checklist: Optional[Dict[str, bool]] = None
    notes: Optional[str] = None


def _deal_to_dict(
    d: Deal,
    contact: Optional[Contact] = None,
    stage: Optional[PipelineStage] = None,
    owner: Optional[User] = None,
) -> Dict[str, Any]:
    contact_name = None
    if contact:
        contact_name = (contact.full_name or f"{contact.first_name or ''} {contact.last_name or ''}").strip() or None
    stage_name = stage.name if stage else None
    owner_name = None
    if owner:
        owner_name = f"{owner.first_name} {owner.last_name}".strip() or owner.email

    return {
        "id": d.id,
        "tenant_id": d.tenant_id,
        "name": d.name,
        "amount": float(d.amount or 0.0),
        "currency": d.currency,
        "status": d.status,
        "contact_id": d.contact_id,
        "contact_name": contact_name,
        "account_id": d.account_id,
        "account_name": d.account_name,
        "pipeline_id": d.pipeline_id,
        "stage_id": d.stage_id,
        "stage_name": stage_name,
        "next_step_at": dt_to_iso(d.next_step_at),
        "next_step_note": d.next_step_note,
        "last_touchpoint_at": dt_to_iso(d.last_touchpoint_at),
        "lead_score": int(d.lead_score or 0),
        "lead_tier": d.lead_tier,
        "sales_motion_type": d.sales_motion_type,
        "partner_id": d.partner_id,
        "product_id": d.product_id,
        "partner_name": d.partner_name,
        "product_name": d.product_name,
        "spiced": d.spiced or {},
        "spiced_complete": _spiced_complete(d.spiced or {}),
        "demo_title": d.demo_title,
        "demo_type": d.demo_type,
        "demo_status": d.demo_status,
        "demo_scheduled_at": dt_to_iso(d.demo_scheduled_at),
        "demo_duration_minutes": int(d.demo_duration_minutes or 30),
        "demo_meet_url": d.demo_meet_url,
        "demo_calendar_url": d.demo_calendar_url,
        "demo_completed_at": dt_to_iso(d.demo_completed_at),
        "demo_notes": d.demo_notes,
        "owner_id": d.owner_id,
        "owner_name": owner_name,
        "handoff_status": d.handoff_status,
        "created_at": dt_to_iso(d.created_at),
        "updated_at": dt_to_iso(d.updated_at),
    }


def _spiced_complete(spiced: Dict[str, Any]) -> bool:
    required = ["situation", "problem", "implication", "critical_event", "economic_impact", "decision"]
    for k in required:
        v = (spiced or {}).get(k)
        if not is_non_empty(v):
            return False
    return True


def _normalize_spiced(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    allowed = ["situation", "problem", "implication", "critical_event", "economic_impact", "decision"]
    invalid_keys = [k for k in (incoming or {}).keys() if k not in allowed]
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid spiced keys: {', '.join(invalid_keys)}")

    if not incoming:
        return {}

    merged = {k: (existing or {}).get(k) for k in allowed}
    for k, v in incoming.items():
        merged[k] = v.strip() if isinstance(v, str) else v
    return merged


def _demo_is_scheduled(deal: Deal) -> bool:
    return bool(deal.demo_scheduled_at)


def _demo_is_completed(deal: Deal) -> bool:
    if (deal.demo_status or "").strip().lower() == "completed":
        return True
    return bool(deal.demo_completed_at)


def _stage_requires_calculation(stage: PipelineStage) -> bool:
    if bool(stage.requires_calculation_complete):
        return True
    name = (stage.name or "").lower()
    return ("demo" in name and ("schedule" in name or "scheduled" in name)) or ("discovery" in name and "scheduled" in name)


@router.get("/deals")
async def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    filters: List[Any] = [Deal.tenant_id == tenant_id]
    if status:
        filters.append(Deal.status == status)
    if pipeline_id:
        filters.append(Deal.pipeline_id == pipeline_id)
    if contact_id:
        filters.append(Deal.contact_id == contact_id)

    total_res = await db.execute(select(func.count()).select_from(Deal).where(and_(*filters)))
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Deal)
        .where(and_(*filters))
        .order_by(Deal.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    deals = (await db.execute(stmt)).scalars().all()

    contact_ids = [d.contact_id for d in deals if d.contact_id]
    stage_ids = [d.stage_id for d in deals if d.stage_id]
    owner_ids = [d.owner_id for d in deals if d.owner_id]

    contacts_map: Dict[str, Contact] = {}
    if contact_ids:
        contacts = (
            await db.execute(select(Contact).where(and_(Contact.tenant_id == tenant_id, Contact.id.in_(contact_ids))))
        ).scalars().all()
        contacts_map = {c.id: c for c in contacts}

    stages_map: Dict[str, PipelineStage] = {}
    if stage_ids:
        stages = (await db.execute(select(PipelineStage).where(PipelineStage.id.in_(stage_ids)))).scalars().all()
        stages_map = {s.id: s for s in stages}

    owners_map: Dict[str, User] = {}
    if owner_ids:
        owners = (
            await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.id.in_(owner_ids))))
        ).scalars().all()
        owners_map = {o.id: o for o in owners}

    return {
        "deals": [
            _deal_to_dict(d, contact=contacts_map.get(d.contact_id), stage=stages_map.get(d.stage_id), owner=owners_map.get(d.owner_id))
            for d in deals
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/deals", status_code=201)
async def create_deal(
    data: DealCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == data.pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    stage = (
        await db.execute(
            select(PipelineStage).where(and_(PipelineStage.id == data.stage_id, PipelineStage.pipeline_id == data.pipeline_id))
        )
    ).scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    contact: Optional[Contact] = None
    if data.contact_id:
        contact = (
            await db.execute(select(Contact).where(and_(Contact.id == data.contact_id, Contact.tenant_id == tenant_id)))
        ).scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=400, detail="Contact not found")

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

    resolved_account = {"account_id": None, "account_name": None}
    if contact:
        account_name_input = contact.account_name or contact.company_name or contact.full_name
        if account_name_input:
            resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])
            if not contact.account_id:
                contact.account_id = resolved_account.get("account_id")
                contact.account_name = resolved_account.get("account_name")
                contact.updated_at = now_utc()

    # Scoring fields
    lead_score = data.lead_score
    lead_tier = (data.lead_tier or "").strip().upper() if data.lead_tier else None
    if lead_score is None and contact and contact.lead_score is not None:
        lead_score = int(contact.lead_score)
    if not lead_tier and contact and contact.lead_tier:
        lead_tier = str(contact.lead_tier).strip().upper()

    if lead_score is not None:
        lead_score = int(max(0, min(100, lead_score)))
    if lead_tier and lead_tier not in VALID_LEAD_TIERS:
        raise HTTPException(status_code=400, detail="Invalid lead_tier. Must be one of: A, B, C, D")
    if lead_score is not None and not lead_tier:
        lead_tier = calculate_tier(lead_score)
    if lead_tier and lead_score is None:
        lead_score = {"A": 80, "B": 60, "C": 40, "D": 0}.get(lead_tier, 0)
    if lead_score is None:
        lead_score = 0
    if not lead_tier:
        lead_tier = "D"

    next_step_dt = parse_iso_datetime(data.next_step_at) if data.next_step_at else None

    spiced = data.spiced if data.spiced is not None else {}
    if not isinstance(spiced, dict):
        raise HTTPException(status_code=400, detail="spiced must be an object")

    demo_scheduled_dt = parse_iso_datetime((data.demo_scheduled_at or "").strip()) if data.demo_scheduled_at else None
    if data.demo_scheduled_at and not demo_scheduled_dt:
        raise HTTPException(status_code=400, detail="demo_scheduled_at must be a valid ISO datetime")

    demo_completed_dt = parse_iso_datetime((data.demo_completed_at or "").strip()) if data.demo_completed_at else None
    if data.demo_completed_at and not demo_completed_dt:
        raise HTTPException(status_code=400, detail="demo_completed_at must be a valid ISO datetime")

    demo_status = (data.demo_status or "").strip().lower() or None
    if demo_status and demo_status not in {"scheduled", "completed", "no_show", "canceled"}:
        raise HTTPException(status_code=400, detail="Invalid demo_status")
    if not demo_status and demo_completed_dt:
        demo_status = "completed"
    if not demo_status and demo_scheduled_dt:
        demo_status = "scheduled"

    demo_duration_minutes = int(data.demo_duration_minutes or 30)

    now = now_utc()
    deal = Deal(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=data.name,
        amount=float(data.amount or 0.0),
        currency="USD",
        status="open",
        contact_id=data.contact_id,
        account_id=resolved_account.get("account_id"),
        account_name=resolved_account.get("account_name"),
        pipeline_id=data.pipeline_id,
        stage_id=data.stage_id,
        next_step_at=next_step_dt,
        next_step_note=data.next_step_note,
        last_touchpoint_at=None,
        lead_score=lead_score,
        lead_tier=lead_tier,
        sales_motion_type=(data.sales_motion_type or "partnership_sales").strip(),
        partner_id=resolved.get("partner_id"),
        product_id=resolved.get("product_id"),
        partner_name=resolved.get("partner_name"),
        product_name=resolved.get("product_name"),
        spiced=spiced,
        demo_title=(data.demo_title or "").strip() or None,
        demo_type=(data.demo_type or "").strip() or None,
        demo_status=demo_status,
        demo_scheduled_at=demo_scheduled_dt,
        demo_duration_minutes=demo_duration_minutes,
        demo_meet_url=(data.demo_meet_url or "").strip() or None,
        demo_calendar_url=(data.demo_calendar_url or "").strip() or None,
        demo_completed_at=demo_completed_dt,
        demo_notes=data.demo_notes,
        owner_id=user["id"],
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
        raise HTTPException(status_code=400, detail=f"Missing required fields for stage '{stage.name}': {', '.join(missing)}")

    db.add(deal)
    await db.flush()

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="deal_created",
        title=f"Deal created: {deal.name}",
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        deal_id=deal.id,
    )

    if deal.next_step_at:
        await upsert_open_next_step_task_for_deal(
            db=db,
            tenant_id=tenant_id,
            deal_id=deal.id,
            due_at=deal.next_step_at,
            owner_id=deal.owner_id or user["id"],
            created_by=user["id"],
            note=deal.next_step_note,
        )

    # @mentions in notes -> create mention tasks for tagged teammates
    try:
        await create_mention_tasks_from_text(
            db=db,
            tenant_id=tenant_id,
            actor_id=user.get("id"),
            actor_name=user.get("full_name"),
            text=deal.next_step_note,
            source=f"deal:{deal.id}:next_step_note",
            related_type="deal",
            related_id=deal.id,
            context_label=f"Deal: {deal.name}",
        )
        await create_mention_tasks_from_text(
            db=db,
            tenant_id=tenant_id,
            actor_id=user.get("id"),
            actor_name=user.get("full_name"),
            text=deal.demo_notes,
            source=f"deal:{deal.id}:demo_notes",
            related_type="deal",
            related_id=deal.id,
            context_label=f"Deal: {deal.name}",
        )
    except Exception:
        pass

    return _deal_to_dict(deal, contact=contact, stage=stage)


@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    deal = (await db.execute(select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)))).scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    contact = None
    if deal.contact_id:
        contact = (await db.execute(select(Contact).where(and_(Contact.id == deal.contact_id, Contact.tenant_id == tenant_id)))).scalar_one_or_none()
    stage = None
    if deal.stage_id:
        stage = (await db.execute(select(PipelineStage).where(PipelineStage.id == deal.stage_id))).scalar_one_or_none()

    return _deal_to_dict(deal, contact=contact, stage=stage)


@router.put("/deals/{deal_id}")
async def update_deal(
    deal_id: str,
    data: DealUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    deal = (await db.execute(select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)))).scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    current_stage = None
    if deal.stage_id:
        current_stage = (await db.execute(select(PipelineStage).where(PipelineStage.id == deal.stage_id))).scalar_one_or_none()
    current_required = set((current_stage.required_fields or []) if current_stage else [])

    now = now_utc()
    contact: Optional[Contact] = None

    if data.name is not None:
        deal.name = data.name
    if data.amount is not None:
        deal.amount = float(data.amount or 0.0)

    if data.contact_id is not None:
        if not data.contact_id:
            if "contact_id" in current_required:
                raise HTTPException(status_code=400, detail="contact_id is required for the current stage")
            deal.contact_id = None
            deal.account_id = None
            deal.account_name = None
        else:
            contact = (
                await db.execute(select(Contact).where(and_(Contact.id == data.contact_id, Contact.tenant_id == tenant_id)))
            ).scalar_one_or_none()
            if not contact:
                raise HTTPException(status_code=400, detail="Contact not found")
            deal.contact_id = data.contact_id

            account_name_input = contact.account_name or contact.company_name or contact.full_name
            if account_name_input:
                resolved_account = await resolve_account(db, tenant_id, account_name_input, user["id"])
                deal.account_id = resolved_account.get("account_id")
                deal.account_name = resolved_account.get("account_name")
                if not contact.account_id:
                    contact.account_id = resolved_account.get("account_id")
                    contact.account_name = resolved_account.get("account_name")
                    contact.updated_at = now

            if data.lead_score is None and data.lead_tier is None:
                if contact.lead_score is not None:
                    deal.lead_score = int(contact.lead_score)
                if contact.lead_tier:
                    deal.lead_tier = str(contact.lead_tier).strip().upper()

    if data.next_step_at is not None:
        value = (data.next_step_at or "").strip()
        next_step_dt = parse_iso_datetime(value) if value else None
        if value and not next_step_dt:
            raise HTTPException(status_code=400, detail="next_step_at must be a valid ISO datetime")
        if not next_step_dt and "next_step_at" in current_required:
            raise HTTPException(status_code=400, detail="next_step_at is required for the current stage")
        deal.next_step_at = next_step_dt

    if data.next_step_note is not None:
        deal.next_step_note = data.next_step_note
        try:
            await create_mention_tasks_from_text(
                db=db,
                tenant_id=tenant_id,
                actor_id=user.get("id"),
                actor_name=user.get("full_name"),
                text=deal.next_step_note,
                source=f"deal:{deal.id}:next_step_note",
                related_type="deal",
                related_id=deal.id,
                context_label=f"Deal: {deal.name}",
            )
        except Exception:
            pass

    if data.spiced is not None:
        incoming = data.spiced or {}
        if not isinstance(incoming, dict):
            raise HTTPException(status_code=400, detail="spiced must be an object")
        deal.spiced = _normalize_spiced(deal.spiced or {}, incoming)

    if data.demo_title is not None:
        v = (data.demo_title or "").strip() or None
        if not v and "demo_title" in current_required:
            raise HTTPException(status_code=400, detail="demo_title is required for the current stage")
        deal.demo_title = v

    if data.demo_type is not None:
        v = (data.demo_type or "").strip() or None
        if not v and "demo_type" in current_required:
            raise HTTPException(status_code=400, detail="demo_type is required for the current stage")
        deal.demo_type = v

    if data.demo_scheduled_at is not None:
        value = (data.demo_scheduled_at or "").strip()
        dt = parse_iso_datetime(value) if value else None
        if value and not dt:
            raise HTTPException(status_code=400, detail="demo_scheduled_at must be a valid ISO datetime")
        if not dt and "demo_scheduled_at" in current_required:
            raise HTTPException(status_code=400, detail="demo_scheduled_at is required for the current stage")
        deal.demo_scheduled_at = dt

    if data.demo_duration_minutes is not None:
        deal.demo_duration_minutes = int(data.demo_duration_minutes or 30)

    if data.demo_meet_url is not None:
        v = (data.demo_meet_url or "").strip() or None
        if not v and "demo_meet_url" in current_required:
            raise HTTPException(status_code=400, detail="demo_meet_url is required for the current stage")
        deal.demo_meet_url = v

    if data.demo_calendar_url is not None:
        v = (data.demo_calendar_url or "").strip() or None
        if not v and "demo_calendar_url" in current_required:
            raise HTTPException(status_code=400, detail="demo_calendar_url is required for the current stage")
        deal.demo_calendar_url = v

    if data.demo_completed_at is not None:
        value = (data.demo_completed_at or "").strip()
        dt = parse_iso_datetime(value) if value else None
        if value and not dt:
            raise HTTPException(status_code=400, detail="demo_completed_at must be a valid ISO datetime")
        if not dt and "demo_completed_at" in current_required:
            raise HTTPException(status_code=400, detail="demo_completed_at is required for the current stage")
        deal.demo_completed_at = dt

    if data.demo_notes is not None:
        deal.demo_notes = data.demo_notes
        try:
            await create_mention_tasks_from_text(
                db=db,
                tenant_id=tenant_id,
                actor_id=user.get("id"),
                actor_name=user.get("full_name"),
                text=deal.demo_notes,
                source=f"deal:{deal.id}:demo_notes",
                related_type="deal",
                related_id=deal.id,
                context_label=f"Deal: {deal.name}",
            )
        except Exception:
            pass

    if data.demo_status is not None:
        demo_status = (data.demo_status or "").strip().lower() or None
        if demo_status and demo_status not in {"scheduled", "completed", "no_show", "canceled"}:
            raise HTTPException(status_code=400, detail="Invalid demo_status")
        if not demo_status and "demo_status" in current_required:
            raise HTTPException(status_code=400, detail="demo_status is required for the current stage")
        deal.demo_status = demo_status

    if deal.demo_completed_at:
        deal.demo_status = "completed"
    elif deal.demo_scheduled_at and not deal.demo_status:
        deal.demo_status = "scheduled"

    if (deal.demo_status or "").strip().lower() == "scheduled" and not deal.demo_scheduled_at:
        raise HTTPException(status_code=400, detail="demo_scheduled_at is required when demo_status is scheduled")

    if (deal.demo_status or "").strip().lower() == "completed" and not deal.demo_completed_at:
        deal.demo_completed_at = now

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
            tenant_id=tenant_id,
            sales_motion_type=data.sales_motion_type or deal.sales_motion_type,
            partner_id=data.partner_id if data.partner_id is not None else deal.partner_id,
            product_id=data.product_id if data.product_id is not None else deal.product_id,
            partner_name=data.partner_name if data.partner_name is not None else deal.partner_name,
            product_name=data.product_name if data.product_name is not None else deal.product_name,
            actor_id=user["id"],
        )
        deal.sales_motion_type = (data.sales_motion_type or deal.sales_motion_type or "partnership_sales").strip()
        deal.partner_id = resolved.get("partner_id")
        deal.product_id = resolved.get("product_id")
        deal.partner_name = resolved.get("partner_name")
        deal.product_name = resolved.get("product_name")

    if data.lead_score is not None or data.lead_tier is not None:
        lead_score = data.lead_score
        lead_tier = (data.lead_tier or "").strip().upper() if data.lead_tier else None
        if lead_score is not None:
            lead_score = int(max(0, min(100, lead_score)))
        if lead_tier and lead_tier not in VALID_LEAD_TIERS:
            raise HTTPException(status_code=400, detail="Invalid lead_tier. Must be one of: A, B, C, D")
        if lead_score is not None and not lead_tier:
            lead_tier = calculate_tier(lead_score)
        if lead_tier and lead_score is None:
            lead_score = {"A": 80, "B": 60, "C": 40, "D": 0}.get(lead_tier, 0)
        if lead_score is not None:
            deal.lead_score = lead_score
        if lead_tier:
            deal.lead_tier = lead_tier

    deal.updated_at = now
    await db.flush()

    # Sync Next Step task (discipline)
    if (deal.status or "open") == "open" and deal.next_step_at:
        await upsert_open_next_step_task_for_deal(
            db=db,
            tenant_id=tenant_id,
            deal_id=deal.id,
            due_at=deal.next_step_at,
            owner_id=deal.owner_id or user["id"],
            created_by=user["id"],
            note=deal.next_step_note,
        )

    if not contact and deal.contact_id:
        contact = (await db.execute(select(Contact).where(and_(Contact.id == deal.contact_id, Contact.tenant_id == tenant_id)))).scalar_one_or_none()
    stage = None
    if deal.stage_id:
        stage = (await db.execute(select(PipelineStage).where(PipelineStage.id == deal.stage_id))).scalar_one_or_none()

    return _deal_to_dict(deal, contact=contact, stage=stage)


@router.get("/deals/{deal_id}/handoff")
async def get_deal_handoff(
    deal_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    deal = (await db.execute(select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)))).scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    handoff = await get_or_create_deal_handoff(db, tenant_id, deal_id, user["id"])
    complete = handoff_complete(handoff.delivery_owner_id, handoff.kickoff_at, handoff.checklist or {})
    return {
        "id": handoff.id,
        "tenant_id": handoff.tenant_id,
        "deal_id": handoff.deal_id,
        "delivery_owner_id": handoff.delivery_owner_id,
        "kickoff_at": dt_to_iso(handoff.kickoff_at),
        "checklist": handoff.checklist or {},
        "notes": handoff.notes,
        "status": handoff.status,
        "completed_at": dt_to_iso(handoff.completed_at),
        "created_by": handoff.created_by,
        "created_at": dt_to_iso(handoff.created_at),
        "updated_at": dt_to_iso(handoff.updated_at),
        "is_complete": complete,
    }


@router.put("/deals/{deal_id}/handoff")
async def update_deal_handoff(
    deal_id: str,
    data: DealHandoffUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    deal = (await db.execute(select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)))).scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    handoff = await get_or_create_deal_handoff(db, tenant_id, deal_id, user["id"])
    now = now_utc()

    if data.delivery_owner_id is not None:
        if data.delivery_owner_id:
            owner = (
                await db.execute(select(User).where(and_(User.id == data.delivery_owner_id, User.tenant_id == tenant_id)))
            ).scalar_one_or_none()
            if not owner:
                raise HTTPException(status_code=400, detail="Delivery owner not found")
            handoff.delivery_owner_id = data.delivery_owner_id
        else:
            handoff.delivery_owner_id = None

    if data.kickoff_at is not None:
        kickoff_dt = parse_iso_datetime((data.kickoff_at or "").strip()) if data.kickoff_at else None
        if data.kickoff_at and not kickoff_dt:
            raise HTTPException(status_code=400, detail="Invalid kickoff date/time")
        handoff.kickoff_at = kickoff_dt

    if data.notes is not None:
        handoff.notes = data.notes
        try:
            await create_mention_tasks_from_text(
                db=db,
                tenant_id=tenant_id,
                actor_id=user.get("id"),
                actor_name=user.get("full_name"),
                text=handoff.notes,
                source=f"deal:{deal.id}:handoff_notes",
                related_type="deal",
                related_id=deal.id,
                context_label=f"Deal: {deal.name} (Handoff)",
            )
        except Exception:
            pass

    if data.checklist is not None:
        incoming = data.checklist or {}
        required_keys = [
            "spiced_summary",
            "gap_analysis",
            "proposal",
            "contract",
            "risk_notes",
            "kickoff_readiness_checklist",
        ]
        invalid_keys = [k for k in incoming.keys() if k not in required_keys]
        if invalid_keys:
            raise HTTPException(status_code=400, detail=f"Invalid checklist keys: {', '.join(invalid_keys)}")

        merged = {k: bool((handoff.checklist or {}).get(k)) for k in required_keys}
        for k, v in incoming.items():
            merged[k] = bool(v)
        handoff.checklist = merged

    handoff.updated_at = now
    deal.updated_at = now
    await sync_deal_handoff_status(db, tenant_id, deal, handoff, user)
    await db.flush()

    complete = handoff_complete(handoff.delivery_owner_id, handoff.kickoff_at, handoff.checklist or {})
    return {
        "id": handoff.id,
        "tenant_id": handoff.tenant_id,
        "deal_id": handoff.deal_id,
        "delivery_owner_id": handoff.delivery_owner_id,
        "kickoff_at": dt_to_iso(handoff.kickoff_at),
        "checklist": handoff.checklist or {},
        "notes": handoff.notes,
        "status": handoff.status,
        "completed_at": dt_to_iso(handoff.completed_at),
        "created_by": handoff.created_by,
        "created_at": dt_to_iso(handoff.created_at),
        "updated_at": dt_to_iso(handoff.updated_at),
        "is_complete": complete,
    }


@router.post("/deals/{deal_id}/move-stage")
async def move_deal_stage(
    deal_id: str,
    payload: Optional[MoveDealStageRequest] = None,
    new_stage_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    if payload and payload.stage_id:
        new_stage_id = payload.stage_id
    if not new_stage_id:
        raise HTTPException(status_code=422, detail="stage_id is required")

    override = bool(payload.override) if payload else False
    override_reason = (payload.override_reason or "").strip() if payload else ""

    if override:
        if user.get("role") not in ["admin", "manager"]:
            raise HTTPException(status_code=403, detail="Admin access required to override stage rules")
        if len(override_reason) < 3:
            raise HTTPException(status_code=400, detail="override_reason is required when override=true")

    deal = (await db.execute(select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id)))).scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    old_stage = None
    if deal.stage_id:
        old_stage = (await db.execute(select(PipelineStage).where(PipelineStage.id == deal.stage_id))).scalar_one_or_none()

    new_stage = (await db.execute(select(PipelineStage).where(PipelineStage.id == new_stage_id))).scalar_one_or_none()
    if not new_stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    if deal.pipeline_id and new_stage.pipeline_id != deal.pipeline_id:
        raise HTTPException(status_code=400, detail="Stage does not belong to this deal's pipeline")

    new_stage_name_lower = (new_stage.name or "").strip().lower()
    moving_to_closed_won = "closed won" in new_stage_name_lower
    moving_to_closed_lost = "closed lost" in new_stage_name_lower
    moving_to_handoff = "handoff" in new_stage_name_lower
    moving_to_demo_scheduled = "demo" in new_stage_name_lower and ("schedule" in new_stage_name_lower or "scheduled" in new_stage_name_lower)
    moving_to_demo_completed = "demo" in new_stage_name_lower and "completed" in new_stage_name_lower
    moving_to_verbal = "verbal commitment" in new_stage_name_lower

    if not override:
        if (deal.status or "open").lower() in ["won", "lost"]:
            if not (moving_to_closed_won or moving_to_closed_lost or moving_to_handoff):
                raise HTTPException(status_code=400, detail="Deal is closed. Stage changes require an admin override")

        missing = []
        for field in list(new_stage.required_fields or []):
            value = getattr(deal, field, None) if hasattr(deal, field) else None
            if not is_non_empty(value):
                missing.append(field)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields for stage '{new_stage.name}': {', '.join(missing)}")

        if _stage_requires_calculation(new_stage):
            calc_def = await get_active_calculation_definition(db, tenant_id)
            if calc_def:
                calc_result = await get_calculation_result(db, deal_id=deal_id, definition_id=calc_def.id)
                if not calc_result or not calc_result.is_complete:
                    raise HTTPException(status_code=400, detail="Calculation must be complete before moving to this stage")

        if moving_to_demo_scheduled and not _demo_is_scheduled(deal):
            raise HTTPException(status_code=400, detail="Demo must be scheduled (demo_scheduled_at) before moving to this stage")

        if moving_to_demo_completed:
            if not _demo_is_completed(deal):
                raise HTTPException(status_code=400, detail="Demo must be completed (demo_completed_at) before moving to this stage")
            if not _spiced_complete(deal.spiced or {}):
                raise HTTPException(status_code=400, detail="SPICED summary must be complete before moving to this stage")

        if moving_to_verbal and not _demo_is_completed(deal):
            raise HTTPException(status_code=400, detail="Demo must be completed before moving to Verbal Commitment")

        if moving_to_handoff:
            handoff = (
                await db.execute(select(DealHandoff).where(and_(DealHandoff.tenant_id == tenant_id, DealHandoff.deal_id == deal_id)))
            ).scalar_one_or_none()
            if not handoff or not handoff_complete(handoff.delivery_owner_id, handoff.kickoff_at, handoff.checklist or {}):
                raise HTTPException(status_code=400, detail="Delivery handoff must be completed before moving to Handoff to Delivery")

    now = now_utc()
    previous_status = (deal.status or "open").lower()
    old_stage_id = deal.stage_id

    deal.stage_id = new_stage_id
    deal.updated_at = now

    if moving_to_closed_won:
        deal.status = "won"
        deal.closed_won_at = now
        deal.closed_at = now
    elif moving_to_closed_lost:
        deal.status = "lost"
        deal.closed_lost_at = now
        deal.closed_at = now
    elif previous_status in ["won", "lost"] and not moving_to_handoff:
        deal.status = "open"
        deal.reopened_at = now

    if override:
        deal.last_override = {
            "from_stage_id": old_stage_id,
            "to_stage_id": new_stage_id,
            "reason": override_reason,
            "actor_id": user.get("id"),
            "actor_name": user.get("full_name"),
            "created_at": now.isoformat(),
        }

    await db.flush()

    if deal.status in ["won", "lost"]:
        await complete_open_next_step_tasks_for_deal(db, tenant_id, deal_id, user["id"])

    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="stage_changed",
        title=f"Stage changed: {(old_stage.name if old_stage else 'Unknown')} -> {new_stage.name}",
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        deal_id=deal_id,
        metadata={
            "from_stage": old_stage.name if old_stage else None,
            "to_stage": new_stage.name,
            "override": override,
            **({"override_reason": override_reason} if override else {}),
        },
    )

    if moving_to_closed_won and previous_status != "won":
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="deal_won",
            title="Deal marked Closed Won",
            actor_id=user["id"],
            actor_name=user.get("full_name"),
            deal_id=deal_id,
        )
        handoff = await get_or_create_deal_handoff(db, tenant_id, deal_id, user["id"])
        deal.handoff_status = handoff.status
        deal.updated_at = now
        await db.flush()

    if moving_to_closed_lost and previous_status != "lost":
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="deal_lost",
            title="Deal marked Closed Lost",
            actor_id=user["id"],
            actor_name=user.get("full_name"),
            deal_id=deal_id,
        )

    return {"success": True, "new_stage_id": new_stage_id}

