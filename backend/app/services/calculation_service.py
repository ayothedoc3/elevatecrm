"""
Calculation Engine Service

Handles running calculations on deals and enforcing calculation-based stage rules.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import (
    Deal, PipelineStage, CalculationDefinition, CalculationResult,
    StageTransitionRule, TimelineEvent, TimelineEventType, VisibilityScope
)

logger = logging.getLogger(__name__)


class CalculationService:
    """Service for running calculations and enforcing calculation gates"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_calculation_for_deal(
        self, 
        tenant_id: str, 
        deal_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get calculation definition and current result for a deal"""
        # Get deal to find applicable calculation
        result = await self.db.execute(
            select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id))
        )
        deal = result.scalar_one_or_none()
        
        if not deal:
            return None
        
        # Get calculations for this tenant
        result = await self.db.execute(
            select(CalculationDefinition).where(
                and_(
                    CalculationDefinition.tenant_id == tenant_id,
                    CalculationDefinition.is_active == True
                )
            )
        )
        calculations = result.scalars().all()
        
        if not calculations:
            return None
        
        # Use first active calculation (typically one per CRM)
        calc_def = calculations[0]
        
        # Get existing result for this deal
        result = await self.db.execute(
            select(CalculationResult).where(
                and_(
                    CalculationResult.deal_id == deal_id,
                    CalculationResult.calculation_id == calc_def.id
                )
            )
        )
        calc_result = result.scalar_one_or_none()
        
        return {
            "definition": {
                "id": calc_def.id,
                "name": calc_def.name,
                "slug": calc_def.slug,
                "description": calc_def.description,
                "inputs": json.loads(calc_def.input_schema or '[]'),
                "outputs": json.loads(calc_def.output_schema or '[]'),
                "editable_by_roles": json.loads(calc_def.editable_by_roles or '[]')
            },
            "result": {
                "id": calc_result.id if calc_result else None,
                "inputs": json.loads(calc_result.inputs or '{}') if calc_result else {},
                "outputs": json.loads(calc_result.outputs or '{}') if calc_result else {},
                "is_complete": calc_result.is_complete if calc_result else False,
                "status": calc_result.status if calc_result else "pending",
                "calculated_at": calc_result.calculated_at.isoformat() if calc_result and calc_result.calculated_at else None,
                "validation_errors": json.loads(calc_result.validation_errors or '[]') if calc_result else []
            } if calc_result else None
        }
    
    async def update_calculation_inputs(
        self,
        tenant_id: str,
        deal_id: str,
        inputs: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update calculation inputs and auto-run calculation.
        May trigger stage change if inputs changed.
        """
        # Get calculation definition
        result = await self.db.execute(
            select(CalculationDefinition).where(
                and_(
                    CalculationDefinition.tenant_id == tenant_id,
                    CalculationDefinition.is_active == True
                )
            )
        )
        calc_def = result.scalar_one_or_none()
        
        if not calc_def:
            raise ValueError("No calculation definition found")
        
        # Get deal
        result = await self.db.execute(
            select(Deal).where(and_(Deal.id == deal_id, Deal.tenant_id == tenant_id))
        )
        deal = result.scalar_one_or_none()
        
        if not deal:
            raise ValueError("Deal not found")
        
        # Get or create calculation result
        result = await self.db.execute(
            select(CalculationResult).where(
                and_(
                    CalculationResult.deal_id == deal_id,
                    CalculationResult.calculation_id == calc_def.id
                )
            )
        )
        calc_result = result.scalar_one_or_none()
        
        old_inputs = {}
        if calc_result:
            old_inputs = json.loads(calc_result.inputs or '{}')
        else:
            calc_result = CalculationResult(
                tenant_id=tenant_id,
                deal_id=deal_id,
                calculation_id=calc_def.id,
                calculation_version=calc_def.version
            )
            self.db.add(calc_result)
        
        # Update inputs
        calc_result.inputs = json.dumps(inputs)
        calc_result.updated_at = datetime.now(timezone.utc)
        
        # Validate inputs
        input_schema = json.loads(calc_def.input_schema or '[]')
        validation_errors = self._validate_inputs(inputs, input_schema)
        calc_result.validation_errors = json.dumps(validation_errors)
        
        # Check if all required inputs are present
        all_required_present = all(
            field['name'] in inputs and inputs[field['name']] is not None
            for field in input_schema if field.get('required', False)
        )
        
        # Run calculation if all inputs present
        outputs = {}
        if all_required_present and not validation_errors:
            outputs = self._run_calculation(inputs, json.loads(calc_def.output_schema or '[]'))
            calc_result.outputs = json.dumps(outputs)
            calc_result.is_complete = True
            calc_result.status = "complete"
            calc_result.calculated_at = datetime.now(timezone.utc)
        else:
            calc_result.is_complete = False
            calc_result.status = "incomplete" if not validation_errors else "error"
        
        # Check if inputs changed (for return-to-stage rule)
        inputs_changed = self._check_inputs_changed(old_inputs, inputs, calc_def)
        
        # Handle stage return if inputs changed and deal is past calculation stage
        stage_returned = False
        if inputs_changed and calc_def.return_to_stage_on_change:
            stage_returned = await self._handle_input_change_stage_return(
                deal, calc_def.return_to_stage_on_change, user_id
            )
        
        await self.db.commit()
        
        # Create timeline event
        event = TimelineEvent(
            tenant_id=tenant_id,
            deal_id=deal_id,
            event_type=TimelineEventType.CALCULATION_RUN,
            visibility=VisibilityScope.INTERNAL,
            event_data=json.dumps({
                "calculation_name": calc_def.name,
                "is_complete": calc_result.is_complete,
                "inputs_changed": inputs_changed,
                "stage_returned": stage_returned
            }),
            actor_id=user_id
        )
        self.db.add(event)
        await self.db.commit()
        
        return {
            "id": calc_result.id,
            "inputs": inputs,
            "outputs": outputs,
            "is_complete": calc_result.is_complete,
            "status": calc_result.status,
            "validation_errors": validation_errors,
            "inputs_changed": inputs_changed,
            "stage_returned": stage_returned
        }
    
    def _validate_inputs(self, inputs: Dict[str, Any], schema: List[Dict]) -> List[str]:
        """Validate inputs against schema"""
        errors = []
        
        for field in schema:
            name = field['name']
            required = field.get('required', False)
            field_type = field.get('type', 'text')
            
            value = inputs.get(name)
            
            # Check required
            if required and (value is None or value == '' or value == []):
                errors.append(f"{field.get('label', name)} is required")
                continue
            
            if value is None:
                continue
            
            # Type validation
            if field_type == 'integer':
                try:
                    int_val = int(value)
                    if 'min' in field and int_val < field['min']:
                        errors.append(f"{field.get('label', name)} must be at least {field['min']}")
                    if 'max' in field and int_val > field['max']:
                        errors.append(f"{field.get('label', name)} must be at most {field['max']}")
                except (ValueError, TypeError):
                    errors.append(f"{field.get('label', name)} must be a number")
            
            elif field_type == 'currency':
                try:
                    float_val = float(value)
                    if 'min' in field and float_val < field['min']:
                        errors.append(f"{field.get('label', name)} must be at least {field['min']}")
                except (ValueError, TypeError):
                    errors.append(f"{field.get('label', name)} must be a valid amount")
            
            elif field_type == 'select':
                options = [opt['value'] for opt in field.get('options', [])]
                if value not in options:
                    errors.append(f"{field.get('label', name)} must be one of: {', '.join(options)}")
            
            elif field_type == 'multi_select':
                options = [opt['value'] for opt in field.get('options', [])]
                if isinstance(value, list):
                    invalid = [v for v in value if v not in options]
                    if invalid:
                        errors.append(f"{field.get('label', name)} contains invalid options: {', '.join(invalid)}")
                else:
                    errors.append(f"{field.get('label', name)} must be a list")
        
        return errors
    
    def _run_calculation(self, inputs: Dict[str, Any], output_schema: List[Dict]) -> Dict[str, Any]:
        """Run calculation formulas on inputs"""
        outputs = {}
        
        # Extract input values
        number_of_fryers = int(inputs.get('number_of_fryers', 0))
        fryer_capacities = inputs.get('fryer_capacities', [])
        oil_units = inputs.get('oil_units', 'boxes')
        quantity_per_month = int(inputs.get('quantity_per_month', 0))
        cost_per_unit = float(inputs.get('cost_per_unit', 0))
        
        # Calculate outputs
        monthly_oil_spend = quantity_per_month * cost_per_unit
        yearly_oil_spend = monthly_oil_spend * 12
        estimated_savings_low = yearly_oil_spend * 0.30
        estimated_savings_high = yearly_oil_spend * 0.50
        recommended_device_quantity = number_of_fryers
        
        # Determine recommended device size based on largest fryer
        size_map = {'16L': 'Small', '30L': 'Medium', '45L': 'Large'}
        size_order = ['45L', '30L', '16L']
        recommended_device_size = 'Medium'  # Default
        for size in size_order:
            if size in fryer_capacities:
                recommended_device_size = size_map[size]
                break
        
        outputs = {
            'monthly_oil_spend': round(monthly_oil_spend, 2),
            'yearly_oil_spend': round(yearly_oil_spend, 2),
            'estimated_savings_low': round(estimated_savings_low, 2),
            'estimated_savings_high': round(estimated_savings_high, 2),
            'recommended_device_quantity': recommended_device_quantity,
            'recommended_device_size': recommended_device_size
        }
        
        return outputs
    
    def _check_inputs_changed(
        self, 
        old_inputs: Dict, 
        new_inputs: Dict, 
        calc_def: CalculationDefinition
    ) -> bool:
        """Check if calculation-relevant inputs changed"""
        if not old_inputs:
            return False
        
        # Get trigger fields from schema
        input_schema = json.loads(calc_def.input_schema or '[]')
        trigger_fields = [f['name'] for f in input_schema if f.get('required', False)]
        
        for field in trigger_fields:
            old_val = old_inputs.get(field)
            new_val = new_inputs.get(field)
            if old_val != new_val:
                return True
        
        return False
    
    async def _handle_input_change_stage_return(
        self,
        deal: Deal,
        return_stage_id: str,
        user_id: Optional[str]
    ) -> bool:
        """Return deal to calculation stage if inputs changed"""
        if not deal.stage_id or deal.stage_id == return_stage_id:
            return False
        
        # Get current stage order
        result = await self.db.execute(
            select(PipelineStage).where(PipelineStage.id == deal.stage_id)
        )
        current_stage = result.scalar_one_or_none()
        
        result = await self.db.execute(
            select(PipelineStage).where(PipelineStage.id == return_stage_id)
        )
        return_stage = result.scalar_one_or_none()
        
        if not current_stage or not return_stage:
            return False
        
        # Only return if current stage is after return stage
        if current_stage.display_order > return_stage.display_order:
            old_stage_id = deal.stage_id
            deal.stage_id = return_stage_id
            deal.pipeline_id = return_stage.pipeline_id
            deal.updated_at = datetime.now(timezone.utc)
            
            # Create stage change event
            event = TimelineEvent(
                tenant_id=deal.tenant_id,
                deal_id=deal.id,
                event_type=TimelineEventType.STAGE_CHANGED,
                visibility=VisibilityScope.INTERNAL,
                event_data=json.dumps({
                    "from_stage_id": old_stage_id,
                    "to_stage_id": return_stage_id,
                    "reason": "Calculation inputs changed",
                    "auto_return": True
                }),
                actor_id=user_id
            )
            self.db.add(event)
            
            return True
        
        return False
    
    async def check_calculation_complete(
        self,
        tenant_id: str,
        deal_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if calculation is complete for stage transition.
        Returns (is_complete, error_message)
        """
        result = await self.db.execute(
            select(CalculationDefinition).where(
                and_(
                    CalculationDefinition.tenant_id == tenant_id,
                    CalculationDefinition.is_active == True
                )
            )
        )
        calc_def = result.scalar_one_or_none()
        
        if not calc_def:
            return (True, None)  # No calculation required
        
        result = await self.db.execute(
            select(CalculationResult).where(
                and_(
                    CalculationResult.deal_id == deal_id,
                    CalculationResult.calculation_id == calc_def.id
                )
            )
        )
        calc_result = result.scalar_one_or_none()
        
        if not calc_result or not calc_result.is_complete:
            return (False, f"Calculation '{calc_def.name}' must be complete before proceeding")
        
        return (True, None)
    
    async def check_all_inputs_collected(
        self,
        tenant_id: str,
        deal_id: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if all required calculation inputs are collected.
        Returns (all_collected, missing_fields)
        """
        result = await self.db.execute(
            select(CalculationDefinition).where(
                and_(
                    CalculationDefinition.tenant_id == tenant_id,
                    CalculationDefinition.is_active == True
                )
            )
        )
        calc_def = result.scalar_one_or_none()
        
        if not calc_def:
            return (True, [])
        
        result = await self.db.execute(
            select(CalculationResult).where(
                and_(
                    CalculationResult.deal_id == deal_id,
                    CalculationResult.calculation_id == calc_def.id
                )
            )
        )
        calc_result = result.scalar_one_or_none()
        
        input_schema = json.loads(calc_def.input_schema or '[]')
        required_fields = [f for f in input_schema if f.get('required', False)]
        
        if not calc_result:
            missing = [f.get('label', f['name']) for f in required_fields]
            return (False, missing)
        
        inputs = json.loads(calc_result.inputs or '{}')
        missing = []
        
        for field in required_fields:
            name = field['name']
            if name not in inputs or inputs[name] is None or inputs[name] == '' or inputs[name] == []:
                missing.append(field.get('label', name))
        
        return (len(missing) == 0, missing)
