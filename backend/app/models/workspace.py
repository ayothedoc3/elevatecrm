"""
CRM Workspace and Blueprint Models for Elevate CRM

This module implements the multi-CRM architecture with:
- CRMWorkspace: Isolated CRM instances (extends Tenant concept)
- CRMBlueprint: Reusable CRM templates
- WorkspaceUser: User membership in workspaces
- CalculationDefinition: Calculation formulas per blueprint
- CalculationResult: Calculation results per deal
- ProvisioningJob: Async workspace creation tracking
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base


class WorkspaceStatus(str, enum.Enum):
    PROVISIONING = 'provisioning'
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    ARCHIVED = 'archived'


class ProvisioningStatus(str, enum.Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'


class WorkspaceRole(str, enum.Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    MANAGER = 'manager'
    MEMBER = 'member'
    VIEWER = 'viewer'


class CRMBlueprint(Base):
    """
    CRM Blueprint - A template for creating new CRM workspaces.
    Contains all configuration needed to provision a complete CRM.
    """
    __tablename__ = 'crm_blueprints'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    
    # Blueprint is system-owned or user-created
    is_system = Column(Boolean, default=False)  # System blueprints cannot be deleted
    is_default = Column(Boolean, default=False)  # Default blueprint for "Add CRM"
    is_active = Column(Boolean, default=True)
    
    # Blueprint configuration (JSON)
    # Contains: pipelines, stages, workflow_rules, calculations, forms, properties
    config = Column(Text, default='{}')
    
    # Preview/display
    icon = Column(String(50), default='briefcase')
    color = Column(String(20), default='#6366F1')
    preview_image_url = Column(String(500), nullable=True)
    
    # Metadata
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    workspaces = relationship('CRMWorkspace', back_populates='blueprint')


class CRMWorkspace(Base):
    """
    CRM Workspace - An isolated CRM instance.
    Each workspace is a complete CRM with its own data, users, and configuration.
    """
    __tablename__ = 'crm_workspaces'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Blueprint used to create this workspace
    blueprint_id = Column(String(36), ForeignKey('crm_blueprints.id', ondelete='SET NULL'), nullable=True, index=True)
    blueprint_version = Column(Integer, nullable=True)  # Version at time of creation
    
    # Status
    status = Column(SQLEnum(WorkspaceStatus), default=WorkspaceStatus.PROVISIONING, index=True)
    
    # Settings (JSON)
    settings = Column(Text, default='{}')
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(20), default='#6366F1')
    
    # Billing/limits (for future use)
    plan = Column(String(50), default='free')
    max_users = Column(Integer, default=10)
    max_contacts = Column(Integer, default=1000)
    
    # Timestamps
    created_by = Column(String(36), nullable=True)  # User who created this workspace
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    blueprint = relationship('CRMBlueprint', back_populates='workspaces')
    members = relationship('WorkspaceUser', back_populates='workspace', cascade='all, delete-orphan')
    provisioning_jobs = relationship('ProvisioningJob', back_populates='workspace', cascade='all, delete-orphan')


class WorkspaceUser(Base):
    """
    User membership in a workspace.
    A user can belong to multiple workspaces with different roles.
    """
    __tablename__ = 'workspace_users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey('crm_workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Role in this workspace
    role = Column(SQLEnum(WorkspaceRole), default=WorkspaceRole.MEMBER)
    
    # Permissions override (JSON) - can override role defaults
    permissions = Column(Text, default='{}')
    
    # Status
    is_active = Column(Boolean, default=True)
    invited_by = Column(String(36), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_access_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workspace = relationship('CRMWorkspace', back_populates='members')
    user = relationship('User', back_populates='workspace_memberships')
    
    # Unique constraint: user can only be in a workspace once
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class ProvisioningJob(Base):
    """
    Tracks async workspace provisioning progress.
    """
    __tablename__ = 'provisioning_jobs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey('crm_workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Status
    status = Column(SQLEnum(ProvisioningStatus), default=ProvisioningStatus.PENDING, index=True)
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(255), nullable=True)
    
    # Steps completed (JSON array)
    completed_steps = Column(Text, default='[]')
    
    # Error info
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Options used for provisioning
    options = Column(Text, default='{}')  # include_demo_data, etc.
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    workspace = relationship('CRMWorkspace', back_populates='provisioning_jobs')


class CalculationDefinition(Base):
    """
    Defines a calculation for a CRM workspace.
    Calculations are formulas that run on deal data.
    """
    __tablename__ = 'calculation_definitions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Version for tracking changes
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Input schema (JSON) - defines required inputs
    # Example: [{"name": "number_of_fryers", "type": "integer", "required": true, "label": "Number of Fryers"}]
    input_schema = Column(Text, default='[]')
    
    # Output schema (JSON) - defines outputs
    # Example: [{"name": "monthly_oil_spend", "type": "currency", "label": "Monthly Oil Spend"}]
    output_schema = Column(Text, default='[]')
    
    # Calculation formula/logic (JSON or expression)
    # Can be simple formulas or complex rule sets
    formula = Column(Text, default='{}')
    
    # Which roles can edit inputs
    editable_by_roles = Column(Text, default='["admin", "manager", "member"]')
    
    # Stage rules - which stage requires this calculation
    required_for_stages = Column(Text, default='[]')  # Stage IDs where this calc is required
    
    # Auto-run triggers
    auto_run_on_input_change = Column(Boolean, default=True)
    return_to_stage_on_change = Column(String(36), nullable=True)  # Stage to return to if inputs change
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CalculationResult(Base):
    """
    Stores calculation results for a deal.
    """
    __tablename__ = 'calculation_results'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='CASCADE'), nullable=False, index=True)
    calculation_id = Column(String(36), ForeignKey('calculation_definitions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Version of calculation definition used
    calculation_version = Column(Integer, default=1)
    
    # Status
    status = Column(String(50), default='pending')  # pending, complete, error
    
    # Input values (JSON)
    inputs = Column(Text, default='{}')
    
    # Calculated output values (JSON)
    outputs = Column(Text, default='{}')
    
    # Is the calculation complete (all required inputs provided)?
    is_complete = Column(Boolean, default=False)
    
    # Validation errors (JSON array)
    validation_errors = Column(Text, default='[]')
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class StageTransitionRule(Base):
    """
    Defines rules for moving between pipeline stages.
    """
    __tablename__ = 'stage_transition_rules'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    pipeline_id = Column(String(36), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # From stage (null = any stage)
    from_stage_id = Column(String(36), ForeignKey('pipeline_stages.id', ondelete='CASCADE'), nullable=True)
    # To stage
    to_stage_id = Column(String(36), ForeignKey('pipeline_stages.id', ondelete='CASCADE'), nullable=False)
    
    # Rule type
    rule_type = Column(String(50), nullable=False)  # 'require_calculation', 'require_property', 'require_action', 'require_touchpoints', 'custom'
    
    # Rule configuration (JSON)
    # For require_calculation: {"calculation_id": "xxx", "must_be_complete": true}
    # For require_property: {"property_name": "email", "must_exist": true}
    # For require_action: {"action_type": "demo_completed"}
    # For require_touchpoints: {"min_count": 6, "max_count": 10}
    config = Column(Text, default='{}')
    
    # Error message to show when rule is violated
    error_message = Column(String(500), nullable=True)
    
    # Can this rule be overridden by admin?
    allow_override = Column(Boolean, default=True)
    
    # Priority (lower = checked first)
    priority = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class OutreachActivity(Base):
    """
    Tracks outreach activities (touchpoints) for deals.
    Used to enforce rules like "6-10 touchpoints before Unresponsive".
    """
    __tablename__ = 'outreach_activities'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='CASCADE'), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Activity type
    activity_type = Column(String(50), nullable=False)  # call, email, sms, linkedin, meeting, demo
    
    # Direction
    direction = Column(String(20), default='outbound')  # inbound, outbound
    
    # Status
    status = Column(String(50), default='completed')  # completed, no_answer, voicemail, bounced
    
    # Details
    subject = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # For calls
    
    # Response tracking
    got_response = Column(Boolean, default=False)
    response_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    activity_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
