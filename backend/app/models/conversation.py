from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base


class MessageChannel(str, enum.Enum):
    EMAIL = 'email'
    SMS = 'sms'


class MessageDirection(str, enum.Enum):
    INBOUND = 'inbound'
    OUTBOUND = 'outbound'


class MessageStatus(str, enum.Enum):
    PENDING = 'pending'
    SENT = 'sent'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    READ = 'read'


class Conversation(Base):
    """A conversation thread with a contact."""
    __tablename__ = 'conversations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Conversation metadata
    channel = Column(SQLEnum(MessageChannel), nullable=False, index=True)
    subject = Column(String(500), nullable=True)  # For email threads
    
    # Status
    is_open = Column(Boolean, default=True)
    is_read = Column(Boolean, default=False)
    assigned_to_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Counts
    message_count = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)
    
    # Last message preview
    last_message_preview = Column(String(500), nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    messages = relationship('Message', back_populates='conversation', cascade='all, delete-orphan', order_by='Message.created_at')


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = 'messages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Message details
    channel = Column(SQLEnum(MessageChannel), nullable=False)
    direction = Column(SQLEnum(MessageDirection), nullable=False)
    status = Column(SQLEnum(MessageStatus), default=MessageStatus.PENDING)
    
    # Content
    from_address = Column(String(255), nullable=True)  # Email or phone
    to_address = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)  # For emails
    body = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)  # For email HTML
    
    # Attachments (JSON array of attachment info)
    attachments = Column(Text, default='[]')
    
    # Sender info
    sent_by_user_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    sent_by_name = Column(String(255), nullable=True)
    
    # External IDs for tracking
    external_id = Column(String(255), nullable=True)  # Twilio SID, SendGrid ID, etc.
    
    # Timestamps
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    conversation = relationship('Conversation', back_populates='messages')
