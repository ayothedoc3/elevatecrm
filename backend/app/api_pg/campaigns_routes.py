from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.utils import dt_to_iso, now_utc, parse_iso_datetime
from app.core.database import get_db
from app.pg_models.models import Campaign, ListMember

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


class CampaignCreate(BaseModel):
    name: str
    subject: Optional[str] = None
    content: str = ""
    campaign_type: str = "email"
    list_id: Optional[str] = None
    scheduled_at: Optional[str] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    list_id: Optional[str] = None
    scheduled_at: Optional[str] = None


def _campaign_to_dict(c: Campaign) -> dict:
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "name": c.name,
        "subject": c.subject,
        "content": c.content,
        "campaign_type": c.campaign_type,
        "status": c.status,
        "list_id": c.list_id,
        "scheduled_at": dt_to_iso(c.scheduled_at),
        "sent_at": dt_to_iso(c.sent_at),
        "sent_count": int(c.sent_count or 0),
        "delivered_count": int(c.delivered_count or 0),
        "open_count": int(c.open_count or 0),
        "click_count": int(c.click_count or 0),
        "bounce_count": int(c.bounce_count or 0),
        "unsubscribe_count": int(c.unsubscribe_count or 0),
        "created_by": c.created_by,
        "created_at": dt_to_iso(c.created_at),
        "updated_at": dt_to_iso(c.updated_at),
    }


@router.get("")
async def list_campaigns(
    campaign_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = [Campaign.tenant_id == user["tenant_id"]]
    if campaign_type:
        where.append(Campaign.campaign_type == campaign_type)
    if status:
        where.append(Campaign.status == status)
    if search:
        like = f"%{search.strip()}%"
        where.append(or_(Campaign.name.ilike(like), Campaign.subject.ilike(like)))

    total_res = await db.execute(select(func.count(Campaign.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(Campaign).where(and_(*where)).order_by(Campaign.created_at.desc()).offset(offset).limit(page_size)
    )
    campaigns = res.scalars().all()
    return {"campaigns": [_campaign_to_dict(c) for c in campaigns], "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
async def create_campaign(
    data: CampaignCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = now_utc()
    campaign = Campaign(
        id=str(uuid.uuid4()),
        tenant_id=user["tenant_id"],
        name=data.name,
        subject=data.subject,
        content=data.content or "",
        campaign_type=data.campaign_type,
        status="draft",
        list_id=data.list_id,
        scheduled_at=parse_iso_datetime(data.scheduled_at),
        sent_at=None,
        sent_count=0,
        delivered_count=0,
        open_count=0,
        click_count=0,
        bounce_count=0,
        unsubscribe_count=0,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(campaign)
    await db.flush()
    return _campaign_to_dict(campaign)


@router.get("/stats/overview")
async def get_campaigns_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    total_res = await db.execute(select(func.count(Campaign.id)).where(Campaign.tenant_id == tenant_id))
    draft_res = await db.execute(
        select(func.count(Campaign.id)).where(and_(Campaign.tenant_id == tenant_id, Campaign.status == "draft"))
    )
    scheduled_res = await db.execute(
        select(func.count(Campaign.id)).where(and_(Campaign.tenant_id == tenant_id, Campaign.status == "scheduled"))
    )
    sent_res = await db.execute(
        select(func.count(Campaign.id)).where(and_(Campaign.tenant_id == tenant_id, Campaign.status == "sent"))
    )

    totals_res = await db.execute(
        select(
            func.coalesce(func.sum(Campaign.sent_count), 0),
            func.coalesce(func.sum(Campaign.open_count), 0),
            func.coalesce(func.sum(Campaign.click_count), 0),
        ).where(Campaign.tenant_id == tenant_id)
    )
    total_sent, total_opens, total_clicks = totals_res.one()

    return {
        "total_campaigns": int(total_res.scalar() or 0),
        "draft_count": int(draft_res.scalar() or 0),
        "scheduled_count": int(scheduled_res.scalar() or 0),
        "sent_count": int(sent_res.scalar() or 0),
        "total_emails_sent": int(total_sent or 0),
        "total_opens": int(total_opens or 0),
        "total_clicks": int(total_clicks or 0),
    }


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Campaign).where(and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"]))
    )
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_dict(campaign)


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Campaign).where(and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"]))
    )
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "scheduled_at" in update_data:
        update_data["scheduled_at"] = parse_iso_datetime(update_data["scheduled_at"])
    update_data["updated_at"] = now_utc()
    await db.execute(
        update(Campaign).where(and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"])).values(**update_data)
    )
    return {"success": True}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Campaign).where(and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"]))
    )
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(campaign)
    return {"success": True}


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Campaign).where(and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"]))
    )
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "sent":
        raise HTTPException(status_code=400, detail="Campaign already sent")

    sent_count = 0
    if campaign.list_id:
        cnt_res = await db.execute(select(func.count(ListMember.id)).where(ListMember.list_id == campaign.list_id))
        sent_count = int(cnt_res.scalar() or 0)

    now = now_utc()
    await db.execute(
        update(Campaign)
        .where(Campaign.id == campaign.id)
        .values(status="sent", sent_at=now, sent_count=sent_count, updated_at=now)
    )

    return {"success": True, "message": f"Campaign sent to {sent_count} recipients"}


@router.post("/{campaign_id}/duplicate")
async def duplicate_campaign(
    campaign_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Campaign).where(and_(Campaign.id == campaign_id, Campaign.tenant_id == user["tenant_id"]))
    )
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    now = now_utc()
    new_campaign = Campaign(
        id=str(uuid.uuid4()),
        tenant_id=campaign.tenant_id,
        name=f"{campaign.name} (Copy)",
        subject=campaign.subject,
        content=campaign.content,
        campaign_type=campaign.campaign_type,
        status="draft",
        list_id=campaign.list_id,
        scheduled_at=None,
        sent_at=None,
        sent_count=0,
        delivered_count=0,
        open_count=0,
        click_count=0,
        bounce_count=0,
        unsubscribe_count=0,
        created_by=user["id"],
        created_at=now,
        updated_at=now,
    )
    db.add(new_campaign)
    await db.flush()
    return _campaign_to_dict(new_campaign)

