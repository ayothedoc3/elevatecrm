"""
Outreach Activity API Routes

Handles tracking of touchpoints (calls, emails, SMS, etc.) for deals and contacts.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum

from app.core.database import get_db
from app.models import User, Deal, Contact, OutreachActivity, TimelineEvent, TimelineEventType
from app.services import create_timeline_event

router = APIRouter(prefix="/outreach", tags=["Outreach"])


# ==================== ENUMS ====================

class ActivityType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    SMS = "sms"
    LINKEDIN = "linkedin"
    MEETING = "meeting"
    DEMO = "demo"
    NOTE = "note"


class ActivityDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ActivityStatus(str, Enum):
    COMPLETED = "completed"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"
    BOUNCED = "bounced"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


# ==================== SCHEMAS ====================

class CreateActivityRequest(BaseModel):
    deal_id: str
    contact_id: Optional[str] = None
    activity_type: ActivityType
    direction: ActivityDirection = ActivityDirection.OUTBOUND
    status: ActivityStatus = ActivityStatus.COMPLETED
    subject: Optional[str] = None
    notes: Optional[str] = None
    duration_seconds: Optional[int] = None
    got_response: bool = False


class ActivityResponse(BaseModel):
    id: str
    deal_id: str
    contact_id: Optional[str]
    user_id: Optional[str]
    user_name: Optional[str]
    activity_type: str
    direction: str
    status: str
    subject: Optional[str]
    notes: Optional[str]
    duration_seconds: Optional[int]
    got_response: bool
    response_at: Optional[str]
    created_at: str


class ActivityListResponse(BaseModel):
    activities: List[ActivityResponse]
    total: int
    touchpoint_count: int


class DealTouchpointSummary(BaseModel):
    deal_id: str
    total_touchpoints: int
    calls: int
    emails: int
    sms: int
    meetings: int
    responses: int
    last_activity_at: Optional[str]
    days_since_last_contact: Optional[int]


# ==================== HELPER FUNCTIONS ====================

async def get_current_user(
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from auth context - placeholder"""
    # In real implementation, this would come from auth middleware
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ==================== ENDPOINTS ====================

@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(
    data: CreateActivityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Log a new outreach activity (touchpoint)"""
    # Verify deal exists and user has access
    result = await db.execute(
        select(Deal).where(
            and_(
                Deal.id == data.deal_id,
                Deal.tenant_id == user.tenant_id
            )
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Verify contact if provided
    contact_name = None
    if data.contact_id:
        result = await db.execute(
            select(Contact).where(Contact.id == data.contact_id)
        )
        contact = result.scalar_one_or_none()
        if contact:
            contact_name = contact.full_name
    
    # Create activity
    activity = OutreachActivity(
        tenant_id=user.tenant_id,
        deal_id=data.deal_id,
        contact_id=data.contact_id or deal.contact_id,
        user_id=user.id,
        activity_type=data.activity_type.value,
        direction=data.direction.value,
        status=data.status.value,
        subject=data.subject,
        notes=data.notes,
        duration_seconds=data.duration_seconds,
        got_response=data.got_response,
        scheduled_at=data.scheduled_at
    )
    
    if data.got_response:
        activity.response_at = datetime.now(timezone.utc)
    
    db.add(activity)
    
    # Update deal's last activity
    deal.last_activity_at = datetime.now(timezone.utc)
    
    # Create timeline event
    activity_labels = {
        "call": "📞 Call",
        "email": "📧 Email",
        "sms": "💬 SMS",
        "linkedin": "💼 LinkedIn",
        "meeting": "🤝 Meeting",
        "demo": "📺 Demo",
        "note": "📝 Note"
    }
    
    await create_timeline_event(
        db, 
        user.tenant_id, 
        TimelineEventType.ACTIVITY,
        f"{activity_labels.get(data.activity_type.value, 'Activity')}: {data.subject or data.activity_type.value}",
        actor_id=user.id,
        actor_name=user.full_name,
        deal_id=deal.id,
        contact_id=activity.contact_id,
        description=data.notes,
        metadata={
            "activity_type": data.activity_type.value,
            "direction": data.direction.value,
            "status": data.status.value,
            "got_response": data.got_response
        }
    )
    
    await db.flush()
    
    return ActivityResponse(
        id=activity.id,
        deal_id=activity.deal_id,
        contact_id=activity.contact_id,
        user_id=activity.user_id,
        user_name=user.full_name,
        activity_type=activity.activity_type,
        direction=activity.direction,
        status=activity.status,
        subject=activity.subject,
        notes=activity.notes,
        duration_seconds=activity.duration_seconds,
        got_response=activity.got_response,
        response_at=activity.response_at.isoformat() if activity.response_at else None,
        scheduled_at=activity.scheduled_at.isoformat() if activity.scheduled_at else None,
        created_at=activity.created_at.isoformat()
    )


@router.get("/deal/{deal_id}", response_model=ActivityListResponse)
async def list_deal_activities(
    deal_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    activity_type: Optional[ActivityType] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all outreach activities for a deal"""
    # Base query
    query = select(OutreachActivity).where(
        and_(
            OutreachActivity.deal_id == deal_id,
            OutreachActivity.tenant_id == user.tenant_id
        )
    )
    count_query = select(func.count(OutreachActivity.id)).where(
        and_(
            OutreachActivity.deal_id == deal_id,
            OutreachActivity.tenant_id == user.tenant_id
        )
    )
    
    # Filter by type if specified
    if activity_type:
        query = query.where(OutreachActivity.activity_type == activity_type.value)
        count_query = count_query.where(OutreachActivity.activity_type == activity_type.value)
    
    # Get total
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get total touchpoint count (completed activities)
    touchpoint_query = select(func.count(OutreachActivity.id)).where(
        and_(
            OutreachActivity.deal_id == deal_id,
            OutreachActivity.tenant_id == user.tenant_id,
            OutreachActivity.status.in_(['completed', 'no_answer', 'voicemail'])
        )
    )
    touchpoint_result = await db.execute(touchpoint_query)
    touchpoint_count = touchpoint_result.scalar() or 0
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(OutreachActivity.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # Get user names
    user_ids = [a.user_id for a in activities if a.user_id]
    user_names = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in users_result.scalars().all():
            user_names[u.id] = u.full_name
    
    return ActivityListResponse(
        activities=[
            ActivityResponse(
                id=a.id,
                deal_id=a.deal_id,
                contact_id=a.contact_id,
                user_id=a.user_id,
                user_name=user_names.get(a.user_id),
                activity_type=a.activity_type,
                direction=a.direction,
                status=a.status,
                subject=a.subject,
                notes=a.notes,
                duration_seconds=a.duration_seconds,
                got_response=a.got_response,
                response_at=a.response_at.isoformat() if a.response_at else None,
                scheduled_at=a.scheduled_at.isoformat() if a.scheduled_at else None,
                created_at=a.created_at.isoformat()
            )
            for a in activities
        ],
        total=total,
        touchpoint_count=touchpoint_count
    )


@router.get("/deal/{deal_id}/summary", response_model=DealTouchpointSummary)
async def get_deal_touchpoint_summary(
    deal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get touchpoint summary for a deal (for rule enforcement)"""
    # Get counts by type
    base_filter = and_(
        OutreachActivity.deal_id == deal_id,
        OutreachActivity.tenant_id == user.tenant_id
    )
    
    # Total touchpoints
    total_result = await db.execute(
        select(func.count(OutreachActivity.id)).where(base_filter)
    )
    total = total_result.scalar() or 0
    
    # By type
    type_counts = {}
    for activity_type in ['call', 'email', 'sms', 'meeting']:
        count_result = await db.execute(
            select(func.count(OutreachActivity.id)).where(
                and_(base_filter, OutreachActivity.activity_type == activity_type)
            )
        )
        type_counts[activity_type] = count_result.scalar() or 0
    
    # Responses
    response_result = await db.execute(
        select(func.count(OutreachActivity.id)).where(
            and_(base_filter, OutreachActivity.got_response == True)
        )
    )
    responses = response_result.scalar() or 0
    
    # Last activity
    last_result = await db.execute(
        select(OutreachActivity)
        .where(base_filter)
        .order_by(OutreachActivity.created_at.desc())
        .limit(1)
    )
    last_activity = last_result.scalar_one_or_none()
    
    days_since = None
    if last_activity:
        delta = datetime.now(timezone.utc) - last_activity.created_at
        days_since = delta.days
    
    return DealTouchpointSummary(
        deal_id=deal_id,
        total_touchpoints=total,
        calls=type_counts.get('call', 0),
        emails=type_counts.get('email', 0),
        sms=type_counts.get('sms', 0),
        meetings=type_counts.get('meeting', 0),
        responses=responses,
        last_activity_at=last_activity.created_at.isoformat() if last_activity else None,
        days_since_last_contact=days_since
    )


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(
    activity_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an outreach activity"""
    result = await db.execute(
        select(OutreachActivity).where(
            and_(
                OutreachActivity.id == activity_id,
                OutreachActivity.tenant_id == user.tenant_id
            )
        )
    )
    activity = result.scalar_one_or_none()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    await db.delete(activity)
