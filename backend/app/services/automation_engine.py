"""Automation engine for executing workflows."""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    Workflow, WorkflowRun, ScheduledJob, WorkflowStatus, WorkflowRunStatus,
    TriggerType, ActionType, Contact, Deal, TimelineEvent, TimelineEventType, VisibilityScope
)
from app.services.messaging_service import messaging_service

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Engine for executing automation workflows."""
    
    async def trigger_workflow(
        self,
        db: AsyncSession,
        workflow_id: str,
        tenant_id: str,
        trigger_type: TriggerType,
        trigger_data: Dict[str, Any],
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Optional[WorkflowRun]:
        """Trigger a workflow execution."""
        
        # Get workflow
        result = await db.execute(
            select(Workflow).where(
                Workflow.id == workflow_id,
                Workflow.tenant_id == tenant_id,
                Workflow.status == WorkflowStatus.ACTIVE
            )
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            logger.warning(f"Workflow {workflow_id} not found or not active")
            return None
        
        # Check idempotency
        if idempotency_key:
            result = await db.execute(
                select(WorkflowRun).where(
                    WorkflowRun.idempotency_key == idempotency_key
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                logger.info(f"Workflow run already exists for idempotency key: {idempotency_key}")
                return existing
        
        # Create workflow run
        run = WorkflowRun(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            contact_id=contact_id,
            deal_id=deal_id,
            trigger_type=trigger_type,
            trigger_data=json.dumps(trigger_data),
            status=WorkflowRunStatus.RUNNING,
            idempotency_key=idempotency_key,
            execution_log=json.dumps([])
        )
        db.add(run)
        
        # Update workflow stats
        workflow.total_runs += 1
        
        await db.flush()
        
        # Execute actions
        try:
            await self._execute_actions(db, run, workflow, contact_id, deal_id)
            run.status = WorkflowRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            workflow.successful_runs += 1
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            run.status = WorkflowRunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            workflow.failed_runs += 1
        
        return run
    
    async def _execute_actions(
        self,
        db: AsyncSession,
        run: WorkflowRun,
        workflow: Workflow,
        contact_id: Optional[str],
        deal_id: Optional[str]
    ):
        """Execute workflow actions sequentially."""
        try:
            actions = json.loads(workflow.actions) if workflow.actions else []
        except:
            actions = []
        
        execution_log = []
        
        for i, action in enumerate(actions):
            run.current_action_index = i
            
            action_type = action.get('type')
            action_config = action.get('config', {})
            delay_minutes = action.get('delay_minutes', 0)
            
            # Handle delay
            if delay_minutes > 0:
                # Schedule for later execution
                scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                job = ScheduledJob(
                    tenant_id=run.tenant_id,
                    job_type='workflow_action',
                    workflow_run_id=run.id,
                    payload=json.dumps({
                        'action_index': i,
                        'action': action,
                        'contact_id': contact_id,
                        'deal_id': deal_id
                    }),
                    scheduled_for=scheduled_time
                )
                db.add(job)
                run.status = WorkflowRunStatus.WAITING
                run.next_action_at = scheduled_time
                execution_log.append({
                    'action_index': i,
                    'type': action_type,
                    'status': 'scheduled',
                    'scheduled_for': scheduled_time.isoformat()
                })
                break  # Stop here, job will continue later
            
            # Execute action
            result = await self._execute_single_action(
                db, run.tenant_id, action_type, action_config,
                contact_id, deal_id
            )
            
            execution_log.append({
                'action_index': i,
                'type': action_type,
                'status': 'completed',
                'result': result,
                'executed_at': datetime.now(timezone.utc).isoformat()
            })
        
        run.execution_log = json.dumps(execution_log)
    
    async def _execute_single_action(
        self,
        db: AsyncSession,
        tenant_id: str,
        action_type: str,
        config: Dict[str, Any],
        contact_id: Optional[str],
        deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute a single workflow action."""
        
        logger.info(f"Executing action: {action_type} with config: {config}")
        
        if action_type == ActionType.SEND_SMS.value:
            return await self._action_send_sms(db, tenant_id, config, contact_id, deal_id)
        
        elif action_type == ActionType.SEND_EMAIL.value:
            return await self._action_send_email(db, tenant_id, config, contact_id, deal_id)
        
        elif action_type == ActionType.CREATE_TASK.value:
            return await self._action_create_task(db, tenant_id, config, contact_id, deal_id)
        
        elif action_type == ActionType.SET_PROPERTY.value:
            return await self._action_set_property(db, tenant_id, config, contact_id, deal_id)
        
        elif action_type == ActionType.ADD_TAG.value:
            return await self._action_add_tag(db, tenant_id, config, contact_id, deal_id)
        
        elif action_type == ActionType.CREATE_NOTIFICATION.value:
            return await self._action_create_notification(db, tenant_id, config, contact_id, deal_id)
        
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {'status': 'skipped', 'reason': f'Unknown action type: {action_type}'}
    
    async def _action_send_sms(
        self, db: AsyncSession, tenant_id: str, config: Dict[str, Any],
        contact_id: Optional[str], deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Send SMS action."""
        if not contact_id:
            return {'status': 'skipped', 'reason': 'No contact'}
        
        # Get contact
        result = await db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact or not contact.phone:
            return {'status': 'skipped', 'reason': 'Contact has no phone'}
        
        body = config.get('body', config.get('template', 'Hello!'))
        # Replace placeholders
        body = body.replace('{{first_name}}', contact.first_name or '')
        body = body.replace('{{last_name}}', contact.last_name or '')
        
        message = await messaging_service.send_sms(
            db, tenant_id, contact_id, contact.phone, body,
            sender_name='Automation', deal_id=deal_id
        )
        
        return {'status': 'sent', 'message_id': message.id}
    
    async def _action_send_email(
        self, db: AsyncSession, tenant_id: str, config: Dict[str, Any],
        contact_id: Optional[str], deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Send email action."""
        if not contact_id:
            return {'status': 'skipped', 'reason': 'No contact'}
        
        result = await db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact or not contact.email:
            return {'status': 'skipped', 'reason': 'Contact has no email'}
        
        subject = config.get('subject', 'Message from CRM OS')
        body = config.get('body', config.get('template', 'Hello!'))
        
        # Replace placeholders
        subject = subject.replace('{{first_name}}', contact.first_name or '')
        body = body.replace('{{first_name}}', contact.first_name or '')
        body = body.replace('{{last_name}}', contact.last_name or '')
        
        message = await messaging_service.send_email(
            db, tenant_id, contact_id, contact.email, subject, body,
            sender_name='Automation', deal_id=deal_id
        )
        
        return {'status': 'sent', 'message_id': message.id}
    
    async def _action_create_task(
        self, db: AsyncSession, tenant_id: str, config: Dict[str, Any],
        contact_id: Optional[str], deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Create task action."""
        title = config.get('title', 'Follow up task')
        description = config.get('description', '')
        due_days = config.get('due_days', 1)
        
        due_date = datetime.now(timezone.utc) + timedelta(days=due_days)
        
        task = TimelineEvent(
            tenant_id=tenant_id,
            contact_id=contact_id,
            deal_id=deal_id,
            event_type=TimelineEventType.TASK,
            title=title,
            description=description,
            visibility=VisibilityScope.INTERNAL_ONLY,
            due_date=due_date
        )
        db.add(task)
        await db.flush()
        
        return {'status': 'created', 'task_id': task.id}
    
    async def _action_set_property(
        self, db: AsyncSession, tenant_id: str, config: Dict[str, Any],
        contact_id: Optional[str], deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Set property action."""
        property_name = config.get('property')
        property_value = config.get('value')
        object_type = config.get('object_type', 'contact')
        
        if object_type == 'contact' and contact_id:
            result = await db.execute(
                select(Contact).where(Contact.id == contact_id)
            )
            contact = result.scalar_one_or_none()
            if contact and hasattr(contact, property_name):
                setattr(contact, property_name, property_value)
                return {'status': 'updated', 'property': property_name}
        
        elif object_type == 'deal' and deal_id:
            result = await db.execute(
                select(Deal).where(Deal.id == deal_id)
            )
            deal = result.scalar_one_or_none()
            if deal and hasattr(deal, property_name):
                setattr(deal, property_name, property_value)
                return {'status': 'updated', 'property': property_name}
        
        return {'status': 'skipped', 'reason': 'Property not found'}
    
    async def _action_add_tag(
        self, db: AsyncSession, tenant_id: str, config: Dict[str, Any],
        contact_id: Optional[str], deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Add tag action."""
        tag = config.get('tag')
        if not tag:
            return {'status': 'skipped', 'reason': 'No tag specified'}
        
        if contact_id:
            result = await db.execute(
                select(Contact).where(Contact.id == contact_id)
            )
            contact = result.scalar_one_or_none()
            if contact:
                try:
                    tags = json.loads(contact.tags) if contact.tags else []
                except:
                    tags = []
                if tag not in tags:
                    tags.append(tag)
                    contact.tags = json.dumps(tags)
                    return {'status': 'added', 'tag': tag}
        
        return {'status': 'skipped', 'reason': 'Contact not found'}
    
    async def _action_create_notification(
        self, db: AsyncSession, tenant_id: str, config: Dict[str, Any],
        contact_id: Optional[str], deal_id: Optional[str]
    ) -> Dict[str, Any]:
        """Create internal notification."""
        title = config.get('title', 'Notification')
        description = config.get('description', '')
        
        notification = TimelineEvent(
            tenant_id=tenant_id,
            contact_id=contact_id,
            deal_id=deal_id,
            event_type=TimelineEventType.INTERNAL_NOTIFICATION,
            title=title,
            description=description,
            visibility=VisibilityScope.INTERNAL_ONLY
        )
        db.add(notification)
        await db.flush()
        
        return {'status': 'created', 'notification_id': notification.id}
    
    async def find_and_trigger_workflows(
        self,
        db: AsyncSession,
        tenant_id: str,
        trigger_type: TriggerType,
        trigger_data: Dict[str, Any],
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None
    ) -> List[WorkflowRun]:
        """Find all workflows matching the trigger and execute them."""
        result = await db.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.trigger_type == trigger_type,
                Workflow.status == WorkflowStatus.ACTIVE
            )
        )
        workflows = result.scalars().all()
        
        runs = []
        for workflow in workflows:
            # Check conditions (if any)
            try:
                config = json.loads(workflow.trigger_config) if workflow.trigger_config else {}
            except:
                config = {}
            
            # TODO: Implement condition checking
            
            run = await self.trigger_workflow(
                db, workflow.id, tenant_id, trigger_type, trigger_data,
                contact_id, deal_id,
                idempotency_key=f"{workflow.id}_{contact_id}_{deal_id}_{datetime.now().timestamp()}"
            )
            if run:
                runs.append(run)
        
        return runs


# Singleton instance
automation_engine = AutomationEngine()
