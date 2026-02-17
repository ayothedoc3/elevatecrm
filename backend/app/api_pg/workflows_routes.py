from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.workflow_engine import trigger_workflow_by_id
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Workflow, WorkflowRun

router = APIRouter(prefix="/workflows", tags=["Workflows"])


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "draft"
    trigger_type: str = "form_submitted"
    trigger_config: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None


class TriggerWorkflowRequest(BaseModel):
    trigger_data: Dict[str, Any] = {}
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None


def _workflow_to_dict(w: Workflow) -> dict:
    return {
        "id": w.id,
        "tenant_id": w.tenant_id,
        "name": w.name,
        "description": w.description,
        "status": w.status,
        "trigger_type": w.trigger_type,
        "trigger_config": w.trigger_config or {},
        "actions": list(w.actions or []),
        "total_runs": int(w.total_runs or 0),
        "successful_runs": int(w.successful_runs or 0),
        "failed_runs": int(w.failed_runs or 0),
        "created_by_id": w.created_by,
        "created_at": dt_to_iso(w.created_at),
        "updated_at": dt_to_iso(w.updated_at),
    }


def _run_to_dict(run: WorkflowRun, workflow_name: Optional[str] = None) -> dict:
    return {
        "id": run.id,
        "tenant_id": run.tenant_id,
        "workflow_id": run.workflow_id,
        "workflow_name": workflow_name,
        "status": run.status,
        "trigger_type": run.trigger_type,
        "trigger_data": run.trigger_data or {},
        "contact_id": run.contact_id,
        "deal_id": run.deal_id,
        "error_message": run.error,
        "started_at": dt_to_iso(run.started_at),
        "completed_at": dt_to_iso(run.completed_at),
    }


@router.get("")
async def list_workflows(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Workflow).where(Workflow.tenant_id == user["tenant_id"]).order_by(Workflow.created_at.desc())
    )
    workflows = res.scalars().all()
    return {"workflows": [_workflow_to_dict(w) for w in workflows], "total": len(workflows)}


@router.post("", status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    workflow = Workflow(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        description=data.description,
        status=data.status,
        trigger_type=data.trigger_type,
        trigger_config=data.trigger_config or {},
        actions=list(data.actions or []),
        total_runs=0,
        successful_runs=0,
        failed_runs=0,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(workflow)
    await db.flush()
    return _workflow_to_dict(workflow)


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.tenant_id == user["tenant_id"]))
    )
    workflow = res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if "actions" in updates:
        updates["actions"] = list(updates["actions"] or [])
    if "trigger_config" in updates:
        updates["trigger_config"] = updates["trigger_config"] or {}
    updates["updated_at"] = now_utc()

    await db.execute(
        update(Workflow)
        .where(and_(Workflow.id == workflow_id, Workflow.tenant_id == user["tenant_id"]))
        .values(**updates)
    )
    return {"success": True}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.tenant_id == user["tenant_id"]))
    )
    workflow = res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(workflow)
    return {"success": True}


@router.post("/{workflow_id}/trigger")
async def trigger_workflow(
    workflow_id: str,
    data: TriggerWorkflowRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = await trigger_workflow_by_id(
        db=db,
        tenant_id=user["tenant_id"],
        workflow_id=workflow_id,
        trigger_type="manual",
        trigger_data=data.trigger_data or {},
        contact_id=data.contact_id,
        deal_id=data.deal_id,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found or not active")

    wf_res = await db.execute(
        select(Workflow).where(and_(Workflow.id == run.workflow_id, Workflow.tenant_id == user["tenant_id"]))
    )
    workflow = wf_res.scalar_one_or_none()
    return _run_to_dict(run, workflow_name=workflow.name if workflow else None)


@router.get("/{workflow_id}/runs")
async def list_workflow_runs(
    workflow_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workflow_res = await db.execute(
        select(Workflow).where(and_(Workflow.id == workflow_id, Workflow.tenant_id == user["tenant_id"]))
    )
    workflow = workflow_res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    where = [WorkflowRun.tenant_id == user["tenant_id"], WorkflowRun.workflow_id == workflow_id]
    total_res = await db.execute(select(func.count(WorkflowRun.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    runs_res = await db.execute(
        select(WorkflowRun)
        .where(and_(*where))
        .order_by(WorkflowRun.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    runs = runs_res.scalars().all()
    return {
        "runs": [_run_to_dict(run, workflow_name=workflow.name) for run in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

