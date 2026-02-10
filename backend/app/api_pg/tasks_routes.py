from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc, parse_iso_datetime
from app.core.database import get_db
from app.pg_models.models import Task, User

router = APIRouter(tags=["Tasks"])

VALID_TASK_STATUSES = {"open", "completed", "canceled"}
VALID_TASK_RELATED_TYPES = {"deal", "lead", "contact", "account"}


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    due_at: str = Field(..., min_length=1)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[str] = None
    kind: str = "manual"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    due_at: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str = "open",
    owner_id: Optional[str] = None,
    related_type: Optional[str] = None,
    related_id: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    filters: List[Any] = [Task.tenant_id == tenant_id]

    status_norm = (status or "open").strip().lower()
    if status_norm != "all":
        if status_norm not in VALID_TASK_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status. Use open|completed|canceled|all")
        filters.append(Task.status == status_norm)

    if owner_id:
        filters.append(Task.owner_id == owner_id)

    if related_type:
        rt = related_type.strip().lower()
        if rt not in VALID_TASK_RELATED_TYPES:
            raise HTTPException(status_code=400, detail="Invalid related_type")
        filters.append(Task.related_type == rt)
    if related_id:
        filters.append(Task.related_id == related_id)

    if due_after:
        after_dt = parse_iso_datetime(due_after)
        if not after_dt:
            raise HTTPException(status_code=400, detail="Invalid due_after")
        filters.append(Task.due_at >= after_dt)
    if due_before:
        before_dt = parse_iso_datetime(due_before)
        if not before_dt:
            raise HTTPException(status_code=400, detail="Invalid due_before")
        filters.append(Task.due_at <= before_dt)

    total_res = await db.execute(select(func.count()).select_from(Task).where(and_(*filters)))
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Task)
        .where(and_(*filters))
        .order_by(Task.due_at.asc().nulls_last(), Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tasks = (await db.execute(stmt)).scalars().all()

    owner_ids = list({t.owner_id for t in tasks if t.owner_id})
    owners_map: Dict[str, User] = {}
    if owner_ids:
        owners = (
            await db.execute(select(User).where(and_(User.tenant_id == tenant_id, User.id.in_(owner_ids))))
        ).scalars().all()
        owners_map = {o.id: o for o in owners}

    resp_tasks: List[Dict[str, Any]] = []
    for t in tasks:
        owner = owners_map.get(t.owner_id)
        owner_name = None
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip() or owner.email
        resp_tasks.append(
            {
                "id": t.id,
                "tenant_id": t.tenant_id,
                "title": t.title,
                "description": t.description,
                "due_at": dt_to_iso(t.due_at),
                "owner_id": t.owner_id,
                "owner_name": owner_name,
                "status": t.status,
                "kind": t.kind,
                "related_type": t.related_type,
                "related_id": t.related_id,
                "completed_at": dt_to_iso(t.completed_at),
                "completed_by": t.completed_by,
                "created_at": dt_to_iso(t.created_at),
                "updated_at": dt_to_iso(t.updated_at),
            }
        )

    return {"tasks": resp_tasks, "total": total, "page": page, "page_size": page_size}


@router.post("/tasks", status_code=201)
async def create_task(
    data: TaskCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    owner_id = data.owner_id or user["id"]
    owner = (
        await db.execute(select(User).where(and_(User.id == owner_id, User.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=400, detail="Owner not found")

    related_type = (data.related_type or "").strip().lower() if data.related_type else None
    if related_type and related_type not in VALID_TASK_RELATED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid related_type")
    if related_type and not data.related_id:
        raise HTTPException(status_code=400, detail="related_id is required when related_type is provided")

    due_dt = parse_iso_datetime(data.due_at)
    if not due_dt:
        raise HTTPException(status_code=400, detail="due_at must be a valid ISO datetime")

    now = now_utc()
    task = Task(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=data.title,
        description=data.description,
        due_at=due_dt,
        owner_id=owner_id,
        created_by=user["id"],
        status="open",
        kind=(data.kind or "manual").strip().lower(),
        related_type=related_type,
        related_id=data.related_id,
        completed_at=None,
        completed_by=None,
        metadata={},
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.flush()

    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "title": task.title,
        "description": task.description,
        "due_at": dt_to_iso(task.due_at),
        "owner_id": task.owner_id,
        "owner_name": f"{owner.first_name} {owner.last_name}".strip() or owner.email,
        "status": task.status,
        "kind": task.kind,
        "related_type": task.related_type,
        "related_id": task.related_id,
        "created_at": dt_to_iso(task.created_at),
        "updated_at": dt_to_iso(task.updated_at),
    }


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    task = (
        await db.execute(select(Task).where(and_(Task.id == task_id, Task.tenant_id == tenant_id)))
    ).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = now_utc()
    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.due_at is not None:
        due_dt = parse_iso_datetime(data.due_at)
        if not due_dt:
            raise HTTPException(status_code=400, detail="due_at must be a valid ISO datetime")
        task.due_at = due_dt
    if data.status is not None:
        status_norm = (data.status or "").strip().lower()
        if status_norm not in VALID_TASK_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        task.status = status_norm
        if status_norm == "completed":
            task.completed_at = now
            task.completed_by = user["id"]
        elif status_norm == "open":
            task.completed_at = None
            task.completed_by = None

    task.updated_at = now
    await db.flush()

    owner_name = None
    if task.owner_id:
        owner = (
            await db.execute(select(User).where(and_(User.id == task.owner_id, User.tenant_id == tenant_id)))
        ).scalar_one_or_none()
        if owner:
            owner_name = f"{owner.first_name} {owner.last_name}".strip() or owner.email

    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "title": task.title,
        "description": task.description,
        "due_at": dt_to_iso(task.due_at),
        "owner_id": task.owner_id,
        "owner_name": owner_name,
        "status": task.status,
        "kind": task.kind,
        "related_type": task.related_type,
        "related_id": task.related_id,
        "completed_at": dt_to_iso(task.completed_at),
        "completed_by": task.completed_by,
        "created_at": dt_to_iso(task.created_at),
        "updated_at": dt_to_iso(task.updated_at),
    }

