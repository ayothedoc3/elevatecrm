"""
Elev8 CRM - Partner-Specific Configuration Routes

Per PRD Section 12, Partner Sales must support:
- Partner-specific pipelines mapped to universal stages
- Partner-specific required fields
- Partner-specific KPIs
- Partner-specific compliance rules

Core CRM logic remains unchanged.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

from app.db.mongodb import get_database
from app.api.elev8.auth import get_current_user

router = APIRouter(tags=["Partner Configuration"])


# ==================== SCHEMAS ====================

class PartnerPipelineConfig(BaseModel):
    """Partner-specific pipeline configuration"""
    stage_mappings: Optional[Dict[str, str]] = None  # Map universal stages to partner stages
    skip_stages: Optional[List[str]] = None  # Stages to skip for this partner
    custom_stages: Optional[List[Dict[str, Any]]] = None  # Additional custom stages


class PartnerFieldConfig(BaseModel):
    """Partner-specific required fields"""
    required_at_qualification: Optional[List[str]] = None
    required_at_discovery: Optional[List[str]] = None
    required_at_proposal: Optional[List[str]] = None
    required_at_close: Optional[List[str]] = None
    custom_fields: Optional[List[Dict[str, Any]]] = None  # Custom field definitions


class PartnerKPIConfig(BaseModel):
    """Partner-specific KPI configuration"""
    target_win_rate: Optional[float] = None
    target_deal_size: Optional[float] = None
    target_cycle_days: Optional[int] = None
    target_qualification_rate: Optional[float] = None
    custom_kpis: Optional[List[Dict[str, Any]]] = None


class PartnerComplianceConfig(BaseModel):
    """Partner-specific compliance rules"""
    rules: Optional[List[str]] = None
    required_certifications: Optional[List[str]] = None
    approval_thresholds: Optional[Dict[str, float]] = None  # e.g., {"discount": 10, "contract_value": 50000}
    mandatory_reviews: Optional[List[str]] = None


class PartnerConfigUpdate(BaseModel):
    """Full partner configuration update"""
    pipeline_config: Optional[PartnerPipelineConfig] = None
    field_config: Optional[PartnerFieldConfig] = None
    kpi_config: Optional[PartnerKPIConfig] = None
    compliance_config: Optional[PartnerComplianceConfig] = None


# ==================== PARTNER CONFIG ENDPOINTS ====================

@router.get("/partners/{partner_id}/config")
async def get_partner_config(
    partner_id: str,
    user = Depends(get_current_user)
):
    """
    Get the full configuration for a partner.
    """
    db = get_database()
    
    partner = await db.partners.find_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Get or create config
    config = await db.partner_configs.find_one(
        {"partner_id": partner_id},
        {"_id": 0}
    )
    
    # Default configuration
    default_config = {
        "partner_id": partner_id,
        "partner_name": partner.get("name"),
        "pipeline_config": {
            "stage_mappings": {},
            "skip_stages": [],
            "custom_stages": []
        },
        "field_config": {
            "required_at_qualification": ["economic_units", "urgency"],
            "required_at_discovery": ["spiced_situation", "spiced_pain"],
            "required_at_proposal": ["amount"],
            "required_at_close": ["spiced_summary"],
            "custom_fields": []
        },
        "kpi_config": {
            "target_win_rate": 25.0,
            "target_deal_size": 5000.0,
            "target_cycle_days": 45,
            "target_qualification_rate": 30.0,
            "custom_kpis": []
        },
        "compliance_config": {
            "rules": [],
            "required_certifications": [],
            "approval_thresholds": {},
            "mandatory_reviews": []
        }
    }
    
    if config:
        # Merge with defaults
        for key in default_config:
            if key not in config or config[key] is None:
                config[key] = default_config[key]
        return config
    
    return default_config


@router.put("/partners/{partner_id}/config")
async def update_partner_config(
    partner_id: str,
    data: PartnerConfigUpdate,
    user = Depends(get_current_user)
):
    """
    Update partner-specific configuration.
    Only admins can update partner configurations.
    """
    db = get_database()
    
    # Check admin role
    if user.get("role") not in ["admin", "owner", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    partner = await db.partners.find_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get existing config or create new
    existing = await db.partner_configs.find_one({"partner_id": partner_id})
    
    config_data = {
        "partner_id": partner_id,
        "tenant_id": user["tenant_id"],
        "updated_at": now,
        "updated_by": user["id"]
    }
    
    if data.pipeline_config:
        config_data["pipeline_config"] = data.pipeline_config.dict()
    if data.field_config:
        config_data["field_config"] = data.field_config.dict()
    if data.kpi_config:
        config_data["kpi_config"] = data.kpi_config.dict()
    if data.compliance_config:
        config_data["compliance_config"] = data.compliance_config.dict()
    
    if existing:
        await db.partner_configs.update_one(
            {"partner_id": partner_id},
            {"$set": config_data}
        )
    else:
        config_data["id"] = str(uuid.uuid4())
        config_data["created_at"] = now
        await db.partner_configs.insert_one(config_data)
    
    # Log the change
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "type": "partner_config_updated",
        "partner_id": partner_id,
        "user_id": user["id"],
        "description": f"Partner configuration updated for {partner.get('name')}",
        "created_at": now
    })
    
    config_data.pop("_id", None)
    return {"message": "Configuration updated", "config": config_data}


@router.get("/partners/{partner_id}/kpis")
async def get_partner_kpis(
    partner_id: str,
    period: str = Query("month", description="Period: week, month, quarter"),
    user = Depends(get_current_user)
):
    """
    Get KPIs for a specific partner.
    """
    db = get_database()
    
    partner = await db.partners.find_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Get partner config for targets
    config = await db.partner_configs.find_one({"partner_id": partner_id}, {"_id": 0})
    targets = config.get("kpi_config", {}) if config else {}
    
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    if period == "week":
        period_start = now - timedelta(days=7)
    elif period == "quarter":
        period_start = now - timedelta(days=90)
    else:
        period_start = now - timedelta(days=30)
    
    # Get leads for this partner
    leads_count = await db.leads.count_documents({
        "tenant_id": user["tenant_id"],
        "partner_id": partner_id,
        "created_at": {"$gte": period_start.isoformat()}
    })
    
    qualified_count = await db.leads.count_documents({
        "tenant_id": user["tenant_id"],
        "partner_id": partner_id,
        "status": "qualified",
        "qualified_at": {"$gte": period_start.isoformat()}
    })
    
    # Get deals for this partner
    deals = await db.deals.find({
        "tenant_id": user["tenant_id"],
        "partner_id": partner_id,
        "status": "open"
    }, {"_id": 0}).to_list(length=1000)
    
    won_deals = await db.deals.find({
        "tenant_id": user["tenant_id"],
        "partner_id": partner_id,
        "status": "won",
        "updated_at": {"$gte": period_start.isoformat()}
    }, {"_id": 0}).to_list(length=100)
    
    lost_deals = await db.deals.count_documents({
        "tenant_id": user["tenant_id"],
        "partner_id": partner_id,
        "status": "lost",
        "updated_at": {"$gte": period_start.isoformat()}
    })
    
    # Calculate metrics
    pipeline_value = sum(d.get("amount", 0) for d in deals)
    won_value = sum(d.get("amount", 0) for d in won_deals)
    avg_deal_size = won_value / max(len(won_deals), 1)
    win_rate = (len(won_deals) / max(len(won_deals) + lost_deals, 1)) * 100
    qualification_rate = (qualified_count / max(leads_count, 1)) * 100
    
    return {
        "partner_id": partner_id,
        "partner_name": partner.get("name"),
        "period": period,
        "metrics": {
            "leads_created": leads_count,
            "leads_qualified": qualified_count,
            "qualification_rate": round(qualification_rate, 1),
            "deals_open": len(deals),
            "deals_won": len(won_deals),
            "deals_lost": lost_deals,
            "win_rate": round(win_rate, 1),
            "pipeline_value": pipeline_value,
            "won_value": won_value,
            "avg_deal_size": round(avg_deal_size, 2)
        },
        "targets": {
            "target_win_rate": targets.get("target_win_rate", 25.0),
            "target_deal_size": targets.get("target_deal_size", 5000.0),
            "target_qualification_rate": targets.get("target_qualification_rate", 30.0)
        },
        "performance": {
            "win_rate_vs_target": round(win_rate - targets.get("target_win_rate", 25.0), 1),
            "deal_size_vs_target": round(avg_deal_size - targets.get("target_deal_size", 5000.0), 2),
            "qualification_vs_target": round(qualification_rate - targets.get("target_qualification_rate", 30.0), 1)
        }
    }


@router.get("/partners/{partner_id}/compliance-check")
async def check_partner_compliance(
    partner_id: str,
    deal_id: Optional[str] = None,
    user = Depends(get_current_user)
):
    """
    Check compliance rules for a partner, optionally for a specific deal.
    """
    db = get_database()
    
    partner = await db.partners.find_one(
        {"id": partner_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Get partner config
    config = await db.partner_configs.find_one({"partner_id": partner_id}, {"_id": 0})
    compliance = config.get("compliance_config", {}) if config else {}
    
    result = {
        "partner_id": partner_id,
        "partner_name": partner.get("name"),
        "compliance_rules": compliance.get("rules", []),
        "required_certifications": compliance.get("required_certifications", []),
        "approval_thresholds": compliance.get("approval_thresholds", {}),
        "checks": [],
        "is_compliant": True
    }
    
    # If deal provided, check against deal
    if deal_id:
        deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
        if deal:
            result["deal_id"] = deal_id
            result["deal_name"] = deal.get("name")
            
            # Check approval thresholds
            thresholds = compliance.get("approval_thresholds", {})
            
            if "contract_value" in thresholds:
                threshold = thresholds["contract_value"]
                amount = deal.get("amount", 0)
                needs_approval = amount > threshold
                result["checks"].append({
                    "rule": "Contract Value Approval",
                    "threshold": threshold,
                    "actual": amount,
                    "needs_approval": needs_approval,
                    "passed": not needs_approval
                })
                if needs_approval:
                    result["is_compliant"] = False
            
            # Check mandatory reviews
            mandatory_reviews = compliance.get("mandatory_reviews", [])
            for review in mandatory_reviews:
                # Check if review exists in deal activities
                review_activity = await db.activities.find_one({
                    "deal_id": deal_id,
                    "type": review
                })
                result["checks"].append({
                    "rule": f"Mandatory Review: {review}",
                    "completed": review_activity is not None,
                    "passed": review_activity is not None
                })
                if not review_activity:
                    result["is_compliant"] = False
    
    return result


@router.get("/config/fields-by-stage")
async def get_required_fields_by_stage(
    partner_id: Optional[str] = None,
    stage: str = Query(..., description="Stage name"),
    user = Depends(get_current_user)
):
    """
    Get required fields for a specific stage, optionally partner-specific.
    """
    db = get_database()
    
    # Default required fields by stage (universal)
    stage_fields = {
        "New / Assigned": [],
        "Working": ["touchpoint_count"],
        "Info Collected": ["economic_units", "usage_volume", "urgency"],
        "Qualified": ["economic_units", "usage_volume", "urgency", "decision_role"],
        "Calculations / Analysis In Progress": ["economic_units", "usage_volume"],
        "Discovery / Demo Scheduled": ["economic_units", "urgency"],
        "Discovery / Demo Completed": ["spiced_situation", "spiced_pain", "spiced_impact"],
        "Decision Pending": ["spiced_situation", "spiced_pain", "spiced_impact", "spiced_economic"],
        "Verbal Commitment": ["amount", "spiced_summary"],
        "Closed Won": ["amount", "spiced_summary"],
        "Handoff to Delivery": ["spiced_summary"]
    }
    
    required_fields = stage_fields.get(stage, [])
    
    # If partner specified, merge with partner-specific requirements
    if partner_id:
        config = await db.partner_configs.find_one({"partner_id": partner_id}, {"_id": 0})
        if config and config.get("field_config"):
            field_config = config["field_config"]
            
            # Map stages to config keys
            stage_config_map = {
                "Qualified": "required_at_qualification",
                "Discovery / Demo Completed": "required_at_discovery",
                "Decision Pending": "required_at_proposal",
                "Closed Won": "required_at_close"
            }
            
            config_key = stage_config_map.get(stage)
            if config_key and field_config.get(config_key):
                # Merge partner-specific fields with defaults
                partner_fields = field_config[config_key]
                required_fields = list(set(required_fields + partner_fields))
    
    return {
        "stage": stage,
        "partner_id": partner_id,
        "required_fields": required_fields,
        "field_details": [
            {"name": f, "label": f.replace("_", " ").title()} 
            for f in required_fields
        ]
    }
