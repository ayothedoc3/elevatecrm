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
    industry: Optional[str] = None
    company_size: Optional[str] = None
    country: Optional[str] = None
    icp_tier: Optional[str] = None


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
                "domain_lower": a.domain_lower,
                "industry": a.industry,
                "company_size": a.company_size,
                "country": a.country,
                "icp_tier": a.icp_tier,
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
    resolved = await resolve_account(
        db=db,
        tenant_id=tenant_id,
        account_name=data.name,
        actor_id=user["id"],
        domain=data.domain,
        industry=data.industry,
        company_size=data.company_size,
        country=data.country,
        icp_tier=data.icp_tier,
    )

    res = await db.execute(select(Account).where(and_(Account.id == resolved.get("account_id"), Account.tenant_id == tenant_id)))
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=500, detail="Failed to create account")

    await db.flush()

    return {
        "id": account.id,
        "tenant_id": account.tenant_id,
        "name": account.name,
        "name_lower": account.name_lower,
        "domain": account.domain,
        "domain_lower": account.domain_lower,
        "industry": account.industry,
        "company_size": account.company_size,
        "country": account.country,
        "icp_tier": account.icp_tier,
        "is_active": account.is_active,
        "created_at": dt_to_iso(account.created_at),
        "updated_at": dt_to_iso(account.updated_at),
    }

