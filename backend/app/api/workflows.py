"""API routes for Automation Workflows."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import json
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import (
    User, UserRole, Contact, Deal,
    Workflow, WorkflowRun, WorkflowStatus, TriggerType, WorkflowRunStatus
)
from app.schemas.automation import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowListResponse,
    WorkflowRunResponse, WorkflowRunListResponse, TriggerWorkflowRequest
)
from app.services import automation_engine

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def get_current_user_dep(user = None):
    """Placeholder - will be replaced with actual dependency."""
    return user


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[WorkflowStatus] = None,
    trigger_type: Optional[TriggerType] = None,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """List all workflows."""
    query = select(Workflow).where(Workflow.tenant_id == user.tenant_id)
    
    if status:
        query = query.where(Workflow.status == status)
    if trigger_type:
        query = query.where(Workflow.trigger_type == trigger_type)
    
    query = query.order_by(Workflow.created_at.desc())
    
    result = await db.execute(query)
    workflows = result.scalars().all()
    
    return WorkflowListResponse(
        workflows=[_workflow_to_response(w) for w in workflows],
        total=len(workflows)
    )


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Create a new workflow."""
    workflow = Workflow(
        tenant_id=user.tenant_id,
        name=data.name,
        description=data.description,
        status=data.status,
        trigger_type=data.trigger_type,
        trigger_config=json.dumps(data.trigger_config),
        actions=json.dumps(data.actions),
        created_by_id=user.id
    )
    db.add(workflow)
    await db.flush()
    
    return _workflow_to_response(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Get a workflow by ID."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == user.tenant_id
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return _workflow_to_response(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdate,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Update a workflow."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == user.tenant_id
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'trigger_config' and value is not None:
            setattr(workflow, field, json.dumps(value))
        elif field == 'actions' and value is not None:
            setattr(workflow, field, json.dumps(value))
        else:
            setattr(workflow, field, value)
    
    workflow.updated_at = datetime.now(timezone.utc)
    
    return _workflow_to_response(workflow)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Delete a workflow."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == user.tenant_id
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    await db.delete(workflow)


@router.post("/{workflow_id}/trigger", response_model=WorkflowRunResponse)
async def trigger_workflow(
    workflow_id: str,
    data: TriggerWorkflowRequest,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a workflow."""
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.tenant_id == user.tenant_id
        )
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status != WorkflowStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Workflow is not active")
    
    run = await automation_engine.trigger_workflow(
        db, workflow_id, user.tenant_id, TriggerType.MANUAL,
        data.trigger_data, data.contact_id, data.deal_id
    )
    
    if not run:
        raise HTTPException(status_code=500, detail="Failed to trigger workflow")
    
    return await _workflow_run_to_response(run, db)


@router.get("/{workflow_id}/runs", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    workflow_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[WorkflowRunStatus] = None,
    user: User = Depends(get_current_user_dep),
    db: AsyncSession = Depends(get_db)
):
    """List runs for a workflow."""
    query = select(WorkflowRun).where(
        WorkflowRun.workflow_id == workflow_id,
        WorkflowRun.tenant_id == user.tenant_id
    )
    count_query = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.workflow_id == workflow_id,
        WorkflowRun.tenant_id == user.tenant_id
    )
    
    if status:
        query = query.where(WorkflowRun.status == status)
        count_query = count_query.where(WorkflowRun.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(WorkflowRun.started_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    runs = result.scalars().all()
    
    run_responses = []
    for run in runs:
        run_responses.append(await _workflow_run_to_response(run, db))
    
    return WorkflowRunListResponse(
        runs=run_responses,
        total=total,
        page=page,
        page_size=page_size
    )


def _workflow_to_response(workflow: Workflow) -> WorkflowResponse:
    try:
        trigger_config = json.loads(workflow.trigger_config) if workflow.trigger_config else {}
    except:
        trigger_config = {}
    
    try:
        actions = json.loads(workflow.actions) if workflow.actions else []
    except:
        actions = []
    
    return WorkflowResponse(
        id=workflow.id,
        tenant_id=workflow.tenant_id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status,
        trigger_type=workflow.trigger_type,
        trigger_config=trigger_config,
        actions=actions,
        total_runs=workflow.total_runs,
        successful_runs=workflow.successful_runs,
        failed_runs=workflow.failed_runs,
        created_by_id=workflow.created_by_id,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )


async def _workflow_run_to_response(run: WorkflowRun, db: AsyncSession) -> WorkflowRunResponse:
    try:
        trigger_data = json.loads(run.trigger_data) if run.trigger_data else {}
    except:
        trigger_data = {}
    
    try:
        execution_log = json.loads(run.execution_log) if run.execution_log else []
    except:
        execution_log = []
    
    # Get workflow name
    workflow_name = None
    workflow_result = await db.execute(
        select(Workflow).where(Workflow.id == run.workflow_id)
    )
    workflow = workflow_result.scalar_one_or_none()
    if workflow:
        workflow_name = workflow.name
    
    # Get contact name
    contact_name = None
    if run.contact_id:
        contact_result = await db.execute(
            select(Contact).where(Contact.id == run.contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        if contact:
            contact_name = contact.full_name
    
    return WorkflowRunResponse(
        id=run.id,
        tenant_id=run.tenant_id,
        workflow_id=run.workflow_id,
        contact_id=run.contact_id,
        deal_id=run.deal_id,
        trigger_type=run.trigger_type,
        trigger_data=trigger_data,
        status=run.status,
        current_action_index=run.current_action_index,
        error_message=run.error_message,
        execution_log=execution_log,
        started_at=run.started_at,
        completed_at=run.completed_at,
        next_action_at=run.next_action_at,
        workflow_name=workflow_name,
        contact_name=contact_name
    )
