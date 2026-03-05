from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import get_workspace_sla_config
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Contact, Deal, Pipeline, PipelineStage

router = APIRouter(tags=["Pipelines"])


def _spiced_complete(spiced: Dict[str, Any]) -> bool:
    required = ["situation", "problem", "implication", "critical_event", "economic_impact", "decision"]
    for k in required:
        v = (spiced or {}).get(k)
        if not (v is not None and str(v).strip()):
            return False
    return True


def _require_admin(user: dict) -> None:
    if user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin access required")


class PipelineStageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    color: str = "#6366F1"
    probability: float = Field(default=0.0, ge=0.0, le=100.0)
    required_fields: List[str] = Field(default_factory=list)
    requires_calculation_complete: bool = False
    display_order: Optional[int] = Field(default=None, ge=0, le=9999)


class PipelineStageUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    probability: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    required_fields: Optional[List[str]] = None
    requires_calculation_complete: Optional[bool] = None
    display_order: Optional[int] = Field(default=None, ge=0, le=9999)


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: bool = False
    display_order: Optional[int] = Field(default=None, ge=0, le=9999)
    stages: Optional[List[PipelineStageCreate]] = None


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    display_order: Optional[int] = Field(default=None, ge=0, le=9999)


class PipelineCloneRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: bool = False


class PipelineStagesReorder(BaseModel):
    stage_ids: List[str] = Field(default_factory=list)


@router.get("/pipelines")
async def list_pipelines(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    pipelines = (
        await db.execute(select(Pipeline).where(Pipeline.tenant_id == tenant_id).order_by(Pipeline.display_order.asc()))
    ).scalars().all()

    result: List[Dict[str, Any]] = []
    for p in pipelines:
        stages = (
            await db.execute(
                select(PipelineStage).where(PipelineStage.pipeline_id == p.id).order_by(PipelineStage.display_order.asc())
            )
        ).scalars().all()
        result.append(
            {
                "id": p.id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "description": p.description,
                "is_default": p.is_default,
                "display_order": p.display_order,
                "created_at": dt_to_iso(p.created_at),
                "updated_at": dt_to_iso(p.updated_at),
                "stages": [
                    {
                        "id": s.id,
                        "pipeline_id": s.pipeline_id,
                        "name": s.name,
                        "color": s.color,
                        "display_order": s.display_order,
                        "probability": float(s.probability or 0.0),
                        "required_fields": list(s.required_fields or []),
                        "requires_calculation_complete": bool(s.requires_calculation_complete),
                        "created_at": dt_to_iso(s.created_at),
                        "updated_at": dt_to_iso(s.updated_at),
                    }
                    for s in stages
                ],
            }
        )

    return {"pipelines": result}


@router.post("/pipelines", status_code=201)
async def create_pipeline(
    data: PipelineCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]
    now = now_utc()

    display_order = data.display_order
    if display_order is None:
        max_res = await db.execute(select(func.max(Pipeline.display_order)).where(Pipeline.tenant_id == tenant_id))
        display_order = int(max_res.scalar_one_or_none() or 0) + 1

    if data.is_default:
        await db.execute(
            update(Pipeline)
            .where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)))
            .values(is_default=False, updated_at=now)
            .execution_options(synchronize_session=False)
        )

    pipeline = Pipeline(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        is_default=bool(data.is_default),
        display_order=int(display_order or 0),
        created_at=now,
        updated_at=now,
    )
    db.add(pipeline)
    await db.flush()

    stages = data.stages or []
    if not stages:
        stages = [
            PipelineStageCreate(
                name="New",
                color="#6366F1",
                probability=0.0,
                required_fields=["next_step_at", "contact_id"],
                requires_calculation_complete=False,
                display_order=0,
            )
        ]

    for idx, s in enumerate(stages):
        order = int(s.display_order) if s.display_order is not None else idx
        db.add(
            PipelineStage(
                id=str(uuid.uuid4()),
                pipeline_id=pipeline.id,
                name=s.name,
                color=s.color or "#6366F1",
                display_order=order,
                probability=float(s.probability or 0.0),
                required_fields=list(s.required_fields or []),
                requires_calculation_complete=bool(s.requires_calculation_complete),
                created_at=now,
                updated_at=now,
            )
        )

    await db.flush()
    return {"id": pipeline.id, "success": True}


@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    data: PipelineUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]
    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    now = now_utc()

    if data.is_default is not None:
        if data.is_default:
            await db.execute(
                update(Pipeline)
                .where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)))
                .values(is_default=False, updated_at=now)
                .execution_options(synchronize_session=False)
            )
            pipeline.is_default = True
        else:
            pipeline.is_default = False

    if data.name is not None:
        pipeline.name = data.name
    if data.description is not None:
        pipeline.description = data.description
    if data.display_order is not None:
        pipeline.display_order = int(data.display_order)

    pipeline.updated_at = now
    await db.flush()
    return {"success": True}


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]
    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    deal_count = (
        await db.execute(
            select(func.count(Deal.id)).where(and_(Deal.tenant_id == tenant_id, Deal.pipeline_id == pipeline_id))
        )
    ).scalar_one()
    if int(deal_count or 0) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete pipeline with existing deals")

    await db.delete(pipeline)
    return {"success": True}


@router.post("/pipelines/{pipeline_id}/clone", status_code=201)
async def clone_pipeline(
    pipeline_id: str,
    data: PipelineCloneRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]

    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    stages = (
        await db.execute(
            select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.display_order.asc())
        )
    ).scalars().all()

    now = now_utc()
    max_res = await db.execute(select(func.max(Pipeline.display_order)).where(Pipeline.tenant_id == tenant_id))
    next_order = int(max_res.scalar_one_or_none() or 0) + 1

    if data.is_default:
        await db.execute(
            update(Pipeline)
            .where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)))
            .values(is_default=False, updated_at=now)
            .execution_options(synchronize_session=False)
        )

    new_pipeline = Pipeline(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=data.name,
        description=data.description if data.description is not None else pipeline.description,
        is_default=bool(data.is_default),
        display_order=next_order,
        created_at=now,
        updated_at=now,
    )
    db.add(new_pipeline)
    await db.flush()

    for s in stages:
        db.add(
            PipelineStage(
                id=str(uuid.uuid4()),
                pipeline_id=new_pipeline.id,
                name=s.name,
                color=s.color,
                display_order=int(s.display_order or 0),
                probability=float(s.probability or 0.0),
                required_fields=list(s.required_fields or []),
                requires_calculation_complete=bool(s.requires_calculation_complete),
                created_at=now,
                updated_at=now,
            )
        )

    await db.flush()
    return {"id": new_pipeline.id, "success": True}


@router.post("/pipelines/{pipeline_id}/stages", status_code=201)
async def create_pipeline_stage(
    pipeline_id: str,
    data: PipelineStageCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]
    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    now = now_utc()
    order = data.display_order
    if order is None:
        max_res = await db.execute(select(func.max(PipelineStage.display_order)).where(PipelineStage.pipeline_id == pipeline_id))
        order = int(max_res.scalar_one_or_none() or 0) + 1

    stage = PipelineStage(
        id=str(uuid.uuid4()),
        pipeline_id=pipeline_id,
        name=data.name,
        color=data.color or "#6366F1",
        display_order=int(order or 0),
        probability=float(data.probability or 0.0),
        required_fields=list(data.required_fields or []),
        requires_calculation_complete=bool(data.requires_calculation_complete),
        created_at=now,
        updated_at=now,
    )
    db.add(stage)
    await db.flush()
    return {"id": stage.id, "success": True}


@router.put("/pipelines/{pipeline_id}/stages/{stage_id}")
async def update_pipeline_stage(
    pipeline_id: str,
    stage_id: str,
    data: PipelineStageUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    stage = (
        await db.execute(select(PipelineStage).where(and_(PipelineStage.id == stage_id, PipelineStage.pipeline_id == pipeline_id)))
    ).scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    now = now_utc()
    if data.name is not None:
        stage.name = data.name
    if data.color is not None:
        stage.color = data.color
    if data.display_order is not None:
        stage.display_order = int(data.display_order)
    if data.probability is not None:
        stage.probability = float(data.probability)
    if data.required_fields is not None:
        stage.required_fields = list(data.required_fields or [])
    if data.requires_calculation_complete is not None:
        stage.requires_calculation_complete = bool(data.requires_calculation_complete)
    stage.updated_at = now
    await db.flush()
    return {"success": True}


@router.delete("/pipelines/{pipeline_id}/stages/{stage_id}")
async def delete_pipeline_stage(
    pipeline_id: str,
    stage_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    stage = (
        await db.execute(select(PipelineStage).where(and_(PipelineStage.id == stage_id, PipelineStage.pipeline_id == pipeline_id)))
    ).scalar_one_or_none()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    deal_count = (
        await db.execute(select(func.count(Deal.id)).where(and_(Deal.tenant_id == user["tenant_id"], Deal.stage_id == stage_id)))
    ).scalar_one()
    if int(deal_count or 0) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete stage with existing deals")

    await db.delete(stage)
    return {"success": True}


@router.post("/pipelines/{pipeline_id}/stages/reorder")
async def reorder_pipeline_stages(
    pipeline_id: str,
    data: PipelineStagesReorder,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    tenant_id = user["tenant_id"]
    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    stage_ids = [s for s in (data.stage_ids or []) if s]
    if not stage_ids:
        raise HTTPException(status_code=400, detail="stage_ids is required")

    stages = (
        await db.execute(select(PipelineStage).where(and_(PipelineStage.pipeline_id == pipeline_id, PipelineStage.id.in_(stage_ids))))
    ).scalars().all()
    stages_map = {s.id: s for s in stages}
    missing = [s for s in stage_ids if s not in stages_map]
    if missing:
        raise HTTPException(status_code=400, detail="Invalid stage_ids for pipeline")

    now = now_utc()
    for order, stage_id in enumerate(stage_ids):
        stage = stages_map[stage_id]
        stage.display_order = order
        stage.updated_at = now

    await db.flush()
    return {"success": True}


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    stages = (
        await db.execute(
            select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.display_order.asc())
        )
    ).scalars().all()

    return {
        "id": pipeline.id,
        "tenant_id": pipeline.tenant_id,
        "name": pipeline.name,
        "description": pipeline.description,
        "is_default": pipeline.is_default,
        "display_order": pipeline.display_order,
        "created_at": dt_to_iso(pipeline.created_at),
        "updated_at": dt_to_iso(pipeline.updated_at),
        "stages": [
            {
                "id": s.id,
                "pipeline_id": s.pipeline_id,
                "name": s.name,
                "color": s.color,
                "display_order": s.display_order,
                "probability": float(s.probability or 0.0),
                "required_fields": list(s.required_fields or []),
                "requires_calculation_complete": bool(s.requires_calculation_complete),
            }
            for s in stages
        ],
    }


@router.get("/pipelines/{pipeline_id}/kanban")
async def get_pipeline_kanban(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    is_finance = (user.get("role") or "").strip().lower() == "finance"
    sla = await get_workspace_sla_config(db, tenant_id)
    now = now_utc()
    cadence_threshold = int(sla.get("deal_cadence_hours") or 72)
    pipeline = (
        await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    stages = (
        await db.execute(
            select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.display_order.asc())
        )
    ).scalars().all()

    deal_filters = [Deal.pipeline_id == pipeline_id, Deal.tenant_id == tenant_id]
    if is_finance:
        deal_filters.append(Deal.status == "won")
    deals = (await db.execute(select(Deal).where(and_(*deal_filters)))).scalars().all()

    contact_ids = [d.contact_id for d in deals if d.contact_id]
    contacts_map: Dict[str, Contact] = {}
    if contact_ids:
        contacts = (
            await db.execute(select(Contact).where(and_(Contact.tenant_id == tenant_id, Contact.id.in_(contact_ids))))
        ).scalars().all()
        contacts_map = {c.id: c for c in contacts}

    columns: List[Dict[str, Any]] = []
    total_value = 0.0
    total_deals = 0
    for stage in stages:
        stage_deals = [d for d in deals if d.stage_id == stage.id]
        stage_total = sum(float(d.amount or 0.0) for d in stage_deals)
        total_value += stage_total
        total_deals += len(stage_deals)

        column_deals: List[Dict[str, Any]] = []
        for deal in stage_deals:
            contact = contacts_map.get(deal.contact_id) if deal.contact_id else None
            contact_name = None
            if contact:
                contact_name = (contact.full_name or f"{contact.first_name or ''} {contact.last_name or ''}").strip() or None

            cadence_base = deal.last_touchpoint_at or deal.created_at or now
            cadence_hours = (now - cadence_base).total_seconds() / 3600.0 if cadence_base else 0.0
            cadence_breached = cadence_hours > cadence_threshold and (deal.status or "open") == "open"

            column_deals.append(
                {
                    "id": deal.id,
                    "tenant_id": deal.tenant_id,
                    "name": deal.name,
                    "amount": float(deal.amount or 0.0),
                    "currency": deal.currency,
                    "status": deal.status,
                    "origin_lead_id": deal.origin_lead_id,
                    "contact_id": deal.contact_id,
                    "contact_name": contact_name,
                    "contact_email": contact.email if contact else None,
                    "account_id": deal.account_id,
                    "account_name": deal.account_name,
                    "pipeline_id": deal.pipeline_id,
                    "stage_id": deal.stage_id,
                    "stage_name": stage.name,
                    "next_step_at": dt_to_iso(deal.next_step_at),
                    "next_step_note": deal.next_step_note,
                    "estimated_close_date": dt_to_iso(deal.estimated_close_date),
                    "product_service_type": deal.product_service_type,
                    "last_touchpoint_at": dt_to_iso(deal.last_touchpoint_at),
                    "cadence_hours_since_touch": round(max(0.0, cadence_hours), 1),
                    "cadence_breached": bool(cadence_breached),
                    "lead_score": int(deal.lead_score or 0),
                    "lead_tier": deal.lead_tier,
                    "sales_motion_type": deal.sales_motion_type,
                    "partner_id": deal.partner_id,
                    "product_id": deal.product_id,
                    "partner_name": deal.partner_name,
                    "product_name": deal.product_name,
                    "client_name": deal.client_name,
                    "partner_commission_structure": deal.partner_commission_structure,
                    "product_category": deal.product_category,
                    "spiced": deal.spiced or {},
                    "spiced_complete": _spiced_complete(deal.spiced or {}),
                    "demo_title": deal.demo_title,
                    "demo_type": deal.demo_type,
                    "demo_status": deal.demo_status,
                    "demo_scheduled_at": dt_to_iso(deal.demo_scheduled_at),
                    "demo_duration_minutes": int(deal.demo_duration_minutes or 30),
                    "demo_meet_url": deal.demo_meet_url,
                    "demo_calendar_url": deal.demo_calendar_url,
                    "demo_completed_at": dt_to_iso(deal.demo_completed_at),
                    "demo_notes": deal.demo_notes,
                    "proposal_value": float(deal.proposal_value) if deal.proposal_value is not None else None,
                    "commercial_summary_url": deal.commercial_summary_url,
                    "stakeholder_map": deal.stakeholder_map or {},
                    "contract_final_value": float(deal.contract_final_value) if deal.contract_final_value is not None else None,
                    "payment_terms": deal.payment_terms,
                    "deal_locked": bool(deal.deal_locked),
                    "at_risk": bool(deal.at_risk),
                    "owner_id": deal.owner_id,
                    "handoff_status": deal.handoff_status,
                    "created_at": dt_to_iso(deal.created_at),
                    "updated_at": dt_to_iso(deal.updated_at),
                }
            )

        columns.append(
            {
                "id": stage.id,
                "name": stage.name,
                "color": stage.color or "#6366F1",
                "display_order": stage.display_order,
                "probability": float(stage.probability or 0.0),
                "required_fields": list(stage.required_fields or []),
                "requires_calculation_complete": bool(stage.requires_calculation_complete),
                "deals": column_deals,
                "total_value": round(float(stage_total), 2),
                "deal_count": len(column_deals),
            }
        )

    return {
        "pipeline": {
            "id": pipeline.id,
            "tenant_id": pipeline.tenant_id,
            "name": pipeline.name,
            "description": pipeline.description,
            "is_default": pipeline.is_default,
            "display_order": pipeline.display_order,
        },
        "columns": columns,
        "total_deals": total_deals,
        "total_value": round(float(total_value), 2),
    }

