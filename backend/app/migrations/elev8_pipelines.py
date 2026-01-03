"""
Elev8 CRM Pipeline Configuration

Creates the dual pipeline structure per Elev8 specification:
- Pipeline A: Qualification Pipeline (Section 5.1)
- Pipeline B: Sales Pipeline (Section 5.2)

Run this script to seed the Elev8 pipelines for a tenant.
"""

import asyncio
import uuid
from datetime import datetime, timezone

# Pipeline stage definitions per Section 5
QUALIFICATION_STAGES = [
    {
        "name": "New / Assigned",
        "color": "#6366F1",
        "probability": 5,
        "description": "New lead assigned to SDR",
        "required_fields": [],
        "stage_type": "new"
    },
    {
        "name": "Working",
        "color": "#8B5CF6",
        "probability": 10,
        "description": "Active contact attempts in progress",
        "required_fields": ["first_name", "last_name"],
        "stage_type": "working"
    },
    {
        "name": "Info Collected",
        "color": "#A855F7",
        "probability": 25,
        "description": "Qualification and scoring fields completed",
        "required_fields": ["economic_units", "usage_volume", "urgency", "decision_role"],
        "stage_type": "qualified_info"
    },
    {
        "name": "Unresponsive",
        "color": "#6B7280",
        "probability": 0,
        "description": "No response after minimum touchpoints",
        "required_fields": [],
        "stage_type": "unresponsive",
        "min_touchpoints": 5
    },
    {
        "name": "Disqualified",
        "color": "#EF4444",
        "probability": 0,
        "description": "Lead does not meet qualification criteria",
        "required_fields": [],
        "stage_type": "disqualified",
        "is_closed": True
    },
    {
        "name": "Qualified",
        "color": "#22C55E",
        "probability": 35,
        "description": "Lead qualified and ready for Sales Pipeline",
        "required_fields": ["economic_units", "usage_volume", "urgency", "decision_role"],
        "stage_type": "qualified",
        "push_to_sales": True
    }
]

SALES_STAGES = [
    {
        "name": "Calculations / Analysis",
        "color": "#6366F1",
        "probability": 35,
        "description": "ROI calculations and initial analysis in progress",
        "required_fields": [],
        "stage_type": "calculations"
    },
    {
        "name": "Discovery Scheduled",
        "color": "#8B5CF6",
        "probability": 40,
        "description": "Discovery meeting or demo scheduled",
        "required_fields": ["calculation_complete"],
        "stage_type": "discovery_scheduled",
        "requires_calculation": True
    },
    {
        "name": "Discovery Completed",
        "color": "#A855F7",
        "probability": 50,
        "description": "Discovery/demo completed, SPICED captured",
        "required_fields": ["spiced_summary"],
        "stage_type": "discovery_completed",
        "requires_spiced": True
    },
    {
        "name": "Decision Pending",
        "color": "#D946EF",
        "probability": 60,
        "description": "Awaiting decision from stakeholders",
        "required_fields": ["spiced_summary"],
        "stage_type": "decision_pending"
    },
    {
        "name": "Trial / Pilot",
        "color": "#EC4899",
        "probability": 70,
        "description": "Trial or pilot in progress",
        "required_fields": [],
        "stage_type": "trial",
        "is_optional": True
    },
    {
        "name": "Verbal Commitment",
        "color": "#F97316",
        "probability": 85,
        "description": "Verbal commitment received, contract pending",
        "required_fields": ["spiced_summary", "amount"],
        "stage_type": "verbal_commitment",
        "requires_discovery": True
    },
    {
        "name": "Closed Won",
        "color": "#22C55E",
        "probability": 100,
        "description": "Deal closed successfully",
        "required_fields": ["amount"],
        "stage_type": "closed_won",
        "is_closed": True,
        "is_won": True,
        "requires_handoff": True
    },
    {
        "name": "Closed Lost",
        "color": "#EF4444",
        "probability": 0,
        "description": "Deal lost",
        "required_fields": ["loss_reason"],
        "stage_type": "closed_lost",
        "is_closed": True,
        "is_won": False
    },
    {
        "name": "Handoff to Delivery",
        "color": "#10B981",
        "probability": 100,
        "description": "Customer handoff to delivery team complete",
        "required_fields": ["handoff_complete"],
        "stage_type": "handoff",
        "is_closed": True,
        "is_won": True
    }
]


async def create_elev8_pipelines(db, tenant_id: str):
    """
    Create the Elev8 dual pipeline structure for a tenant.
    
    Args:
        db: MongoDB database instance
        tenant_id: The tenant ID to create pipelines for
        
    Returns:
        Dict with qualification_pipeline_id and sales_pipeline_id
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # Check if pipelines already exist
    existing_qual = await db.pipelines.find_one({
        "tenant_id": tenant_id, 
        "pipeline_type": "qualification"
    })
    existing_sales = await db.pipelines.find_one({
        "tenant_id": tenant_id, 
        "pipeline_type": "sales"
    })
    
    if existing_qual and existing_sales:
        return {
            "qualification_pipeline_id": existing_qual["id"],
            "sales_pipeline_id": existing_sales["id"],
            "created": False,
            "message": "Elev8 pipelines already exist"
        }
    
    # Create Qualification Pipeline
    qual_pipeline_id = str(uuid.uuid4())
    qual_pipeline = {
        "id": qual_pipeline_id,
        "tenant_id": tenant_id,
        "name": "Qualification Pipeline",
        "description": "Activate, contact, and qualify leads (Section 5.1)",
        "pipeline_type": "qualification",
        "is_default": False,
        "display_order": 0,
        "created_at": now,
        "updated_at": now
    }
    await db.pipelines.insert_one(qual_pipeline)
    
    # Create Qualification Stages
    for i, stage_def in enumerate(QUALIFICATION_STAGES):
        stage = {
            "id": str(uuid.uuid4()),
            "pipeline_id": qual_pipeline_id,
            "name": stage_def["name"],
            "color": stage_def["color"],
            "probability": stage_def["probability"],
            "description": stage_def.get("description", ""),
            "required_fields": stage_def.get("required_fields", []),
            "stage_type": stage_def.get("stage_type"),
            "is_closed": stage_def.get("is_closed", False),
            "min_touchpoints": stage_def.get("min_touchpoints"),
            "push_to_sales": stage_def.get("push_to_sales", False),
            "display_order": i,
            "created_at": now
        }
        await db.pipeline_stages.insert_one(stage)
    
    # Create Sales Pipeline
    sales_pipeline_id = str(uuid.uuid4())
    sales_pipeline = {
        "id": sales_pipeline_id,
        "tenant_id": tenant_id,
        "name": "Sales Pipeline",
        "description": "Convert qualified leads into revenue (Section 5.2)",
        "pipeline_type": "sales",
        "is_default": True,
        "display_order": 1,
        "created_at": now,
        "updated_at": now
    }
    await db.pipelines.insert_one(sales_pipeline)
    
    # Create Sales Stages
    for i, stage_def in enumerate(SALES_STAGES):
        stage = {
            "id": str(uuid.uuid4()),
            "pipeline_id": sales_pipeline_id,
            "name": stage_def["name"],
            "color": stage_def["color"],
            "probability": stage_def["probability"],
            "description": stage_def.get("description", ""),
            "required_fields": stage_def.get("required_fields", []),
            "stage_type": stage_def.get("stage_type"),
            "is_closed": stage_def.get("is_closed", False),
            "is_won": stage_def.get("is_won"),
            "is_optional": stage_def.get("is_optional", False),
            "requires_calculation": stage_def.get("requires_calculation", False),
            "requires_spiced": stage_def.get("requires_spiced", False),
            "requires_discovery": stage_def.get("requires_discovery", False),
            "requires_handoff": stage_def.get("requires_handoff", False),
            "display_order": i,
            "created_at": now
        }
        await db.pipeline_stages.insert_one(stage)
    
    return {
        "qualification_pipeline_id": qual_pipeline_id,
        "sales_pipeline_id": sales_pipeline_id,
        "created": True,
        "message": "Elev8 pipelines created successfully"
    }


async def migrate_existing_deals_to_sales_pipeline(db, tenant_id: str, old_pipeline_id: str, new_pipeline_id: str):
    """
    Migrate existing deals from old pipeline to new sales pipeline.
    Maps stages based on probability/position.
    """
    # Get new pipeline stages
    new_stages = await db.pipeline_stages.find(
        {"pipeline_id": new_pipeline_id}
    ).sort("display_order", 1).to_list(length=100)
    
    if not new_stages:
        return {"migrated": 0, "message": "No stages in new pipeline"}
    
    # Get first stage for migration
    first_stage = new_stages[0]
    
    # Update all open deals to the new pipeline's first stage
    result = await db.deals.update_many(
        {"tenant_id": tenant_id, "pipeline_id": old_pipeline_id, "status": "open"},
        {"$set": {
            "pipeline_id": new_pipeline_id,
            "stage_id": first_stage["id"],
            "stage_name": first_stage["name"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "migrated": result.modified_count,
        "message": f"Migrated {result.modified_count} deals to Sales Pipeline"
    }
