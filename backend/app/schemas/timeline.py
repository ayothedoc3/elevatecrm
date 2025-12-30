from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.timeline_event import TimelineEventType, VisibilityScope

class TimelineEventCreate(BaseModel):
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    event_type: TimelineEventType
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    visibility: VisibilityScope = VisibilityScope.INTERNAL_ONLY
    due_date: Optional[datetime] = None

class TimelineEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    visibility: Optional[VisibilityScope] = None
    is_completed: Optional[bool] = None
    due_date: Optional[datetime] = None

class TimelineEventResponse(BaseModel):
    id: str
    tenant_id: str
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    event_type: TimelineEventType
    title: str
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    visibility: VisibilityScope
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    is_completed: bool
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TimelineListResponse(BaseModel):
    events: List[TimelineEventResponse]
    total: int
    page: int
    page_size: int
