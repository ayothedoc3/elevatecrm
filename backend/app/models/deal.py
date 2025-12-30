from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base

class DealStatus(str, enum.Enum):
    OPEN = 'open'
    WON = 'won'
    LOST = 'lost'

class BlueprintComplianceStatus(str, enum.Enum):
    COMPLIANT = 'compliant'
    MISSING_REQUIREMENTS = 'missing_requirements'
    OVERRIDDEN = 'overridden'
    NOT_APPLICABLE = 'not_applicable'

class Deal(Base):
    __tablename__ = 'deals'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    pipeline_id = Column(String(36), ForeignKey('pipelines.id', ondelete='SET NULL'), nullable=True, index=True)
    stage_id = Column(String(36), ForeignKey('pipeline_stages.id', ondelete='SET NULL'), nullable=True, index=True)
    contact_id = Column(String(36), ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey('companies.id', ondelete='SET NULL'), nullable=True, index=True)
    owner_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    blueprint_id = Column(String(36), ForeignKey('workflow_blueprints.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Deal info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    amount = Column(Float, default=0.0)
    currency = Column(String(10), default='USD')
    
    # Status tracking
    status = Column(SQLEnum(DealStatus), default=DealStatus.OPEN, index=True)
    close_date = Column(DateTime(timezone=True), nullable=True)
    won_date = Column(DateTime(timezone=True), nullable=True)
    lost_date = Column(DateTime(timezone=True), nullable=True)
    lost_reason = Column(String(500), nullable=True)
    
    # Blueprint compliance
    blueprint_compliance = Column(SQLEnum(BlueprintComplianceStatus), default=BlueprintComplianceStatus.NOT_APPLICABLE)
    current_blueprint_stage_id = Column(String(36), nullable=True)  # Current stage in the blueprint
    
    # Completed blueprint stages (JSON array of stage IDs that have been completed)
    completed_blueprint_stages = Column(Text, default='[]')
    
    # Properties
    priority = Column(String(20), default='medium')  # low, medium, high, urgent
    tags = Column(Text, default='[]')
    custom_properties = Column(Text, default='{}')
    
    # Timestamps
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='deals')
    pipeline = relationship('Pipeline', back_populates='deals')
    stage = relationship('PipelineStage', back_populates='deals')
    contact = relationship('Contact', back_populates='deals')
    owner = relationship('User', back_populates='owned_deals', foreign_keys=[owner_id])
    blueprint = relationship('WorkflowBlueprint', back_populates='deals')
    timeline_events = relationship('TimelineEvent', back_populates='deal', cascade='all, delete-orphan')
