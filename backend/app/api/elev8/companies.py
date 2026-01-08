"""
Elev8 CRM - Company Routes

Company/Account management endpoints.
Per Elev8 specification section 3.
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.db.mongodb import get_database
from .auth import get_current_user
from .models import CompanyCreate, CompanyUpdate

router = APIRouter(tags=["Companies"])


@router.get("/companies")
async def list_companies(
    user = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    industry: Optional[str] = None
):
    """List companies"""
    
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if industry:
        query["industry"] = industry
    
    total = await db.companies.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.companies.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    companies = await cursor.to_list(length=page_size)
    
    # Add contact and deal counts
    for company in companies:
        company["contact_count"] = await db.contacts.count_documents({"company_id": company["id"]})
        company["deal_count"] = await db.deals.count_documents({"company_id": company["id"]})
    
    return {
        "companies": companies,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/companies", status_code=http_status.HTTP_201_CREATED)
async def create_company(data: CompanyCreate, user = Depends(get_current_user)):
    """Create a new company"""
    
    db = get_database()
    
    now = datetime.now(timezone.utc).isoformat()
    
    company = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.companies.insert_one(company)
    company.pop("_id", None)
    
    return company


@router.get("/companies/{company_id}")
async def get_company(company_id: str, user = Depends(get_current_user)):
    """Get a specific company"""
    
    db = get_database()
    
    company = await db.companies.find_one(
        {"id": company_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Add related contacts and deals
    company["contacts"] = await db.contacts.find(
        {"company_id": company_id},
        {"_id": 0}
    ).to_list(length=100)
    
    company["deals"] = await db.deals.find(
        {"company_id": company_id},
        {"_id": 0}
    ).to_list(length=100)
    
    return company


@router.put("/companies/{company_id}")
async def update_company(company_id: str, data: CompanyUpdate, user = Depends(get_current_user)):
    """Update a company"""
    
    db = get_database()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.companies.update_one(
        {"id": company_id, "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Return updated company
    updated_company = await db.companies.find_one(
        {"id": company_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    return updated_company


@router.delete("/companies/{company_id}")
async def delete_company(company_id: str, user = Depends(get_current_user)):
    """Delete a company"""
    
    db = get_database()
    
    result = await db.companies.delete_one(
        {"id": company_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"message": "Company deleted"}
