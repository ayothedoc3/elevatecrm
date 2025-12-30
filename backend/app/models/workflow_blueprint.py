from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base

class WorkflowBlueprint(Base):
    """Workflow Blueprint defines an ordered sequence of stages with requirements.
    This is used to enforce business processes like the NLA 15-step tax filing workflow.
    """
    __tablename__ = 'workflow_blueprints'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default blueprint for new deals
    
    # Configuration
    allow_skip_stages = Column(Boolean, default=False)  # Can stages be skipped?
    allow_admin_override = Column(Boolean, default=True)  # Can admins override requirements?
    require_override_reason = Column(Boolean, default=True)  # Must provide reason for override?
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    tenant = relationship('Tenant', back_populates='workflow_blueprints')
    stages = relationship('BlueprintStage', back_populates='blueprint', cascade='all, delete-orphan', order_by='BlueprintStage.stage_order')
    deals = relationship('Deal', back_populates='blueprint')


class BlueprintStage(Base):
    """Individual stage in a workflow blueprint with requirements."""
    __tablename__ = 'blueprint_stages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blueprint_id = Column(String(36), ForeignKey('workflow_blueprints.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    stage_order = Column(Integer, nullable=False)  # Order in the workflow (1-based)
    
    # Requirements (JSON)
    # Format: { "properties": ["email", "phone"], "actions": ["id_verified", "docs_received"] }
    required_properties = Column(Text, default='[]')  # JSON array of required property names
    required_actions = Column(Text, default='[]')  # JSON array of required action types
    
    # Automations to trigger on entry (JSON)
    # Format: [{ "type": "send_sms", "template": "welcome", "delay_minutes": 0 }]
    entry_automations = Column(Text, default='[]')
    
    # Automations to trigger on exit (JSON)
    exit_automations = Column(Text, default='[]')
    
    # Visual
    color = Column(String(20), default='#3B82F6')
    icon = Column(String(50), default='circle')  # Icon name for UI
    
    # Flags
    is_start_stage = Column(Boolean, default=False)
    is_end_stage = Column(Boolean, default=False)
    is_milestone = Column(Boolean, default=False)  # Important stage to highlight
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    blueprint = relationship('WorkflowBlueprint', back_populates='stages')
