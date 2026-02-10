from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Workflow

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

