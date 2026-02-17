from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, Optional

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.services import create_timeline_event
from app.api_pg.utils import now_utc
from app.core.database import get_db
from app.pg_models.models import Campaign, Conversation, Message

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _map_sendgrid_message_status(event_type: str) -> Optional[str]:
    e = (event_type or "").strip().lower()
    if e in {"processed", "sent"}:
        return "sent"
    if e == "delivered":
        return "delivered"
    if e == "open":
        return "opened"
    if e == "click":
        return "clicked"
    if e in {"bounce", "dropped", "spamreport"}:
        return "failed"
    if e in {"deferred"}:
        return "pending"
    return None


def _map_twilio_message_status(status: str) -> str:
    s = (status or "").strip().lower()
    if s in {"queued", "accepted", "sending"}:
        return "pending"
    if s == "sent":
        return "sent"
    if s == "delivered":
        return "delivered"
    if s in {"undelivered", "failed"}:
        return "failed"
    return "pending"


async def _load_contact_id_for_message(db: AsyncSession, message: Message) -> Optional[str]:
    if not message or not message.conversation_id:
        return None
    conv_res = await db.execute(select(Conversation).where(Conversation.id == message.conversation_id))
    conv = conv_res.scalar_one_or_none()
    return conv.contact_id if conv else None


async def _apply_campaign_stats_increments(
    db: AsyncSession,
    increments: Dict[str, Dict[str, int]],
) -> None:
    if not increments:
        return

    for campaign_id, inc in increments.items():
        campaign_res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = campaign_res.scalar_one_or_none()
        if not campaign:
            continue
        campaign.delivered_count = int(campaign.delivered_count or 0) + int(inc.get("delivered") or 0)
        campaign.open_count = int(campaign.open_count or 0) + int(inc.get("open") or 0)
        campaign.click_count = int(campaign.click_count or 0) + int(inc.get("click") or 0)
        campaign.bounce_count = int(campaign.bounce_count or 0) + int(inc.get("bounce") or 0)
        campaign.unsubscribe_count = int(campaign.unsubscribe_count or 0) + int(inc.get("unsubscribe") or 0)
        campaign.updated_at = now_utc()


def _to_events(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(payload, dict):
        yield payload


@router.post("/sendgrid")
async def sendgrid_events_webhook(
    payload: Any = Body(...),
    db: AsyncSession = Depends(get_db),
):
    updated_messages = 0
    timeline_events = 0
    campaign_increments: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"delivered": 0, "open": 0, "click": 0, "bounce": 0, "unsubscribe": 0}
    )

    for event in _to_events(payload):
        evt_type = (event.get("event") or "").strip().lower()
        custom_args = event.get("custom_args") or event.get("unique_args") or {}
        message_id = str(custom_args.get("crm_message_id") or event.get("crm_message_id") or "").strip()
        campaign_id = str(custom_args.get("campaign_id") or event.get("campaign_id") or "").strip() or None

        if campaign_id:
            if evt_type == "delivered":
                campaign_increments[campaign_id]["delivered"] += 1
            elif evt_type == "open":
                campaign_increments[campaign_id]["open"] += 1
            elif evt_type == "click":
                campaign_increments[campaign_id]["click"] += 1
            elif evt_type in {"bounce", "dropped", "spamreport"}:
                campaign_increments[campaign_id]["bounce"] += 1
            elif evt_type == "unsubscribe":
                campaign_increments[campaign_id]["unsubscribe"] += 1

        if not message_id:
            continue

        msg_res = await db.execute(select(Message).where(Message.id == message_id))
        message = msg_res.scalar_one_or_none()
        if not message:
            continue

        status = _map_sendgrid_message_status(evt_type)
        if status:
            message.status = status
            updated_messages += 1

        if evt_type in {"delivered", "open", "click", "bounce", "dropped", "spamreport"}:
            contact_id = await _load_contact_id_for_message(db, message)
            if contact_id:
                timeline_type_map = {
                    "delivered": "email_delivered",
                    "open": "email_opened",
                    "click": "email_clicked",
                    "bounce": "email_bounced",
                    "dropped": "email_bounced",
                    "spamreport": "email_bounced",
                }
                timeline_title_map = {
                    "delivered": "Email delivered",
                    "open": "Email opened",
                    "click": "Email link clicked",
                    "bounce": "Email bounced",
                    "dropped": "Email dropped",
                    "spamreport": "Email marked as spam",
                }
                await create_timeline_event(
                    db=db,
                    tenant_id=message.tenant_id,
                    event_type=timeline_type_map.get(evt_type) or "email_event",
                    title=timeline_title_map.get(evt_type) or "Email activity",
                    contact_id=contact_id,
                    metadata={
                        "message_id": message.id,
                        "campaign_id": campaign_id,
                        "provider": "sendgrid",
                        "event_type": evt_type,
                    },
                )
                timeline_events += 1

    await _apply_campaign_stats_increments(db, campaign_increments)
    return {
        "success": True,
        "updated_messages": updated_messages,
        "timeline_events": timeline_events,
        "campaigns_updated": len(campaign_increments),
    }


@router.post("/twilio/status")
async def twilio_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    message_status = str(form.get("MessageStatus") or "").strip()
    error_code = str(form.get("ErrorCode") or "").strip() or None

    message_id = str(request.query_params.get("message_id") or "").strip() or None
    campaign_id = str(request.query_params.get("campaign_id") or "").strip() or None

    updated = 0
    timeline_created = 0
    if message_id:
        msg_res = await db.execute(select(Message).where(Message.id == message_id))
        message = msg_res.scalar_one_or_none()
        if message:
            mapped = _map_twilio_message_status(message_status)
            message.status = mapped
            updated = 1

            contact_id = await _load_contact_id_for_message(db, message)
            if contact_id and mapped in {"delivered", "failed"}:
                await create_timeline_event(
                    db=db,
                    tenant_id=message.tenant_id,
                    event_type="sms_delivered" if mapped == "delivered" else "sms_failed",
                    title="SMS delivered" if mapped == "delivered" else "SMS failed",
                    contact_id=contact_id,
                    metadata={
                        "message_id": message.id,
                        "campaign_id": campaign_id,
                        "provider": "twilio",
                        "twilio_status": message_status,
                        "twilio_error_code": error_code,
                    },
                )
                timeline_created = 1

            if campaign_id:
                campaign_res = await db.execute(
                    select(Campaign).where(
                        and_(Campaign.id == campaign_id, Campaign.tenant_id == message.tenant_id)
                    )
                )
                campaign = campaign_res.scalar_one_or_none()
                if campaign:
                    if mapped == "delivered":
                        campaign.delivered_count = int(campaign.delivered_count or 0) + 1
                    elif mapped == "failed":
                        campaign.bounce_count = int(campaign.bounce_count or 0) + 1
                    campaign.updated_at = now_utc()

    return {"success": True, "updated_messages": updated, "timeline_events": timeline_created}

