"""API routes for Forms and Landing Pages."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import json
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import (
    User, Contact, Deal, DealStatus, BlueprintComplianceStatus,
    Form, FormSubmission, LandingPage, Pipeline, PipelineStage,
    TimelineEvent, TimelineEventType, VisibilityScope, TriggerType
)
from app.schemas.forms import (
    FormCreate, FormUpdate, FormResponse, FormListResponse,
    PublicFormResponse, FormSubmissionCreate, FormSubmissionResponse, FormSubmissionListResponse,
    LandingPageCreate, LandingPageUpdate, LandingPageResponse, LandingPageListResponse
)
from app.services import automation_engine

router = APIRouter(tags=["forms"])


async def get_current_user_dep(user = None):
    """Placeholder - will be replaced with actual dependency."""
    return user


# ==================== FORMS ====================

@router.get("/forms", response_model=FormListResponse)
async def list_forms(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """List all forms."""
    result = await db.execute(
        select(Form)
        .where(Form.tenant_id == user.tenant_id)
        .order_by(Form.created_at.desc())
    )
    forms = result.scalars().all()
    
    return FormListResponse(
        forms=[_form_to_response(f) for f in forms],
        total=len(forms)
    )


@router.post("/forms", response_model=FormResponse, status_code=201)
async def create_form(
    data: FormCreate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Create a new form."""
    # Check slug uniqueness
    result = await db.execute(
        select(Form).where(
            Form.tenant_id == user.tenant_id,
            Form.slug == data.slug
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Form slug already exists")
    
    form = Form(
        tenant_id=user.tenant_id,
        name=data.name,
        description=data.description,
        slug=data.slug,
        fields=json.dumps(data.fields),
        submit_button_text=data.submit_button_text,
        success_message=data.success_message,
        redirect_url=data.redirect_url,
        create_contact=data.create_contact,
        create_deal=data.create_deal,
        assign_pipeline_id=data.assign_pipeline_id,
        assign_stage_id=data.assign_stage_id,
        assign_owner_id=data.assign_owner_id,
        default_tags=json.dumps(data.default_tags),
        is_active=data.is_active,
        is_public=data.is_public,
        theme=data.theme,
        custom_css=data.custom_css
    )
    db.add(form)
    await db.flush()
    
    return _form_to_response(form)


@router.get("/forms/{form_id}", response_model=FormResponse)
async def get_form(
    form_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Get a form by ID."""
    result = await db.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == user.tenant_id
        )
    )
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    return _form_to_response(form)


@router.put("/forms/{form_id}", response_model=FormResponse)
async def update_form(
    form_id: str,
    data: FormUpdate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Update a form."""
    result = await db.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == user.tenant_id
        )
    )
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'fields' and value is not None:
            setattr(form, field, json.dumps(value))
        elif field == 'default_tags' and value is not None:
            setattr(form, field, json.dumps(value))
        else:
            setattr(form, field, value)
    
    form.updated_at = datetime.now(timezone.utc)
    
    return _form_to_response(form)


@router.delete("/forms/{form_id}", status_code=204)
async def delete_form(
    form_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Delete a form."""
    result = await db.execute(
        select(Form).where(
            Form.id == form_id,
            Form.tenant_id == user.tenant_id
        )
    )
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    await db.delete(form)


@router.get("/forms/{form_id}/submissions", response_model=FormSubmissionListResponse)
async def list_form_submissions(
    form_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """List submissions for a form."""
    query = select(FormSubmission).where(
        FormSubmission.form_id == form_id,
        FormSubmission.tenant_id == user.tenant_id
    )
    count_query = select(func.count(FormSubmission.id)).where(
        FormSubmission.form_id == form_id,
        FormSubmission.tenant_id == user.tenant_id
    )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(FormSubmission.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    return FormSubmissionListResponse(
        submissions=[_submission_to_response(s) for s in submissions],
        total=total,
        page=page,
        page_size=page_size
    )


# ==================== PUBLIC FORM ENDPOINTS ====================

@router.get("/public/forms/{tenant_slug}/{form_slug}", response_model=PublicFormResponse)
async def get_public_form(
    tenant_slug: str,
    form_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a public form for embedding."""
    from app.models import Tenant
    
    # Find tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Find form
    result = await db.execute(
        select(Form).where(
            Form.tenant_id == tenant.id,
            Form.slug == form_slug,
            Form.is_active == True,
            Form.is_public == True
        )
    )
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    try:
        fields = json.loads(form.fields) if form.fields else []
    except:
        fields = []
    
    return PublicFormResponse(
        id=form.id,
        name=form.name,
        description=form.description,
        fields=fields,
        submit_button_text=form.submit_button_text,
        theme=form.theme,
        custom_css=form.custom_css
    )


@router.post("/public/forms/{tenant_slug}/{form_slug}/submit", response_model=FormSubmissionResponse)
async def submit_public_form(
    tenant_slug: str,
    form_slug: str,
    data: FormSubmissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Submit a public form."""
    from app.models import Tenant
    
    # Find tenant
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Find form
    result = await db.execute(
        select(Form).where(
            Form.tenant_id == tenant.id,
            Form.slug == form_slug,
            Form.is_active == True,
            Form.is_public == True
        )
    )
    form = result.scalar_one_or_none()
    
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Process form submission
    contact_id = None
    deal_id = None
    
    # Create or update contact
    if form.create_contact:
        contact = await _create_or_update_contact(db, tenant.id, form, data.data)
        contact_id = contact.id
    
    # Create deal if configured
    if form.create_deal and contact_id:
        deal = await _create_deal_from_form(db, tenant.id, form, contact_id, data.data)
        deal_id = deal.id
    
    # Create submission record
    submission = FormSubmission(
        tenant_id=tenant.id,
        form_id=form.id,
        contact_id=contact_id,
        deal_id=deal_id,
        data=json.dumps(data.data),
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
        utm_term=data.utm_term,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
        referrer=request.headers.get('referer')
    )
    db.add(submission)
    
    # Update form stats
    form.submission_count += 1
    
    await db.flush()
    
    # Create timeline event
    if contact_id:
        timeline = TimelineEvent(
            tenant_id=tenant.id,
            contact_id=contact_id,
            deal_id=deal_id,
            event_type=TimelineEventType.FORM_SUBMITTED,
            title=f"Form submitted: {form.name}",
            metadata_json=json.dumps({
                'form_id': form.id,
                'form_name': form.name,
                'submission_id': submission.id
            }),
            visibility=VisibilityScope.INTERNAL_ONLY
        )
        db.add(timeline)
    
    # Trigger workflows
    await automation_engine.find_and_trigger_workflows(
        db, tenant.id, TriggerType.FORM_SUBMITTED,
        {'form_id': form.id, 'form_name': form.name, 'submission_id': submission.id},
        contact_id=contact_id, deal_id=deal_id
    )
    
    return _submission_to_response(submission)


# ==================== LANDING PAGES ====================

@router.get("/landing-pages", response_model=LandingPageListResponse)
async def list_landing_pages(
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """List all landing pages."""
    result = await db.execute(
        select(LandingPage)
        .where(LandingPage.tenant_id == user.tenant_id)
        .order_by(LandingPage.created_at.desc())
    )
    pages = result.scalars().all()
    
    return LandingPageListResponse(
        pages=[_landing_page_to_response(p) for p in pages],
        total=len(pages)
    )


@router.post("/landing-pages", response_model=LandingPageResponse, status_code=201)
async def create_landing_page(
    data: LandingPageCreate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Create a new landing page."""
    # Check slug uniqueness
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.tenant_id == user.tenant_id,
            LandingPage.slug == data.slug
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Landing page slug already exists")
    
    page = LandingPage(
        tenant_id=user.tenant_id,
        name=data.name,
        slug=data.slug,
        content=json.dumps(data.content),
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        theme=data.theme,
        custom_css=data.custom_css,
        header_code=data.header_code,
        footer_code=data.footer_code,
        form_id=data.form_id,
        is_published=data.is_published
    )
    db.add(page)
    await db.flush()
    
    return _landing_page_to_response(page)


@router.get("/landing-pages/{page_id}", response_model=LandingPageResponse)
async def get_landing_page(
    page_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Get a landing page by ID."""
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.id == page_id,
            LandingPage.tenant_id == user.tenant_id
        )
    )
    page = result.scalar_one_or_none()
    
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")
    
    return _landing_page_to_response(page)


@router.put("/landing-pages/{page_id}", response_model=LandingPageResponse)
async def update_landing_page(
    page_id: str,
    data: LandingPageUpdate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Update a landing page."""
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.id == page_id,
            LandingPage.tenant_id == user.tenant_id
        )
    )
    page = result.scalar_one_or_none()
    
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'content' and value is not None:
            setattr(page, field, json.dumps(value))
        else:
            setattr(page, field, value)
    
    page.updated_at = datetime.now(timezone.utc)
    
    return _landing_page_to_response(page)


# ==================== HELPER FUNCTIONS ====================

async def _create_or_update_contact(
    db: AsyncSession,
    tenant_id: str,
    form: Form,
    data: dict
) -> Contact:
    """Create or update a contact from form data."""
    # Extract email from data using field mappings
    try:
        fields = json.loads(form.fields) if form.fields else []
    except:
        fields = []
    
    email = None
    first_name = None
    last_name = None
    phone = None
    
    for field in fields:
        mapping = field.get('mapping')
        field_id = field.get('id')
        value = data.get(field_id)
        
        if mapping == 'email' and value:
            email = value
        elif mapping == 'first_name' and value:
            first_name = value
        elif mapping == 'last_name' and value:
            last_name = value
        elif mapping == 'phone' and value:
            phone = value
    
    # Also check direct field names
    email = email or data.get('email')
    first_name = first_name or data.get('first_name') or data.get('firstName')
    last_name = last_name or data.get('last_name') or data.get('lastName')
    phone = phone or data.get('phone')
    
    # Try to find existing contact by email
    contact = None
    if email:
        result = await db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.email == email
            )
        )
        contact = result.scalar_one_or_none()
    
    if contact:
        # Update existing contact
        if first_name:
            contact.first_name = first_name
        if last_name:
            contact.last_name = last_name
        if phone:
            contact.phone = phone
        contact.updated_at = datetime.now(timezone.utc)
        contact.last_activity_at = datetime.now(timezone.utc)
    else:
        # Create new contact
        try:
            tags = json.loads(form.default_tags) if form.default_tags else []
        except:
            tags = []
        
        contact = Contact(
            tenant_id=tenant_id,
            owner_id=form.assign_owner_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            lifecycle_stage='lead',
            lead_source='Form',
            tags=json.dumps(tags)
        )
        db.add(contact)
        await db.flush()
    
    return contact


async def _create_deal_from_form(
    db: AsyncSession,
    tenant_id: str,
    form: Form,
    contact_id: str,
    data: dict
) -> Deal:
    """Create a deal from form submission."""
    pipeline_id = form.assign_pipeline_id
    stage_id = form.assign_stage_id
    
    # Get default pipeline if not specified
    if not pipeline_id:
        result = await db.execute(
            select(Pipeline).where(
                Pipeline.tenant_id == tenant_id,
                Pipeline.is_default == True
            )
        )
        default_pipeline = result.scalar_one_or_none()
        if default_pipeline:
            pipeline_id = default_pipeline.id
    
    # Get first stage if not specified
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
    
    # Get contact name for deal name
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    deal_name = data.get('deal_name') or f"{contact.full_name if contact else 'New'} - {form.name}"
    
    deal = Deal(
        tenant_id=tenant_id,
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        contact_id=contact_id,
        owner_id=form.assign_owner_id,
        name=deal_name,
        status=DealStatus.OPEN,
        blueprint_compliance=BlueprintComplianceStatus.NOT_APPLICABLE
    )
    db.add(deal)
    await db.flush()
    
    return deal


def _form_to_response(form: Form) -> FormResponse:
    try:
        fields = json.loads(form.fields) if form.fields else []
    except:
        fields = []
    
    try:
        tags = json.loads(form.default_tags) if form.default_tags else []
    except:
        tags = []
    
    return FormResponse(
        id=form.id,
        tenant_id=form.tenant_id,
        name=form.name,
        description=form.description,
        slug=form.slug,
        is_active=form.is_active,
        is_public=form.is_public,
        fields=fields,
        submit_button_text=form.submit_button_text,
        success_message=form.success_message,
        redirect_url=form.redirect_url,
        create_contact=form.create_contact,
        create_deal=form.create_deal,
        assign_pipeline_id=form.assign_pipeline_id,
        assign_stage_id=form.assign_stage_id,
        assign_owner_id=form.assign_owner_id,
        default_tags=tags,
        theme=form.theme,
        custom_css=form.custom_css,
        submission_count=form.submission_count,
        created_at=form.created_at,
        updated_at=form.updated_at
    )


def _submission_to_response(submission: FormSubmission) -> FormSubmissionResponse:
    try:
        data = json.loads(submission.data) if submission.data else {}
    except:
        data = {}
    
    return FormSubmissionResponse(
        id=submission.id,
        tenant_id=submission.tenant_id,
        form_id=submission.form_id,
        contact_id=submission.contact_id,
        deal_id=submission.deal_id,
        data=data,
        utm_source=submission.utm_source,
        utm_medium=submission.utm_medium,
        utm_campaign=submission.utm_campaign,
        ip_address=submission.ip_address,
        created_at=submission.created_at
    )


def _landing_page_to_response(page: LandingPage) -> LandingPageResponse:
    try:
        content = json.loads(page.content) if page.content else {}
    except:
        content = {}
    
    return LandingPageResponse(
        id=page.id,
        tenant_id=page.tenant_id,
        name=page.name,
        slug=page.slug,
        is_published=page.is_published,
        content=content,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        theme=page.theme,
        custom_css=page.custom_css,
        header_code=page.header_code,
        footer_code=page.footer_code,
        form_id=page.form_id,
        view_count=page.view_count,
        created_at=page.created_at,
        updated_at=page.updated_at
    )
