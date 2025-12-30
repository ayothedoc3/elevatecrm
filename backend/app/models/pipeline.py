from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class Pipeline(Base):
    __tablename__ = 'pipelines'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='pipelines')
    stages = relationship('PipelineStage', back_populates='pipeline', cascade='all, delete-orphan', order_by='PipelineStage.display_order')
    deals = relationship('Deal', back_populates='pipeline')


class PipelineStage(Base):
    __tablename__ = 'pipeline_stages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(String(36), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0)
    probability = Column(Float, default=0.0)  # Win probability percentage
    color = Column(String(20), default='#6B7280')  # Hex color for UI
    
    # Stage settings
    is_won_stage = Column(Boolean, default=False)
    is_lost_stage = Column(Boolean, default=False)
    
    # Default tasks/actions when deal enters this stage (JSON)
    default_tasks = Column(Text, default='[]')
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    pipeline = relationship('Pipeline', back_populates='stages')
    deals = relationship('Deal', back_populates='stage')
