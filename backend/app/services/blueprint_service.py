from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import json
from datetime import datetime, timezone

from app.models import (
    Deal, DealStatus, BlueprintComplianceStatus,
    WorkflowBlueprint, BlueprintStage,
    TimelineEvent, TimelineEventType, VisibilityScope
)


async def get_blueprint_with_stages(db: AsyncSession, blueprint_id: str, tenant_id: str) -> Optional[WorkflowBlueprint]:
    """Get a blueprint with all its stages loaded."""
    result = await db.execute(
        select(WorkflowBlueprint)
        .options(selectinload(WorkflowBlueprint.stages))
        .where(
            WorkflowBlueprint.id == blueprint_id,
            WorkflowBlueprint.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def get_deal_with_blueprint(db: AsyncSession, deal_id: str, tenant_id: str) -> Optional[Deal]:
    """Get a deal with its blueprint loaded."""
    result = await db.execute(
        select(Deal)
        .where(
            Deal.id == deal_id,
            Deal.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


def get_completed_actions(deal: Deal) -> List[str]:
    """Get list of completed actions for a deal from timeline events."""
    # This would typically query timeline events, but for simplicity
    # we'll store completed actions in custom_properties
    try:
        props = json.loads(deal.custom_properties) if deal.custom_properties else {}
        return props.get('completed_actions', [])
    except:
        return []


def get_deal_properties(deal: Deal) -> Dict[str, Any]:
    """Get all properties of a deal as a dict."""
    props = {
        'name': deal.name,
        'description': deal.description,
        'amount': deal.amount,
        'currency': deal.currency,
        'status': deal.status.value if deal.status else None,
        'priority': deal.priority,
        'contact_id': deal.contact_id,
        'company_id': deal.company_id,
        'owner_id': deal.owner_id,
    }
    
    # Add custom properties
    try:
        custom = json.loads(deal.custom_properties) if deal.custom_properties else {}
        props.update(custom)
    except:
        pass
    
    return props


async def validate_stage_move(
    db: AsyncSession,
    deal: Deal,
    target_stage_order: int,
    tenant_id: str
) -> Dict[str, Any]:
    """Validate if a deal can move to a target blueprint stage.
    
    Returns:
        {
            'can_move': bool,
            'current_stage_order': int,
            'target_stage_order': int,
            'missing_requirements': {
                'properties': [...],
                'actions': [...]
            },
            'message': str
        }
    """
    result = {
        'can_move': True,
        'current_stage_order': 0,
        'target_stage_order': target_stage_order,
        'missing_requirements': {
            'properties': [],
            'actions': []
        },
        'message': 'Move allowed'
    }
    
    # If no blueprint assigned, always allow move
    if not deal.blueprint_id:
        result['message'] = 'No blueprint assigned - move allowed'
        return result
    
    # Get blueprint with stages
    blueprint = await get_blueprint_with_stages(db, deal.blueprint_id, tenant_id)
    if not blueprint:
        result['message'] = 'Blueprint not found - move allowed'
        return result
    
    # Get current stage order
    current_stage_order = 0
    if deal.current_blueprint_stage_id:
        for stage in blueprint.stages:
            if stage.id == deal.current_blueprint_stage_id:
                current_stage_order = stage.stage_order
                break
    
    result['current_stage_order'] = current_stage_order
    
    # If moving backwards, always allow (for corrections)
    if target_stage_order <= current_stage_order:
        result['message'] = 'Moving to earlier stage - allowed'
        return result
    
    # Check if skipping stages is allowed
    if not blueprint.allow_skip_stages and target_stage_order > current_stage_order + 1:
        result['can_move'] = False
        result['message'] = f'Cannot skip stages. Must complete stage {current_stage_order + 1} first.'
        return result
    
    # Get the current stage requirements
    current_stage = None
    for stage in blueprint.stages:
        if stage.stage_order == current_stage_order:
            current_stage = stage
            break
    
    if not current_stage:
        # No current stage means we're at the beginning
        return result
    
    # Check required properties
    deal_props = get_deal_properties(deal)
    try:
        required_props = json.loads(current_stage.required_properties) if current_stage.required_properties else []
    except:
        required_props = []
    
    for prop in required_props:
        if prop not in deal_props or not deal_props[prop]:
            result['missing_requirements']['properties'].append(prop)
    
    # Check required actions
    completed_actions = get_completed_actions(deal)
    try:
        required_actions = json.loads(current_stage.required_actions) if current_stage.required_actions else []
    except:
        required_actions = []
    
    for action in required_actions:
        if action not in completed_actions:
            result['missing_requirements']['actions'].append(action)
    
    # Determine if move is allowed
    if result['missing_requirements']['properties'] or result['missing_requirements']['actions']:
        result['can_move'] = False
        missing = []
        if result['missing_requirements']['properties']:
            missing.append(f"Properties: {', '.join(result['missing_requirements']['properties'])}")
        if result['missing_requirements']['actions']:
            missing.append(f"Actions: {', '.join(result['missing_requirements']['actions'])}")
        result['message'] = f"Missing requirements: {'; '.join(missing)}"
    
    return result


async def move_deal_stage(
    db: AsyncSession,
    deal: Deal,
    target_stage_order: int,
    tenant_id: str,
    actor_id: str,
    actor_name: str,
    override: bool = False,
    override_reason: Optional[str] = None
) -> Dict[str, Any]:
    """Move a deal to a new blueprint stage.
    
    Returns:
        {
            'success': bool,
            'deal': Deal,
            'message': str,
            'validation': dict
        }
    """
    # Validate the move
    validation = await validate_stage_move(db, deal, target_stage_order, tenant_id)
    
    if not validation['can_move'] and not override:
        return {
            'success': False,
            'deal': deal,
            'message': validation['message'],
            'validation': validation
        }
    
    # Get blueprint and target stage
    blueprint = await get_blueprint_with_stages(db, deal.blueprint_id, tenant_id) if deal.blueprint_id else None
    
    target_stage = None
    from_stage = None
    if blueprint:
        for stage in blueprint.stages:
            if stage.stage_order == target_stage_order:
                target_stage = stage
            if deal.current_blueprint_stage_id and stage.id == deal.current_blueprint_stage_id:
                from_stage = stage
    
    # Update deal
    old_stage_id = deal.current_blueprint_stage_id
    old_stage_order = validation['current_stage_order']
    
    if target_stage:
        deal.current_blueprint_stage_id = target_stage.id
        
        # Mark stages as completed
        try:
            completed = json.loads(deal.completed_blueprint_stages) if deal.completed_blueprint_stages else []
        except:
            completed = []
        
        if target_stage.id not in completed:
            completed.append(target_stage.id)
            deal.completed_blueprint_stages = json.dumps(completed)
    
    # Update compliance status
    if override and not validation['can_move']:
        deal.blueprint_compliance = BlueprintComplianceStatus.OVERRIDDEN
    elif validation['can_move']:
        deal.blueprint_compliance = BlueprintComplianceStatus.COMPLIANT
    else:
        deal.blueprint_compliance = BlueprintComplianceStatus.MISSING_REQUIREMENTS
    
    deal.updated_at = datetime.now(timezone.utc)
    deal.last_activity_at = datetime.now(timezone.utc)
    
    # Create timeline event
    event_type = TimelineEventType.BLUEPRINT_OVERRIDE if override else TimelineEventType.STAGE_CHANGED
    
    metadata = {
        'from_stage_order': old_stage_order,
        'to_stage_order': target_stage_order,
        'from_stage_name': from_stage.name if from_stage else 'Start',
        'to_stage_name': target_stage.name if target_stage else f'Stage {target_stage_order}',
    }
    
    if override:
        metadata['override_reason'] = override_reason
        metadata['missing_requirements'] = validation['missing_requirements']
    
    timeline_event = TimelineEvent(
        tenant_id=tenant_id,
        deal_id=deal.id,
        contact_id=deal.contact_id,
        event_type=event_type,
        title=f"{'Override: ' if override else ''}Stage changed to {target_stage.name if target_stage else f'Stage {target_stage_order}'}",
        description=override_reason if override else None,
        metadata_json=json.dumps(metadata),
        visibility=VisibilityScope.INTERNAL_ONLY,
        actor_id=actor_id,
        actor_name=actor_name
    )
    db.add(timeline_event)
    
    await db.flush()
    
    return {
        'success': True,
        'deal': deal,
        'message': f"Successfully moved to stage {target_stage_order}",
        'validation': validation
    }


async def get_blueprint_progress(deal: Deal, blueprint: WorkflowBlueprint) -> Dict[str, Any]:
    """Get the progress of a deal through its blueprint stages."""
    if not blueprint or not blueprint.stages:
        return {
            'total_stages': 0,
            'current_stage': 0,
            'completed_stages': 0,
            'progress_percentage': 0,
            'stages': []
        }
    
    try:
        completed_ids = json.loads(deal.completed_blueprint_stages) if deal.completed_blueprint_stages else []
    except:
        completed_ids = []
    
    current_order = 0
    for stage in blueprint.stages:
        if stage.id == deal.current_blueprint_stage_id:
            current_order = stage.stage_order
            break
    
    stages_info = []
    for stage in sorted(blueprint.stages, key=lambda s: s.stage_order):
        stages_info.append({
            'id': stage.id,
            'name': stage.name,
            'order': stage.stage_order,
            'is_completed': stage.id in completed_ids,
            'is_current': stage.id == deal.current_blueprint_stage_id,
            'is_milestone': stage.is_milestone,
            'color': stage.color,
            'icon': stage.icon
        })
    
    total = len(blueprint.stages)
    completed = len(completed_ids)
    
    return {
        'total_stages': total,
        'current_stage': current_order,
        'completed_stages': completed,
        'progress_percentage': round((completed / total) * 100) if total > 0 else 0,
        'stages': stages_info
    }
