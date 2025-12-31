from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import os
import json
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import app modules
from app.core.database import get_db, init_db, engine, Base
from app.core.security import (
    verify_password, get_password_hash, create_access_token, decode_access_token
)
from app.models import (
    Tenant, User, UserRole, AuditLog,
    Contact, Company, Deal, DealStatus, BlueprintComplianceStatus,
    Pipeline, PipelineStage,
    WorkflowBlueprint, BlueprintStage,
    TimelineEvent, TimelineEventType, VisibilityScope
)
from app.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse, TenantCreate, TenantResponse,
    ContactCreate, ContactUpdate, ContactResponse, ContactListResponse,
    DealCreate, DealUpdate, DealStageMove, DealResponse, DealListResponse,
    PipelineCreate, PipelineUpdate, PipelineResponse, PipelineListResponse,
    PipelineStageCreate, PipelineStageResponse,
    BlueprintCreate, BlueprintResponse, BlueprintListResponse,
    BlueprintStageResponse, ValidateMoveRequest, ValidateMoveResponse, OverrideMoveRequest,
    TimelineEventCreate, TimelineEventResponse, TimelineListResponse
)
from app.services import (
    validate_stage_move, move_deal_stage, get_blueprint_progress,
    create_audit_log, create_timeline_event
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


# Optional auth - returns None if not authenticated
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# Permission check decorator
def require_role(allowed_roles: List[UserRole]):
    async def check_role(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {[r.value for r in allowed_roles]}"
            )
        return user
    return check_role


# Lifespan for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed data
    logger.info("Starting up Elevate CRM...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed demo data
    await seed_demo_data()
    
    # Seed system blueprints
    from app.services.provisioning_service import seed_system_blueprints
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_system_blueprints(db)
    
    logger.info("Elevate CRM started successfully!")
    yield
    # Shutdown
    logger.info("Shutting down Elevate CRM...")


# Create FastAPI app
app = FastAPI(
    title="Elevate CRM",
    description="Multi-CRM Platform with Workflow Automation and Calculation Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== HEALTH & ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "Elevate CRM API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(
    data: UserCreate,
    tenant_slug: str = Query(..., description="Tenant slug to register under"),
    db: AsyncSession = Depends(get_db)
):
    # Find tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if email exists in tenant
    result = await db.execute(
        select(User).where(User.email == data.email, User.tenant_id == tenant.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        tenant_id=tenant.id,
        email=data.email,
        password_hash=get_password_hash(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        phone=data.phone
    )
    db.add(user)
    await db.flush()
    
    # Create audit log
    await create_audit_log(
        db, tenant.id, user.id, 'create', 'user', user.id,
        after_json={'email': user.email, 'role': user.role.value}
    )
    
    # Create token
    token = create_access_token({'sub': user.id, 'tenant_id': tenant.id})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    tenant_slug: str = Query(..., description="Tenant slug"),
    db: AsyncSession = Depends(get_db)
):
    # Find tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Find user
    result = await db.execute(
        select(User).where(
            User.email == data.email,
            User.tenant_id == tenant.id,
            User.is_active == True
        )
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    
    # Create token
    token = create_access_token({'sub': user.id, 'tenant_id': user.tenant_id})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


# ==================== TENANT ENDPOINTS ====================

@api_router.get("/tenants/{slug}", response_model=TenantResponse)
async def get_tenant(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


# ==================== CONTACT ENDPOINTS ====================

@api_router.get("/contacts", response_model=ContactListResponse)
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    lifecycle_stage: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Base query with tenant filter
    query = select(Contact).where(Contact.tenant_id == user.tenant_id)
    count_query = select(func.count(Contact.id)).where(Contact.tenant_id == user.tenant_id)
    
    # Apply filters
    if search:
        search_filter = or_(
            Contact.email.ilike(f"%{search}%"),
            Contact.first_name.ilike(f"%{search}%"),
            Contact.last_name.ilike(f"%{search}%"),
            Contact.company_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if lifecycle_stage:
        query = query.where(Contact.lifecycle_stage == lifecycle_stage)
        count_query = count_query.where(Contact.lifecycle_stage == lifecycle_stage)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Contact.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    contacts = result.scalars().all()
    
    return ContactListResponse(
        contacts=[_contact_to_response(c) for c in contacts],
        total=total,
        page=page,
        page_size=page_size
    )


@api_router.post("/contacts", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    contact = Contact(
        tenant_id=user.tenant_id,
        owner_id=data.owner_id or user.id,
        email=data.email,
        phone=data.phone,
        first_name=data.first_name,
        last_name=data.last_name,
        company_name=data.company_name,
        job_title=data.job_title,
        street_address=data.street_address,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code,
        country=data.country,
        lead_source=data.lead_source,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
        utm_term=data.utm_term,
        lifecycle_stage=data.lifecycle_stage or 'lead',
        tags=json.dumps(data.tags or []),
        custom_properties=json.dumps(data.custom_properties or {})
    )
    db.add(contact)
    await db.flush()
    
    # Create timeline event
    await create_timeline_event(
        db, user.tenant_id, TimelineEventType.CONTACT_CREATED,
        f"Contact created: {contact.full_name}",
        actor_id=user.id, actor_name=user.full_name,
        contact_id=contact.id
    )
    
    # Create audit log
    await create_audit_log(
        db, user.tenant_id, user.id, 'create', 'contact', contact.id,
        after_json={'email': contact.email, 'name': contact.full_name}
    )
    
    return _contact_to_response(contact)


@api_router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == user.tenant_id
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _contact_to_response(contact)


@api_router.put("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == user.tenant_id
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Store before state for audit
    before_state = {'email': contact.email, 'name': contact.full_name}
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'tags' and value is not None:
            setattr(contact, field, json.dumps(value))
        elif field == 'custom_properties' and value is not None:
            setattr(contact, field, json.dumps(value))
        else:
            setattr(contact, field, value)
    
    contact.updated_at = datetime.now(timezone.utc)
    
    # Create audit log
    await create_audit_log(
        db, user.tenant_id, user.id, 'update', 'contact', contact.id,
        before_json=before_state,
        after_json={'email': contact.email, 'name': contact.full_name}
    )
    
    return _contact_to_response(contact)


@api_router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str,
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == user.tenant_id
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Audit log before delete
    await create_audit_log(
        db, user.tenant_id, user.id, 'delete', 'contact', contact.id,
        before_json={'email': contact.email, 'name': contact.full_name}
    )
    
    await db.delete(contact)


def _contact_to_response(contact: Contact) -> ContactResponse:
    try:
        tags = json.loads(contact.tags) if contact.tags else []
    except:
        tags = []
    
    try:
        custom_props = json.loads(contact.custom_properties) if contact.custom_properties else {}
    except:
        custom_props = {}
    
    return ContactResponse(
        id=contact.id,
        tenant_id=contact.tenant_id,
        owner_id=contact.owner_id,
        email=contact.email,
        phone=contact.phone,
        first_name=contact.first_name,
        last_name=contact.last_name,
        full_name=contact.full_name,
        company_name=contact.company_name,
        job_title=contact.job_title,
        street_address=contact.street_address,
        city=contact.city,
        state=contact.state,
        postal_code=contact.postal_code,
        country=contact.country,
        lead_source=contact.lead_source,
        utm_source=contact.utm_source,
        utm_medium=contact.utm_medium,
        utm_campaign=contact.utm_campaign,
        lifecycle_stage=contact.lifecycle_stage,
        tags=tags,
        custom_properties=custom_props,
        is_active=contact.is_active,
        last_activity_at=contact.last_activity_at,
        created_at=contact.created_at,
        updated_at=contact.updated_at
    )


# ==================== PIPELINE ENDPOINTS ====================

@api_router.get("/pipelines", response_model=PipelineListResponse)
async def list_pipelines(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.stages))
        .where(Pipeline.tenant_id == user.tenant_id, Pipeline.is_active == True)
        .order_by(Pipeline.display_order)
    )
    pipelines = result.scalars().all()
    
    pipeline_responses = []
    for p in pipelines:
        # Get deal counts per stage
        stage_responses = []
        for s in sorted(p.stages, key=lambda x: x.display_order):
            count_result = await db.execute(
                select(func.count(Deal.id)).where(
                    Deal.stage_id == s.id,
                    Deal.tenant_id == user.tenant_id
                )
            )
            deal_count = count_result.scalar() or 0
            
            stage_responses.append(PipelineStageResponse(
                id=s.id,
                pipeline_id=s.pipeline_id,
                name=s.name,
                description=s.description,
                display_order=s.display_order,
                probability=s.probability,
                color=s.color,
                is_won_stage=s.is_won_stage,
                is_lost_stage=s.is_lost_stage,
                default_tasks=json.loads(s.default_tasks) if s.default_tasks else [],
                created_at=s.created_at,
                updated_at=s.updated_at,
                deal_count=deal_count
            ))
        
        pipeline_responses.append(PipelineResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            name=p.name,
            description=p.description,
            is_default=p.is_default,
            is_active=p.is_active,
            display_order=p.display_order,
            stages=stage_responses,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    
    return PipelineListResponse(pipelines=pipeline_responses, total=len(pipeline_responses))


@api_router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.stages))
        .where(
            Pipeline.id == pipeline_id,
            Pipeline.tenant_id == user.tenant_id
        )
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    stage_responses = []
    for s in sorted(pipeline.stages, key=lambda x: x.display_order):
        count_result = await db.execute(
            select(func.count(Deal.id)).where(Deal.stage_id == s.id)
        )
        deal_count = count_result.scalar() or 0
        
        stage_responses.append(PipelineStageResponse(
            id=s.id,
            pipeline_id=s.pipeline_id,
            name=s.name,
            description=s.description,
            display_order=s.display_order,
            probability=s.probability,
            color=s.color,
            is_won_stage=s.is_won_stage,
            is_lost_stage=s.is_lost_stage,
            default_tasks=json.loads(s.default_tasks) if s.default_tasks else [],
            created_at=s.created_at,
            updated_at=s.updated_at,
            deal_count=deal_count
        ))
    
    return PipelineResponse(
        id=pipeline.id,
        tenant_id=pipeline.tenant_id,
        name=pipeline.name,
        description=pipeline.description,
        is_default=pipeline.is_default,
        is_active=pipeline.is_active,
        display_order=pipeline.display_order,
        stages=stage_responses,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at
    )


# ==================== DEAL ENDPOINTS ====================

@api_router.get("/deals", response_model=DealListResponse)
async def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    pipeline_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    status: Optional[DealStatus] = None,
    search: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Deal).where(Deal.tenant_id == user.tenant_id)
    count_query = select(func.count(Deal.id)).where(Deal.tenant_id == user.tenant_id)
    
    if pipeline_id:
        query = query.where(Deal.pipeline_id == pipeline_id)
        count_query = count_query.where(Deal.pipeline_id == pipeline_id)
    
    if stage_id:
        query = query.where(Deal.stage_id == stage_id)
        count_query = count_query.where(Deal.stage_id == stage_id)
    
    if status:
        query = query.where(Deal.status == status)
        count_query = count_query.where(Deal.status == status)
    
    if search:
        query = query.where(Deal.name.ilike(f"%{search}%"))
        count_query = count_query.where(Deal.name.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(Deal.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    deals = result.scalars().all()
    
    deal_responses = []
    for deal in deals:
        deal_responses.append(await _deal_to_response(deal, db))
    
    return DealListResponse(
        deals=deal_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@api_router.post("/deals", response_model=DealResponse, status_code=201)
async def create_deal(
    data: DealCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # If no pipeline specified, get default
    pipeline_id = data.pipeline_id
    stage_id = data.stage_id
    
    if not pipeline_id:
        result = await db.execute(
            select(Pipeline).where(
                Pipeline.tenant_id == user.tenant_id,
                Pipeline.is_default == True,
                Pipeline.is_active == True
            )
        )
        default_pipeline = result.scalar_one_or_none()
        if default_pipeline:
            pipeline_id = default_pipeline.id
    
    # If no stage specified, get first stage
    if pipeline_id and not stage_id:
        result = await db.execute(
            select(PipelineStage)
            .where(PipelineStage.pipeline_id == pipeline_id)
            .order_by(PipelineStage.display_order)
            .limit(1)
        )
        first_stage = result.scalar_one_or_none()
        if first_stage:
            stage_id = first_stage.id
    
    # Get default blueprint if not specified
    blueprint_id = data.blueprint_id
    if not blueprint_id:
        result = await db.execute(
            select(WorkflowBlueprint).where(
                WorkflowBlueprint.tenant_id == user.tenant_id,
                WorkflowBlueprint.is_default == True,
                WorkflowBlueprint.is_active == True
            )
        )
        default_bp = result.scalar_one_or_none()
        if default_bp:
            blueprint_id = default_bp.id
    
    # Get first blueprint stage if blueprint assigned
    current_blueprint_stage_id = None
    if blueprint_id:
        result = await db.execute(
            select(BlueprintStage)
            .where(BlueprintStage.blueprint_id == blueprint_id)
            .order_by(BlueprintStage.stage_order)
            .limit(1)
        )
        first_bp_stage = result.scalar_one_or_none()
        if first_bp_stage:
            current_blueprint_stage_id = first_bp_stage.id
    
    deal = Deal(
        tenant_id=user.tenant_id,
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        contact_id=data.contact_id,
        company_id=data.company_id,
        owner_id=data.owner_id or user.id,
        blueprint_id=blueprint_id,
        current_blueprint_stage_id=current_blueprint_stage_id,
        name=data.name,
        description=data.description,
        amount=data.amount or 0.0,
        currency=data.currency or 'USD',
        close_date=data.close_date,
        priority=data.priority or 'medium',
        tags=json.dumps(data.tags or []),
        custom_properties=json.dumps(data.custom_properties or {}),
        blueprint_compliance=BlueprintComplianceStatus.COMPLIANT if blueprint_id else BlueprintComplianceStatus.NOT_APPLICABLE
    )
    db.add(deal)
    await db.flush()
    
    # Create timeline event
    await create_timeline_event(
        db, user.tenant_id, TimelineEventType.DEAL_CREATED,
        f"Deal created: {deal.name}",
        actor_id=user.id, actor_name=user.full_name,
        deal_id=deal.id, contact_id=deal.contact_id
    )
    
    # Create audit log
    await create_audit_log(
        db, user.tenant_id, user.id, 'create', 'deal', deal.id,
        after_json={'name': deal.name, 'amount': deal.amount}
    )
    
    return await _deal_to_response(deal, db)


@api_router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return await _deal_to_response(deal, db)


@api_router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: str,
    data: DealUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    before_state = {'name': deal.name, 'amount': deal.amount, 'status': deal.status.value}
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'tags' and value is not None:
            setattr(deal, field, json.dumps(value))
        elif field == 'custom_properties' and value is not None:
            setattr(deal, field, json.dumps(value))
        elif field == 'status' and value == DealStatus.WON:
            deal.status = DealStatus.WON
            deal.won_date = datetime.now(timezone.utc)
        elif field == 'status' and value == DealStatus.LOST:
            deal.status = DealStatus.LOST
            deal.lost_date = datetime.now(timezone.utc)
        else:
            setattr(deal, field, value)
    
    deal.updated_at = datetime.now(timezone.utc)
    deal.last_activity_at = datetime.now(timezone.utc)
    
    await create_audit_log(
        db, user.tenant_id, user.id, 'update', 'deal', deal.id,
        before_json=before_state,
        after_json={'name': deal.name, 'amount': deal.amount, 'status': deal.status.value}
    )
    
    return await _deal_to_response(deal, db)


@api_router.post("/deals/{deal_id}/move-stage", response_model=DealResponse)
async def move_deal_to_stage(
    deal_id: str,
    data: DealStageMove,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Move deal to a new pipeline stage."""
    result = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Get target stage
    result = await db.execute(
        select(PipelineStage).where(PipelineStage.id == data.stage_id)
    )
    target_stage = result.scalar_one_or_none()
    if not target_stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    old_stage_id = deal.stage_id
    deal.stage_id = data.stage_id
    deal.updated_at = datetime.now(timezone.utc)
    deal.last_activity_at = datetime.now(timezone.utc)
    
    # Handle won/lost stages
    if target_stage.is_won_stage:
        deal.status = DealStatus.WON
        deal.won_date = datetime.now(timezone.utc)
    elif target_stage.is_lost_stage:
        deal.status = DealStatus.LOST
        deal.lost_date = datetime.now(timezone.utc)
    
    # Get old stage name for timeline
    old_stage_name = "Unknown"
    if old_stage_id:
        result = await db.execute(
            select(PipelineStage).where(PipelineStage.id == old_stage_id)
        )
        old_stage = result.scalar_one_or_none()
        if old_stage:
            old_stage_name = old_stage.name
    
    # Create timeline event
    await create_timeline_event(
        db, user.tenant_id, TimelineEventType.STAGE_CHANGED,
        f"Stage changed: {old_stage_name} → {target_stage.name}",
        actor_id=user.id, actor_name=user.full_name,
        deal_id=deal.id, contact_id=deal.contact_id,
        metadata={
            'from_stage': old_stage_name,
            'to_stage': target_stage.name,
            'from_stage_id': old_stage_id,
            'to_stage_id': data.stage_id
        }
    )
    
    return await _deal_to_response(deal, db)


async def _deal_to_response(deal: Deal, db: AsyncSession) -> DealResponse:
    try:
        tags = json.loads(deal.tags) if deal.tags else []
    except:
        tags = []
    
    try:
        custom_props = json.loads(deal.custom_properties) if deal.custom_properties else {}
    except:
        custom_props = {}
    
    try:
        completed_stages = json.loads(deal.completed_blueprint_stages) if deal.completed_blueprint_stages else []
    except:
        completed_stages = []
    
    # Get related names
    stage_name = None
    pipeline_name = None
    contact_name = None
    owner_name = None
    
    if deal.stage_id:
        result = await db.execute(
            select(PipelineStage).where(PipelineStage.id == deal.stage_id)
        )
        stage = result.scalar_one_or_none()
        if stage:
            stage_name = stage.name
    
    if deal.pipeline_id:
        result = await db.execute(
            select(Pipeline).where(Pipeline.id == deal.pipeline_id)
        )
        pipeline = result.scalar_one_or_none()
        if pipeline:
            pipeline_name = pipeline.name
    
    if deal.contact_id:
        result = await db.execute(
            select(Contact).where(Contact.id == deal.contact_id)
        )
        contact = result.scalar_one_or_none()
        if contact:
            contact_name = contact.full_name
    
    if deal.owner_id:
        result = await db.execute(
            select(User).where(User.id == deal.owner_id)
        )
        owner = result.scalar_one_or_none()
        if owner:
            owner_name = owner.full_name
    
    return DealResponse(
        id=deal.id,
        tenant_id=deal.tenant_id,
        pipeline_id=deal.pipeline_id,
        stage_id=deal.stage_id,
        contact_id=deal.contact_id,
        company_id=deal.company_id,
        owner_id=deal.owner_id,
        blueprint_id=deal.blueprint_id,
        name=deal.name,
        description=deal.description,
        amount=deal.amount,
        currency=deal.currency,
        status=deal.status,
        close_date=deal.close_date,
        won_date=deal.won_date,
        lost_date=deal.lost_date,
        lost_reason=deal.lost_reason,
        blueprint_compliance=deal.blueprint_compliance,
        current_blueprint_stage_id=deal.current_blueprint_stage_id,
        completed_blueprint_stages=completed_stages,
        priority=deal.priority,
        tags=tags,
        custom_properties=custom_props,
        last_activity_at=deal.last_activity_at,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        stage_name=stage_name,
        pipeline_name=pipeline_name,
        contact_name=contact_name,
        owner_name=owner_name
    )


# ==================== BLUEPRINT ENDPOINTS ====================

@api_router.get("/blueprints", response_model=BlueprintListResponse)
async def list_blueprints(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowBlueprint)
        .options(selectinload(WorkflowBlueprint.stages))
        .where(WorkflowBlueprint.tenant_id == user.tenant_id, WorkflowBlueprint.is_active == True)
    )
    blueprints = result.scalars().all()
    
    return BlueprintListResponse(
        blueprints=[_blueprint_to_response(bp) for bp in blueprints],
        total=len(blueprints)
    )


@api_router.get("/blueprints/{blueprint_id}", response_model=BlueprintResponse)
async def get_blueprint(
    blueprint_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowBlueprint)
        .options(selectinload(WorkflowBlueprint.stages))
        .where(
            WorkflowBlueprint.id == blueprint_id,
            WorkflowBlueprint.tenant_id == user.tenant_id
        )
    )
    blueprint = result.scalar_one_or_none()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return _blueprint_to_response(blueprint)


@api_router.post("/blueprints/validate-move", response_model=ValidateMoveResponse)
async def validate_blueprint_move(
    data: ValidateMoveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate if a deal can move to a target blueprint stage."""
    result = await db.execute(
        select(Deal).where(
            Deal.id == data.deal_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    validation = await validate_stage_move(db, deal, data.target_stage_order, user.tenant_id)
    
    return ValidateMoveResponse(
        can_move=validation['can_move'],
        current_stage_order=validation['current_stage_order'],
        target_stage_order=validation['target_stage_order'],
        missing_requirements=validation['missing_requirements'],
        message=validation['message']
    )


@api_router.post("/blueprints/override-move", response_model=DealResponse)
async def override_blueprint_move(
    data: OverrideMoveRequest,
    user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db)
):
    """Admin override to move deal to a stage even if requirements aren't met."""
    result = await db.execute(
        select(Deal).where(
            Deal.id == data.deal_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    if not deal.blueprint_id:
        raise HTTPException(status_code=400, detail="Deal has no blueprint assigned")
    
    move_result = await move_deal_stage(
        db, deal, data.target_stage_order, user.tenant_id,
        user.id, user.full_name,
        override=True, override_reason=data.reason
    )
    
    if not move_result['success']:
        raise HTTPException(status_code=400, detail=move_result['message'])
    
    return await _deal_to_response(move_result['deal'], db)


@api_router.get("/deals/{deal_id}/blueprint-progress")
async def get_deal_blueprint_progress(
    deal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the blueprint progress for a deal."""
    result = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    if not deal.blueprint_id:
        return {
            'has_blueprint': False,
            'progress': None
        }
    
    result = await db.execute(
        select(WorkflowBlueprint)
        .options(selectinload(WorkflowBlueprint.stages))
        .where(WorkflowBlueprint.id == deal.blueprint_id)
    )
    blueprint = result.scalar_one_or_none()
    
    if not blueprint:
        return {
            'has_blueprint': False,
            'progress': None
        }
    
    progress = await get_blueprint_progress(deal, blueprint)
    
    return {
        'has_blueprint': True,
        'blueprint_name': blueprint.name,
        'compliance_status': deal.blueprint_compliance.value,
        'progress': progress
    }


def _blueprint_to_response(blueprint: WorkflowBlueprint) -> BlueprintResponse:
    stages = []
    for s in sorted(blueprint.stages, key=lambda x: x.stage_order):
        try:
            req_props = json.loads(s.required_properties) if s.required_properties else []
        except:
            req_props = []
        
        try:
            req_actions = json.loads(s.required_actions) if s.required_actions else []
        except:
            req_actions = []
        
        try:
            entry_auto = json.loads(s.entry_automations) if s.entry_automations else []
        except:
            entry_auto = []
        
        try:
            exit_auto = json.loads(s.exit_automations) if s.exit_automations else []
        except:
            exit_auto = []
        
        stages.append(BlueprintStageResponse(
            id=s.id,
            blueprint_id=s.blueprint_id,
            name=s.name,
            description=s.description,
            stage_order=s.stage_order,
            required_properties=req_props,
            required_actions=req_actions,
            entry_automations=entry_auto,
            exit_automations=exit_auto,
            color=s.color,
            icon=s.icon,
            is_start_stage=s.is_start_stage,
            is_end_stage=s.is_end_stage,
            is_milestone=s.is_milestone,
            created_at=s.created_at,
            updated_at=s.updated_at
        ))
    
    return BlueprintResponse(
        id=blueprint.id,
        tenant_id=blueprint.tenant_id,
        name=blueprint.name,
        description=blueprint.description,
        version=blueprint.version,
        is_active=blueprint.is_active,
        is_default=blueprint.is_default,
        allow_skip_stages=blueprint.allow_skip_stages,
        allow_admin_override=blueprint.allow_admin_override,
        require_override_reason=blueprint.require_override_reason,
        stages=stages,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at
    )


# ==================== TIMELINE ENDPOINTS ====================

@api_router.get("/timeline", response_model=TimelineListResponse)
async def list_timeline_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    event_type: Optional[TimelineEventType] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(TimelineEvent).where(TimelineEvent.tenant_id == user.tenant_id)
    count_query = select(func.count(TimelineEvent.id)).where(TimelineEvent.tenant_id == user.tenant_id)
    
    if contact_id:
        query = query.where(TimelineEvent.contact_id == contact_id)
        count_query = count_query.where(TimelineEvent.contact_id == contact_id)
    
    if deal_id:
        query = query.where(TimelineEvent.deal_id == deal_id)
        count_query = count_query.where(TimelineEvent.deal_id == deal_id)
    
    if event_type:
        query = query.where(TimelineEvent.event_type == event_type)
        count_query = count_query.where(TimelineEvent.event_type == event_type)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(TimelineEvent.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    return TimelineListResponse(
        events=[_timeline_to_response(e) for e in events],
        total=total,
        page=page,
        page_size=page_size
    )


@api_router.post("/timeline", response_model=TimelineEventResponse, status_code=201)
async def create_timeline_event_endpoint(
    data: TimelineEventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    event = await create_timeline_event(
        db, user.tenant_id, data.event_type, data.title,
        actor_id=user.id, actor_name=user.full_name,
        contact_id=data.contact_id, deal_id=data.deal_id,
        company_id=data.company_id, description=data.description,
        metadata=data.metadata_json, visibility=data.visibility,
        due_date=data.due_date
    )
    return _timeline_to_response(event)


def _timeline_to_response(event: TimelineEvent) -> TimelineEventResponse:
    try:
        metadata = json.loads(event.metadata_json) if event.metadata_json else {}
    except:
        metadata = {}
    
    return TimelineEventResponse(
        id=event.id,
        tenant_id=event.tenant_id,
        contact_id=event.contact_id,
        deal_id=event.deal_id,
        company_id=event.company_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        metadata_json=metadata,
        visibility=event.visibility,
        actor_id=event.actor_id,
        actor_name=event.actor_name,
        is_completed=event.is_completed,
        due_date=event.due_date,
        completed_at=event.completed_at,
        created_at=event.created_at,
        updated_at=event.updated_at
    )


# ==================== KANBAN BOARD ENDPOINT ====================

@api_router.get("/pipelines/{pipeline_id}/kanban")
async def get_kanban_board(
    pipeline_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pipeline data formatted for Kanban board display."""
    # Get pipeline with stages
    result = await db.execute(
        select(Pipeline)
        .options(selectinload(Pipeline.stages))
        .where(
            Pipeline.id == pipeline_id,
            Pipeline.tenant_id == user.tenant_id
        )
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    # Get all deals in this pipeline
    result = await db.execute(
        select(Deal).where(
            Deal.pipeline_id == pipeline_id,
            Deal.tenant_id == user.tenant_id
        )
    )
    deals = result.scalars().all()
    
    # Organize deals by stage
    columns = []
    for stage in sorted(pipeline.stages, key=lambda s: s.display_order):
        stage_deals = [d for d in deals if d.stage_id == stage.id]
        
        deal_cards = []
        for deal in stage_deals:
            # Get contact name
            contact_name = None
            if deal.contact_id:
                contact_result = await db.execute(
                    select(Contact).where(Contact.id == deal.contact_id)
                )
                contact = contact_result.scalar_one_or_none()
                if contact:
                    contact_name = contact.full_name
            
            deal_cards.append({
                'id': deal.id,
                'name': deal.name,
                'amount': deal.amount,
                'currency': deal.currency,
                'contact_name': contact_name,
                'contact_id': deal.contact_id,
                'priority': deal.priority,
                'status': deal.status.value,
                'blueprint_compliance': deal.blueprint_compliance.value,
                'created_at': deal.created_at.isoformat(),
                'last_activity_at': deal.last_activity_at.isoformat() if deal.last_activity_at else None
            })
        
        columns.append({
            'id': stage.id,
            'name': stage.name,
            'color': stage.color,
            'probability': stage.probability,
            'is_won_stage': stage.is_won_stage,
            'is_lost_stage': stage.is_lost_stage,
            'display_order': stage.display_order,
            'deals': deal_cards,
            'deal_count': len(deal_cards),
            'total_value': sum(d['amount'] for d in deal_cards)
        })
    
    return {
        'pipeline': {
            'id': pipeline.id,
            'name': pipeline.name,
            'description': pipeline.description
        },
        'columns': columns,
        'total_deals': len(deals),
        'total_value': sum(d.amount for d in deals)
    }


# ==================== NEW FEATURE IMPORTS & ROUTES ====================
from app.models import (
    Conversation, Message, MessageChannel, MessageDirection, MessageStatus,
    Workflow, WorkflowRun, ScheduledJob, WorkflowStatus, TriggerType, ActionType, WorkflowRunStatus,
    Form, FormSubmission, LandingPage, FieldType
)
from app.schemas import (
    MessageCreate, MessageResponse, ConversationResponse, ConversationListResponse, InboxStats,
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowListResponse,
    WorkflowRunResponse, WorkflowRunListResponse, TriggerWorkflowRequest,
    FormCreate, FormUpdate, FormResponse, FormListResponse,
    PublicFormResponse, FormSubmissionCreate, FormSubmissionResponse, FormSubmissionListResponse,
    LandingPageCreate, LandingPageUpdate, LandingPageResponse, LandingPageListResponse
)
from app.services import messaging_service, automation_engine

# Setup extended routes BEFORE including the router
from app.api.extended_routes import setup_routes
setup_routes(
    api_router, get_db, get_current_user,
    Contact, Pipeline, PipelineStage, Deal, DealStatus, BlueprintComplianceStatus,
    TimelineEvent, TimelineEventType, VisibilityScope, Tenant,
    Conversation, Message, MessageChannel, MessageDirection, MessageStatus,
    Workflow, WorkflowRun, WorkflowStatus, TriggerType, WorkflowRunStatus,
    Form, FormSubmission, LandingPage,
    MessageCreate, MessageResponse, ConversationResponse, ConversationListResponse, InboxStats,
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowListResponse,
    WorkflowRunResponse, WorkflowRunListResponse, TriggerWorkflowRequest,
    FormCreate, FormUpdate, FormResponse, FormListResponse,
    PublicFormResponse, FormSubmissionCreate, FormSubmissionResponse, FormSubmissionListResponse,
    LandingPageCreate, LandingPageUpdate, LandingPageResponse, LandingPageListResponse,
    messaging_service, automation_engine, User
)

# Setup workspace and calculation routes (Multi-CRM architecture)
from app.api.workspace_routes import router as workspace_router
from app.api.calculation_routes import router as calculation_router
from app.api.outreach_routes import router as outreach_router
api_router.include_router(workspace_router)
api_router.include_router(calculation_router)
api_router.include_router(outreach_router)

# Include router AFTER all routes are added
app.include_router(api_router)


# ==================== SEED DATA ====================

async def seed_demo_data():
    """Seed demo tenant, users, pipeline, and NLA workflow blueprint."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if demo tenant exists
            result = await db.execute(
                select(Tenant).where(Tenant.slug == 'demo')
            )
            if result.scalar_one_or_none():
                logger.info("Demo data already exists, skipping seed")
                return
            
            logger.info("Seeding demo data...")
            
            # Create demo tenant
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name="Demo Company",
                slug="demo",
                domain="demo.crm-os.local"
            )
            db.add(tenant)
            await db.flush()
            
            # Create users
            admin_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                email="admin@demo.com",
                password_hash=get_password_hash("admin123"),
                first_name="Admin",
                last_name="User",
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            
            manager_user = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                email="manager@demo.com",
                password_hash=get_password_hash("manager123"),
                first_name="Sarah",
                last_name="Manager",
                role=UserRole.MANAGER
            )
            db.add(manager_user)
            
            sales_rep = User(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                email="sales@demo.com",
                password_hash=get_password_hash("sales123"),
                first_name="John",
                last_name="Sales",
                role=UserRole.SALES_REP
            )
            db.add(sales_rep)
            await db.flush()
            
            # Create Frylow Sales Pipeline
            pipeline = Pipeline(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                name="Frylow Sales Pipeline",
                description="Sales pipeline for Frylow oil savings solutions",
                is_default=True,
                display_order=0
            )
            db.add(pipeline)
            await db.flush()
            
            # Create pipeline stages (matching blueprint)
            stage_data = [
                {"name": "Estimate Requested", "probability": 5, "color": "#6366F1"},
                {"name": "Sign-Up Sent", "probability": 10, "color": "#8B5CF6"},
                {"name": "Form Submitted", "probability": 20, "color": "#A855F7"},
                {"name": "Client Profile Created", "probability": 25, "color": "#D946EF"},
                {"name": "Questionnaire Sent", "probability": 30, "color": "#EC4899"},
                {"name": "Questionnaire Completed", "probability": 40, "color": "#F43F5E"},
                {"name": "Docs Received", "probability": 50, "color": "#F97316"},
                {"name": "ID Verified", "probability": 55, "color": "#EAB308"},
                {"name": "Estimate Prepared", "probability": 60, "color": "#84CC16"},
                {"name": "Estimate Approved", "probability": 70, "color": "#22C55E"},
                {"name": "Engagement Letter Signed", "probability": 80, "color": "#14B8A6"},
                {"name": "Banking Info Captured", "probability": 85, "color": "#06B6D4"},
                {"name": "Final Docs Signed (1040)", "probability": 90, "color": "#0EA5E9"},
                {"name": "Complete + Review Requested", "probability": 95, "color": "#3B82F6", "is_won_stage": True},
                {"name": "Commission Routed", "probability": 100, "color": "#10B981", "is_won_stage": True},
            ]
            
            pipeline_stages = []
            for i, sd in enumerate(stage_data):
                stage = PipelineStage(
                    id=str(uuid.uuid4()),
                    pipeline_id=pipeline.id,
                    name=sd["name"],
                    display_order=i,
                    probability=sd["probability"],
                    color=sd["color"],
                    is_won_stage=sd.get("is_won_stage", False),
                    is_lost_stage=sd.get("is_lost_stage", False)
                )
                db.add(stage)
                pipeline_stages.append(stage)
            await db.flush()
            
            # Create Frylow Sales Workflow Blueprint
            blueprint = WorkflowBlueprint(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                name="Frylow Sales Workflow",
                description="Sales workflow with required actions and automations for Frylow",
                is_default=True,
                allow_skip_stages=False,
                allow_admin_override=True,
                require_override_reason=True
            )
            db.add(blueprint)
            await db.flush()
            
            # Create blueprint stages with requirements
            blueprint_stage_data = [
                {
                    "name": "Estimate Requested",
                    "required_properties": ["email", "phone"],
                    "required_actions": [],
                    "entry_automations": [{"type": "send_sms", "template": "estimate_welcome"}],
                    "is_start_stage": True,
                    "icon": "file-text",
                    "color": "#6366F1"
                },
                {
                    "name": "Sign-Up Sent",
                    "required_properties": ["email"],
                    "required_actions": ["estimate_sent"],
                    "entry_automations": [{"type": "send_email", "template": "signup_link"}],
                    "icon": "send",
                    "color": "#8B5CF6"
                },
                {
                    "name": "Form Submitted",
                    "required_properties": ["first_name", "last_name", "email"],
                    "required_actions": ["signup_completed"],
                    "entry_automations": [{"type": "send_sms", "template": "form_received"}],
                    "is_milestone": True,
                    "icon": "check-circle",
                    "color": "#A855F7"
                },
                {
                    "name": "Client Profile Created",
                    "required_properties": ["first_name", "last_name", "email", "phone"],
                    "required_actions": ["profile_created"],
                    "icon": "user",
                    "color": "#D946EF"
                },
                {
                    "name": "Questionnaire Sent",
                    "required_properties": [],
                    "required_actions": ["questionnaire_sent"],
                    "entry_automations": [{"type": "send_email", "template": "questionnaire_link"}],
                    "icon": "clipboard",
                    "color": "#EC4899"
                },
                {
                    "name": "Questionnaire Completed",
                    "required_properties": [],
                    "required_actions": ["questionnaire_completed"],
                    "is_milestone": True,
                    "icon": "clipboard-check",
                    "color": "#F43F5E"
                },
                {
                    "name": "Docs Received",
                    "required_properties": [],
                    "required_actions": ["docs_uploaded"],
                    "entry_automations": [{"type": "request_document", "doc_type": "tax_documents"}],
                    "icon": "folder",
                    "color": "#F97316"
                },
                {
                    "name": "ID Verified",
                    "required_properties": [],
                    "required_actions": ["id_verified"],
                    "entry_automations": [{"type": "request_document", "doc_type": "id_verification"}],
                    "is_milestone": True,
                    "icon": "shield-check",
                    "color": "#EAB308"
                },
                {
                    "name": "Estimate Prepared",
                    "required_properties": [],
                    "required_actions": ["estimate_prepared"],
                    "icon": "calculator",
                    "color": "#84CC16"
                },
                {
                    "name": "Estimate Approved",
                    "required_properties": [],
                    "required_actions": ["estimate_approved"],
                    "is_milestone": True,
                    "icon": "thumbs-up",
                    "color": "#22C55E"
                },
                {
                    "name": "Engagement Letter Signed",
                    "required_properties": [],
                    "required_actions": ["engagement_letter_signed"],
                    "entry_automations": [{"type": "e_signature_request", "doc_type": "engagement_letter"}],
                    "icon": "file-signature",
                    "color": "#14B8A6"
                },
                {
                    "name": "Banking Info Captured",
                    "required_properties": [],
                    "required_actions": ["banking_info_captured"],
                    "icon": "building-bank",
                    "color": "#06B6D4"
                },
                {
                    "name": "Final Docs Signed (1040)",
                    "required_properties": [],
                    "required_actions": ["final_docs_signed"],
                    "entry_automations": [{"type": "e_signature_request", "doc_type": "1040"}],
                    "is_milestone": True,
                    "icon": "file-check",
                    "color": "#0EA5E9"
                },
                {
                    "name": "Complete + Review Requested",
                    "required_properties": [],
                    "required_actions": ["filing_complete"],
                    "entry_automations": [
                        {"type": "send_sms", "template": "congratulations"},
                        {"type": "request_review", "platform": "google"}
                    ],
                    "is_milestone": True,
                    "icon": "star",
                    "color": "#3B82F6"
                },
                {
                    "name": "Commission Routed",
                    "required_properties": [],
                    "required_actions": ["commission_calculated"],
                    "entry_automations": [{"type": "internal_notification", "channel": "accounting"}],
                    "is_end_stage": True,
                    "icon": "dollar-sign",
                    "color": "#10B981"
                },
            ]
            
            for i, bsd in enumerate(blueprint_stage_data):
                bp_stage = BlueprintStage(
                    id=str(uuid.uuid4()),
                    blueprint_id=blueprint.id,
                    name=bsd["name"],
                    stage_order=i + 1,
                    required_properties=json.dumps(bsd.get("required_properties", [])),
                    required_actions=json.dumps(bsd.get("required_actions", [])),
                    entry_automations=json.dumps(bsd.get("entry_automations", [])),
                    exit_automations=json.dumps(bsd.get("exit_automations", [])),
                    color=bsd.get("color", "#3B82F6"),
                    icon=bsd.get("icon", "circle"),
                    is_start_stage=bsd.get("is_start_stage", False),
                    is_end_stage=bsd.get("is_end_stage", False),
                    is_milestone=bsd.get("is_milestone", False)
                )
                db.add(bp_stage)
            await db.flush()
            
            # Create sample contacts
            contacts_data = [
                {"first_name": "Michael", "last_name": "Johnson", "email": "michael.j@example.com", "phone": "+1-555-0101", "company_name": "Johnson LLC"},
                {"first_name": "Emily", "last_name": "Davis", "email": "emily.d@example.com", "phone": "+1-555-0102", "company_name": "Davis & Co"},
                {"first_name": "Robert", "last_name": "Wilson", "email": "robert.w@example.com", "phone": "+1-555-0103", "company_name": "Wilson Industries"},
                {"first_name": "Jennifer", "last_name": "Brown", "email": "jennifer.b@example.com", "phone": "+1-555-0104", "company_name": "Brown Services"},
                {"first_name": "David", "last_name": "Miller", "email": "david.m@example.com", "phone": "+1-555-0105", "company_name": "Miller Corp"},
            ]
            
            contacts = []
            for cd in contacts_data:
                contact = Contact(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant.id,
                    owner_id=sales_rep.id,
                    first_name=cd["first_name"],
                    last_name=cd["last_name"],
                    email=cd["email"],
                    phone=cd["phone"],
                    company_name=cd["company_name"],
                    lifecycle_stage="opportunity",
                    lead_source="Website"
                )
                db.add(contact)
                contacts.append(contact)
            await db.flush()
            
            # Create sample deals at various stages
            deals_data = [
                {"name": "Johnson LLC - 2024 Tax Return", "amount": 2500, "stage_idx": 0, "contact_idx": 0},
                {"name": "Davis & Co - Business Filing", "amount": 4500, "stage_idx": 2, "contact_idx": 1},
                {"name": "Wilson Industries - Corporate Tax", "amount": 8000, "stage_idx": 5, "contact_idx": 2},
                {"name": "Brown Services - Annual Filing", "amount": 3200, "stage_idx": 8, "contact_idx": 3},
                {"name": "Miller Corp - Tax Planning", "amount": 5500, "stage_idx": 12, "contact_idx": 4},
            ]
            
            # Get first blueprint stage for initial stage
            result = await db.execute(
                select(BlueprintStage)
                .where(BlueprintStage.blueprint_id == blueprint.id)
                .order_by(BlueprintStage.stage_order)
            )
            bp_stages = result.scalars().all()
            
            for dd in deals_data:
                deal = Deal(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant.id,
                    pipeline_id=pipeline.id,
                    stage_id=pipeline_stages[dd["stage_idx"]].id,
                    contact_id=contacts[dd["contact_idx"]].id,
                    owner_id=sales_rep.id,
                    blueprint_id=blueprint.id,
                    current_blueprint_stage_id=bp_stages[dd["stage_idx"]].id if dd["stage_idx"] < len(bp_stages) else bp_stages[0].id,
                    name=dd["name"],
                    amount=dd["amount"],
                    currency="USD",
                    status=DealStatus.OPEN,
                    blueprint_compliance=BlueprintComplianceStatus.COMPLIANT
                )
                db.add(deal)
            
            # Create Frylow ROI Calculator definition
            from app.models import CalculationDefinition
            
            frylow_calc_input_schema = [
                {
                    "name": "number_of_fryers",
                    "type": "integer",
                    "label": "Number of Fryers",
                    "required": True,
                    "placeholder": "e.g. 4",
                    "help_text": "Total number of fryers in the kitchen",
                    "min": 1,
                    "max": 50
                },
                {
                    "name": "fryer_capacities",
                    "type": "multi_select",
                    "label": "Fryer Capacities",
                    "required": True,
                    "help_text": "Select all fryer sizes used",
                    "options": [
                        {"value": "16L", "label": "16 Liters (Small)"},
                        {"value": "30L", "label": "30 Liters (Medium)"},
                        {"value": "45L", "label": "45 Liters (Large)"}
                    ]
                },
                {
                    "name": "oil_units",
                    "type": "select",
                    "label": "Oil Purchase Units",
                    "required": True,
                    "options": [
                        {"value": "boxes", "label": "Boxes"},
                        {"value": "gallons", "label": "Gallons"},
                        {"value": "liters", "label": "Liters"}
                    ]
                },
                {
                    "name": "quantity_per_month",
                    "type": "integer",
                    "label": "Quantity Purchased Per Month",
                    "required": True,
                    "placeholder": "e.g. 20",
                    "min": 1
                },
                {
                    "name": "cost_per_unit",
                    "type": "currency",
                    "label": "Cost Per Unit ($)",
                    "required": True,
                    "placeholder": "e.g. 45.00",
                    "min": 0
                }
            ]
            
            frylow_calc_output_schema = [
                {
                    "name": "monthly_oil_spend",
                    "type": "currency",
                    "label": "Monthly Oil Spend",
                    "description": "Current monthly expenditure on cooking oil"
                },
                {
                    "name": "yearly_oil_spend",
                    "type": "currency",
                    "label": "Yearly Oil Spend",
                    "description": "Projected annual expenditure on cooking oil"
                },
                {
                    "name": "estimated_savings_low",
                    "type": "currency",
                    "label": "Estimated Savings (Low)",
                    "description": "Conservative savings estimate (30%)"
                },
                {
                    "name": "estimated_savings_high",
                    "type": "currency",
                    "label": "Estimated Savings (High)",
                    "description": "Optimistic savings estimate (50%)"
                },
                {
                    "name": "recommended_device_quantity",
                    "type": "integer",
                    "label": "Recommended Device Quantity",
                    "description": "Number of Frylow devices needed"
                },
                {
                    "name": "recommended_device_size",
                    "type": "text",
                    "label": "Recommended Device Size",
                    "description": "Best Frylow device size for your setup"
                }
            ]
            
            import json as json_module
            frylow_calc = CalculationDefinition(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                name="Frylow ROI Calculator",
                slug="frylow-roi-calculator",
                description="Calculate oil savings and recommended Frylow device configuration",
                version=1,
                is_active=True,
                input_schema=json_module.dumps(frylow_calc_input_schema),
                output_schema=json_module.dumps(frylow_calc_output_schema),
                editable_by_roles=json_module.dumps(["admin", "manager", "member"]),
                auto_run_on_input_change=True
            )
            db.add(frylow_calc)
            
            await db.commit()
            logger.info("Demo data seeded successfully!")
            
        except Exception as e:
            logger.error(f"Error seeding demo data: {e}")
            await db.rollback()
            raise
