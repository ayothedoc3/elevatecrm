from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from app.core.database import Base


class WorkflowStatus(str, enum.Enum):
    ACTIVE = 'active'
    PAUSED = 'paused'
    DRAFT = 'draft'
    ARCHIVED = 'archived'


class TriggerType(str, enum.Enum):
    FORM_SUBMITTED = 'form_submitted'
    DEAL_STAGE_CHANGED = 'deal_stage_changed'
    DEAL_CREATED = 'deal_created'
    CONTACT_CREATED = 'contact_created'
    MESSAGE_RECEIVED = 'message_received'
    DOCUMENT_RECEIVED = 'document_received'
    E_SIGNATURE_COMPLETED = 'e_signature_completed'
    PAYMENT_COMPLETED = 'payment_completed'
    TASK_OVERDUE = 'task_overdue'
    MANUAL = 'manual'
    SCHEDULED = 'scheduled'


class ActionType(str, enum.Enum):
    SEND_EMAIL = 'send_email'
    SEND_SMS = 'send_sms'
    CREATE_TASK = 'create_task'
    SET_PROPERTY = 'set_property'
    ADD_TAG = 'add_tag'
    REMOVE_TAG = 'remove_tag'
    ASSIGN_OWNER = 'assign_owner'
    MOVE_DEAL_STAGE = 'move_deal_stage'
    CREATE_DEAL = 'create_deal'
    REQUEST_DOCUMENT = 'request_document'
    CREATE_NOTIFICATION = 'create_notification'
    FIRE_WEBHOOK = 'fire_webhook'
    DELAY = 'delay'
    IF_CONDITION = 'if_condition'


class WorkflowRunStatus(str, enum.Enum):
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    WAITING = 'waiting'  # Waiting on delay


class Workflow(Base):
    """Automation workflow definition."""
    __tablename__ = 'workflows'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.DRAFT)
    
    # Trigger configuration (JSON)
    # Format: { "type": "form_submitted", "form_id": "...", "conditions": [...] }
    trigger_type = Column(SQLEnum(TriggerType), nullable=False)
    trigger_config = Column(Text, default='{}')
    
    # Actions (JSON array)
    # Format: [{ "type": "send_email", "config": {...}, "delay_minutes": 0 }, ...]
    actions = Column(Text, default='[]')
    
    # Stats
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    
    # Metadata
    created_by_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    runs = relationship('WorkflowRun', back_populates='workflow', cascade='all, delete-orphan')


class WorkflowRun(Base):
    """Individual execution of a workflow."""
    __tablename__ = 'workflow_runs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    workflow_id = Column(String(36), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Context - what triggered this run
    contact_id = Column(String(36), ForeignKey('contacts.id', ondelete='SET NULL'), nullable=True)
    deal_id = Column(String(36), ForeignKey('deals.id', ondelete='SET NULL'), nullable=True)
    
    # Trigger info
    trigger_type = Column(SQLEnum(TriggerType), nullable=False)
    trigger_data = Column(Text, default='{}')  # JSON with trigger context
    
    # Status
    status = Column(SQLEnum(WorkflowRunStatus), default=WorkflowRunStatus.RUNNING)
    current_action_index = Column(Integer, default=0)
    
    # Results
    error_message = Column(Text, nullable=True)
    execution_log = Column(Text, default='[]')  # JSON array of action results
    
    # Timing
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    next_action_at = Column(DateTime(timezone=True), nullable=True)  # For delayed actions
    
    # Idempotency
    idempotency_key = Column(String(255), nullable=True, unique=True)
    
    # Relationships
    workflow = relationship('Workflow', back_populates='runs')


class ScheduledJob(Base):
    """Queue for scheduled workflow actions."""
    __tablename__ = 'scheduled_jobs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Job type
    job_type = Column(String(50), nullable=False)  # 'workflow_action', 'send_message', etc.
    
    # Reference
    workflow_run_id = Column(String(36), ForeignKey('workflow_runs.id', ondelete='CASCADE'), nullable=True)
    
    # Payload
    payload = Column(Text, default='{}')  # JSON with job data
    
    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Status
    is_processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
