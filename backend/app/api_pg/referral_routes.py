from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.utils import now_utc
from app.core.database import get_db
from app.pg_models.models import AffiliateEvent, AffiliateLink, AffiliateProgram

router = APIRouter(tags=["Referrals"])


@router.get("/ref/{referral_code}")
async def public_referral_redirect(
    referral_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(AffiliateLink).where(and_(AffiliateLink.referral_code == referral_code, AffiliateLink.is_active.is_(True)))
    )
    link = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Invalid referral link")

    program = None
    if link.program_id:
        prog_res = await db.execute(select(AffiliateProgram).where(AffiliateProgram.id == link.program_id))
        program = prog_res.scalar_one_or_none()
    cookie_days = int(program.cookie_duration_days or 30) if program else 30

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer", "")

    now = now_utc()
    event = AffiliateEvent(
        id=str(uuid.uuid4()),
        tenant_id=link.tenant_id,
        event_type="affiliate_link_clicked",
        affiliate_id=link.affiliate_id,
        link_id=link.id,
        program_id=link.program_id,
        deal_id=None,
        contact_id=None,
        commission_id=None,
        payment_id=None,
        ip_address=ip_address,
        user_agent=user_agent,
        meta={"referral_code": referral_code, "referer": referer},
        created_at=now,
    )
    db.add(event)

    await db.execute(
        update(AffiliateLink).where(AffiliateLink.id == link.id).values(click_count=int(link.click_count or 0) + 1)
    )

    redirect_url = link.landing_page_url or "/"
    if "?" in redirect_url:
        redirect_url += f"&ref={referral_code}"
    else:
        redirect_url += f"?ref={referral_code}"

    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(
        key="_aff_ref",
        value=referral_code,
        max_age=cookie_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
    )
    return response

