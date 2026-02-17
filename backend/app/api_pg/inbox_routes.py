from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.messaging_service import MessagingProviderError, send_outbound_message_via_provider
from app.api_pg.utils import dt_to_iso, now_utc
from app.core.database import get_db
from app.pg_models.models import Contact, Conversation, Message

router = APIRouter(tags=["Inbox"])


class SendMessageRequest(BaseModel):
    contact_id: str
    channel: str = "email"
    to_address: str
    subject: Optional[str] = None
    body: str
    body_html: Optional[str] = None


def _message_to_dict(msg: Message) -> dict:
    return {
        "id": msg.id,
        "tenant_id": msg.tenant_id,
        "conversation_id": msg.conversation_id,
        "channel": msg.channel,
        "direction": msg.direction,
        "status": msg.status,
        "from_address": msg.from_address,
        "to_address": msg.to_address,
        "subject": msg.subject,
        "body": msg.body,
        "body_html": msg.body_html,
        "sent_by_user_id": msg.sent_by_user_id,
        "sent_by_name": msg.sent_by_name,
        "sent_at": dt_to_iso(msg.sent_at),
        "created_at": dt_to_iso(msg.created_at),
    }


def _conversation_to_dict(conv: Conversation) -> dict:
    return {
        "id": conv.id,
        "tenant_id": conv.tenant_id,
        "contact_id": conv.contact_id,
        "channel": conv.channel,
        "subject": conv.subject,
        "is_open": bool(conv.is_open),
        "is_read": bool(conv.is_read),
        "message_count": int(conv.message_count or 0),
        "unread_count": int(conv.unread_count or 0),
        "last_message_preview": conv.last_message_preview,
        "last_message_at": dt_to_iso(conv.last_message_at),
        "created_at": dt_to_iso(conv.created_at),
        "updated_at": dt_to_iso(conv.updated_at),
    }


@router.get("/inbox")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    where = [Conversation.tenant_id == user["tenant_id"]]
    if channel:
        where.append(Conversation.channel == channel)

    total_res = await db.execute(select(func.count(Conversation.id)).where(and_(*where)))
    total = int(total_res.scalar() or 0)

    offset = (page - 1) * page_size
    res = await db.execute(
        select(Conversation)
        .where(and_(*where))
        .order_by(Conversation.last_message_at.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    conversations = res.scalars().all()

    contact_ids = [c.contact_id for c in conversations if c.contact_id]
    contacts_by_id = {}
    if contact_ids:
        contacts_res = await db.execute(
            select(Contact).where(and_(Contact.tenant_id == user["tenant_id"], Contact.id.in_(contact_ids)))
        )
        for c in contacts_res.scalars().all():
            contacts_by_id[c.id] = c

    conv_responses = []
    for conv in conversations:
        contact = contacts_by_id.get(conv.contact_id) if conv.contact_id else None
        conv_responses.append(
            {
                **_conversation_to_dict(conv),
                "contact_name": (contact.full_name or "").strip() or "Unknown" if contact else "Unknown",
                "contact_email": contact.email if contact else None,
                "contact_phone": contact.phone if contact else None,
            }
        )

    return {"conversations": conv_responses, "total": total, "page": page, "page_size": page_size}


@router.get("/inbox/stats")
async def get_inbox_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]
    total_res = await db.execute(select(func.count(Conversation.id)).where(Conversation.tenant_id == tenant_id))
    total = int(total_res.scalar() or 0)

    unread_res = await db.execute(
        select(func.count(Conversation.id)).where(and_(Conversation.tenant_id == tenant_id, Conversation.is_read.is_(False)))
    )
    unread = int(unread_res.scalar() or 0)

    email_res = await db.execute(
        select(func.count(Conversation.id)).where(and_(Conversation.tenant_id == tenant_id, Conversation.channel == "email"))
    )
    sms_res = await db.execute(
        select(func.count(Conversation.id)).where(and_(Conversation.tenant_id == tenant_id, Conversation.channel == "sms"))
    )
    return {
        "total_conversations": total,
        "unread_conversations": unread,
        "email_count": int(email_res.scalar() or 0),
        "sms_count": int(sms_res.scalar() or 0),
    }


@router.get("/inbox/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Conversation).where(and_(Conversation.id == conversation_id, Conversation.tenant_id == user["tenant_id"]))
    )
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Mark as read
    now = now_utc()
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(is_read=True, unread_count=0, updated_at=now)
    )

    msgs_res = await db.execute(
        select(Message)
        .where(and_(Message.conversation_id == conversation_id, Message.tenant_id == user["tenant_id"]))
        .order_by(Message.created_at.asc())
        .limit(1000)
    )
    messages = msgs_res.scalars().all()

    contact = None
    if conv.contact_id:
        c_res = await db.execute(
            select(Contact).where(and_(Contact.id == conv.contact_id, Contact.tenant_id == user["tenant_id"]))
        )
        contact = c_res.scalar_one_or_none()

    return {
        **_conversation_to_dict(conv),
        "contact_name": (contact.full_name or "").strip() or "Unknown" if contact else "Unknown",
        "contact_email": contact.email if contact else None,
        "contact_phone": contact.phone if contact else None,
        "messages": [_message_to_dict(m) for m in messages],
    }


@router.post("/inbox/send", status_code=201)
async def send_message(
    data: SendMessageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    contact_res = await db.execute(select(Contact).where(and_(Contact.id == data.contact_id, Contact.tenant_id == tenant_id)))
    contact = contact_res.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    conv_res = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.contact_id == data.contact_id,
                Conversation.channel == data.channel,
            )
        )
    )
    conv = conv_res.scalar_one_or_none()

    now = now_utc()
    if not conv:
        conv = Conversation(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            contact_id=data.contact_id,
            channel=data.channel,
            subject=data.subject,
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

    message_id = str(uuid.uuid4())
    preview = (data.body or "")[:100] + ("..." if len(data.body or "") > 100 else "")

    msg = Message(
        id=message_id,
        tenant_id=tenant_id,
        conversation_id=conv.id,
        channel=data.channel,
        direction="outbound",
        status="pending",
        from_address=user.get("email"),
        to_address=data.to_address,
        subject=data.subject,
        body=data.body,
        body_html=data.body_html,
        sent_by_user_id=user["id"],
        sent_by_name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        sent_at=now,
        created_at=now,
    )
    db.add(msg)

    provider_error = None
    try:
        send_result = await send_outbound_message_via_provider(
            db=db,
            tenant_id=tenant_id,
            channel=data.channel,
            to_address=data.to_address,
            subject=data.subject,
            body=data.body,
            body_html=data.body_html,
            message_id=message_id,
            campaign_id=None,
        )
        msg.status = send_result.get("status") or "sent"
    except MessagingProviderError as exc:
        msg.status = "failed"
        provider_error = str(exc)

    await db.execute(
        update(Conversation)
        .where(Conversation.id == conv.id)
        .values(
            last_message_preview=preview,
            last_message_at=now,
            updated_at=now,
            message_count=(conv.message_count or 0) + 1,
            is_read=True,
            unread_count=0,
        )
    )

    await db.flush()

    out = _message_to_dict(msg)
    if provider_error:
        out["provider_error"] = provider_error
    return out

