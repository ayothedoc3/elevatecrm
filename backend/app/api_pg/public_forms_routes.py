from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.landing_pages_routes import (
    PageStatus,
    PublicFormSubmissionRequest,
    submit_public_landing_form_internal,
)
from app.core.database import get_db
from app.pg_models.models import LandingPage, Tenant

router = APIRouter(prefix="/public/forms", tags=["Public Forms"])


@router.post("/{tenant_slug}/{slug}", status_code=201)
async def submit_public_form(
    tenant_slug: str,
    slug: str,
    data: PublicFormSubmissionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_res = await db.execute(
        select(Tenant).where(and_(Tenant.slug == tenant_slug, Tenant.is_active.is_(True))).limit(1)
    )
    tenant = tenant_res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    page_res = await db.execute(
        select(LandingPage).where(
            and_(
                LandingPage.tenant_id == tenant.id,
                LandingPage.slug == slug,
                LandingPage.status == PageStatus.PUBLISHED.value,
            )
        )
    )
    page = page_res.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return await submit_public_landing_form_internal(
        page=page,
        slug=slug,
        data=data,
        db=db,
        request=request,
    )

