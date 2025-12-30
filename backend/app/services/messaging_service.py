"""Mock messaging service for SMS and Email.
Replace with real Twilio/SendGrid when API keys are available.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    Conversation, Message, MessageChannel, MessageDirection, MessageStatus,
    Contact, TimelineEvent, TimelineEventType, VisibilityScope
)

logger = logging.getLogger(__name__)

# Mock configuration - replace with real credentials
TWILIO_ACCOUNT_SID = None
TWILIO_AUTH_TOKEN = None
TWILIO_PHONE_NUMBER = None
SENDGRID_API_KEY = None
SENDGRID_FROM_EMAIL = "noreply@crm-os.local"


class MockMessagingService:
    """Mock messaging service that logs messages instead of sending."""
    
    @staticmethod
    async def send_sms(
        db: AsyncSession,
        tenant_id: str,
        contact_id: str,
        to_phone: str,
        body: str,
        sender_user_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        deal_id: Optional[str] = None
    ) -> Message:
        """Send an SMS message (mocked)."""
        logger.info(f"[MOCK SMS] To: {to_phone}, Body: {body[:50]}...")
        
        # Find or create conversation
        conversation = await _get_or_create_conversation(
            db, tenant_id, contact_id, MessageChannel.SMS, deal_id
        )
        
        # Create message
        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            channel=MessageChannel.SMS,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.SENT,  # Mock: immediately "sent"
            from_address=TWILIO_PHONE_NUMBER or "+1-555-CRM-OS",
            to_address=to_phone,
            body=body,
            sent_by_user_id=sender_user_id,
            sent_by_name=sender_name,
            external_id=f"mock_sms_{datetime.now().timestamp()}",
            sent_at=datetime.now(timezone.utc)
        )
        db.add(message)
        
        # Update conversation
        conversation.message_count += 1
        conversation.last_message_preview = body[:100]
        conversation.last_message_at = datetime.now(timezone.utc)
        
        await db.flush()
        
        # Create timeline event
        timeline = TimelineEvent(
            tenant_id=tenant_id,
            contact_id=contact_id,
            deal_id=deal_id,
            event_type=TimelineEventType.SMS_SENT,
            title=f"SMS sent to {to_phone}",
            description=body[:200],
            metadata_json=json.dumps({
                'to': to_phone,
                'message_id': message.id,
                'mocked': True
            }),
            visibility=VisibilityScope.INTERNAL_ONLY,
            actor_id=sender_user_id,
            actor_name=sender_name
        )
        db.add(timeline)
        
        return message
    
    @staticmethod
    async def send_email(
        db: AsyncSession,
        tenant_id: str,
        contact_id: str,
        to_email: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        sender_user_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        deal_id: Optional[str] = None
    ) -> Message:
        """Send an email message (mocked)."""
        logger.info(f"[MOCK EMAIL] To: {to_email}, Subject: {subject}")
        
        # Find or create conversation
        conversation = await _get_or_create_conversation(
            db, tenant_id, contact_id, MessageChannel.EMAIL, deal_id, subject
        )
        
        # Create message
        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            channel=MessageChannel.EMAIL,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.SENT,
            from_address=SENDGRID_FROM_EMAIL,
            to_address=to_email,
            subject=subject,
            body=body,
            body_html=body_html,
            sent_by_user_id=sender_user_id,
            sent_by_name=sender_name,
            external_id=f"mock_email_{datetime.now().timestamp()}",
            sent_at=datetime.now(timezone.utc)
        )
        db.add(message)
        
        # Update conversation
        conversation.message_count += 1
        conversation.last_message_preview = body[:100]
        conversation.last_message_at = datetime.now(timezone.utc)
        if not conversation.subject:
            conversation.subject = subject
        
        await db.flush()
        
        # Create timeline event
        timeline = TimelineEvent(
            tenant_id=tenant_id,
            contact_id=contact_id,
            deal_id=deal_id,
            event_type=TimelineEventType.EMAIL_SENT,
            title=f"Email sent: {subject}",
            description=body[:200],
            metadata_json=json.dumps({
                'to': to_email,
                'subject': subject,
                'message_id': message.id,
                'mocked': True
            }),
            visibility=VisibilityScope.INTERNAL_ONLY,
            actor_id=sender_user_id,
            actor_name=sender_name
        )
        db.add(timeline)
        
        return message


async def _get_or_create_conversation(
    db: AsyncSession,
    tenant_id: str,
    contact_id: str,
    channel: MessageChannel,
    deal_id: Optional[str] = None,
    subject: Optional[str] = None
) -> Conversation:
    """Get existing conversation or create a new one."""
    # Try to find existing open conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.contact_id == contact_id,
            Conversation.channel == channel,
            Conversation.is_open == True
        ).order_by(Conversation.created_at.desc()).limit(1)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(
            tenant_id=tenant_id,
            contact_id=contact_id,
            deal_id=deal_id,
            channel=channel,
            subject=subject
        )
        db.add(conversation)
        await db.flush()
    
    return conversation


# Singleton instance
messaging_service = MockMessagingService()
