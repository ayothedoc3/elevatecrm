from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.automation import WorkflowStatus, TriggerType, ActionType, WorkflowRunStatus


class WorkflowActionConfig(BaseModel):
    type: ActionType
    config: Dict[str, Any] = {}
    delay_minutes: int = 0


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_config: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []
    status: WorkflowStatus = WorkflowStatus.DRAFT


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    trigger_config: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    status: Optional[WorkflowStatus] = None


class WorkflowResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    status: WorkflowStatus
    trigger_type: TriggerType
    trigger_config: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []
    total_runs: int
    successful_runs: int
    failed_runs: int
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowResponse]
    total: int


class WorkflowRunResponse(BaseModel):
    id: str
    tenant_id: str
    workflow_id: str
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    trigger_type: TriggerType
    trigger_data: Dict[str, Any] = {}
    status: WorkflowRunStatus
    current_action_index: int
    error_message: Optional[str] = None
    execution_log: List[Dict[str, Any]] = []
    started_at: datetime
    completed_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None
    
    # Populated
    workflow_name: Optional[str] = None
    contact_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class WorkflowRunListResponse(BaseModel):
    runs: List[WorkflowRunResponse]
    total: int
    page: int
    page_size: int


class TriggerWorkflowRequest(BaseModel):
    workflow_id: str
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    trigger_data: Dict[str, Any] = {}
