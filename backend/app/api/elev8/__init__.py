"""
Elev8 CRM API Module

This module provides the refactored, modular API structure for Elev8 CRM.
Routes are split by entity for better maintainability:

- leads.py: Lead management and qualification
- partners.py: Partner management
- products.py: Product catalog
- companies.py: Company/Account management
- pipelines.py: Pipeline setup and queries
- ai_assistant.py: AI Assistant (advisory/draft-only)
- kpis.py: KPIs and forecasting
- handoff.py: Handoff to Delivery workflow
- partner_config.py: Partner-specific configurations
- tasks.py: SLA & Task management
- scoring.py: Lead scoring engine (business logic)
- models.py: Shared enums and schemas
- auth.py: Authentication helpers

All routes are prefixed with /api/elev8/
"""

from fastapi import APIRouter

from .leads import router as leads_router
from .partners import router as partners_router
from .products import router as products_router
from .companies import router as companies_router
from .pipelines import router as pipelines_router
from .ai_assistant import router as ai_assistant_router
from .kpis import router as kpis_router
from .handoff import router as handoff_router
from .partner_config import router as partner_config_router
from .tasks import router as tasks_router

# Create main router
router = APIRouter(prefix="/elev8", tags=["Elev8 CRM"])

# Include all sub-routers
router.include_router(leads_router)
router.include_router(partners_router)
router.include_router(products_router)
router.include_router(companies_router)
router.include_router(pipelines_router)
router.include_router(ai_assistant_router)
router.include_router(kpis_router)
router.include_router(handoff_router)
router.include_router(partner_config_router)
router.include_router(tasks_router)

# Export commonly used items
from .models import (
    SalesMotionType,
    LeadTier,
    LeadStatus,
    PartnerType,
    PartnerStatus,
    LeadCreate,
    LeadUpdate,
    PartnerCreate,
    PartnerUpdate,
    ProductCreate,
    ProductUpdate,
    CompanyCreate,
    CompanyUpdate,
)

from .scoring import (
    calculate_lead_score,
    get_tier_probability,
    get_score_breakdown,
)

__all__ = [
    "router",
    "SalesMotionType",
    "LeadTier", 
    "LeadStatus",
    "PartnerType",
    "PartnerStatus",
    "LeadCreate",
    "LeadUpdate",
    "PartnerCreate",
    "PartnerUpdate",
    "ProductCreate",
    "ProductUpdate",
    "CompanyCreate",
    "CompanyUpdate",
    "calculate_lead_score",
    "get_tier_probability",
    "get_score_breakdown",
]
