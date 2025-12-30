from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Standard properties
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)  # 1-10, 11-50, 51-200, 201-500, 500+
    annual_revenue = Column(String(50), nullable=True)
    
    # Contact info
    phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Address
    street_address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Custom properties
    custom_properties = Column(Text, default='{}')
    tags = Column(Text, default='[]')
    
    # Status
    is_active = Column(Boolean, default=True)
    employee_count = Column(Integer, nullable=True)
    
    # Timestamps
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='companies')
