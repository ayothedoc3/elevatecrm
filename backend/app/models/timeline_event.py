from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base

class TimelineEventType(str, enum.Enum):
    NOTE = 'note'
    TASK = 'task'
    CALL_LOG = 'call_log'
    MEETING = 'meeting'
    EMAIL_SENT = 'email_sent'
    EMAIL_RECEIVED = 'email_received'
    SMS_SENT = 'sms_sent'
    SMS_RECEIVED = 'sms_received'
    STAGE_CHANGED = 'stage_changed'
    PROPERTY_CHANGED = 'property_changed'
    DOCUMENT_REQUESTED = 'document_requested'
    DOCUMENT_RECEIVED = 'document_received'
    E_SIGNATURE_REQUESTED = 'e_signature_requested'
    E_SIGNATURE_COMPLETED = 'e_signature_completed'
    PAYMENT_REQUESTED = 'payment_requested'
    PAYMENT_COMPLETED = 'payment_completed'
    REVIEW_REQUESTED = 'review_requested'
    COMMISSION_EVENT = 'commission_event'
    INTERNAL_NOTIFICATION = 'internal_notification'
    WEBHOOK_FIRED = 'webhook_fired'
    FORM_SUBMITTED = 'form_submitted'
    BLUEPRINT_OVERRIDE = 'blueprint_override'
    DEAL_CREATED = 'deal_created'
    DEAL_WON = 'deal_won'
    DEAL_LOST = 'deal_lost'
    CONTACT_CREATED = 'contact_created'

class VisibilityScope(str, enum.Enum):
    CLIENT_VISIBLE = 'client_visible'
    INTERNAL_ONLY = 'internal_only'

class TimelineEvent(Base):
    __tablename__ = 'timeline_events'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Associated objects (at least one should be set)
    contact_id = Column(String(36), ForeignKey('contacts.id', ondelete='CASCADE'), nullable=True, index=True)
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='CASCADE'), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey('companies.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Event details
    event_type = Column(SQLEnum(TimelineEventType), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata (JSON) - stores type-specific data
    # For stage_changed: { "from_stage": "...", "to_stage": "...", "from_stage_id": "...", "to_stage_id": "..." }
    # For property_changed: { "property": "...", "old_value": "...", "new_value": "..." }
    # For blueprint_override: { "stage": "...", "reason": "...", "missing_requirements": [...] }
    metadata_json = Column(Text, default='{}')
    
    # Visibility
    visibility = Column(SQLEnum(VisibilityScope), default=VisibilityScope.INTERNAL_ONLY)
    
    # Actor (who performed this action)
    actor_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    actor_name = Column(String(255), nullable=True)  # Stored for display even if user deleted
    
    # For tasks
    is_completed = Column(Boolean, default=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='timeline_events')
    contact = relationship('Contact', back_populates='timeline_events')
    deal = relationship('Deal', back_populates='timeline_events')
