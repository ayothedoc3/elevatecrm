from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class Contact(Base):
    __tablename__ = 'contacts'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Standard properties
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    
    # Address
    street_address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Marketing
    lead_source = Column(String(100), nullable=True)
    utm_source = Column(String(255), nullable=True)
    utm_medium = Column(String(255), nullable=True)
    utm_campaign = Column(String(255), nullable=True)
    utm_content = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)
    
    # Status
    lifecycle_stage = Column(String(50), default='lead')  # lead, subscriber, opportunity, customer, evangelist
    tags = Column(Text, default='[]')  # JSON array of tags
    
    # Custom properties stored as JSON
    custom_properties = Column(Text, default='{}')
    
    # Timestamps
    is_active = Column(Boolean, default=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='contacts')
    owner = relationship('User', back_populates='owned_contacts', foreign_keys=[owner_id])
    deals = relationship('Deal', back_populates='contact', cascade='all, delete-orphan')
    timeline_events = relationship('TimelineEvent', back_populates='contact', cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        parts = [self.first_name, self.last_name]
        return ' '.join(filter(None, parts)) or self.email or 'Unknown'
