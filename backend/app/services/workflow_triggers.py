"""
Workflow Triggers Service

Handles triggering workflows based on affiliate events:
- affiliate_link_clicked
- affiliate_signup
- affiliate_approved
- commission_earned
- commission_paid
- landing_page_view
- landing_page_conversion
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid

from app.db.mongodb import get_database

logger = logging.getLogger(__name__)


class WorkflowTriggerService:
    """Service for triggering workflows based on events"""
    
    @staticmethod
    async def trigger_event(
        tenant_id: str,
        event_type: str,
        entity_id: str,
        entity_type: str,  # 'affiliate', 'link', 'commission', 'landing_page'
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Trigger workflows that match the given event type.
        
        Args:
            tenant_id: The tenant ID
            event_type: Type of event (e.g., 'affiliate_link_clicked')
            entity_id: ID of the related entity
            entity_type: Type of entity
            metadata: Additional event data
        """
        db = get_database()
        
        # Find active workflows that match this trigger
        workflows = await db.workflows.find({
            "tenant_id": tenant_id,
            "trigger_type": event_type,
            "status": "active"
        }).to_list(length=100)
        
        if not workflows:
            logger.debug(f"No active workflows found for event: {event_type}")
            return
        
        logger.info(f"Found {len(workflows)} workflows for event: {event_type}")
        
        # Create workflow runs for each matching workflow
        for workflow in workflows:
            try:
                run = {
                    "id": str(uuid.uuid4()),
                    "workflow_id": workflow["id"],
                    "tenant_id": tenant_id,
                    "trigger_event": event_type,
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "metadata": metadata or {},
                    "status": "pending",
                    "actions_completed": 0,
                    "actions_total": len(workflow.get("actions", [])),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "error": None
                }
                
                await db.workflow_runs.insert_one(run)
                
                # Execute actions (simplified - in production would use a job queue)
                await WorkflowTriggerService._execute_workflow(db, workflow, run, metadata)
                
            except Exception as e:
                logger.error(f"Failed to trigger workflow {workflow['id']}: {e}")
    
    @staticmethod
    async def _execute_workflow(db, workflow: dict, run: dict, context: dict):
        """Execute workflow actions"""
        try:
            # Update run status
            await db.workflow_runs.update_one(
                {"id": run["id"]},
                {"$set": {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            actions = workflow.get("actions", [])
            
            for i, action in enumerate(actions):
                try:
                    await WorkflowTriggerService._execute_action(db, action, context, run["tenant_id"])
                    
                    # Update progress
                    await db.workflow_runs.update_one(
                        {"id": run["id"]},
                        {"$set": {"actions_completed": i + 1}}
                    )
                except Exception as e:
                    logger.error(f"Action {action.get('type')} failed: {e}")
                    raise
            
            # Mark as completed
            await db.workflow_runs.update_one(
                {"id": run["id"]},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            # Update workflow stats
            await db.workflows.update_one(
                {"id": workflow["id"]},
                {"$inc": {"total_runs": 1, "successful_runs": 1}}
            )
            
        except Exception as e:
            # Mark as failed
            await db.workflow_runs.update_one(
                {"id": run["id"]},
                {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat(), "error": str(e)}}
            )
            await db.workflows.update_one(
                {"id": workflow["id"]},
                {"$inc": {"total_runs": 1, "failed_runs": 1}}
            )
    
    @staticmethod
    async def _execute_action(db, action: dict, context: dict, tenant_id: str):
        """Execute a single workflow action"""
        action_type = action.get("type")
        config = action.get("config", {})
        
        if action_type == "send_email":
            # Placeholder - would integrate with email service
            logger.info(f"Would send email: {config.get('subject')} to {config.get('to')}")
            
        elif action_type == "notify_affiliate":
            # Create notification for affiliate
            affiliate_id = context.get("affiliate_id")
            if affiliate_id:
                notification = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "affiliate_id": affiliate_id,
                    "type": "workflow_notification",
                    "title": config.get("title", "Notification"),
                    "message": config.get("message", ""),
                    "read": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.affiliate_notifications.insert_one(notification)
                
        elif action_type == "approve_affiliate":
            affiliate_id = context.get("affiliate_id")
            if affiliate_id:
                await db.affiliates.update_one(
                    {"id": affiliate_id},
                    {"$set": {"status": "active", "approved_at": datetime.now(timezone.utc).isoformat()}}
                )
                
        elif action_type == "create_commission":
            affiliate_id = context.get("affiliate_id")
            deal_id = context.get("deal_id")
            amount = config.get("amount", 0)
            
            if affiliate_id and amount > 0:
                commission = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "affiliate_id": affiliate_id,
                    "deal_id": deal_id,
                    "program_id": context.get("program_id"),
                    "amount": amount,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.affiliate_commissions.insert_one(commission)
                
        elif action_type == "update_affiliate_status":
            affiliate_id = context.get("affiliate_id")
            new_status = config.get("status")
            if affiliate_id and new_status:
                await db.affiliates.update_one(
                    {"id": affiliate_id},
                    {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                
        elif action_type == "add_tag":
            # Add tag to entity
            entity_id = context.get("entity_id")
            entity_type = context.get("entity_type")
            tag = config.get("tag")
            if entity_id and tag:
                collection = f"{entity_type}s" if entity_type else "contacts"
                await db[collection].update_one(
                    {"id": entity_id},
                    {"$addToSet": {"tags": tag}}
                )
                
        elif action_type == "delay":
            # In production, would schedule continuation
            import asyncio
            delay_seconds = config.get("seconds", 0)
            if delay_seconds > 0 and delay_seconds <= 60:
                await asyncio.sleep(delay_seconds)
                
        else:
            logger.warning(f"Unknown action type: {action_type}")


# Helper functions to trigger specific events
async def trigger_affiliate_link_clicked(tenant_id: str, link_id: str, affiliate_id: str, metadata: dict = None):
    """Trigger workflow when affiliate link is clicked"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="affiliate_link_clicked",
        entity_id=link_id,
        entity_type="link",
        metadata={"affiliate_id": affiliate_id, **(metadata or {})}
    )


async def trigger_affiliate_signup(tenant_id: str, affiliate_id: str, metadata: dict = None):
    """Trigger workflow when new affiliate signs up"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="affiliate_signup",
        entity_id=affiliate_id,
        entity_type="affiliate",
        metadata={"affiliate_id": affiliate_id, **(metadata or {})}
    )


async def trigger_affiliate_approved(tenant_id: str, affiliate_id: str, metadata: dict = None):
    """Trigger workflow when affiliate is approved"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="affiliate_approved",
        entity_id=affiliate_id,
        entity_type="affiliate",
        metadata={"affiliate_id": affiliate_id, **(metadata or {})}
    )


async def trigger_commission_earned(tenant_id: str, commission_id: str, affiliate_id: str, amount: float, metadata: dict = None):
    """Trigger workflow when commission is earned"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="commission_earned",
        entity_id=commission_id,
        entity_type="commission",
        metadata={"affiliate_id": affiliate_id, "amount": amount, **(metadata or {})}
    )


async def trigger_commission_paid(tenant_id: str, commission_id: str, affiliate_id: str, amount: float, metadata: dict = None):
    """Trigger workflow when commission is paid"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="commission_paid",
        entity_id=commission_id,
        entity_type="commission",
        metadata={"affiliate_id": affiliate_id, "amount": amount, **(metadata or {})}
    )


async def trigger_landing_page_view(tenant_id: str, page_id: str, affiliate_ref: str = None, metadata: dict = None):
    """Trigger workflow when landing page is viewed"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="landing_page_view",
        entity_id=page_id,
        entity_type="landing_page",
        metadata={"affiliate_ref": affiliate_ref, **(metadata or {})}
    )


async def trigger_landing_page_conversion(tenant_id: str, page_id: str, affiliate_ref: str = None, metadata: dict = None):
    """Trigger workflow when landing page conversion happens"""
    await WorkflowTriggerService.trigger_event(
        tenant_id=tenant_id,
        event_type="landing_page_conversion",
        entity_id=page_id,
        entity_type="landing_page",
        metadata={"affiliate_ref": affiliate_ref, **(metadata or {})}
    )
