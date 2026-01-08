"""
Elev8 CRM - Product Routes

Product management endpoints linked to Partners.
Per Elev8 specification section 3.
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.db.mongodb import get_database
from .auth import get_current_user
from .models import ProductCreate, ProductUpdate

router = APIRouter(tags=["Products"])


@router.get("/products")
async def list_products(
    user = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    partner_id: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """List products"""
    
    db = get_database()
    
    query = {"tenant_id": user["tenant_id"]}
    
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if partner_id:
        query["partner_id"] = partner_id
    if is_active is not None:
        query["is_active"] = is_active
    
    total = await db.products.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.products.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(page_size)
    products = await cursor.to_list(length=page_size)
    
    # Enrich with partner names
    for product in products:
        if product.get("partner_id"):
            partner = await db.partners.find_one({"id": product["partner_id"]}, {"_id": 0, "name": 1})
            product["partner_name"] = partner.get("name") if partner else None
    
    return {
        "products": products,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/products", status_code=http_status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, user = Depends(get_current_user)):
    """Create a new product"""
    
    db = get_database()
    
    # Verify partner exists
    partner = await db.partners.find_one(
        {"id": data.partner_id, "tenant_id": user["tenant_id"]}
    )
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    product = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        **data.dict(),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    
    await db.products.insert_one(product)
    product.pop("_id", None)
    
    return product


@router.get("/products/{product_id}")
async def get_product(product_id: str, user = Depends(get_current_user)):
    """Get a specific product"""
    
    db = get_database()
    
    product = await db.products.find_one(
        {"id": product_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Add partner info
    if product.get("partner_id"):
        partner = await db.partners.find_one({"id": product["partner_id"]}, {"_id": 0, "name": 1})
        product["partner_name"] = partner.get("name") if partner else None
    
    return product


@router.put("/products/{product_id}")
async def update_product(product_id: str, data: ProductUpdate, user = Depends(get_current_user)):
    """Update a product"""
    
    db = get_database()
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.products.update_one(
        {"id": product_id, "tenant_id": user["tenant_id"]},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Return updated product
    updated_product = await db.products.find_one(
        {"id": product_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    return updated_product


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user = Depends(get_current_user)):
    """Delete a product"""
    
    db = get_database()
    
    result = await db.products.delete_one(
        {"id": product_id, "tenant_id": user["tenant_id"]}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted"}
