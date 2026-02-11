from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.utils import now_utc, normalize_lower, scoring_inputs_complete
from app.pg_models.models import (
    Account,
    CalculationDefinition,
    CalculationResult,
    Deal,
    DealHandoff,
    Partner,
    Pipeline,
    PipelineStage,
    Product,
    Task,
    TimelineEvent,
)


async def resolve_account(
    db: AsyncSession,
    tenant_id: str,
    account_name: str,
    actor_id: Optional[str],
) -> Dict[str, Optional[str]]:
    name = " ".join((account_name or "").strip().split())
    if not name:
        raise HTTPException(status_code=400, detail="account_name is required")

    name_lower = normalize_lower(name)
    existing = await db.execute(
        select(Account).where(and_(Account.tenant_id == tenant_id, Account.name_lower == name_lower))
    )
    account = existing.scalar_one_or_none()
    if account:
        return {"account_id": account.id, "account_name": account.name or name}

    new_account = Account(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        name_lower=name_lower,
        is_active=True,
        created_by=actor_id,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(new_account)
    await db.flush()
    return {"account_id": new_account.id, "account_name": new_account.name}


async def resolve_partner_and_product(
    db: AsyncSession,
    tenant_id: str,
    sales_motion_type: str,
    partner_id: Optional[str],
    product_id: Optional[str],
    partner_name: Optional[str],
    product_name: Optional[str],
    actor_id: Optional[str],
) -> Dict[str, Optional[str]]:
    sales_motion_type = (sales_motion_type or "partnership_sales").strip()
    if sales_motion_type not in {"partnership_sales", "partner_sales"}:
        raise HTTPException(status_code=400, detail="Invalid sales_motion_type")

    if sales_motion_type == "partnership_sales":
        return {"partner_id": None, "partner_name": None, "product_id": None, "product_name": None}

    # Partner
    partner: Optional[Partner] = None
    if partner_id:
        partner_res = await db.execute(
            select(Partner).where(and_(Partner.id == partner_id, Partner.tenant_id == tenant_id))
        )
        partner = partner_res.scalar_one_or_none()
        if not partner:
            raise HTTPException(status_code=400, detail="Partner not found")
        partner_name = partner.name
    else:
        name = (partner_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="partner_name is required for partner_sales")
        name_lower = normalize_lower(name)
        partner_res = await db.execute(
            select(Partner).where(and_(Partner.tenant_id == tenant_id, Partner.name_lower == name_lower))
        )
        partner = partner_res.scalar_one_or_none()
        if not partner:
            partner = Partner(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=name,
                name_lower=name_lower,
                is_active=True,
                created_by=actor_id,
                created_at=now_utc(),
                updated_at=now_utc(),
            )
            db.add(partner)
            await db.flush()
        partner_id = partner.id
        partner_name = partner.name

    # Product
    product: Optional[Product] = None
    if product_id:
        product_res = await db.execute(
            select(Product).where(and_(Product.id == product_id, Product.tenant_id == tenant_id))
        )
        product = product_res.scalar_one_or_none()
        if not product or product.partner_id != partner_id:
            raise HTTPException(status_code=400, detail="Product not found for partner")
        product_name = product.name
    else:
        name = (product_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="product_name is required for partner_sales")
        name_lower = normalize_lower(name)
        product_res = await db.execute(
            select(Product).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.partner_id == partner_id,
                    Product.name_lower == name_lower,
                )
            )
        )
        product = product_res.scalar_one_or_none()
        if not product:
            product = Product(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                partner_id=partner_id,
                name=name,
                name_lower=name_lower,
                is_active=True,
                created_by=actor_id,
                created_at=now_utc(),
                updated_at=now_utc(),
            )
            db.add(product)
            await db.flush()
        product_id = product.id
        product_name = product.name

    return {
        "partner_id": partner_id,
        "partner_name": partner_name,
        "product_id": product_id,
        "product_name": product_name,
    }


async def create_timeline_event(
    db: AsyncSession,
    tenant_id: str,
    event_type: str,
    title: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    deal_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    description: Optional[str] = None,
    visibility: str = "internal_only",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    event = TimelineEvent(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        event_type=event_type,
        title=title,
        description=description,
        actor_id=actor_id,
        actor_name=actor_name,
        deal_id=deal_id,
        contact_id=contact_id,
        visibility=visibility,
        meta=metadata or {},
        created_at=now_utc(),
    )
    db.add(event)
    await db.flush()
    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "deal_id": event.deal_id,
        "contact_id": event.contact_id,
        "visibility": event.visibility,
        "metadata": event.meta or {},
        "created_at": event.created_at.isoformat(),
    }


async def complete_open_next_step_tasks_for_deal(
    db: AsyncSession,
    tenant_id: str,
    deal_id: str,
    completed_by: Optional[str],
) -> int:
    now = now_utc()
    result = await db.execute(
        update(Task)
        .where(
            and_(
                Task.tenant_id == tenant_id,
                Task.related_type == "deal",
                Task.related_id == deal_id,
                Task.kind == "next_step",
                Task.status == "open",
            )
        )
        .values(status="completed", completed_at=now, completed_by=completed_by, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)


async def upsert_open_next_step_task_for_deal(
    db: AsyncSession,
    tenant_id: str,
    deal_id: str,
    due_at: datetime,
    owner_id: Optional[str],
    created_by: Optional[str],
    note: Optional[str] = None,
) -> None:
    existing_res = await db.execute(
        select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.related_type == "deal",
                Task.related_id == deal_id,
                Task.kind == "next_step",
                Task.status == "open",
            )
        )
    )
    task = existing_res.scalar_one_or_none()
    now = now_utc()
    if task:
        task.due_at = due_at
        task.owner_id = owner_id
        task.description = note
        task.updated_at = now
        return

    new_task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title="Next Step",
        description=note,
        status="open",
        kind="next_step",
        due_at=due_at,
        owner_id=owner_id,
        related_type="deal",
        related_id=deal_id,
        created_by=created_by,
        meta={},
        created_at=now,
        updated_at=now,
    )
    db.add(new_task)
    await db.flush()


async def get_default_pipeline_and_stage(
    db: AsyncSession,
    tenant_id: str,
    pipeline_id: Optional[str],
    stage_id: Optional[str],
    sales_motion_type: Optional[str] = None,
    partner_id: Optional[str] = None,
) -> Dict[str, Any]:
    pipeline: Optional[Pipeline] = None
    if pipeline_id:
        pipeline_res = await db.execute(select(Pipeline).where(and_(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)))
        pipeline = pipeline_res.scalar_one_or_none()
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
    else:
        if (sales_motion_type or "").strip() == "partner_sales" and partner_id:
            partner = (
                await db.execute(select(Partner).where(and_(Partner.tenant_id == tenant_id, Partner.id == partner_id)))
            ).scalar_one_or_none()
            if partner and partner.default_pipeline_id:
                pipeline = (
                    await db.execute(
                        select(Pipeline).where(and_(Pipeline.tenant_id == tenant_id, Pipeline.id == partner.default_pipeline_id))
                    )
                ).scalar_one_or_none()

        pipeline_res = await db.execute(
            select(Pipeline).where(and_(Pipeline.tenant_id == tenant_id, Pipeline.is_default == True)).limit(1)
        )
        pipeline = pipeline or pipeline_res.scalar_one_or_none()
        if not pipeline:
            pipeline_res = await db.execute(select(Pipeline).where(Pipeline.tenant_id == tenant_id).limit(1))
            pipeline = pipeline_res.scalar_one_or_none()
        if not pipeline:
            raise HTTPException(status_code=400, detail="No pipelines configured for tenant")

    stage: Optional[PipelineStage] = None
    if stage_id:
        stage_res = await db.execute(
            select(PipelineStage).where(and_(PipelineStage.id == stage_id, PipelineStage.pipeline_id == pipeline.id))
        )
        stage = stage_res.scalar_one_or_none()
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
    else:
        stage_res = await db.execute(
            select(PipelineStage).where(PipelineStage.pipeline_id == pipeline.id).order_by(PipelineStage.display_order.asc()).limit(1)
        )
        stage = stage_res.scalar_one_or_none()
        if not stage:
            raise HTTPException(status_code=400, detail="No stages configured for pipeline")

    return {"pipeline": pipeline, "stage": stage}


async def get_active_calculation_definition(db: AsyncSession, tenant_id: str) -> Optional[CalculationDefinition]:
    res = await db.execute(
        select(CalculationDefinition)
        .where(and_(CalculationDefinition.tenant_id == tenant_id, CalculationDefinition.is_active == True))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_calculation_result(
    db: AsyncSession, deal_id: str, definition_id: str
) -> Optional[CalculationResult]:
    res = await db.execute(
        select(CalculationResult).where(and_(CalculationResult.deal_id == deal_id, CalculationResult.definition_id == definition_id))
    )
    return res.scalar_one_or_none()


async def get_or_create_deal_handoff(
    db: AsyncSession,
    tenant_id: str,
    deal_id: str,
    actor_id: Optional[str],
) -> DealHandoff:
    res = await db.execute(
        select(DealHandoff).where(and_(DealHandoff.tenant_id == tenant_id, DealHandoff.deal_id == deal_id))
    )
    handoff = res.scalar_one_or_none()
    if handoff:
        return handoff

    now = now_utc()
    handoff = DealHandoff(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        deal_id=deal_id,
        delivery_owner_id=None,
        kickoff_at=None,
        checklist={},
        notes=None,
        status="pending",
        completed_at=None,
        created_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(handoff)
    await db.flush()
    return handoff


def handoff_complete(delivery_owner_id: Optional[str], kickoff_at: Any, checklist: Dict[str, Any]) -> bool:
    if not delivery_owner_id:
        return False
    if not kickoff_at:
        return False

    required_keys = [
        "spiced_summary",
        "gap_analysis",
        "proposal",
        "contract",
        "risk_notes",
        "kickoff_readiness_checklist",
    ]
    checklist = checklist or {}
    return all(bool(checklist.get(k)) for k in required_keys)


async def sync_deal_handoff_status(
    db: AsyncSession,
    tenant_id: str,
    deal: Deal,
    handoff: DealHandoff,
    actor: Dict[str, Any],
) -> None:
    complete = handoff_complete(handoff.delivery_owner_id, handoff.kickoff_at, handoff.checklist or {})
    now = now_utc()

    if complete and handoff.status != "completed":
        handoff.status = "completed"
        handoff.completed_at = now
        handoff.updated_at = now
        deal.handoff_status = "completed"
        deal.handoff_completed_at = now
        deal.updated_at = now
        await create_timeline_event(
            db=db,
            tenant_id=tenant_id,
            event_type="handoff_completed",
            title="Delivery handoff completed",
            actor_id=actor.get("id"),
            actor_name=actor.get("full_name"),
            deal_id=deal.id,
            metadata={"handoff_id": handoff.id},
        )
        return

    if not complete and handoff.status == "completed":
        handoff.status = "pending"
        handoff.completed_at = None
        handoff.updated_at = now
        deal.handoff_status = "pending"
        deal.handoff_completed_at = None
        deal.updated_at = now
