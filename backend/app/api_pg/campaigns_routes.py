from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.messaging_service import MessagingProviderError, send_outbound_message_via_provider
from app.api_pg.utils import dt_to_iso, now_utc, parse_iso_datetime
from app.core.database import get_db
from app.pg_models.models import Campaign, Contact, Conversation, ListMember, Message

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


async def _get_or_create_conversation(
    *,
    db: AsyncSession,
    tenant_id: str,
    contact_id: str,
    channel: str,
    subject: Optional[str],
) -> Conversation:
    res = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.contact_id == contact_id,
                Conversation.channel == channel,
            )
        )
    )
    conv = res.scalar_one_or_none()
    now = now_utc()
    if conv:
        return conv

    conv = Conversation(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        contact_id=contact_id,
        channel=channel,
        subject=subject,
        is_open=True,
        is_read=True,
        message_count=0,
        unread_count=0,
        last_message_preview=None,
        last_message_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    await db.flush()
    return conv


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
    if not campaign.list_id:
        raise HTTPException(status_code=400, detail="Campaign must be linked to a contact list")

    recipients_res = await db.execute(
        select(Contact)
        .join(
            ListMember,
            and_(
                ListMember.contact_id == Contact.id,
                ListMember.tenant_id == user["tenant_id"],
            ),
        )
        .where(and_(ListMember.list_id == campaign.list_id, Contact.tenant_id == user["tenant_id"]))
    )
    recipients = recipients_res.scalars().all()
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients found in selected list")

    channel = "sms" if (campaign.campaign_type or "").strip().lower() == "sms" else "email"
    now = now_utc()

    attempted = 0
    sent_ok = 0
    failed = 0
    skipped = 0
    failures: list[str] = []
    sender_name = (user.get("full_name") or "").strip() or user.get("email") or "System"

    for contact in recipients:
        to_address = (contact.phone or "").strip() if channel == "sms" else (contact.email or "").strip()
        if not to_address:
            skipped += 1
            continue

        conv = await _get_or_create_conversation(
            db=db,
            tenant_id=user["tenant_id"],
            contact_id=contact.id,
            channel=channel,
            subject=campaign.subject,
        )

        sent_at = now_utc()
        message_id = str(uuid.uuid4())
        msg = Message(
            id=message_id,
            tenant_id=user["tenant_id"],
            conversation_id=conv.id,
            channel=channel,
            direction="outbound",
            status="pending",
            from_address=user.get("email"),
            to_address=to_address,
            subject=campaign.subject if channel == "email" else None,
            body=campaign.content or "",
            body_html=None,
            sent_by_user_id=user["id"],
            sent_by_name=sender_name,
            sent_at=sent_at,
            created_at=sent_at,
        )
        db.add(msg)

        preview = (campaign.content or "")[:100] + ("..." if len(campaign.content or "") > 100 else "")
        conv.message_count = int(conv.message_count or 0) + 1
        conv.last_message_preview = preview
        conv.last_message_at = sent_at
        conv.updated_at = sent_at
        conv.is_read = True
        conv.unread_count = 0

        attempted += 1
        try:
            send_result = await send_outbound_message_via_provider(
                db=db,
                tenant_id=user["tenant_id"],
                channel=channel,
                to_address=to_address,
                subject=campaign.subject,
                body=campaign.content or "",
                body_html=None,
                message_id=message_id,
                campaign_id=campaign.id,
            )
            msg.status = send_result.get("status") or "sent"
            if msg.status == "failed":
                failed += 1
            else:
                sent_ok += 1
        except MessagingProviderError as exc:
            msg.status = "failed"
            failed += 1
            failures.append(str(exc))

    campaign.status = "sent" if sent_ok > 0 else "draft"
    campaign.sent_at = now if sent_ok > 0 else campaign.sent_at
    campaign.sent_count = attempted
    campaign.delivered_count = int(campaign.delivered_count or 0)
    campaign.bounce_count = int(campaign.bounce_count or 0) + failed
    campaign.updated_at = now

    await db.flush()

    summary = f"Campaign processed: attempted {attempted}, sent {sent_ok}, failed {failed}, skipped {skipped}"
    out = {"success": True, "message": summary, "attempted": attempted, "sent": sent_ok, "failed": failed, "skipped": skipped}
    if failures:
        out["errors"] = failures[:5]
    return out


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

