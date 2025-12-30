from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    SALES_REP = 'sales_rep'
    VIEWER = 'viewer'

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    settings = Column(Text, default='{}')
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='users')
    audit_logs = relationship('AuditLog', back_populates='actor', foreign_keys='AuditLog.actor_id')
    owned_deals = relationship('Deal', back_populates='owner', foreign_keys='Deal.owner_id')
    owned_contacts = relationship('Contact', back_populates='owner', foreign_keys='Contact.owner_id')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
