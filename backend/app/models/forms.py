from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base


class FieldType(str, enum.Enum):
    TEXT = 'text'
    EMAIL = 'email'
    PHONE = 'phone'
    NUMBER = 'number'
    TEXTAREA = 'textarea'
    SELECT = 'select'
    MULTI_SELECT = 'multi_select'
    CHECKBOX = 'checkbox'
    DATE = 'date'
    FILE = 'file'
    HIDDEN = 'hidden'


class Form(Base):
    """Form definition."""
    __tablename__ = 'forms'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=False, index=True)  # For public URL
    
    # Form settings
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)  # Can be embedded/shared
    
    # Fields (JSON array)
    # Format: [{ "id": "...", "type": "text", "label": "Name", "required": true, "mapping": "first_name" }]
    fields = Column(Text, default='[]')
    
    # After submission
    submit_button_text = Column(String(100), default='Submit')
    success_message = Column(Text, default='Thank you for your submission!')
    redirect_url = Column(String(500), nullable=True)
    
    # CRM Integration
    create_contact = Column(Boolean, default=True)
    create_deal = Column(Boolean, default=False)
    assign_pipeline_id = Column(String(36), nullable=True)
    assign_stage_id = Column(String(36), nullable=True)
    assign_owner_id = Column(String(36), nullable=True)
    default_tags = Column(Text, default='[]')  # JSON array
    
    # Styling
    theme = Column(String(50), default='default')
    custom_css = Column(Text, nullable=True)
    
    # Stats
    submission_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    submissions = relationship('FormSubmission', back_populates='form', cascade='all, delete-orphan')


class FormSubmission(Base):
    """Form submission record."""
    __tablename__ = 'form_submissions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    form_id = Column(String(36), ForeignKey('forms.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Created records
    contact_id = Column(String(36), ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True)
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='SET NULL'), nullable=True)
    
    # Submission data (JSON)
    data = Column(Text, default='{}')
    
    # UTM tracking
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)
    
    # Request info
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    form = relationship('Form', back_populates='submissions')


class LandingPage(Base):
    """Landing page with form."""
    __tablename__ = 'landing_pages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)  # For public URL
    
    # Status
    is_published = Column(Boolean, default=False)
    
    # Page content (JSON - sections and blocks)
    # Format: { "sections": [{ "type": "hero", "content": {...} }, { "type": "form", "form_id": "..." }] }
    content = Column(Text, default='{"sections": []}')
    
    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    
    # Styling
    theme = Column(String(50), default='default')
    custom_css = Column(Text, nullable=True)
    header_code = Column(Text, nullable=True)  # Custom header scripts
    footer_code = Column(Text, nullable=True)  # Custom footer scripts
    
    # Associated form
    form_id = Column(String(36), ForeignKey('forms.id', ondelete='SET NULL'), nullable=True)
    
    # Stats
    view_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
