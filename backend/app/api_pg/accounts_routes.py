from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import resolve_account
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import Account

router = APIRouter(tags=["Accounts"])


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = None


@router.get("/accounts")
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    filters = [Account.tenant_id == tenant_id]
    if search:
        filters.append(Account.name.ilike(f"%{search}%"))

    total_res = await db.execute(select(func.count()).select_from(Account).where(and_(*filters)))
    total = int(total_res.scalar_one() or 0)

    stmt = (
        select(Account)
        .where(and_(*filters))
        .order_by(Account.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    accounts = (await db.execute(stmt)).scalars().all()

    return {
        "accounts": [
            {
                "id": a.id,
                "tenant_id": a.tenant_id,
                "name": a.name,
                "name_lower": a.name_lower,
                "domain": a.domain,
                "is_active": a.is_active,
                "created_at": dt_to_iso(a.created_at),
                "updated_at": dt_to_iso(a.updated_at),
            }
            for a in accounts
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/accounts", status_code=201)
async def create_account(
    data: AccountCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    resolved = await resolve_account(db, tenant_id, data.name, user["id"])

    res = await db.execute(select(Account).where(and_(Account.id == resolved.get("account_id"), Account.tenant_id == tenant_id)))
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=500, detail="Failed to create account")

    if data.domain and not account.domain:
        account.domain = data.domain

    await db.flush()

    return {
        "id": account.id,
        "tenant_id": account.tenant_id,
        "name": account.name,
        "name_lower": account.name_lower,
        "domain": account.domain,
        "is_active": account.is_active,
        "created_at": dt_to_iso(account.created_at),
        "updated_at": dt_to_iso(account.updated_at),
    }

