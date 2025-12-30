from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.deal import DealStatus, BlueprintComplianceStatus

class DealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[float] = 0.0
    currency: Optional[str] = "USD"
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    owner_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    close_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    tags: Optional[List[str]] = []
    custom_properties: Optional[Dict[str, Any]] = {}

class DealUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    owner_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    close_date: Optional[datetime] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_properties: Optional[Dict[str, Any]] = None
    status: Optional[DealStatus] = None
    lost_reason: Optional[str] = None

class DealStageMove(BaseModel):
    stage_id: str
    override: bool = False
    override_reason: Optional[str] = None

class DealResponse(BaseModel):
    id: str
    tenant_id: str
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    owner_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    amount: float
    currency: str
    status: DealStatus
    close_date: Optional[datetime] = None
    won_date: Optional[datetime] = None
    lost_date: Optional[datetime] = None
    lost_reason: Optional[str] = None
    blueprint_compliance: BlueprintComplianceStatus
    current_blueprint_stage_id: Optional[str] = None
    completed_blueprint_stages: List[str] = []
    priority: str
    tags: List[str] = []
    custom_properties: Dict[str, Any] = {}
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Populated fields
    stage_name: Optional[str] = None
    pipeline_name: Optional[str] = None
    contact_name: Optional[str] = None
    owner_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class DealListResponse(BaseModel):
    deals: List[DealResponse]
    total: int
    page: int
    page_size: int

class BlueprintValidationResult(BaseModel):
    can_move: bool
    missing_properties: List[str] = []
    missing_actions: List[str] = []
    message: str
