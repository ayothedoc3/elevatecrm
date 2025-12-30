from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class Tenant(Base):
    __tablename__ = 'tenants'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    settings = Column(Text, default='{}')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    users = relationship('User', back_populates='tenant', cascade='all, delete-orphan')
    contacts = relationship('Contact', back_populates='tenant', cascade='all, delete-orphan')
    companies = relationship('Company', back_populates='tenant', cascade='all, delete-orphan')
    deals = relationship('Deal', back_populates='tenant', cascade='all, delete-orphan')
    pipelines = relationship('Pipeline', back_populates='tenant', cascade='all, delete-orphan')
    workflow_blueprints = relationship('WorkflowBlueprint', back_populates='tenant', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', back_populates='tenant', cascade='all, delete-orphan')
    timeline_events = relationship('TimelineEvent', back_populates='tenant', cascade='all, delete-orphan')
