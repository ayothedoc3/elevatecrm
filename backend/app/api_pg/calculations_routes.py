from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_pg.deps import get_current_user
from app.api_pg.services import get_active_calculation_definition, get_calculation_result
from app.api_pg.utils import is_non_empty, now_utc
from app.core.database import get_db
from app.pg_models.models import CalculationResult, Deal

router = APIRouter(prefix="/calculations", tags=["Calculations"])


class UpdateCalculationRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)


@router.get("/deal/{deal_id}")
async def get_deal_calculation(
    deal_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    calc_def = await get_active_calculation_definition(db, user["tenant_id"])
    if not calc_def:
        return {"definition": None, "result": None}

    result = await get_calculation_result(db, deal_id=deal_id, definition_id=calc_def.id)

    return {
        "definition": {
            "id": calc_def.id,
            "name": calc_def.name,
            "description": calc_def.description,
            "inputs": list(calc_def.input_schema or []),
            "outputs": list(calc_def.output_schema or []),
        },
        "result": {
            "inputs": (result.inputs or {}) if result else {},
            "outputs": (result.outputs or {}) if result else {},
            "is_complete": bool(result.is_complete) if result else False,
            "validation_errors": [],
        }
        if result
        else None,
    }


@router.post("/deal/{deal_id}/calculate")
async def calculate_deal(
    deal_id: str,
    inputs: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await update_deal_calculation(deal_id=deal_id, data=UpdateCalculationRequest(inputs=inputs), user=user, db=db)
    return {"success": True, "is_complete": res["is_complete"], "outputs": res["outputs"]}


@router.put("/deal/{deal_id}")
async def update_deal_calculation(
    deal_id: str,
    data: UpdateCalculationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    calc_def = await get_active_calculation_definition(db, user["tenant_id"])
    if not calc_def:
        raise HTTPException(status_code=404, detail="No calculation defined")

    input_schema = list(calc_def.input_schema or [])

    missing_fields: List[str] = []
    for field in input_schema:
        if field.get("required") and not is_non_empty((data.inputs or {}).get(field.get("name"))):
            missing_fields.append(field.get("name"))

    is_complete = len(missing_fields) == 0

    outputs: Dict[str, Any] = {}
    try:
        quantity = float((data.inputs or {}).get("quantity_per_month", 0) or 0)
        cost = float((data.inputs or {}).get("cost_per_unit", 0) or 0)
        monthly_spend = quantity * cost
        yearly_spend = monthly_spend * 12
        outputs = {
            "monthly_oil_spend": monthly_spend,
            "yearly_oil_spend": yearly_spend,
            "estimated_savings_low": yearly_spend * 0.3,
            "estimated_savings_high": yearly_spend * 0.5,
            "recommended_device_quantity": max(1, int((data.inputs or {}).get("number_of_fryers", 1) or 1)),
            "recommended_device_size": "Standard",
        }
    except Exception:
        outputs = {}

    now = now_utc()

    existing = await get_calculation_result(db, deal_id=deal_id, definition_id=calc_def.id)
    if existing:
        existing.inputs = dict(data.inputs or {})
        existing.outputs = outputs
        existing.is_complete = is_complete
        existing.updated_at = now
        result_id = existing.id
    else:
        new_result = CalculationResult(
            id=str(uuid.uuid4()),
            deal_id=deal_id,
            definition_id=calc_def.id,
            inputs=dict(data.inputs or {}),
            outputs=outputs,
            is_complete=is_complete,
            created_at=now,
            updated_at=now,
        )
        db.add(new_result)
        await db.flush()
        result_id = new_result.id

    return {
        "id": result_id,
        "inputs": dict(data.inputs or {}),
        "outputs": outputs,
        "is_complete": is_complete,
        "status": "complete" if is_complete else "missing_inputs",
        "missing_fields": missing_fields,
        "validation_errors": [f"Missing required field: {f}" for f in missing_fields],
        "inputs_changed": True,
        "stage_returned": False,
    }


@router.get("/deal/{deal_id}/check")
async def check_deal_calculation(
    deal_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    calc_def = await get_active_calculation_definition(db, user["tenant_id"])
    if not calc_def:
        return {"is_complete": True, "error_message": None, "missing_fields": []}

    input_schema = list(calc_def.input_schema or [])
    result = await get_calculation_result(db, deal_id=deal_id, definition_id=calc_def.id)
    inputs = (result.inputs or {}) if result else {}

    missing_fields: List[str] = []
    for field in input_schema:
        if field.get("required") and not is_non_empty(inputs.get(field.get("name"))):
            missing_fields.append(field.get("name"))

    is_complete = len(missing_fields) == 0
    return {
        "is_complete": is_complete,
        "error_message": None if is_complete else "Missing required calculation inputs",
        "missing_fields": missing_fields,
    }

