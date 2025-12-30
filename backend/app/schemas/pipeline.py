from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class PipelineStageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    display_order: int = 0
    probability: float = Field(default=0.0, ge=0, le=100)
    color: str = Field(default="#6B7280", pattern=r'^#[0-9A-Fa-f]{6}$')
    is_won_stage: bool = False
    is_lost_stage: bool = False
    default_tasks: List[Dict[str, Any]] = []

class PipelineStageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    display_order: Optional[int] = None
    probability: Optional[float] = Field(None, ge=0, le=100)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    is_won_stage: Optional[bool] = None
    is_lost_stage: Optional[bool] = None
    default_tasks: Optional[List[Dict[str, Any]]] = None

class PipelineStageResponse(BaseModel):
    id: str
    pipeline_id: str
    name: str
    description: Optional[str] = None
    display_order: int
    probability: float
    color: str
    is_won_stage: bool
    is_lost_stage: bool
    default_tasks: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime
    deal_count: int = 0
    
    class Config:
        from_attributes = True

class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: bool = False
    display_order: int = 0
    stages: Optional[List[PipelineStageCreate]] = None

class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: Optional[bool] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class PipelineResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    is_active: bool
    display_order: int
    stages: List[PipelineStageResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PipelineListResponse(BaseModel):
    pipelines: List[PipelineResponse]
    total: int
