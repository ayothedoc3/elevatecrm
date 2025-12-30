from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, stage_changed, etc.
    object_type = Column(String(100), nullable=False, index=True)  # contact, deal, company, etc.
    object_id = Column(String(36), nullable=False, index=True)
    before_json = Column(Text, nullable=True)  # JSON string of before state
    after_json = Column(Text, nullable=True)  # JSON string of after state
    metadata_json = Column(Text, default='{}')  # Additional context
    request_id = Column(String(100), nullable=True)  # For tracing
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    tenant = relationship('Tenant', back_populates='audit_logs')
    actor = relationship('User', back_populates='audit_logs', foreign_keys=[actor_id])
