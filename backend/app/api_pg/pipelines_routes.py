from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import Contact, Deal, Pipeline, PipelineStage

router = APIRouter(tags=["Pipelines"])


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

    deals = (
        await db.execute(select(Deal).where(and_(Deal.pipeline_id == pipeline_id, Deal.tenant_id == tenant_id)))
    ).scalars().all()

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
            column_deals.append(
                {
                    "id": deal.id,
                    "tenant_id": deal.tenant_id,
                    "name": deal.name,
                    "amount": float(deal.amount or 0.0),
                    "currency": deal.currency,
                    "status": deal.status,
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
                    "lead_score": int(deal.lead_score or 0),
                    "lead_tier": deal.lead_tier,
                    "sales_motion_type": deal.sales_motion_type,
                    "partner_id": deal.partner_id,
                    "product_id": deal.product_id,
                    "partner_name": deal.partner_name,
                    "product_name": deal.product_name,
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

