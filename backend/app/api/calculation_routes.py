"""
Calculation API Routes

Handles calculation operations for deals including input updates and output retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import json

from app.core.database import get_db
from app.models import User, Deal, CalculationDefinition, CalculationResult
from app.services.calculation_service import CalculationService

router = APIRouter(prefix="/calculations", tags=["Calculations"])


# ==================== SCHEMAS ====================

class CalculationInputField(BaseModel):
    name: str
    type: str
    label: str
    required: bool
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None
    min: Optional[float] = None
    max: Optional[float] = None


class CalculationOutputField(BaseModel):
    name: str
    type: str
    label: str
    description: Optional[str] = None


class CalculationDefinitionResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    inputs: List[CalculationInputField]
    outputs: List[CalculationOutputField]
    editable_by_roles: List[str]


class CalculationResultResponse(BaseModel):
    id: Optional[str]
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    is_complete: bool
    status: str
    calculated_at: Optional[str]
    validation_errors: List[str]


class DealCalculationResponse(BaseModel):
    definition: CalculationDefinitionResponse
    result: Optional[CalculationResultResponse]


class UpdateCalculationInputsRequest(BaseModel):
    inputs: Dict[str, Any]


class UpdateCalculationInputsResponse(BaseModel):
    id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    is_complete: bool
    status: str
    validation_errors: List[str]
    inputs_changed: bool
    stage_returned: bool


class CalculationCheckResponse(BaseModel):
    is_complete: bool
    error_message: Optional[str]
    missing_fields: List[str]


# ==================== ENDPOINTS ====================

@router.get("/tenant/{tenant_id}/definitions")
async def list_calculation_definitions(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all calculation definitions for a tenant"""
    result = await db.execute(
        select(CalculationDefinition).where(
            and_(
                CalculationDefinition.tenant_id == tenant_id,
                CalculationDefinition.is_active == True
            )
        )
    )
    definitions = result.scalars().all()
    
    return {
        "definitions": [
            {
                "id": d.id,
                "name": d.name,
                "slug": d.slug,
                "description": d.description,
                "version": d.version,
                "inputs": json.loads(d.input_schema or '[]'),
                "outputs": json.loads(d.output_schema or '[]'),
                "editable_by_roles": json.loads(d.editable_by_roles or '[]')
            }
            for d in definitions
        ]
    }


@router.get("/deal/{deal_id}", response_model=DealCalculationResponse)
async def get_deal_calculation(
    deal_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get calculation definition and current result for a deal"""
    # Get deal first to get tenant_id
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    service = CalculationService(db)
    calc_data = await service.get_calculation_for_deal(deal.tenant_id, deal_id)
    
    if not calc_data:
        raise HTTPException(status_code=404, detail="No calculation defined for this workspace")
    
    # Transform to response model
    definition = calc_data['definition']
    result_data = calc_data['result']
    
    return DealCalculationResponse(
        definition=CalculationDefinitionResponse(
            id=definition['id'],
            name=definition['name'],
            slug=definition['slug'],
            description=definition['description'],
            inputs=[CalculationInputField(**inp) for inp in definition['inputs']],
            outputs=[CalculationOutputField(**out) for out in definition['outputs']],
            editable_by_roles=definition['editable_by_roles']
        ),
        result=CalculationResultResponse(
            id=result_data['id'] if result_data else None,
            inputs=result_data['inputs'] if result_data else {},
            outputs=result_data['outputs'] if result_data else {},
            is_complete=result_data['is_complete'] if result_data else False,
            status=result_data['status'] if result_data else "pending",
            calculated_at=result_data['calculated_at'] if result_data else None,
            validation_errors=result_data['validation_errors'] if result_data else []
        ) if result_data else None
    )


@router.put("/deal/{deal_id}", response_model=UpdateCalculationInputsResponse)
async def update_deal_calculation(
    deal_id: str,
    request: UpdateCalculationInputsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update calculation inputs for a deal and auto-run calculation"""
    # Get deal first to get tenant_id
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    service = CalculationService(db)
    
    try:
        result = await service.update_calculation_inputs(
            tenant_id=deal.tenant_id,
            deal_id=deal_id,
            inputs=request.inputs,
            user_id=None  # Will come from auth context
        )
        
        return UpdateCalculationInputsResponse(
            id=result['id'],
            inputs=result['inputs'],
            outputs=result['outputs'],
            is_complete=result['is_complete'],
            status=result['status'],
            validation_errors=result['validation_errors'],
            inputs_changed=result['inputs_changed'],
            stage_returned=result['stage_returned']
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/deal/{deal_id}/check", response_model=CalculationCheckResponse)
async def check_deal_calculation(
    deal_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if calculation is complete for stage transition"""
    # Get deal first to get tenant_id
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    service = CalculationService(db)
    
    is_complete, error_message = await service.check_calculation_complete(
        deal.tenant_id, deal_id
    )
    
    all_collected, missing_fields = await service.check_all_inputs_collected(
        deal.tenant_id, deal_id
    )
    
    return CalculationCheckResponse(
        is_complete=is_complete,
        error_message=error_message,
        missing_fields=missing_fields
    )


@router.post("/deal/{deal_id}/recalculate")
async def recalculate_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Force recalculation for a deal using existing inputs"""
    # Get deal
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Get existing calculation result
    result = await db.execute(
        select(CalculationResult).where(CalculationResult.deal_id == deal_id)
    )
    calc_result = result.scalar_one_or_none()
    
    if not calc_result:
        raise HTTPException(status_code=404, detail="No calculation found for deal")
    
    # Re-run calculation with existing inputs
    service = CalculationService(db)
    existing_inputs = json.loads(calc_result.inputs or '{}')
    
    result = await service.update_calculation_inputs(
        tenant_id=deal.tenant_id,
        deal_id=deal_id,
        inputs=existing_inputs,
        user_id=None
    )
    
    return {
        "success": True,
        "is_complete": result['is_complete'],
        "outputs": result['outputs']
    }
