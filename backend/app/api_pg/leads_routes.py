from __future__ import annotations

import csv
import io
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
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


@router.get("/export")
async def export_leads_csv(
    format: str = Query("hubspot"),
    limit: int = Query(10000, ge=1, le=50000),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    leads = (
        await db.execute(select(Lead).where(Lead.tenant_id == tenant_id).order_by(Lead.created_at.desc()).limit(limit))
    ).scalars().all()

    out = io.StringIO()
    writer = csv.writer(out)

    fmt = (format or "hubspot").strip().lower()
    if fmt == "hubspot":
        writer.writerow(
            [
                "Email",
                "First Name",
                "Last Name",
                "Phone Number",
                "Company Name",
                "Lead Status",
                "Lead Source",
                "Lead Score",
                "Lead Tier",
                "Sales Motion Type",
                "Partner Name",
                "Partner Product",
                "Economic Units",
                "Usage Volume",
                "Urgency (1-5)",
                "Trigger Event",
                "Primary Motivation",
                "Decision Role",
                "Decision Process Clarity (1-5)",
            ]
        )
        for l in leads:
            sd = l.scoring_data or {}
            writer.writerow(
                [
                    l.email or "",
                    l.first_name or "",
                    l.last_name or "",
                    l.phone or "",
                    l.company_name or "",
                    l.status or "",
                    l.source or "",
                    int(l.score or 0),
                    (l.tier or "").strip().upper(),
                    l.sales_motion_type or "",
                    l.partner_name or "",
                    l.product_name or "",
                    sd.get("economic_units", ""),
                    sd.get("usage_volume", ""),
                    sd.get("urgency", ""),
                    sd.get("trigger_event", ""),
                    sd.get("primary_motivation", ""),
                    sd.get("decision_role", ""),
                    sd.get("decision_process_clarity", ""),
                ]
            )
    else:
        writer.writerow(
            [
                "email",
                "first_name",
                "last_name",
                "phone",
                "company_name",
                "status",
                "source",
                "sales_motion_type",
                "partner_name",
                "product_name",
                "score",
                "tier",
                "economic_units",
                "usage_volume",
                "urgency",
                "trigger_event",
                "primary_motivation",
                "decision_role",
                "decision_process_clarity",
                "created_at",
                "updated_at",
            ]
        )
        for l in leads:
            sd = l.scoring_data or {}
            writer.writerow(
                [
                    l.email or "",
                    l.first_name or "",
                    l.last_name or "",
                    l.phone or "",
                    l.company_name or "",
                    l.status or "",
                    l.source or "",
                    l.sales_motion_type or "",
                    l.partner_name or "",
                    l.product_name or "",
                    int(l.score or 0),
                    (l.tier or "").strip().upper(),
                    sd.get("economic_units", ""),
                    sd.get("usage_volume", ""),
                    sd.get("urgency", ""),
                    sd.get("trigger_event", ""),
                    sd.get("primary_motivation", ""),
                    sd.get("decision_role", ""),
                    sd.get("decision_process_clarity", ""),
                    dt_to_iso(l.created_at) or "",
                    dt_to_iso(l.updated_at) or "",
                ]
            )

    filename = f"leads_{tenant_id}.csv"
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
async def import_leads_csv(
    file: UploadFile = File(...),
    max_rows: int = Query(5000, ge=1, le=50000),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    filename = (file.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must include a header row")

    def norm_header(h: str) -> str:
        return "".join(ch for ch in (h or "").strip().lower() if ch.isalnum())

    header_aliases = {
        # Identity
        "email": "email",
        "emailaddress": "email",
        "emailid": "email",
        "firstname": "first_name",
        "lastname": "last_name",
        "fullname": "full_name",
        "name": "full_name",
        "phone": "phone",
        "phonenumber": "phone",
        "mobilenumber": "phone",
        "company": "company_name",
        "companyname": "company_name",
        "organization": "company_name",
        # Lead fields
        "leadstatus": "status",
        "status": "status",
        "leadsource": "source",
        "source": "source",
        "salesmotiontype": "sales_motion_type",
        "salesmotion": "sales_motion_type",
        "motion": "sales_motion_type",
        "partner": "partner_name",
        "partnername": "partner_name",
        "partnerproduct": "product_name",
        "product": "product_name",
        "productname": "product_name",
        "leadscore": "score",
        "score": "score",
        "leadtier": "tier",
        "tier": "tier",
        "notes": "notes",
        # Scoring inputs
        "economicunits": "economic_units",
        "economicunit": "economic_units",
        "usagevolume": "usage_volume",
        "urgency": "urgency",
        "triggerevent": "trigger_event",
        "primarymotivation": "primary_motivation",
        "decisionrole": "decision_role",
        "decisionprocessclarity": "decision_process_clarity",
    }

    header_map: Dict[str, Optional[str]] = {}
    for h in reader.fieldnames:
        header_map[h] = header_aliases.get(norm_header(h))

    created = 0
    updated = 0
    skipped = 0
    errors: list[Dict[str, Any]] = []

    now = now_utc()
    row_count = 0

    def normalize_status(value: str) -> str:
        raw = (value or "").strip().lower()
        if not raw:
            return "new"
        normalized = "".join(ch for ch in raw if ch.isalnum() or ch in {"_", " "}).strip()
        normalized = normalized.replace(" ", "_")
        mapping = {
            "new": "new",
            "assigned": "assigned",
            "working": "working",
            "info_collected": "info_collected",
            "infocollected": "info_collected",
            "unresponsive": "unresponsive",
            "disqualified": "disqualified",
            "qualified": "qualified",
            "converted": "converted",
        }
        return mapping.get(normalized, "new")

    for row_index, row in enumerate(reader, start=2):
        row_count += 1
        if row_count > max_rows:
            skipped += 1
            errors.append({"row": row_index, "error": f"Max rows exceeded ({max_rows}). Remaining rows not processed."})
            break

        values: Dict[str, str] = {}
        for k, v in (row or {}).items():
            field = header_map.get(k)
            if not field:
                continue
            val = (v or "").strip()
            if val != "":
                values[field] = val

        email = (values.get("email") or "").strip()
        phone = (values.get("phone") or "").strip()
        if not email and not phone:
            skipped += 1
            errors.append({"row": row_index, "error": "Missing email and phone"})
            continue

        first_name = (values.get("first_name") or "").strip()
        last_name = (values.get("last_name") or "").strip()
        full_name = (values.get("full_name") or "").strip()
        if (not first_name or not last_name) and full_name:
            parts = [p for p in full_name.split(" ") if p]
            if not first_name and parts:
                first_name = parts[0]
            if not last_name and len(parts) > 1:
                last_name = " ".join(parts[1:])
        if not first_name and email and "@" in email:
            first_name = email.split("@", 1)[0]

        company_name = (values.get("company_name") or "").strip() or None
        status = normalize_status(values.get("status") or "")
        source = (values.get("source") or "").strip() or "hubspot_import"

        partner_name = (values.get("partner_name") or "").strip() or None
        product_name = (values.get("product_name") or "").strip() or None

        raw_motion = (values.get("sales_motion_type") or "").strip()
        sales_motion_type = raw_motion
        if not sales_motion_type:
            sales_motion_type = "partner_sales" if (partner_name or product_name) else "partnership_sales"
        if sales_motion_type not in {"partnership_sales", "partner_sales"}:
            sales_motion_type = "partner_sales" if "partner" in sales_motion_type.lower() else "partnership_sales"

        update_motion_fields = any(k in values for k in ("sales_motion_type", "partner_name", "product_name"))

        scoring_data_updates: Dict[str, Any] = {}
        for key in [
            "economic_units",
            "usage_volume",
            "urgency",
            "trigger_event",
            "primary_motivation",
            "decision_role",
            "decision_process_clarity",
        ]:
            if key in values:
                scoring_data_updates[key] = values[key]

        manual_score = values.get("score")
        manual_tier = (values.get("tier") or "").strip().upper() or None

        existing: Optional[Lead] = None
        if email:
            existing = (
                await db.execute(
                    select(Lead)
                    .where(and_(Lead.tenant_id == tenant_id, func.lower(Lead.email) == email.lower()))
                    .limit(1)
                )
            ).scalar_one_or_none()
        if not existing and phone:
            existing = (
                await db.execute(select(Lead).where(and_(Lead.tenant_id == tenant_id, Lead.phone == phone)).limit(1))
            ).scalar_one_or_none()

        resolved_partner_product: Optional[Dict[str, Optional[str]]] = None
        if sales_motion_type == "partner_sales" and (not existing or update_motion_fields):
            try:
                resolved_partner_product = await resolve_partner_and_product(
                    db=db,
                    tenant_id=tenant_id,
                    sales_motion_type=sales_motion_type,
                    partner_id=None,
                    product_id=None,
                    partner_name=partner_name,
                    product_name=product_name,
                    actor_id=user["id"],
                )
            except HTTPException as exc:
                skipped += 1
                errors.append({"row": row_index, "error": exc.detail})
                continue

        if existing:
            if email:
                existing.email = email
            if phone:
                existing.phone = phone
            if first_name:
                existing.first_name = first_name
            if last_name:
                existing.last_name = last_name
            if first_name or last_name:
                existing.full_name = f"{existing.first_name or ''} {existing.last_name or ''}".strip() or existing.full_name
            if company_name:
                existing.company_name = company_name
            if source:
                existing.source = source
            if status:
                existing.status = status
            if values.get("notes") is not None:
                existing.notes = values.get("notes") or ""

            if update_motion_fields:
                existing.sales_motion_type = sales_motion_type
                if sales_motion_type == "partner_sales":
                    existing.partner_id = (resolved_partner_product or {}).get("partner_id")
                    existing.product_id = (resolved_partner_product or {}).get("product_id")
                    existing.partner_name = (resolved_partner_product or {}).get("partner_name")
                    existing.product_name = (resolved_partner_product or {}).get("product_name")
                else:
                    existing.partner_id = None
                    existing.product_id = None
                    existing.partner_name = None
                    existing.product_name = None

            if scoring_data_updates:
                merged = dict(existing.scoring_data or {})
                merged.update(scoring_data_updates)
                existing.scoring_data = merged
                if scoring_inputs_complete(merged):
                    existing.score = compute_universal_score(merged, existing.source or source)
                    existing.tier = calculate_tier(int(existing.score or 0))

            if manual_score is not None:
                try:
                    existing.score = int(manual_score)
                except Exception:
                    pass
                existing.tier = calculate_tier(int(existing.score or 0))
            if manual_tier:
                existing.tier = manual_tier if manual_tier in VALID_LEAD_TIERS else calculate_tier(int(existing.score or 0))

            existing.updated_at = now
            updated += 1
            continue

        scoring_data = scoring_data_updates or {}
        if manual_score is not None:
            try:
                score = int(manual_score)
            except Exception:
                score = 0
        elif scoring_inputs_complete(scoring_data):
            score = compute_universal_score(scoring_data, source)
        else:
            score = 0

        tier = (manual_tier or calculate_tier(int(score or 0))).strip().upper()
        if tier not in VALID_LEAD_TIERS:
            tier = calculate_tier(int(score or 0))

        lead = Lead(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            first_name=first_name or None,
            last_name=last_name or None,
            full_name=f"{first_name} {last_name}".strip() or full_name or None,
            email=email or None,
            phone=phone or None,
            company_name=company_name,
            source=source,
            sales_motion_type=sales_motion_type,
            partner_id=(resolved_partner_product or {}).get("partner_id") if resolved_partner_product else None,
            product_id=(resolved_partner_product or {}).get("product_id") if resolved_partner_product else None,
            partner_name=(resolved_partner_product or {}).get("partner_name") if resolved_partner_product else None,
            product_name=(resolved_partner_product or {}).get("product_name") if resolved_partner_product else None,
            score=int(score or 0),
            tier=tier,
            scoring_data=scoring_data,
            status=status,
            owner_id=None,
            assigned_at=None,
            notes=(values.get("notes") or None),
            touchpoints_count=0,
            last_touchpoint_at=None,
            tags=[],
            converted_at=None,
            contact_id=None,
            created_at=now,
            updated_at=now,
        )
        db.add(lead)
        created += 1

    if created or updated or skipped:
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="leads_imported",
            title=f"Leads imported ({created} created, {updated} updated)",
            actor_id=user["id"],
            actor_name=user.get("full_name"),
            metadata={"created": created, "updated": updated, "skipped": skipped, "errors": len(errors)},
        )

    await db.flush()
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:200]}


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
    chosen = await get_default_pipeline_and_stage(
        db,
        tenant_id,
        data.pipeline_id,
        data.stage_id,
        sales_motion_type=lead.sales_motion_type,
        partner_id=lead.partner_id,
    )
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

