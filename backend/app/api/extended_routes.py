"""Additional API endpoints for Inbox, Workflows, Forms, and Landing Pages."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
import json
from datetime import datetime, timezone

router = APIRouter()


def setup_routes(
    api_router: APIRouter,
    get_db,
    get_current_user,
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
):
    """Setup all additional routes."""
    
    # ==================== INBOX ENDPOINTS ====================
    
    @api_router.get("/inbox", response_model=ConversationListResponse)
    async def list_conversations(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        channel: Optional[MessageChannel] = None,
        is_read: Optional[bool] = None,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        query = select(Conversation).where(Conversation.tenant_id == user.tenant_id)
        count_query = select(func.count(Conversation.id)).where(Conversation.tenant_id == user.tenant_id)
        
        if channel:
            query = query.where(Conversation.channel == channel)
            count_query = count_query.where(Conversation.channel == channel)
        
        if is_read is not None:
            query = query.where(Conversation.is_read == is_read)
            count_query = count_query.where(Conversation.is_read == is_read)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        offset = (page - 1) * page_size
        query = query.order_by(Conversation.last_message_at.desc().nullslast()).offset(offset).limit(page_size)
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        conv_responses = []
        for conv in conversations:
            contact_result = await db.execute(select(Contact).where(Contact.id == conv.contact_id))
            contact = contact_result.scalar_one_or_none()
            
            conv_responses.append(ConversationResponse(
                id=conv.id, tenant_id=conv.tenant_id, contact_id=conv.contact_id,
                deal_id=conv.deal_id, channel=conv.channel, subject=conv.subject,
                is_open=conv.is_open, is_read=conv.is_read, assigned_to_id=conv.assigned_to_id,
                message_count=conv.message_count, unread_count=conv.unread_count,
                last_message_preview=conv.last_message_preview, last_message_at=conv.last_message_at,
                created_at=conv.created_at, updated_at=conv.updated_at,
                contact_name=contact.full_name if contact else None,
                contact_email=contact.email if contact else None,
                contact_phone=contact.phone if contact else None, messages=[]
            ))
        
        return ConversationListResponse(conversations=conv_responses, total=total, page=page, page_size=page_size)
    
    
    @api_router.get("/inbox/stats", response_model=InboxStats)
    async def get_inbox_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        total = (await db.execute(select(func.count(Conversation.id)).where(Conversation.tenant_id == user.tenant_id))).scalar() or 0
        unread = (await db.execute(select(func.count(Conversation.id)).where(Conversation.tenant_id == user.tenant_id, Conversation.is_read == False))).scalar() or 0
        email_count = (await db.execute(select(func.count(Conversation.id)).where(Conversation.tenant_id == user.tenant_id, Conversation.channel == MessageChannel.EMAIL))).scalar() or 0
        sms_count = (await db.execute(select(func.count(Conversation.id)).where(Conversation.tenant_id == user.tenant_id, Conversation.channel == MessageChannel.SMS))).scalar() or 0
        return InboxStats(total_conversations=total, unread_conversations=unread, email_count=email_count, sms_count=sms_count)
    
    
    @api_router.get("/inbox/{conversation_id}", response_model=ConversationResponse)
    async def get_conversation(conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(
            select(Conversation).options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id, Conversation.tenant_id == user.tenant_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if not conv.is_read:
            conv.is_read = True
            conv.unread_count = 0
        
        contact_result = await db.execute(select(Contact).where(Contact.id == conv.contact_id))
        contact = contact_result.scalar_one_or_none()
        
        messages = []
        for msg in sorted(conv.messages, key=lambda m: m.created_at):
            messages.append(MessageResponse(
                id=msg.id, tenant_id=msg.tenant_id, conversation_id=msg.conversation_id,
                channel=msg.channel, direction=msg.direction, status=msg.status,
                from_address=msg.from_address, to_address=msg.to_address, subject=msg.subject,
                body=msg.body, body_html=msg.body_html, attachments=json.loads(msg.attachments) if msg.attachments else [],
                sent_by_user_id=msg.sent_by_user_id, sent_by_name=msg.sent_by_name,
                external_id=msg.external_id, sent_at=msg.sent_at, delivered_at=msg.delivered_at,
                read_at=msg.read_at, created_at=msg.created_at
            ))
        
        return ConversationResponse(
            id=conv.id, tenant_id=conv.tenant_id, contact_id=conv.contact_id,
            deal_id=conv.deal_id, channel=conv.channel, subject=conv.subject,
            is_open=conv.is_open, is_read=conv.is_read, assigned_to_id=conv.assigned_to_id,
            message_count=conv.message_count, unread_count=conv.unread_count,
            last_message_preview=conv.last_message_preview, last_message_at=conv.last_message_at,
            created_at=conv.created_at, updated_at=conv.updated_at,
            contact_name=contact.full_name if contact else None,
            contact_email=contact.email if contact else None,
            contact_phone=contact.phone if contact else None, messages=messages
        )
    
    
    @api_router.post("/inbox/send", response_model=MessageResponse, status_code=201)
    async def send_message(data: MessageCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        contact_result = await db.execute(select(Contact).where(Contact.id == data.contact_id, Contact.tenant_id == user.tenant_id))
        contact = contact_result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        if data.channel == MessageChannel.SMS:
            message = await messaging_service.send_sms(db, user.tenant_id, data.contact_id, data.to_address, data.body, sender_user_id=user.id, sender_name=user.full_name)
        else:
            message = await messaging_service.send_email(db, user.tenant_id, data.contact_id, data.to_address, data.subject or "Message", data.body, data.body_html, sender_user_id=user.id, sender_name=user.full_name)
        
        return MessageResponse(
            id=message.id, tenant_id=message.tenant_id, conversation_id=message.conversation_id,
            channel=message.channel, direction=message.direction, status=message.status,
            from_address=message.from_address, to_address=message.to_address, subject=message.subject,
            body=message.body, body_html=message.body_html, attachments=[],
            sent_by_user_id=message.sent_by_user_id, sent_by_name=message.sent_by_name,
            external_id=message.external_id, sent_at=message.sent_at, delivered_at=message.delivered_at,
            read_at=message.read_at, created_at=message.created_at
        )
    
    
    # ==================== WORKFLOW ENDPOINTS ====================
    
    @api_router.get("/workflows", response_model=WorkflowListResponse)
    async def list_workflows(
        wf_status: Optional[WorkflowStatus] = Query(None, alias="status"),
        trigger_type: Optional[TriggerType] = None,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        query = select(Workflow).where(Workflow.tenant_id == user.tenant_id)
        if wf_status:
            query = query.where(Workflow.status == wf_status)
        if trigger_type:
            query = query.where(Workflow.trigger_type == trigger_type)
        query = query.order_by(Workflow.created_at.desc())
        result = await db.execute(query)
        workflows = result.scalars().all()
        
        wf_responses = []
        for w in workflows:
            wf_responses.append(WorkflowResponse(
                id=w.id, tenant_id=w.tenant_id, name=w.name, description=w.description,
                status=w.status, trigger_type=w.trigger_type,
                trigger_config=json.loads(w.trigger_config) if w.trigger_config else {},
                actions=json.loads(w.actions) if w.actions else [],
                total_runs=w.total_runs, successful_runs=w.successful_runs,
                failed_runs=w.failed_runs, created_by_id=w.created_by_id,
                created_at=w.created_at, updated_at=w.updated_at
            ))
        return WorkflowListResponse(workflows=wf_responses, total=len(wf_responses))
    
    
    @api_router.post("/workflows", response_model=WorkflowResponse, status_code=201)
    async def create_workflow(data: WorkflowCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        workflow = Workflow(
            tenant_id=user.tenant_id, name=data.name, description=data.description,
            status=data.status, trigger_type=data.trigger_type,
            trigger_config=json.dumps(data.trigger_config), actions=json.dumps(data.actions),
            created_by_id=user.id
        )
        db.add(workflow)
        await db.flush()
        return WorkflowResponse(
            id=workflow.id, tenant_id=workflow.tenant_id, name=workflow.name, description=workflow.description,
            status=workflow.status, trigger_type=workflow.trigger_type,
            trigger_config=json.loads(workflow.trigger_config) if workflow.trigger_config else {},
            actions=json.loads(workflow.actions) if workflow.actions else [],
            total_runs=workflow.total_runs, successful_runs=workflow.successful_runs,
            failed_runs=workflow.failed_runs, created_by_id=workflow.created_by_id,
            created_at=workflow.created_at, updated_at=workflow.updated_at
        )
    
    
    @api_router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
    async def get_workflow(workflow_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == user.tenant_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return WorkflowResponse(
            id=workflow.id, tenant_id=workflow.tenant_id, name=workflow.name, description=workflow.description,
            status=workflow.status, trigger_type=workflow.trigger_type,
            trigger_config=json.loads(workflow.trigger_config) if workflow.trigger_config else {},
            actions=json.loads(workflow.actions) if workflow.actions else [],
            total_runs=workflow.total_runs, successful_runs=workflow.successful_runs,
            failed_runs=workflow.failed_runs, created_by_id=workflow.created_by_id,
            created_at=workflow.created_at, updated_at=workflow.updated_at
        )
    
    
    @api_router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
    async def update_workflow(workflow_id: str, data: WorkflowUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == user.tenant_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ['trigger_config', 'actions'] and value is not None:
                setattr(workflow, field, json.dumps(value))
            else:
                setattr(workflow, field, value)
        workflow.updated_at = datetime.now(timezone.utc)
        return WorkflowResponse(
            id=workflow.id, tenant_id=workflow.tenant_id, name=workflow.name, description=workflow.description,
            status=workflow.status, trigger_type=workflow.trigger_type,
            trigger_config=json.loads(workflow.trigger_config) if workflow.trigger_config else {},
            actions=json.loads(workflow.actions) if workflow.actions else [],
            total_runs=workflow.total_runs, successful_runs=workflow.successful_runs,
            failed_runs=workflow.failed_runs, created_by_id=workflow.created_by_id,
            created_at=workflow.created_at, updated_at=workflow.updated_at
        )
    
    
    @api_router.delete("/workflows/{workflow_id}", status_code=204)
    async def delete_workflow(workflow_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == user.tenant_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        await db.delete(workflow)
    
    
    @api_router.post("/workflows/{workflow_id}/trigger", response_model=WorkflowRunResponse)
    async def trigger_workflow_endpoint(workflow_id: str, data: TriggerWorkflowRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == user.tenant_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.status != WorkflowStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Workflow is not active")
        run = await automation_engine.trigger_workflow(db, workflow_id, user.tenant_id, TriggerType.MANUAL, data.trigger_data, data.contact_id, data.deal_id)
        if not run:
            raise HTTPException(status_code=500, detail="Failed to trigger workflow")
        
        workflow_name = workflow.name
        contact_name = None
        if run.contact_id:
            contact_result = await db.execute(select(Contact).where(Contact.id == run.contact_id))
            contact = contact_result.scalar_one_or_none()
            if contact:
                contact_name = contact.full_name
        
        return WorkflowRunResponse(
            id=run.id, tenant_id=run.tenant_id, workflow_id=run.workflow_id,
            contact_id=run.contact_id, deal_id=run.deal_id, trigger_type=run.trigger_type,
            trigger_data=json.loads(run.trigger_data) if run.trigger_data else {},
            status=run.status, current_action_index=run.current_action_index,
            error_message=run.error_message,
            execution_log=json.loads(run.execution_log) if run.execution_log else [],
            started_at=run.started_at, completed_at=run.completed_at, next_action_at=run.next_action_at,
            workflow_name=workflow_name, contact_name=contact_name
        )
    
    
    # ==================== FORM ENDPOINTS ====================
    
    @api_router.get("/forms", response_model=FormListResponse)
    async def list_forms(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Form).where(Form.tenant_id == user.tenant_id).order_by(Form.created_at.desc()))
        forms = result.scalars().all()
        
        form_responses = []
        for f in forms:
            form_responses.append(FormResponse(
                id=f.id, tenant_id=f.tenant_id, name=f.name, description=f.description,
                slug=f.slug, is_active=f.is_active, is_public=f.is_public,
                fields=json.loads(f.fields) if f.fields else [],
                submit_button_text=f.submit_button_text, success_message=f.success_message,
                redirect_url=f.redirect_url, create_contact=f.create_contact, create_deal=f.create_deal,
                assign_pipeline_id=f.assign_pipeline_id, assign_stage_id=f.assign_stage_id,
                assign_owner_id=f.assign_owner_id, default_tags=json.loads(f.default_tags) if f.default_tags else [],
                theme=f.theme, custom_css=f.custom_css, submission_count=f.submission_count,
                created_at=f.created_at, updated_at=f.updated_at
            ))
        return FormListResponse(forms=form_responses, total=len(form_responses))
    
    
    @api_router.post("/forms", response_model=FormResponse, status_code=201)
    async def create_form(data: FormCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Form).where(Form.tenant_id == user.tenant_id, Form.slug == data.slug))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Form slug already exists")
        form = Form(
            tenant_id=user.tenant_id, name=data.name, description=data.description, slug=data.slug,
            fields=json.dumps(data.fields), submit_button_text=data.submit_button_text,
            success_message=data.success_message, redirect_url=data.redirect_url,
            create_contact=data.create_contact, create_deal=data.create_deal,
            assign_pipeline_id=data.assign_pipeline_id, assign_stage_id=data.assign_stage_id,
            assign_owner_id=data.assign_owner_id, default_tags=json.dumps(data.default_tags),
            is_active=data.is_active, is_public=data.is_public, theme=data.theme, custom_css=data.custom_css
        )
        db.add(form)
        await db.flush()
        return FormResponse(
            id=form.id, tenant_id=form.tenant_id, name=form.name, description=form.description,
            slug=form.slug, is_active=form.is_active, is_public=form.is_public,
            fields=json.loads(form.fields) if form.fields else [],
            submit_button_text=form.submit_button_text, success_message=form.success_message,
            redirect_url=form.redirect_url, create_contact=form.create_contact, create_deal=form.create_deal,
            assign_pipeline_id=form.assign_pipeline_id, assign_stage_id=form.assign_stage_id,
            assign_owner_id=form.assign_owner_id, default_tags=json.loads(form.default_tags) if form.default_tags else [],
            theme=form.theme, custom_css=form.custom_css, submission_count=form.submission_count,
            created_at=form.created_at, updated_at=form.updated_at
        )
    
    
    @api_router.get("/forms/{form_id}", response_model=FormResponse)
    async def get_form(form_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Form).where(Form.id == form_id, Form.tenant_id == user.tenant_id))
        form = result.scalar_one_or_none()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        return FormResponse(
            id=form.id, tenant_id=form.tenant_id, name=form.name, description=form.description,
            slug=form.slug, is_active=form.is_active, is_public=form.is_public,
            fields=json.loads(form.fields) if form.fields else [],
            submit_button_text=form.submit_button_text, success_message=form.success_message,
            redirect_url=form.redirect_url, create_contact=form.create_contact, create_deal=form.create_deal,
            assign_pipeline_id=form.assign_pipeline_id, assign_stage_id=form.assign_stage_id,
            assign_owner_id=form.assign_owner_id, default_tags=json.loads(form.default_tags) if form.default_tags else [],
            theme=form.theme, custom_css=form.custom_css, submission_count=form.submission_count,
            created_at=form.created_at, updated_at=form.updated_at
        )
    
    
    # Public form endpoints (no auth required)
    @api_router.get("/public/forms/{tenant_slug}/{form_slug}", response_model=PublicFormResponse)
    async def get_public_form(tenant_slug: str, form_slug: str, db: AsyncSession = Depends(get_db)):
        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Not found")
        result = await db.execute(select(Form).where(Form.tenant_id == tenant.id, Form.slug == form_slug, Form.is_active == True, Form.is_public == True))
        form = result.scalar_one_or_none()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        return PublicFormResponse(
            id=form.id, name=form.name, description=form.description,
            fields=json.loads(form.fields) if form.fields else [],
            submit_button_text=form.submit_button_text, theme=form.theme, custom_css=form.custom_css
        )
    
    
    @api_router.post("/public/forms/{tenant_slug}/{form_slug}/submit", response_model=FormSubmissionResponse)
    async def submit_public_form(tenant_slug: str, form_slug: str, data: FormSubmissionCreate, request: Request, db: AsyncSession = Depends(get_db)):
        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active == True))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail="Not found")
        result = await db.execute(select(Form).where(Form.tenant_id == tenant.id, Form.slug == form_slug, Form.is_active == True, Form.is_public == True))
        form = result.scalar_one_or_none()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        
        contact_id = None
        deal_id = None
        
        # Create contact if configured
        if form.create_contact:
            fields = json.loads(form.fields) if form.fields else []
            email = data.data.get('email')
            first_name = data.data.get('first_name') or data.data.get('firstName')
            last_name = data.data.get('last_name') or data.data.get('lastName')
            phone = data.data.get('phone')
            
            for field in fields:
                mapping = field.get('mapping')
                field_id = field.get('id')
                value = data.data.get(field_id)
                if mapping == 'email' and value: email = value
                elif mapping == 'first_name' and value: first_name = value
                elif mapping == 'last_name' and value: last_name = value
                elif mapping == 'phone' and value: phone = value
            
            contact = None
            if email:
                contact_result = await db.execute(select(Contact).where(Contact.tenant_id == tenant.id, Contact.email == email))
                contact = contact_result.scalar_one_or_none()
            
            if contact:
                if first_name: contact.first_name = first_name
                if last_name: contact.last_name = last_name
                if phone: contact.phone = phone
                contact.updated_at = datetime.now(timezone.utc)
            else:
                tags = json.loads(form.default_tags) if form.default_tags else []
                contact = Contact(
                    tenant_id=tenant.id, owner_id=form.assign_owner_id, email=email,
                    first_name=first_name, last_name=last_name, phone=phone,
                    lifecycle_stage='lead', lead_source='Form', tags=json.dumps(tags)
                )
                db.add(contact)
                await db.flush()
            contact_id = contact.id
        
        # Create deal if configured
        if form.create_deal and contact_id:
            pipeline_id = form.assign_pipeline_id
            stage_id = form.assign_stage_id
            if not pipeline_id:
                pipeline_result = await db.execute(select(Pipeline).where(Pipeline.tenant_id == tenant.id, Pipeline.is_default == True))
                default_pipeline = pipeline_result.scalar_one_or_none()
                if default_pipeline: pipeline_id = default_pipeline.id
            if pipeline_id and not stage_id:
                stage_result = await db.execute(select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.display_order).limit(1))
                first_stage = stage_result.scalar_one_or_none()
                if first_stage: stage_id = first_stage.id
            
            contact_result = await db.execute(select(Contact).where(Contact.id == contact_id))
            contact = contact_result.scalar_one_or_none()
            deal_name = data.data.get('deal_name') or f"{contact.full_name if contact else 'New'} - {form.name}"
            
            deal = Deal(
                tenant_id=tenant.id, pipeline_id=pipeline_id, stage_id=stage_id,
                contact_id=contact_id, owner_id=form.assign_owner_id, name=deal_name,
                status=DealStatus.OPEN, blueprint_compliance=BlueprintComplianceStatus.NOT_APPLICABLE
            )
            db.add(deal)
            await db.flush()
            deal_id = deal.id
        
        submission = FormSubmission(
            tenant_id=tenant.id, form_id=form.id, contact_id=contact_id, deal_id=deal_id,
            data=json.dumps(data.data), utm_source=data.utm_source, utm_medium=data.utm_medium,
            utm_campaign=data.utm_campaign, utm_content=data.utm_content, utm_term=data.utm_term,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'), referrer=request.headers.get('referer')
        )
        db.add(submission)
        form.submission_count += 1
        await db.flush()
        
        # Create timeline event
        if contact_id:
            timeline = TimelineEvent(
                tenant_id=tenant.id, contact_id=contact_id, deal_id=deal_id,
                event_type=TimelineEventType.FORM_SUBMITTED, title=f"Form submitted: {form.name}",
                metadata_json=json.dumps({'form_id': form.id, 'form_name': form.name}),
                visibility=VisibilityScope.INTERNAL_ONLY
            )
            db.add(timeline)
        
        # Trigger workflows
        await automation_engine.find_and_trigger_workflows(
            db, tenant.id, TriggerType.FORM_SUBMITTED,
            {'form_id': form.id, 'form_name': form.name}, contact_id=contact_id, deal_id=deal_id
        )
        
        return FormSubmissionResponse(
            id=submission.id, tenant_id=submission.tenant_id, form_id=submission.form_id,
            contact_id=submission.contact_id, deal_id=submission.deal_id,
            data=json.loads(submission.data) if submission.data else {},
            utm_source=submission.utm_source, utm_medium=submission.utm_medium,
            utm_campaign=submission.utm_campaign, ip_address=submission.ip_address,
            created_at=submission.created_at
        )
    
    
    # ==================== LANDING PAGE ENDPOINTS ====================
    
    @api_router.get("/landing-pages", response_model=LandingPageListResponse)
    async def list_landing_pages(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(LandingPage).where(LandingPage.tenant_id == user.tenant_id).order_by(LandingPage.created_at.desc()))
        pages = result.scalars().all()
        
        page_responses = []
        for p in pages:
            page_responses.append(LandingPageResponse(
                id=p.id, tenant_id=p.tenant_id, name=p.name, slug=p.slug,
                is_published=p.is_published, content=json.loads(p.content) if p.content else {},
                meta_title=p.meta_title, meta_description=p.meta_description, theme=p.theme,
                custom_css=p.custom_css, header_code=p.header_code, footer_code=p.footer_code,
                form_id=p.form_id, view_count=p.view_count, created_at=p.created_at, updated_at=p.updated_at
            ))
        return LandingPageListResponse(pages=page_responses, total=len(page_responses))
    
    
    @api_router.post("/landing-pages", response_model=LandingPageResponse, status_code=201)
    async def create_landing_page(data: LandingPageCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(LandingPage).where(LandingPage.tenant_id == user.tenant_id, LandingPage.slug == data.slug))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Landing page slug already exists")
        page = LandingPage(
            tenant_id=user.tenant_id, name=data.name, slug=data.slug, content=json.dumps(data.content),
            meta_title=data.meta_title, meta_description=data.meta_description, theme=data.theme,
            custom_css=data.custom_css, header_code=data.header_code, footer_code=data.footer_code,
            form_id=data.form_id, is_published=data.is_published
        )
        db.add(page)
        await db.flush()
        return LandingPageResponse(
            id=page.id, tenant_id=page.tenant_id, name=page.name, slug=page.slug,
            is_published=page.is_published, content=json.loads(page.content) if page.content else {},
            meta_title=page.meta_title, meta_description=page.meta_description, theme=page.theme,
            custom_css=page.custom_css, header_code=page.header_code, footer_code=page.footer_code,
            form_id=page.form_id, view_count=page.view_count, created_at=page.created_at, updated_at=page.updated_at
        )
