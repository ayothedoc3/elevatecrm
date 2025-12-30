from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BlueprintStageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    stage_order: int
    required_properties: List[str] = []
    required_actions: List[str] = []
    entry_automations: List[Dict[str, Any]] = []
    exit_automations: List[Dict[str, Any]] = []
    color: str = Field(default="#3B82F6", pattern=r'^#[0-9A-Fa-f]{6}$')
    icon: str = "circle"
    is_start_stage: bool = False
    is_end_stage: bool = False
    is_milestone: bool = False

class BlueprintStageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    stage_order: Optional[int] = None
    required_properties: Optional[List[str]] = None
    required_actions: Optional[List[str]] = None
    entry_automations: Optional[List[Dict[str, Any]]] = None
    exit_automations: Optional[List[Dict[str, Any]]] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_start_stage: Optional[bool] = None
    is_end_stage: Optional[bool] = None
    is_milestone: Optional[bool] = None

class BlueprintStageResponse(BaseModel):
    id: str
    blueprint_id: str
    name: str
    description: Optional[str] = None
    stage_order: int
    required_properties: List[str] = []
    required_actions: List[str] = []
    entry_automations: List[Dict[str, Any]] = []
    exit_automations: List[Dict[str, Any]] = []
    color: str
    icon: str
    is_start_stage: bool
    is_end_stage: bool
    is_milestone: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BlueprintCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    allow_skip_stages: bool = False
    allow_admin_override: bool = True
    require_override_reason: bool = True
    stages: Optional[List[BlueprintStageCreate]] = None

class BlueprintUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    allow_skip_stages: Optional[bool] = None
    allow_admin_override: Optional[bool] = None
    require_override_reason: Optional[bool] = None

class BlueprintResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    version: int
    is_active: bool
    is_default: bool
    allow_skip_stages: bool
    allow_admin_override: bool
    require_override_reason: bool
    stages: List[BlueprintStageResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BlueprintListResponse(BaseModel):
    blueprints: List[BlueprintResponse]
    total: int

class ValidateMoveRequest(BaseModel):
    deal_id: str
    target_stage_order: int

class ValidateMoveResponse(BaseModel):
    can_move: bool
    current_stage_order: int
    target_stage_order: int
    missing_requirements: Dict[str, List[str]] = {}
    message: str

class OverrideMoveRequest(BaseModel):
    deal_id: str
    target_stage_order: int
    reason: str = Field(..., min_length=10, max_length=1000)
