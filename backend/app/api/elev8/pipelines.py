"""
Elev8 CRM - Pipeline Routes

Pipeline setup and query endpoints.
Per Elev8 specification section 5.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongodb import get_database
from .auth import get_current_user

router = APIRouter(tags=["Pipelines"])


@router.post("/setup/pipelines")
async def setup_elev8_pipelines(user = Depends(get_current_user)):
    """
    Create the Elev8 dual pipeline structure (Qualification + Sales).
    This is typically run once during initial setup.
    """
    db = get_database()
    
    # Check admin role
    if user.get("role") not in ["admin", "owner", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.migrations.elev8_pipelines import create_elev8_pipelines
    
    result = await create_elev8_pipelines(db, user["tenant_id"])
    return result


@router.post("/setup/migrate-deals")
async def migrate_deals_to_elev8(old_pipeline_id: str = Query(...), user = Depends(get_current_user)):
    """
    Migrate existing deals from an old pipeline to the new Sales Pipeline.
    """
    db = get_database()
    
    # Check admin role
    if user.get("role") not in ["admin", "owner", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get sales pipeline
    sales_pipeline = await db.pipelines.find_one({
        "tenant_id": user["tenant_id"],
        "pipeline_type": "sales"
    })
    
    if not sales_pipeline:
        raise HTTPException(status_code=400, detail="Sales pipeline not found. Run /setup/pipelines first.")
    
    from app.migrations.elev8_pipelines import migrate_existing_deals_to_sales_pipeline
    
    result = await migrate_existing_deals_to_sales_pipeline(
        db, user["tenant_id"], old_pipeline_id, sales_pipeline["id"]
    )
    return result


@router.get("/pipelines/elev8")
async def get_elev8_pipelines(user = Depends(get_current_user)):
    """Get the Elev8 dual pipeline configuration"""
    db = get_database()
    
    qual_pipeline = await db.pipelines.find_one(
        {"tenant_id": user["tenant_id"], "pipeline_type": "qualification"},
        {"_id": 0}
    )
    
    sales_pipeline = await db.pipelines.find_one(
        {"tenant_id": user["tenant_id"], "pipeline_type": "sales"},
        {"_id": 0}
    )
    
    result = {"qualification": None, "sales": None}
    
    if qual_pipeline:
        stages = await db.pipeline_stages.find(
            {"pipeline_id": qual_pipeline["id"]},
            {"_id": 0}
        ).sort("display_order", 1).to_list(length=100)
        result["qualification"] = {**qual_pipeline, "stages": stages}
    
    if sales_pipeline:
        stages = await db.pipeline_stages.find(
            {"pipeline_id": sales_pipeline["id"]},
            {"_id": 0}
        ).sort("display_order", 1).to_list(length=100)
        result["sales"] = {**sales_pipeline, "stages": stages}
    
    return result
