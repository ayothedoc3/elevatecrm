"""
CRM Provisioning Service

Handles async creation of new CRM workspaces from blueprints.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    Tenant, User, Pipeline, PipelineStage, 
    CRMBlueprint, CRMWorkspace, WorkspaceUser, ProvisioningJob,
    CalculationDefinition, StageTransitionRule,
    WorkspaceStatus, ProvisioningStatus, WorkspaceRole
)
from app.blueprints.frylow_blueprint import get_blueprint_json, get_all_blueprints, FRYLOW_BLUEPRINT, BLANK_BLUEPRINT, NLA_ACCOUNTING_BLUEPRINT

logger = logging.getLogger(__name__)


class ProvisioningService:
    """Service for provisioning new CRM workspaces"""
    
    PROVISIONING_STEPS = [
        "Validating blueprint",
        "Creating workspace",
        "Setting up pipelines",
        "Configuring stages",
        "Creating calculation definitions",
        "Setting up transition rules",
        "Creating forms",
        "Configuring automations",
        "Assigning admin user",
        "Seeding demo data",
        "Finalizing workspace"
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_workspace(
        self,
        name: str,
        slug: str,
        blueprint_slug: str,
        created_by_user_id: str,
        include_demo_data: bool = False,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start the workspace provisioning process.
        Returns the workspace and provisioning job IDs.
        """
        try:
            # Get or create blueprint record
            blueprint = await self._get_or_create_blueprint(blueprint_slug)
            
            # Create workspace record
            workspace = CRMWorkspace(
                id=str(uuid.uuid4()),
                name=name,
                slug=slug,
                description=description,
                blueprint_id=blueprint.id,
                blueprint_version=blueprint.version,
                status=WorkspaceStatus.PROVISIONING,
                created_by=created_by_user_id
            )
            self.db.add(workspace)
            
            # Create provisioning job
            job = ProvisioningJob(
                id=str(uuid.uuid4()),
                workspace_id=workspace.id,
                status=ProvisioningStatus.PENDING,
                progress=0,
                current_step="Initializing",
                options=json.dumps({
                    "blueprint_slug": blueprint_slug,
                    "include_demo_data": include_demo_data
                })
            )
            self.db.add(job)
            
            await self.db.commit()
            
            return {
                "workspace_id": workspace.id,
                "job_id": job.id,
                "status": "pending"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create workspace: {e}")
            raise
    
    async def run_provisioning(self, job_id: str) -> bool:
        """
        Execute the provisioning job.
        This should be called asynchronously after create_workspace.
        """
        # Get job
        result = await self.db.execute(
            select(ProvisioningJob).where(ProvisioningJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            logger.error(f"Provisioning job not found: {job_id}")
            return False
        
        # Update job status
        job.status = ProvisioningStatus.IN_PROGRESS
        job.started_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        try:
            # Get workspace
            result = await self.db.execute(
                select(CRMWorkspace).where(CRMWorkspace.id == job.workspace_id)
            )
            workspace = result.scalar_one_or_none()
            
            if not workspace:
                raise Exception("Workspace not found")
            
            # Get blueprint config
            options = json.loads(job.options or '{}')
            blueprint_slug = options.get('blueprint_slug', 'blank')
            include_demo_data = options.get('include_demo_data', False)
            blueprint_config = get_blueprint_json(blueprint_slug)
            
            # Create tenant for this workspace (maintains backward compatibility)
            tenant = Tenant(
                id=str(uuid.uuid4()),
                name=workspace.name,
                slug=workspace.slug,
                settings=json.dumps({"workspace_id": workspace.id})
            )
            self.db.add(tenant)
            await self.db.flush()
            
            # Store tenant_id in workspace settings
            workspace_settings = json.loads(workspace.settings or '{}')
            workspace_settings['tenant_id'] = tenant.id
            workspace.settings = json.dumps(workspace_settings)
            
            # Step 1: Create pipelines
            await self._update_job_progress(job, 1, "Setting up pipelines")
            pipeline_map = await self._create_pipelines(tenant.id, blueprint_config)
            
            # Step 2: Create calculations
            await self._update_job_progress(job, 3, "Creating calculation definitions")
            calc_map = await self._create_calculations(tenant.id, blueprint_config, pipeline_map)
            
            # Step 3: Create transition rules
            await self._update_job_progress(job, 5, "Setting up transition rules")
            await self._create_transition_rules(tenant.id, blueprint_config, pipeline_map, calc_map)
            
            # Step 4: Assign admin user
            await self._update_job_progress(job, 7, "Assigning admin user")
            await self._assign_workspace_admin(workspace, tenant)
            
            # Step 5: Seed demo data if requested
            if include_demo_data:
                await self._update_job_progress(job, 9, "Seeding demo data")
                await self._seed_demo_data(tenant.id, pipeline_map)
            
            # Step 6: Finalize
            await self._update_job_progress(job, 10, "Finalizing workspace")
            
            # Mark workspace as active
            workspace.status = WorkspaceStatus.ACTIVE
            
            # Mark job as complete
            job.status = ProvisioningStatus.COMPLETED
            job.progress = 100
            job.current_step = "Complete"
            job.completed_at = datetime.now(timezone.utc)
            completed_steps = json.loads(job.completed_steps or '[]')
            completed_steps.extend(self.PROVISIONING_STEPS)
            job.completed_steps = json.dumps(completed_steps)
            
            await self.db.commit()
            
            logger.info(f"Workspace provisioned successfully: {workspace.slug}")
            return True
            
        except Exception as e:
            logger.error(f"Provisioning failed: {e}")
            job.status = ProvisioningStatus.FAILED
            job.error_message = str(e)
            await self.db.commit()
            return False
    
    async def _get_or_create_blueprint(self, slug: str) -> CRMBlueprint:
        """Get existing blueprint or create from template"""
        result = await self.db.execute(
            select(CRMBlueprint).where(CRMBlueprint.slug == slug)
        )
        blueprint = result.scalar_one_or_none()
        
        if blueprint:
            return blueprint
        
        # Create new blueprint from template
        config = get_blueprint_json(slug)
        blueprint = CRMBlueprint(
            id=str(uuid.uuid4()),
            name=config.get('name', slug),
            slug=slug,
            description=config.get('description', ''),
            version=config.get('version', 1),
            is_system=True,
            is_default=(slug == 'frylow-sales'),
            config=json.dumps(config),
            icon=config.get('icon', 'briefcase'),
            color=config.get('color', '#6366F1')
        )
        self.db.add(blueprint)
        await self.db.flush()
        
        return blueprint
    
    async def _create_pipelines(self, tenant_id: str, config: dict) -> Dict[str, Dict[str, str]]:
        """Create pipelines and stages from blueprint config"""
        pipeline_map = {}  # {pipeline_slug: {stage_slug: stage_id}}
        
        for pipeline_config in config.get('pipelines', []):
            pipeline = Pipeline(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=pipeline_config['name'],
                description=pipeline_config.get('description'),
                is_default=pipeline_config.get('is_default', False),
                is_active=True,
                display_order=pipeline_config.get('display_order', 0)
            )
            self.db.add(pipeline)
            await self.db.flush()
            
            stage_map = {}
            for stage_config in pipeline_config.get('stages', []):
                stage = PipelineStage(
                    id=str(uuid.uuid4()),
                    pipeline_id=pipeline.id,
                    name=stage_config['name'],
                    description=stage_config.get('description'),
                    display_order=stage_config.get('display_order', 0),
                    probability=stage_config.get('probability', 0),
                    color=stage_config.get('color', '#6B7280'),
                    is_won_stage=stage_config.get('is_won_stage', False),
                    is_lost_stage=stage_config.get('is_lost_stage', False),
                    default_tasks=json.dumps(stage_config.get('rules', {}))
                )
                self.db.add(stage)
                await self.db.flush()
                stage_map[stage_config['slug']] = stage.id
            
            pipeline_map[pipeline_config['slug']] = {
                'pipeline_id': pipeline.id,
                'stages': stage_map
            }
        
        return pipeline_map
    
    async def _create_calculations(
        self, 
        tenant_id: str, 
        config: dict, 
        pipeline_map: dict
    ) -> Dict[str, str]:
        """Create calculation definitions from blueprint config"""
        calc_map = {}
        
        for calc_config in config.get('calculations', []):
            # Map stage slugs to IDs
            required_stages = []
            for stage_slug in calc_config.get('required_for_stages', []):
                for pipeline_data in pipeline_map.values():
                    if stage_slug in pipeline_data['stages']:
                        required_stages.append(pipeline_data['stages'][stage_slug])
            
            # Find return stage ID
            return_stage_id = None
            return_stage_slug = calc_config.get('return_to_stage_on_change')
            if return_stage_slug:
                for pipeline_data in pipeline_map.values():
                    if return_stage_slug in pipeline_data['stages']:
                        return_stage_id = pipeline_data['stages'][return_stage_slug]
                        break
            
            calc = CalculationDefinition(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=calc_config['name'],
                slug=calc_config['slug'],
                description=calc_config.get('description'),
                version=calc_config.get('version', 1),
                input_schema=json.dumps(calc_config.get('inputs', [])),
                output_schema=json.dumps(calc_config.get('outputs', [])),
                formula=json.dumps(calc_config.get('formula', {})),
                editable_by_roles=json.dumps(calc_config.get('editable_by_roles', [])),
                required_for_stages=json.dumps(required_stages),
                return_to_stage_on_change=return_stage_id
            )
            self.db.add(calc)
            await self.db.flush()
            calc_map[calc_config['slug']] = calc.id
        
        return calc_map
    
    async def _create_transition_rules(
        self,
        tenant_id: str,
        config: dict,
        pipeline_map: dict,
        calc_map: dict
    ):
        """Create stage transition rules from blueprint config"""
        for rule_config in config.get('transition_rules', []):
            pipeline_slug = rule_config.get('pipeline')
            if pipeline_slug not in pipeline_map:
                continue
            
            pipeline_data = pipeline_map[pipeline_slug]
            pipeline_id = pipeline_data['pipeline_id']
            stages = pipeline_data['stages']
            
            from_stage_id = None
            if rule_config.get('from_stage'):
                from_stage_id = stages.get(rule_config['from_stage'])
            
            to_stage_id = None
            if rule_config.get('to_stage'):
                to_stage_id = stages.get(rule_config['to_stage'])
            
            if not to_stage_id and rule_config['rule_type'] != 'calculation_change_return':
                continue  # Skip invalid rules
            
            # Process config - replace calculation slugs with IDs
            rule_cfg = rule_config.get('config', {})
            if 'calculation' in rule_cfg and rule_cfg['calculation'] in calc_map:
                rule_cfg['calculation_id'] = calc_map[rule_cfg['calculation']]
            
            rule = StageTransitionRule(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                from_stage_id=from_stage_id,
                to_stage_id=to_stage_id,
                rule_type=rule_config['rule_type'],
                config=json.dumps(rule_cfg),
                error_message=rule_config.get('error_message'),
                allow_override=rule_config.get('allow_override', True)
            )
            self.db.add(rule)
    
    async def _assign_workspace_admin(self, workspace: CRMWorkspace, tenant: Tenant):
        """Assign the creating user as workspace admin"""
        if not workspace.created_by:
            return
        
        # Get the user
        result = await self.db.execute(
            select(User).where(User.id == workspace.created_by)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Create workspace membership
            membership = WorkspaceUser(
                id=str(uuid.uuid4()),
                workspace_id=workspace.id,
                user_id=user.id,
                role=WorkspaceRole.OWNER
            )
            self.db.add(membership)
    
    async def _seed_demo_data(self, tenant_id: str, pipeline_map: dict):
        """Seed demo contacts and deals"""
        from app.models import Contact, Deal, DealStatus, BlueprintComplianceStatus
        
        # Demo contacts
        demo_contacts = [
            {"first_name": "Mike", "last_name": "Rodriguez", "email": "mike@bigburger.com", "company_name": "Big Burger Co", "phone": "+1-555-0201"},
            {"first_name": "Sarah", "last_name": "Chen", "email": "sarah@goldenwok.com", "company_name": "Golden Wok", "phone": "+1-555-0202"},
            {"first_name": "James", "last_name": "Wilson", "email": "james@crispychicken.com", "company_name": "Crispy Chicken", "phone": "+1-555-0203"},
            {"first_name": "Maria", "last_name": "Garcia", "email": "maria@tacofiesta.com", "company_name": "Taco Fiesta", "phone": "+1-555-0204"},
            {"first_name": "David", "last_name": "Kim", "email": "david@seoulkitchen.com", "company_name": "Seoul Kitchen", "phone": "+1-555-0205"},
        ]
        
        contact_ids = []
        for contact_data in demo_contacts:
            contact = Contact(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                **contact_data
            )
            self.db.add(contact)
            await self.db.flush()
            contact_ids.append(contact.id)
        
        # Create deals in different stages
        if 'qualifying' in pipeline_map:
            qualifying = pipeline_map['qualifying']
            pipeline_id = qualifying['pipeline_id']
            stages = qualifying['stages']
            
            # Deal in Working stage
            deal1 = Deal(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                stage_id=stages.get('working'),
                contact_id=contact_ids[0],
                name="Big Burger Co - Initial Contact",
                amount=0,
                status=DealStatus.OPEN,
                blueprint_compliance=BlueprintComplianceStatus.COMPLIANT
            )
            self.db.add(deal1)
            
            # Deal in Info Collected
            deal2 = Deal(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                stage_id=stages.get('info-collected'),
                contact_id=contact_ids[1],
                name="Golden Wok - Info Gathered",
                amount=3500,
                status=DealStatus.OPEN,
                blueprint_compliance=BlueprintComplianceStatus.COMPLIANT,
                custom_properties=json.dumps({
                    "number_of_fryers": 4,
                    "fryer_capacities": ["30L"],
                    "oil_units": "boxes",
                    "quantity_per_month": 12,
                    "cost_per_unit": 45
                })
            )
            self.db.add(deal2)
        
        if 'hot-leads' in pipeline_map:
            hot_leads = pipeline_map['hot-leads']
            pipeline_id = hot_leads['pipeline_id']
            stages = hot_leads['stages']
            
            # Deal in Demo Scheduled
            deal3 = Deal(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                stage_id=stages.get('demo-scheduled'),
                contact_id=contact_ids[2],
                name="Crispy Chicken - Demo Tomorrow",
                amount=5200,
                status=DealStatus.OPEN,
                blueprint_compliance=BlueprintComplianceStatus.COMPLIANT,
                custom_properties=json.dumps({
                    "number_of_fryers": 6,
                    "calculated_savings": {"low": 4860, "high": 8100}
                })
            )
            self.db.add(deal3)
            
            # Deal in Verbal Commitment
            deal4 = Deal(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                stage_id=stages.get('verbal-commitment'),
                contact_id=contact_ids[3],
                name="Taco Fiesta - Ready to Close",
                amount=4800,
                status=DealStatus.OPEN,
                blueprint_compliance=BlueprintComplianceStatus.COMPLIANT
            )
            self.db.add(deal4)
    
    async def _update_job_progress(self, job: ProvisioningJob, step: int, message: str):
        """Update provisioning job progress"""
        job.progress = int((step / len(self.PROVISIONING_STEPS)) * 100)
        job.current_step = message
        completed = json.loads(job.completed_steps or '[]')
        if step > 0:
            completed.append(self.PROVISIONING_STEPS[step - 1])
        job.completed_steps = json.dumps(completed)
        await self.db.commit()
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current provisioning job status"""
        result = await self.db.execute(
            select(ProvisioningJob).where(ProvisioningJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        return {
            "id": job.id,
            "workspace_id": job.workspace_id,
            "status": job.status.value,
            "progress": job.progress,
            "current_step": job.current_step,
            "completed_steps": json.loads(job.completed_steps or '[]'),
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }


async def seed_system_blueprints(db: AsyncSession):
    """Seed system blueprints on startup"""
    for bp_data in get_all_blueprints():
        result = await db.execute(
            select(CRMBlueprint).where(CRMBlueprint.slug == bp_data['slug'])
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            blueprint = CRMBlueprint(
                id=str(uuid.uuid4()),
                name=bp_data['name'],
                slug=bp_data['slug'],
                description=bp_data['config'].get('description', ''),
                version=bp_data['config'].get('version', 1),
                is_system=True,
                is_default=bp_data['is_default'],
                config=json.dumps(bp_data['config']),
                icon=bp_data['config'].get('icon', 'briefcase'),
                color=bp_data['config'].get('color', '#6366F1')
            )
            db.add(blueprint)
    
    await db.commit()
    logger.info("System blueprints seeded")
