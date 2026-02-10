from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import ListMember, MarketingList

router = APIRouter(prefix="/lists", tags=["Marketing Lists"])


class ListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: str = "static"  # static | smart
    filters: Optional[Dict[str, Any]] = None


class ListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


def _list_to_dict(lst: MarketingList, contact_count: int) -> dict:
    return {
        "id": lst.id,
        "tenant_id": lst.tenant_id,
        "name": lst.name,
        "description": lst.description,
        "type": lst.type,
        "filters": lst.filters,
        "created_by": lst.created_by,
        "created_at": dt_to_iso(lst.created_at),
        "updated_at": dt_to_iso(lst.updated_at),
        "contact_count": int(contact_count),
    }


@router.get("")
async def get_lists(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = [MarketingList.tenant_id == user["tenant_id"]]
    if type:
        where.append(MarketingList.type == type)
    if search:
        like = f"%{search.strip()}%"
        where.append(or_(MarketingList.name.ilike(like), MarketingList.description.ilike(like)))

    total_res = await db.execute(select(func.count(MarketingList.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(MarketingList)
        .where(and_(*where))
        .order_by(MarketingList.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    lists = res.scalars().all()

    # Compute member counts for static lists.
    list_ids = [l.id for l in lists]
    counts_by_list = {lid: 0 for lid in list_ids}
    if list_ids:
        counts_res = await db.execute(
            select(ListMember.list_id, func.count(ListMember.id))
            .where(ListMember.list_id.in_(list_ids))
            .group_by(ListMember.list_id)
        )
        for lid, cnt in counts_res.all():
            counts_by_list[str(lid)] = int(cnt or 0)

    return {
        "lists": [
            _list_to_dict(lst, counts_by_list.get(lst.id, 0) if lst.type == "static" else 0) for lst in lists
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201)
async def create_list(
    data: ListCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    lst = MarketingList(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        description=data.description,
        type=data.type,
        filters=data.filters if data.type == "smart" else None,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(lst)
    await db.flush()
    return _list_to_dict(lst, contact_count=0)


@router.get("/{list_id}")
async def get_list(
    list_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(MarketingList).where(and_(MarketingList.id == list_id, MarketingList.tenant_id == user["tenant_id"]))
    )
    lst = res.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    count = 0
    if lst.type == "static":
        count_res = await db.execute(select(func.count(ListMember.id)).where(ListMember.list_id == lst.id))
        count = int(count_res.scalar() or 0)
    return _list_to_dict(lst, contact_count=count)


@router.put("/{list_id}")
async def update_list(
    list_id: str,
    data: ListUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(MarketingList).where(and_(MarketingList.id == list_id, MarketingList.tenant_id == user["tenant_id"]))
    )
    lst = res.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    if data.name is not None:
        lst.name = data.name
    if data.description is not None:
        lst.description = data.description
    if data.filters is not None and lst.type == "smart":
        lst.filters = data.filters
    lst.updated_at = now_utc()
    await db.flush()
    return _list_to_dict(lst, contact_count=0)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(MarketingList).where(and_(MarketingList.id == list_id, MarketingList.tenant_id == user["tenant_id"]))
    )
    lst = res.scalar_one_or_none()
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    # Delete members first (cascade is also ok).
    await db.execute(delete(ListMember).where(ListMember.list_id == list_id))
    await db.delete(lst)
    return None
