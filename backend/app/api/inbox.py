"""API routes for Conversations/Inbox."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional
import json
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import (
    User, Contact, Conversation, Message,
    MessageChannel, MessageDirection, MessageStatus
)
from app.schemas.conversation import (
    MessageCreate, MessageResponse, ConversationResponse,
    ConversationListResponse, InboxStats
)
from app.services import messaging_service

router = APIRouter(prefix="/inbox", tags=["inbox"])


async def get_current_user_dep(user = None):
    """Placeholder - will be replaced with actual dependency."""
    return user


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel: Optional[MessageChannel] = None,
    is_read: Optional[bool] = None,
    search: Optional[str] = None,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """List conversations in inbox."""
    query = select(Conversation).where(Conversation.tenant_id == user.tenant_id)
    count_query = select(func.count(Conversation.id)).where(Conversation.tenant_id == user.tenant_id)
    
    if channel:
        query = query.where(Conversation.channel == channel)
        count_query = count_query.where(Conversation.channel == channel)
    
    if is_read is not None:
        query = query.where(Conversation.is_read == is_read)
        count_query = count_query.where(Conversation.is_read == is_read)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(Conversation.last_message_at.desc().nullslast()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    # Enrich with contact info
    conv_responses = []
    for conv in conversations:
        contact_result = await db.execute(
            select(Contact).where(Contact.id == conv.contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        
        conv_responses.append(ConversationResponse(
            id=conv.id,
            tenant_id=conv.tenant_id,
            contact_id=conv.contact_id,
            deal_id=conv.deal_id,
            channel=conv.channel,
            subject=conv.subject,
            is_open=conv.is_open,
            is_read=conv.is_read,
            assigned_to_id=conv.assigned_to_id,
            message_count=conv.message_count,
            unread_count=conv.unread_count,
            last_message_preview=conv.last_message_preview,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            contact_name=contact.full_name if contact else None,
            contact_email=contact.email if contact else None,
            contact_phone=contact.phone if contact else None,
            messages=[]
        ))
    
    return ConversationListResponse(
        conversations=conv_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats", response_model=InboxStats)
async def get_inbox_stats(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Get inbox statistics."""
    total_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == user.tenant_id
        )
    )
    total = total_result.scalar() or 0
    
    unread_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == user.tenant_id,
            Conversation.is_read == False
        )
    )
    unread = unread_result.scalar() or 0
    
    email_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == user.tenant_id,
            Conversation.channel == MessageChannel.EMAIL
        )
    )
    email_count = email_result.scalar() or 0
    
    sms_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.tenant_id == user.tenant_id,
            Conversation.channel == MessageChannel.SMS
        )
    )
    sms_count = sms_result.scalar() or 0
    
    return InboxStats(
        total_conversations=total,
        unread_conversations=unread,
        email_count=email_count,
        sms_count=sms_count
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id
        )
    )
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Mark as read
    if not conv.is_read:
        conv.is_read = True
        conv.unread_count = 0
    
    # Get contact info
    contact_result = await db.execute(
        select(Contact).where(Contact.id == conv.contact_id)
    )
    contact = contact_result.scalar_one_or_none()
    
    messages = []
    for msg in sorted(conv.messages, key=lambda m: m.created_at):
        try:
            attachments = json.loads(msg.attachments) if msg.attachments else []
        except:
            attachments = []
        
        messages.append(MessageResponse(
            id=msg.id,
            tenant_id=msg.tenant_id,
            conversation_id=msg.conversation_id,
            channel=msg.channel,
            direction=msg.direction,
            status=msg.status,
            from_address=msg.from_address,
            to_address=msg.to_address,
            subject=msg.subject,
            body=msg.body,
            body_html=msg.body_html,
            attachments=attachments,
            sent_by_user_id=msg.sent_by_user_id,
            sent_by_name=msg.sent_by_name,
            external_id=msg.external_id,
            sent_at=msg.sent_at,
            delivered_at=msg.delivered_at,
            read_at=msg.read_at,
            created_at=msg.created_at
        ))
    
    return ConversationResponse(
        id=conv.id,
        tenant_id=conv.tenant_id,
        contact_id=conv.contact_id,
        deal_id=conv.deal_id,
        channel=conv.channel,
        subject=conv.subject,
        is_open=conv.is_open,
        is_read=conv.is_read,
        assigned_to_id=conv.assigned_to_id,
        message_count=conv.message_count,
        unread_count=conv.unread_count,
        last_message_preview=conv.last_message_preview,
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        contact_name=contact.full_name if contact else None,
        contact_email=contact.email if contact else None,
        contact_phone=contact.phone if contact else None,
        messages=messages
    )


@router.post("/send", response_model=MessageResponse, status_code=201)
async def send_message(
    data: MessageCreate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Send a new message (email or SMS)."""
    # Verify contact exists
    contact_result = await db.execute(
        select(Contact).where(
            Contact.id == data.contact_id,
            Contact.tenant_id == user.tenant_id
        )
    )
    contact = contact_result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    if data.channel == MessageChannel.SMS:
        message = await messaging_service.send_sms(
            db, user.tenant_id, data.contact_id, data.to_address, data.body,
            sender_user_id=user.id, sender_name=user.full_name
        )
    else:
        message = await messaging_service.send_email(
            db, user.tenant_id, data.contact_id, data.to_address,
            data.subject or "Message from CRM OS", data.body, data.body_html,
            sender_user_id=user.id, sender_name=user.full_name
        )
    
    return MessageResponse(
        id=message.id,
        tenant_id=message.tenant_id,
        conversation_id=message.conversation_id,
        channel=message.channel,
        direction=message.direction,
        status=message.status,
        from_address=message.from_address,
        to_address=message.to_address,
        subject=message.subject,
        body=message.body,
        body_html=message.body_html,
        attachments=[],
        sent_by_user_id=message.sent_by_user_id,
        sent_by_name=message.sent_by_name,
        external_id=message.external_id,
        sent_at=message.sent_at,
        delivered_at=message.delivered_at,
        read_at=message.read_at,
        created_at=message.created_at
    )
