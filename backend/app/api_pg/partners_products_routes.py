from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso
from app.core.database import get_db
from app.pg_models.models import Partner, Pipeline, Product

router = APIRouter(tags=["Partners"])


class PartnerUpdate(BaseModel):
    default_pipeline_id: Optional[str] = None
    is_active: Optional[bool] = None


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
                "default_pipeline_id": p.default_pipeline_id,
                "created_at": dt_to_iso(p.created_at),
                "updated_at": dt_to_iso(p.updated_at),
            }
            for p in partners
        ]
    }


@router.get("/partners/{partner_id}")
async def get_partner(
    partner_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    res = await db.execute(select(Partner).where(and_(Partner.tenant_id == tenant_id, Partner.id == partner_id)))
    partner = res.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {
        "id": partner.id,
        "tenant_id": partner.tenant_id,
        "name": partner.name,
        "is_active": partner.is_active,
        "default_pipeline_id": partner.default_pipeline_id,
        "created_at": dt_to_iso(partner.created_at),
        "updated_at": dt_to_iso(partner.updated_at),
    }


@router.put("/partners/{partner_id}")
async def update_partner(
    partner_id: str,
    data: PartnerUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant_id = user["tenant_id"]
    res = await db.execute(select(Partner).where(and_(Partner.tenant_id == tenant_id, Partner.id == partner_id)))
    partner = res.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    if data.default_pipeline_id is not None:
        if data.default_pipeline_id:
            pipeline = (
                await db.execute(
                    select(Pipeline).where(and_(Pipeline.tenant_id == tenant_id, Pipeline.id == data.default_pipeline_id))
                )
            ).scalar_one_or_none()
            if not pipeline:
                raise HTTPException(status_code=400, detail="Pipeline not found")
            partner.default_pipeline_id = pipeline.id
        else:
            partner.default_pipeline_id = None

    if data.is_active is not None:
        partner.is_active = bool(data.is_active)

    await db.flush()
    return {
        "id": partner.id,
        "tenant_id": partner.tenant_id,
        "name": partner.name,
        "is_active": partner.is_active,
        "default_pipeline_id": partner.default_pipeline_id,
        "created_at": dt_to_iso(partner.created_at),
        "updated_at": dt_to_iso(partner.updated_at),
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

