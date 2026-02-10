from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import Partner, Product

router = APIRouter(tags=["Partners"])


@router.get("/partners")
async def list_partners(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Partner).where(and_(Partner.tenant_id == user["tenant_id"], Partner.is_active == True)).order_by(Partner.name.asc())
    )
    partners = res.scalars().all()
    return {
        "partners": [
            {
                "id": p.id,
                "tenant_id": p.tenant_id,
                "name": p.name,
                "is_active": p.is_active,
                "created_at": dt_to_iso(p.created_at),
                "updated_at": dt_to_iso(p.updated_at),
            }
            for p in partners
        ]
    }


@router.get("/products")
async def list_products(
    partner_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Product.tenant_id == user["tenant_id"]]
    if partner_id:
        filters.append(Product.partner_id == partner_id)

    res = await db.execute(select(Product).where(and_(*filters)).order_by(Product.name.asc()))
    products = res.scalars().all()
    return {
        "products": [
            {
                "id": p.id,
                "tenant_id": p.tenant_id,
                "partner_id": p.partner_id,
                "name": p.name,
                "is_active": p.is_active,
                "created_at": dt_to_iso(p.created_at),
                "updated_at": dt_to_iso(p.updated_at),
            }
            for p in products
        ]
    }

