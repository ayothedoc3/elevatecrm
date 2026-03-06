from __future__ import annotations

import csv
import io
import uuid
from datetime import timedelta
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
    get_workspace_sla_config,
    resolve_account,
    resolve_partner_and_product,
    run_lead_sla_automations,
    upsert_open_task_by_rule,
    upsert_open_next_step_task_for_deal,
)
from app.api_pg.utils import (
    MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE,
    VALID_LEAD_TIERS,
    calculate_tier,
    compute_universal_score,
    dt_to_iso,
    ensure_valid_buying_role,
    ensure_valid_icp_tier,
    is_non_empty,
    now_utc,
    parse_iso_datetime,
    scoring_inputs_complete,
)
from app.core.database import get_db
from app.pg_models.models import Contact, Deal, DealContact, Lead, PipelineStage, Task, User

router = APIRouter(prefix="/leads", tags=["Leads"])

LEAD_QUALIFICATION_STATUSES = {
    "new",
    "assigned",
    "new_assigned",
    "working",
    "info_collected",
    "qualified",
    "disqualified",
    "unresponsive",
    "nurture",
    "converted",
}
PARTNER_SALES_REQUIRED = ["client_name", "partner_commission_structure", "product_category"]
LEAD_STAGE_TRANSITIONS = {
    "new": {"assigned", "working", "disqualified", "nurture"},
    "assigned": {"working", "disqualified", "nurture"},
    "new_assigned": {"working", "disqualified", "nurture"},
    "working": {"info_collected", "unresponsive", "disqualified", "nurture"},
    "info_collected": {"qualified", "disqualified", "nurture"},
    "qualified": {"converted", "nurture", "disqualified"},
    "unresponsive": {"working", "nurture", "disqualified"},
    "nurture": {"working", "disqualified"},
    "disqualified": set(),
    "converted": set(),
}


def _is_finance_user(user: Dict[str, Any]) -> bool:
    return (user.get("role") or "").strip().lower() == "finance"


def _require_non_finance(user: Dict[str, Any]) -> None:
    if _is_finance_user(user):
        raise HTTPException(status_code=403, detail="Finance users can access Closed Won deals only")


def _normalize_lead_status(value: Optional[str]) -> str:
    raw = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in {"new_assigned", "new/assigned", "newassigned"}:
        return "new_assigned"
    if raw in {"info_collected", "infocollected"}:
        return "info_collected"
    if raw in {"qualified", "disqualified", "working", "unresponsive", "nurture", "converted", "new", "assigned"}:
        return raw
    return raw


def _is_partner_sales(motion: Optional[str]) -> bool:
    return (motion or "").strip() == "partner_sales"


def _extract_domain_from_email(email: Optional[str]) -> Optional[str]:
    e = (email or "").strip().lower()
    if "@" not in e:
        return None
    domain = e.split("@", 1)[1].strip().lstrip("www.")
    return domain or None


def _normalize_domain(value: Optional[str]) -> Optional[str]:
    d = (value or "").strip().lower()
    if not d:
        return None
    if d.startswith("http://") or d.startswith("https://"):
        d = d.split("://", 1)[1]
    if "/" in d:
        d = d.split("/", 1)[0]
    if ":" in d:
        d = d.split(":", 1)[0]
    d = d.strip().lstrip("www.")
    return d or None


def _extract_company_domain(lead: Lead, scoring_data: Dict[str, Any]) -> Optional[str]:
    domain = _extract_domain_from_email(lead.email)
    if domain:
        return domain
    return _normalize_domain((scoring_data or {}).get("company_domain"))


def _validate_qualified_lead_requirements(lead: Lead, scoring_data: Dict[str, Any]) -> None:
    scoring = scoring_data or {}

    missing_company: List[str] = []
    if not is_non_empty(lead.company_name):
        missing_company.append("company_name")
    if not _extract_company_domain(lead, scoring):
        missing_company.append("domain")
    if not is_non_empty(scoring.get("industry")):
        missing_company.append("industry")
    if not is_non_empty(scoring.get("company_size")):
        missing_company.append("company_size")
    if not is_non_empty((lead.country_region or scoring.get("country") or "")):
        missing_company.append("country")
    if not is_non_empty(scoring.get("icp_tier")):
        missing_company.append("icp_tier")
    if missing_company:
        raise HTTPException(
            status_code=400,
            detail=f"Missing company fields for qualification: {', '.join(missing_company)}",
        )
    try:
        scoring["icp_tier"] = ensure_valid_icp_tier(str(scoring.get("icp_tier")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    missing_contact: List[str] = []
    if not is_non_empty(lead.first_name):
        missing_contact.append("first_name")
    if not is_non_empty(lead.last_name):
        missing_contact.append("last_name")
    if not is_non_empty(lead.email):
        missing_contact.append("email")
    if not is_non_empty(scoring.get("job_title")):
        missing_contact.append("job_title")
    if not is_non_empty(scoring.get("buying_role")):
        missing_contact.append("buying_role")
    if missing_contact:
        raise HTTPException(
            status_code=400,
            detail=f"Missing contact fields for qualification: {', '.join(missing_contact)}",
        )
    try:
        scoring["buying_role"] = ensure_valid_buying_role(str(scoring.get("buying_role")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _require_partner_sales_fields(data: Dict[str, Any]) -> None:
    missing = [f for f in PARTNER_SALES_REQUIRED if not is_non_empty(data.get(f))]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields for partner_sales: {', '.join(missing)}",
        )


def _normalize_scoring_enums(scoring_data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(scoring_data or {})

    if "icp_tier" in normalized:
        raw_icp = normalized.get("icp_tier")
        if not is_non_empty(raw_icp):
            normalized["icp_tier"] = None
        else:
            try:
                normalized["icp_tier"] = ensure_valid_icp_tier(str(raw_icp))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

    if "buying_role" in normalized:
        raw_role = normalized.get("buying_role")
        if not is_non_empty(raw_role):
            normalized["buying_role"] = None
        else:
            try:
                normalized["buying_role"] = ensure_valid_buying_role(str(raw_role))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

    return normalized


def _extract_valid_buying_role(scoring_data: Dict[str, Any]) -> Optional[str]:
    raw = (scoring_data or {}).get("buying_role")
    if not is_non_empty(raw):
        return None
    try:
        return ensure_valid_buying_role(str(raw))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class LeadCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    country_region: Optional[str] = None
    source: Optional[str] = None
    score: int = Field(default=0, ge=0, le=100)
    tier: Optional[str] = None
    sales_motion_type: str = "partnership_sales"
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None
    client_name: Optional[str] = None
    partner_commission_structure: Optional[str] = None
    product_category: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    owner_id: Optional[str] = None


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    country_region: Optional[str] = None
    source: Optional[str] = None
    score: Optional[int] = Field(default=None, ge=0, le=100)
    tier: Optional[str] = None
    sales_motion_type: Optional[str] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    partner_name: Optional[str] = None
    product_name: Optional[str] = None
    client_name: Optional[str] = None
    partner_commission_structure: Optional[str] = None
    product_category: Optional[str] = None
    status: Optional[str] = None
    disqualification_reason: Optional[str] = None
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
    amount: float = Field(..., ge=0)
    next_step_at: str = Field(..., min_length=1)
    next_step_note: Optional[str] = None
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None
    estimated_close_date: str = Field(..., min_length=1)
    product_service_type: str = Field(..., min_length=1, max_length=255)


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
        "country_region": lead.country_region,
        "source": lead.source,
        "score": int(lead.score or 0),
        "tier": (lead.tier or "D").strip().upper(),
        "sales_motion_type": lead.sales_motion_type,
        "partner_id": lead.partner_id,
        "product_id": lead.product_id,
        "partner_name": lead.partner_name,
        "product_name": lead.product_name,
        "client_name": lead.client_name,
        "partner_commission_structure": lead.partner_commission_structure,
        "product_category": lead.product_category,
        "status": lead.status,
        "disqualification_reason": lead.disqualification_reason,
        "notes": lead.notes,
        "tags": lead.tags or [],
        "owner_id": lead.owner_id,
        "owner_name": owner_name,
        "assigned_at": dt_to_iso(lead.assigned_at),
        "converted_at": dt_to_iso(lead.converted_at),
        "contact_id": lead.contact_id,
        "touchpoints_count": int(lead.touchpoints_count or 0),
        "last_touchpoint_at": dt_to_iso(lead.last_touchpoint_at),
        "first_touchpoint_at": dt_to_iso(lead.first_touchpoint_at),
        "scoring_data": lead.scoring_data or {},
        "created_at": dt_to_iso(lead.created_at),
        "updated_at": dt_to_iso(lead.updated_at),
    }


def _lead_sla_fields(lead: Lead, sla: Dict[str, int], now) -> Dict[str, Any]:
    created_at = lead.created_at or now

    speed_threshold = int(sla.get("speed_to_lead_minutes") or 15)
    if lead.first_touchpoint_at:
        speed_minutes = (lead.first_touchpoint_at - created_at).total_seconds() / 60.0
        speed_breached = speed_minutes > speed_threshold
    else:
        speed_minutes = (now - created_at).total_seconds() / 60.0
        speed_breached = speed_minutes > speed_threshold and lead.status not in {"converted", "disqualified"}

    cadence_threshold = int(sla.get("lead_cadence_hours") or 24)
    cadence_base = lead.last_touchpoint_at or lead.assigned_at or created_at
    cadence_hours = (now - cadence_base).total_seconds() / 3600.0 if cadence_base else 0.0
    cadence_breached = cadence_hours > cadence_threshold and lead.status not in {"converted", "disqualified"}

    return {
        "speed_to_lead_minutes": round(max(0.0, speed_minutes), 1),
        "speed_to_lead_breached": bool(speed_breached),
        "cadence_hours_since_touch": round(max(0.0, cadence_hours), 1),
        "cadence_breached": bool(cadence_breached),
    }


async def _ensure_new_lead_task(db: AsyncSession, tenant_id: str, lead: Lead, created_by: Optional[str]) -> None:
    due_at = (lead.created_at or now_utc()) + timedelta(minutes=15)
    await upsert_open_task_by_rule(
        db=db,
        tenant_id=tenant_id,
        rule_key=f"lead:first-response:{lead.id}",
        title="First response required",
        description="New lead requires first outreach within SLA window.",
        due_at=due_at,
        owner_id=lead.owner_id or created_by,
        created_by=created_by,
        kind="lead_sla",
        related_type="lead",
        related_id=lead.id,
        metadata={"severity": "warning"},
    )


async def _ensure_contact_for_qualified_lead(
    db: AsyncSession,
    tenant_id: str,
    lead: Lead,
    actor_id: str,
) -> Optional[str]:
    if lead.contact_id:
        existing_contact = (
            await db.execute(select(Contact).where(and_(Contact.id == lead.contact_id, Contact.tenant_id == tenant_id)))
        ).scalar_one_or_none()
        if existing_contact:
            return existing_contact.id

    account_name_input = (lead.company_name or lead.full_name or "").strip()
    if not account_name_input:
        return None

    scoring = _normalize_scoring_enums(lead.scoring_data or {})
    resolved_account = await resolve_account(
        db=db,
        tenant_id=tenant_id,
        account_name=account_name_input,
        actor_id=actor_id,
        domain=_extract_company_domain(lead, scoring),
        industry=(scoring.get("industry") or None),
        company_size=(scoring.get("company_size") or None),
        country=(lead.country_region or scoring.get("country") or None),
        icp_tier=(scoring.get("icp_tier") or lead.tier or None),
    )
    now = now_utc()
    buying_role = _extract_valid_buying_role(scoring)

    contact = Contact(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        full_name=(lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}").strip() or lead.company_name,
        email=lead.email,
        phone=lead.phone,
        company_name=lead.company_name,
        account_id=resolved_account.get("account_id"),
        account_name=resolved_account.get("account_name"),
        job_title=(scoring.get("job_title") or None),
        buying_role=buying_role,
        source=lead.source,
        lifecycle_stage="lead",
        lead_score=int(lead.score or 0),
        lead_tier=(lead.tier or "D").strip().upper(),
        owner_id=lead.owner_id or actor_id,
        tags=list(lead.tags or []),
        status="active",
        converted_from_lead_id=lead.id,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(contact)
    await db.flush()
    lead.contact_id = contact.id
    return contact.id


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
    await run_lead_sla_automations(db, tenant_id=tenant_id, actor_id=user.get("id"), actor_name=user.get("full_name"))
    sla = await get_workspace_sla_config(db, tenant_id)
    now = now_utc()

    filters = [Lead.tenant_id == tenant_id]
    if status:
        filters.append(Lead.status == _normalize_lead_status(status))
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
        payload = _lead_to_dict(lead, owner_name=owner_name)
        payload.update(_lead_sla_fields(lead, sla, now))
        leads.append(payload)

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
    _require_non_finance(user)
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
        "country": "country_region",
        "countryregion": "country_region",
        "region": "country_region",
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
        "clientname": "client_name",
        "partnercommissionstructure": "partner_commission_structure",
        "productcategory": "product_category",
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
        "icptier": "icp_tier",
        "buyingrole": "buying_role",
        "buyingrolestrength": "buying_role_strength",
        "companysizefit": "company_size_fit",
        "engagementscore": "engagement_score",
        "emailopen": "email_open",
        "linkclick": "link_click",
        "demobooked": "demo_booked",
        "industry": "industry",
        "companysize": "company_size",
        "jobtitle": "job_title",
        "budgetrange": "budget_range",
        "authorityidentified": "authority_identified",
        "usecasedefined": "use_case_defined",
        "timelineconfirmed": "timeline_confirmed",
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
            "new_assigned": "new_assigned",
            "newassigned": "new_assigned",
            "working": "working",
            "info_collected": "info_collected",
            "infocollected": "info_collected",
            "unresponsive": "unresponsive",
            "nurture": "nurture",
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
        country_region = (values.get("country_region") or "").strip() or None
        if not company_name:
            skipped += 1
            errors.append({"row": row_index, "error": "Company name is required"})
            continue
        if not country_region:
            skipped += 1
            errors.append({"row": row_index, "error": "Country / region is required"})
            continue
        status = normalize_status(values.get("status") or "")
        source = (values.get("source") or "").strip() or "hubspot_import"

        partner_name = (values.get("partner_name") or "").strip() or None
        product_name = (values.get("product_name") or "").strip() or None
        client_name = (values.get("client_name") or "").strip() or None
        partner_commission_structure = (values.get("partner_commission_structure") or "").strip() or None
        product_category = (values.get("product_category") or "").strip() or None

        raw_motion = (values.get("sales_motion_type") or "").strip()
        sales_motion_type = raw_motion
        if not sales_motion_type:
            sales_motion_type = "partner_sales" if (partner_name or product_name) else "partnership_sales"
        if sales_motion_type not in {"partnership_sales", "partner_sales"}:
            sales_motion_type = "partner_sales" if "partner" in sales_motion_type.lower() else "partnership_sales"

        update_motion_fields = any(
            k in values
            for k in (
                "sales_motion_type",
                "partner_name",
                "product_name",
                "client_name",
                "partner_commission_structure",
                "product_category",
            )
        )

        scoring_data_updates: Dict[str, Any] = {}
        for key in [
            "economic_units",
            "usage_volume",
            "urgency",
            "trigger_event",
            "primary_motivation",
            "decision_role",
            "decision_process_clarity",
            "icp_tier",
            "buying_role",
            "buying_role_strength",
            "company_size_fit",
            "engagement_score",
            "email_open",
            "link_click",
            "demo_booked",
            "industry",
            "company_size",
            "country",
            "job_title",
            "budget_range",
            "authority_identified",
            "use_case_defined",
            "timeline_confirmed",
        ]:
            if key in values:
                scoring_data_updates[key] = values[key]
        try:
            scoring_data_updates = _normalize_scoring_enums(scoring_data_updates)
        except HTTPException as exc:
            skipped += 1
            errors.append({"row": row_index, "error": exc.detail})
            continue

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
                _require_partner_sales_fields(
                    {
                        "client_name": client_name,
                        "partner_commission_structure": partner_commission_structure,
                        "product_category": product_category,
                    }
                )
            except HTTPException as exc:
                skipped += 1
                errors.append({"row": row_index, "error": exc.detail})
                continue
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
            if country_region:
                existing.country_region = country_region
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
                    existing.client_name = client_name
                    existing.partner_commission_structure = partner_commission_structure
                    existing.product_category = product_category
                else:
                    existing.partner_id = None
                    existing.product_id = None
                    existing.partner_name = None
                    existing.product_name = None
                    existing.client_name = None
                    existing.partner_commission_structure = None
                    existing.product_category = None

            if scoring_data_updates:
                merged = dict(existing.scoring_data or {})
                merged.update(scoring_data_updates)
                try:
                    merged = _normalize_scoring_enums(merged)
                except HTTPException as exc:
                    skipped += 1
                    errors.append({"row": row_index, "error": exc.detail})
                    continue
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
            country_region=country_region,
            source=source,
            sales_motion_type=sales_motion_type,
            partner_id=(resolved_partner_product or {}).get("partner_id") if resolved_partner_product else None,
            product_id=(resolved_partner_product or {}).get("product_id") if resolved_partner_product else None,
            partner_name=(resolved_partner_product or {}).get("partner_name") if resolved_partner_product else None,
            product_name=(resolved_partner_product or {}).get("product_name") if resolved_partner_product else None,
            client_name=client_name if sales_motion_type == "partner_sales" else None,
            partner_commission_structure=partner_commission_structure if sales_motion_type == "partner_sales" else None,
            product_category=product_category if sales_motion_type == "partner_sales" else None,
            score=int(score or 0),
            tier=tier,
            scoring_data=scoring_data,
            status=("new_assigned" if status in {"new", "assigned"} else status),
            owner_id=user["id"],
            assigned_at=now,
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
    await run_lead_sla_automations(db, tenant_id=tenant_id, actor_id=user.get("id"), actor_name=user.get("full_name"))
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:200]}


@router.post("", status_code=201)
async def create_lead(
    data: LeadCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_non_finance(user)
    tenant_id = user["tenant_id"]
    now = now_utc()

    if not is_non_empty(data.source):
        raise HTTPException(status_code=400, detail="Lead source is required")
    if not is_non_empty(data.company_name):
        raise HTTPException(status_code=400, detail="Company name is required")
    if not is_non_empty(data.country_region):
        raise HTTPException(status_code=400, detail="Country / region is required")

    tier = (data.tier or calculate_tier(int(data.score or 0))).strip().upper()
    if tier not in VALID_LEAD_TIERS:
        tier = calculate_tier(int(data.score or 0))

    if _is_partner_sales(data.sales_motion_type):
        _require_partner_sales_fields(
            {
                "client_name": data.client_name,
                "partner_commission_structure": data.partner_commission_structure,
                "product_category": data.product_category,
            }
        )

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

    # Lead owner is auto-assigned by default.
    owner_name = None
    owner_id = data.owner_id or user["id"]
    owner_res = await db.execute(
        select(User).where(and_(User.id == owner_id, User.tenant_id == tenant_id))
    )
    owner = owner_res.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=400, detail="Assigned user not found")
    owner_name = f"{owner.first_name} {owner.last_name}".strip()

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name=data.first_name,
        last_name=data.last_name,
        full_name=f"{data.first_name} {data.last_name}".strip(),
        email=data.email,
        phone=data.phone,
        company_name=data.company_name,
        country_region=(data.country_region or None),
        source=data.source or "manual",
        score=int(data.score or 0),
        tier=tier,
        sales_motion_type=(data.sales_motion_type or "partnership_sales").strip(),
        partner_id=resolved.get("partner_id"),
        product_id=resolved.get("product_id"),
        partner_name=resolved.get("partner_name"),
        product_name=resolved.get("product_name"),
        client_name=data.client_name if _is_partner_sales(data.sales_motion_type) else None,
        partner_commission_structure=data.partner_commission_structure if _is_partner_sales(data.sales_motion_type) else None,
        product_category=data.product_category if _is_partner_sales(data.sales_motion_type) else None,
        status="new_assigned",
        notes=data.notes,
        tags=list(data.tags or []),
        owner_id=owner_id,
        assigned_at=now,
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
    await _ensure_new_lead_task(db, tenant_id=tenant_id, lead=lead, created_by=user["id"])
    await run_lead_sla_automations(db, tenant_id=tenant_id, actor_id=user.get("id"), actor_name=user.get("full_name"))

    return _lead_to_dict(lead, owner_name=owner_name)


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_non_finance(user)
    await run_lead_sla_automations(
        db,
        tenant_id=user["tenant_id"],
        actor_id=user.get("id"),
        actor_name=user.get("full_name"),
    )
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

    tenant_id = user["tenant_id"]
    sla = await get_workspace_sla_config(db, tenant_id)
    payload = _lead_to_dict(lead, owner_name=owner_name)
    payload.update(_lead_sla_fields(lead, sla, now_utc()))
    return payload


@router.put("/{lead_id}")
async def update_lead(
    lead_id: str,
    data: LeadUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_non_finance(user)
    tenant_id = user["tenant_id"]
    res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = now_utc()
    scoring_data = dict(lead.scoring_data or {})

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
    if data.country_region is not None:
        lead.country_region = data.country_region
    if data.source is not None:
        lead.source = data.source
    if data.score is not None:
        lead.score = int(data.score or 0)
        lead.tier = (data.tier or calculate_tier(int(data.score or 0))).strip().upper()
    if data.tier is not None:
        lead.tier = data.tier

    status_target = None
    if data.status is not None:
        status_target = _normalize_lead_status(data.status)
        if status_target not in LEAD_QUALIFICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(sorted(LEAD_QUALIFICATION_STATUSES))}",
            )

        current_status = _normalize_lead_status(lead.status or "new")
        if current_status != status_target:
            allowed_next = LEAD_STAGE_TRANSITIONS.get(current_status, set())
            if status_target not in allowed_next:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid stage transition: {current_status} -> {status_target}. Leads cannot skip qualification stages.",
                )

        if status_target == "working" and not lead.owner_id and data.owner_id is None:
            raise HTTPException(status_code=400, detail="Lead owner is required to move to Working")

        if status_target == "info_collected":
            if int(lead.touchpoints_count or 0) <= 0:
                raise HTTPException(status_code=400, detail="Call outcome must be logged before moving to Info Collected")
            call_outcome = str(scoring_data.get("call_outcome") or "").strip()
            if not call_outcome:
                raise HTTPException(status_code=400, detail="Call outcome must be logged before moving to Info Collected")

            discovery_notes = (data.notes if data.notes is not None else lead.notes) or scoring_data.get("discovery_notes")
            if not is_non_empty(discovery_notes):
                raise HTTPException(status_code=400, detail="Discovery notes are required before moving to Info Collected")

            open_lead_task = (
                await db.execute(
                    select(Task.id).where(
                        and_(
                            Task.tenant_id == tenant_id,
                            Task.related_type == "lead",
                            Task.related_id == lead.id,
                            Task.status == "open",
                        )
                    )
                )
            ).scalar_one_or_none()
            if not open_lead_task:
                raise HTTPException(status_code=400, detail="Next-step task is required before moving to Info Collected")

        if status_target == "qualified":
            required_qualification_keys = [
                "budget_range",
                "authority_identified",
                "use_case_defined",
                "timeline_confirmed",
            ]
            missing = [k for k in required_qualification_keys if not is_non_empty(scoring_data.get(k))]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing qualification fields: {', '.join(missing)}",
                )

            if not scoring_inputs_complete(scoring_data):
                raise HTTPException(status_code=400, detail="Lead scoring inputs must be completed before moving to Qualified")

            _validate_qualified_lead_requirements(lead, scoring_data)
            if not is_non_empty(lead.country_region):
                lead.country_region = (scoring_data.get("country") or "").strip() or None
            lead.score = int(max(0, min(100, compute_universal_score(scoring_data, lead.source or "manual"))))
            lead.tier = calculate_tier(int(lead.score or 0))
            contact_id = await _ensure_contact_for_qualified_lead(db, tenant_id=tenant_id, lead=lead, actor_id=user["id"])
            if not contact_id:
                raise HTTPException(status_code=400, detail="Qualified lead must have a valid contact and company account")

        if status_target == "unresponsive" and int(lead.touchpoints_count or 0) < MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE:
            raise HTTPException(
                status_code=400,
                detail=f"At least {MIN_TOUCHPOINTS_BEFORE_UNRESPONSIVE} touchpoints are required before marking Unresponsive",
            )

        if status_target == "disqualified":
            reason = (data.disqualification_reason or lead.disqualification_reason or "").strip()
            if not reason:
                raise HTTPException(status_code=400, detail="disqualification_reason is required when moving to Disqualified")
            lead.disqualification_reason = reason
        elif data.disqualification_reason is not None:
            lead.disqualification_reason = (data.disqualification_reason or "").strip() or None

        lead.status = status_target

    if data.notes is not None:
        lead.notes = data.notes

    if data.owner_id is not None:
        owner = (
            await db.execute(select(User).where(and_(User.id == data.owner_id, User.tenant_id == tenant_id)))
        ).scalar_one_or_none()
        if not owner:
            raise HTTPException(status_code=400, detail="Assigned user not found")
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
            data.client_name is not None,
            data.partner_commission_structure is not None,
            data.product_category is not None,
        ]
    )
    if motion_update_requested:
        next_sales_motion = data.sales_motion_type or lead.sales_motion_type
        payload_values = {
            "client_name": data.client_name if data.client_name is not None else lead.client_name,
            "partner_commission_structure": data.partner_commission_structure if data.partner_commission_structure is not None else lead.partner_commission_structure,
            "product_category": data.product_category if data.product_category is not None else lead.product_category,
        }
        if _is_partner_sales(next_sales_motion):
            _require_partner_sales_fields(payload_values)
        resolved = await resolve_partner_and_product(
            db=db,
            tenant_id=tenant_id,
            sales_motion_type=next_sales_motion,
            partner_id=data.partner_id if data.partner_id is not None else lead.partner_id,
            product_id=data.product_id if data.product_id is not None else lead.product_id,
            partner_name=data.partner_name if data.partner_name is not None else lead.partner_name,
            product_name=data.product_name if data.product_name is not None else lead.product_name,
            actor_id=user["id"],
        )
        lead.sales_motion_type = (next_sales_motion or "partnership_sales").strip()
        lead.partner_id = resolved.get("partner_id")
        lead.product_id = resolved.get("product_id")
        lead.partner_name = resolved.get("partner_name")
        lead.product_name = resolved.get("product_name")
        if _is_partner_sales(next_sales_motion):
            lead.client_name = payload_values["client_name"]
            lead.partner_commission_structure = payload_values["partner_commission_structure"]
            lead.product_category = payload_values["product_category"]
        else:
            lead.client_name = None
            lead.partner_commission_structure = None
            lead.product_category = None

    if _is_partner_sales(lead.sales_motion_type):
        _require_partner_sales_fields(
            {
                "client_name": lead.client_name,
                "partner_commission_structure": lead.partner_commission_structure,
                "product_category": lead.product_category,
            }
        )

    lead.full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
    if not lead.owner_id:
        lead.owner_id = user["id"]
    if not lead.assigned_at:
        lead.assigned_at = now
    if _normalize_lead_status(lead.status) == "new":
        lead.status = "new_assigned"
    lead.scoring_data = scoring_data
    lead.updated_at = now
    await db.flush()
    await _ensure_new_lead_task(db, tenant_id=tenant_id, lead=lead, created_by=user["id"])
    await run_lead_sla_automations(db, tenant_id=tenant_id, actor_id=user.get("id"), actor_name=user.get("full_name"))

    owner_name = None
    if lead.owner_id:
        owner_res = await db.execute(select(User).where(and_(User.id == lead.owner_id, User.tenant_id == tenant_id)))
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
    _require_non_finance(user)
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
    _require_non_finance(user)
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
    lead.status = "new_assigned"
    lead.updated_at = now
    await db.flush()
    await _ensure_new_lead_task(db, tenant_id=tenant_id, lead=lead, created_by=user["id"])

    lead_display = (lead.full_name or f"{lead.first_name or ''} {lead.last_name or ''}").strip() or lead.email or lead.id
    assigned_to = f"{(owner.first_name or '').strip()} {(owner.last_name or '').strip()}".strip() or owner.email
    await create_timeline_event(
        db=db,
        tenant_id=tenant_id,
        event_type="lead_assigned",
        title=f"Lead assigned: {lead_display}",
        actor_id=user["id"],
        actor_name=user.get("full_name"),
        description=f"Assigned to {assigned_to}",
        metadata={
            "lead_id": lead_id,
            "assigned_to_user_id": owner.id,
            "assigned_to_user_email": owner.email,
        },
    )

    sla = await get_workspace_sla_config(db, tenant_id)
    payload = _lead_to_dict(lead, owner_name=f"{owner.first_name} {owner.last_name}".strip())
    payload.update(_lead_sla_fields(lead, sla, now))
    return payload


@router.post("/{lead_id}/touchpoint")
async def log_lead_touchpoint(
    lead_id: str,
    data: LeadTouchpointRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_non_finance(user)
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
    if not lead.first_touchpoint_at:
        lead.first_touchpoint_at = now
    if "call" in (data.activity_type or "").strip().lower():
        scoring_data = dict(lead.scoring_data or {})
        if is_non_empty(data.notes):
            scoring_data["call_outcome"] = data.notes
        lead.scoring_data = scoring_data
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

    sla = await get_workspace_sla_config(db, tenant_id)
    payload = _lead_to_dict(lead, owner_name=owner_name)
    payload.update(_lead_sla_fields(lead, sla, now))
    return payload


@router.post("/{lead_id}/score")
async def score_lead(
    lead_id: str,
    data: LeadScoreRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_non_finance(user)
    tenant_id = user["tenant_id"]
    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    scoring_data = dict(lead.scoring_data or {})
    if data.scoring_data is not None:
        scoring_data.update(data.scoring_data or {})
        scoring_data = _normalize_scoring_enums(scoring_data)

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
    _require_non_finance(user)
    tenant_id = user["tenant_id"]
    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.converted_at:
        raise HTTPException(status_code=400, detail="Lead already converted")
    if _normalize_lead_status(lead.status) != "qualified":
        raise HTTPException(status_code=400, detail="Lead must be Qualified before conversion")
    _validate_qualified_lead_requirements(lead, lead.scoring_data or {})

    now = now_utc()

    company_name = lead.company_name
    account_name_input = company_name or (lead.full_name or "").strip()
    resolved_account = None
    if account_name_input:
        scoring = lead.scoring_data or {}
        resolved_account = await resolve_account(
            db,
            tenant_id,
            account_name_input,
            user["id"],
            domain=_extract_company_domain(lead, scoring),
            industry=(scoring.get("industry") or None),
            company_size=(scoring.get("company_size") or None),
            country=(lead.country_region or scoring.get("country") or None),
            icp_tier=(scoring.get("icp_tier") or lead.tier or None),
        )

    contact_id = str(uuid.uuid4())
    normalized_scoring = _normalize_scoring_enums(lead.scoring_data or {})
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
        job_title=(normalized_scoring.get("job_title") or None),
        buying_role=_extract_valid_buying_role(normalized_scoring),
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
        "job_title": contact.job_title,
        "buying_role": contact.buying_role,
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
    _require_non_finance(user)
    tenant_id = user["tenant_id"]

    lead_res = await db.execute(select(Lead).where(and_(Lead.id == lead_id, Lead.tenant_id == tenant_id)))
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if _normalize_lead_status(lead.status) != "qualified":
        raise HTTPException(status_code=400, detail="Lead must be Qualified before pushing to Sales Pipeline")
    _validate_qualified_lead_requirements(lead, lead.scoring_data or {})

    if not scoring_inputs_complete(lead.scoring_data or {}):
        raise HTTPException(status_code=400, detail="Scoring inputs must be completed before pushing to Sales Pipeline")

    if _is_partner_sales(lead.sales_motion_type):
        _require_partner_sales_fields(
            {
                "client_name": lead.client_name,
                "partner_commission_structure": lead.partner_commission_structure,
                "product_category": lead.product_category,
            }
        )

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
            scoring = lead.scoring_data or {}
            resolved_account = await resolve_account(
                db,
                tenant_id,
                account_name_input,
                user["id"],
                domain=_extract_company_domain(lead, scoring),
                industry=(scoring.get("industry") or None),
                company_size=(scoring.get("company_size") or None),
                country=(lead.country_region or scoring.get("country") or None),
                icp_tier=(scoring.get("icp_tier") or lead.tier or None),
            )

        normalized_scoring = _normalize_scoring_enums(lead.scoring_data or {})
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
            job_title=(normalized_scoring.get("job_title") or None),
            buying_role=_extract_valid_buying_role(normalized_scoring),
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
                scoring = lead.scoring_data or {}
                resolved_account = await resolve_account(
                    db,
                    tenant_id,
                    account_name_input,
                    user["id"],
                    domain=_normalize_domain((contact.email or lead.email or "").split("@", 1)[1] if "@" in (contact.email or lead.email or "") else None),
                    industry=(scoring.get("industry") or None),
                    company_size=(scoring.get("company_size") or None),
                    country=(lead.country_region or scoring.get("country") or None),
                    icp_tier=(scoring.get("icp_tier") or lead.tier or None),
                )
                contact.account_id = resolved_account.get("account_id")
                contact.account_name = resolved_account.get("account_name")
                contact.updated_at = now

    if not contact.account_id:
        raise HTTPException(status_code=400, detail="Qualified lead must be linked to a company account before creating a deal")

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
    amount = float(data.amount)
    lead_score = int(lead.score or 0)
    lead_tier = (lead.tier or calculate_tier(lead_score)).strip().upper()
    if lead_tier not in VALID_LEAD_TIERS:
        lead_tier = calculate_tier(lead_score)

    next_step_at_dt = parse_iso_datetime(data.next_step_at)
    if not next_step_at_dt:
        raise HTTPException(status_code=400, detail="next_step_at must be a valid ISO datetime")
    estimated_close_dt = parse_iso_datetime((data.estimated_close_date or "").strip())
    if not estimated_close_dt:
        raise HTTPException(status_code=400, detail="estimated_close_date must be a valid ISO datetime")
    product_service_type = (data.product_service_type or "").strip()
    if not product_service_type:
        raise HTTPException(status_code=400, detail="product_service_type is required")

    deal = Deal(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=deal_name,
        amount=amount,
        currency="USD",
        status="open",
        origin_lead_id=lead.id,
        contact_id=contact.id,
        account_id=contact.account_id,
        account_name=contact.account_name,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        next_step_at=next_step_at_dt,
        next_step_note=data.next_step_note,
        estimated_close_date=estimated_close_dt,
        product_service_type=product_service_type,
        lead_score=lead_score,
        lead_tier=lead_tier,
        sales_motion_type=lead.sales_motion_type or "partnership_sales",
        partner_id=lead.partner_id,
        product_id=lead.product_id,
        partner_name=lead.partner_name,
        product_name=lead.product_name,
        client_name=lead.client_name,
        partner_commission_structure=lead.partner_commission_structure,
        product_category=lead.product_category,
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
    db.add(
        DealContact(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            deal_id=deal.id,
            contact_id=contact.id,
            is_primary=True,
            role=None,
            created_by=user["id"],
            created_at=now,
            updated_at=now,
        )
    )
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
        "job_title": contact.job_title,
        "buying_role": contact.buying_role,
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
        "origin_lead_id": deal.origin_lead_id,
        "contact_id": deal.contact_id,
        "account_id": deal.account_id,
        "account_name": deal.account_name,
        "pipeline_id": deal.pipeline_id,
        "stage_id": deal.stage_id,
        "next_step_at": dt_to_iso(deal.next_step_at),
        "next_step_note": deal.next_step_note,
        "estimated_close_date": dt_to_iso(deal.estimated_close_date),
        "product_service_type": deal.product_service_type,
        "lead_score": deal.lead_score,
        "lead_tier": deal.lead_tier,
        "sales_motion_type": deal.sales_motion_type,
        "partner_id": deal.partner_id,
        "product_id": deal.product_id,
        "partner_name": deal.partner_name,
        "product_name": deal.product_name,
        "client_name": deal.client_name,
        "partner_commission_structure": deal.partner_commission_structure,
        "product_category": deal.product_category,
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
    _require_non_finance(user)
    tenant_id = user["tenant_id"]
    await run_lead_sla_automations(db, tenant_id=tenant_id, actor_id=user.get("id"), actor_name=user.get("full_name"))

    total = int((await db.execute(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id))).scalar_one() or 0)

    async def _count(where_extra):
        res = await db.execute(
            select(func.count()).select_from(Lead).where(and_(Lead.tenant_id == tenant_id, where_extra))
        )
        return int(res.scalar_one() or 0)

    by_status = {
        "new": await _count(Lead.status == "new"),
        "assigned": await _count(Lead.status == "assigned"),
        "new_assigned": await _count(Lead.status == "new_assigned"),
        "working": await _count(Lead.status == "working"),
        "info_collected": await _count(Lead.status == "info_collected"),
        "unresponsive": await _count(Lead.status == "unresponsive"),
        "nurture": await _count(Lead.status == "nurture"),
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

