"""
Marketing Materials API Routes

Handles all marketing materials operations for affiliates:
- Upload/manage marketing assets (images, PDFs, URLs)
- Organize by categories
- Access control (admin upload, affiliates view/download)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import os

from app.db.mongodb import get_database
from app.services.storage_service import get_storage, validate_file, ALLOWED_IMAGE_TYPES, ALLOWED_DOC_TYPES, get_content_type

router = APIRouter(prefix="/materials", tags=["Marketing Materials"])


# ==================== ENUMS ====================

class MaterialType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    URL = "url"
    VIDEO = "video"


class MaterialCategory(str, Enum):
    BANNERS = "banners"
    SOCIAL_POSTS = "social_posts"
    EMAIL_TEMPLATES = "email_templates"
    LOGOS = "logos"
    PRODUCT_IMAGES = "product_images"
    SALES_SHEETS = "sales_sheets"
    VIDEOS = "videos"
    OTHER = "other"


# ==================== SCHEMAS ====================

class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: MaterialCategory = MaterialCategory.OTHER
    material_type: MaterialType = MaterialType.IMAGE
    url: Optional[str] = None  # For URL type materials
    program_id: Optional[str] = None  # Link to specific program
    tags: Optional[List[str]] = []


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[MaterialCategory] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ==================== HELPER FUNCTIONS ====================

async def get_current_user_from_token(request: Request):
    """Extract user from request"""
    from jose import jwt
    import os
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.replace("Bearer ", "")
    try:
        SECRET_KEY = os.environ.get("SECRET_KEY", "elevate-crm-secret-key-change-in-production")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        db = get_database()
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


# ==================== ADMIN ENDPOINTS ====================

@router.post("/upload", status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
    category: str = Form(default="other"),
    program_id: str = Form(default=None),
    tags: str = Form(default=""),  # Comma-separated
    request: Request = None
):
    """Upload a marketing material file (admin only)"""
    user = await get_current_user_from_token(request)
    if user.get("role") not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db = get_database()
    storage = get_storage()
    
    # Read file content
    content = await file.read()
    content_type = file.content_type or get_content_type(file.filename)
    
    # Validate file
    allowed_types = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES
    is_valid, message = validate_file(file.filename, content_type, len(content), allowed_types)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Determine material type
    if content_type in ALLOWED_IMAGE_TYPES:
        material_type = MaterialType.IMAGE.value
    elif content_type == "application/pdf":
        material_type = MaterialType.PDF.value
    else:
        material_type = MaterialType.IMAGE.value
    
    # Upload file
    folder = f"materials/{user['tenant_id']}/{category}"
    upload_result = await storage.upload(content, file.filename, content_type, folder)
    
    # Create material record
    material = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": name,
        "description": description,
        "category": category,
        "material_type": material_type,
        "file_path": upload_result["file_path"],
        "file_name": upload_result["original_name"],
        "file_size": upload_result["size_bytes"],
        "content_type": upload_result["content_type"],
        "storage_provider": upload_result["provider"],
        "url": None,
        "program_id": program_id if program_id else None,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "download_count": 0,
        "is_active": True,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.marketing_materials.insert_one(material)
    
    # Get URL for response
    material["file_url"] = await storage.get_url(upload_result["file_path"])
    
    return {k: v for k, v in material.items() if k != "_id"}


@router.post("/url", status_code=201)
async def create_url_material(
    data: MaterialCreate,
    request: Request
):
    """Create a URL-based material (admin only)"""
    user = await get_current_user_from_token(request)
    if user.get("role") not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if data.material_type != MaterialType.URL or not data.url:
        raise HTTPException(status_code=400, detail="URL is required for URL type materials")
    
    db = get_database()
    
    material = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "name": data.name,
        "description": data.description,
        "category": data.category.value,
        "material_type": MaterialType.URL.value,
        "file_path": None,
        "file_name": None,
        "file_size": 0,
        "content_type": None,
        "storage_provider": None,
        "url": data.url,
        "program_id": data.program_id,
        "tags": data.tags or [],
        "download_count": 0,
        "is_active": True,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.marketing_materials.insert_one(material)
    
    return {k: v for k, v in material.items() if k != "_id"}


@router.get("")
async def list_materials(
    category: Optional[MaterialCategory] = None,
    material_type: Optional[MaterialType] = None,
    program_id: Optional[str] = None,
    search: Optional[str] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """List marketing materials"""
    user = await get_current_user_from_token(request)
    db = get_database()
    storage = get_storage()
    
    query = {"tenant_id": user["tenant_id"], "is_active": is_active}
    
    if category:
        query["category"] = category.value
    if material_type:
        query["material_type"] = material_type.value
    if program_id:
        query["program_id"] = program_id
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.marketing_materials.count_documents(query)
    skip = (page - 1) * page_size
    
    cursor = db.marketing_materials.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    materials = await cursor.to_list(length=page_size)
    
    # Add URLs for files
    for mat in materials:
        if mat.get("file_path"):
            mat["file_url"] = await storage.get_url(mat["file_path"])
        else:
            mat["file_url"] = mat.get("url")
    
    return {
        "materials": materials,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/categories")
async def get_categories(request: Request):
    """Get available categories with counts"""
    user = await get_current_user_from_token(request)
    db = get_database()
    
    pipeline = [
        {"$match": {"tenant_id": user["tenant_id"], "is_active": True}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    results = await db.marketing_materials.aggregate(pipeline).to_list(length=20)
    
    categories = [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in MaterialCategory
    ]
    
    # Add counts
    count_map = {r["_id"]: r["count"] for r in results}
    for cat in categories:
        cat["count"] = count_map.get(cat["value"], 0)
    
    return {"categories": categories}


@router.get("/{material_id}")
async def get_material(
    material_id: str,
    request: Request
):
    """Get material details"""
    user = await get_current_user_from_token(request)
    db = get_database()
    storage = get_storage()
    
    material = await db.marketing_materials.find_one(
        {"id": material_id, "tenant_id": user["tenant_id"]},
        {"_id": 0}
    )
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material.get("file_path"):
        material["file_url"] = await storage.get_url(material["file_path"])
    
    return material


@router.put("/{material_id}")
async def update_material(
    material_id: str,
    data: MaterialUpdate,
    request: Request
):
    """Update material (admin only)"""
    user = await get_current_user_from_token(request)
    if user.get("role") not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db = get_database()
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if "category" in update_data:
        update_data["category"] = update_data["category"].value
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.marketing_materials.update_one(
        {"id": material_id, "tenant_id": user["tenant_id"]},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Material not found")
    
    return {"success": True}


@router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    request: Request
):
    """Delete material (admin only)"""
    user = await get_current_user_from_token(request)
    if user.get("role") not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db = get_database()
    storage = get_storage()
    
    material = await db.marketing_materials.find_one(
        {"id": material_id, "tenant_id": user["tenant_id"]}
    )
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Delete file if exists
    if material.get("file_path"):
        await storage.delete(material["file_path"])
    
    # Soft delete
    await db.marketing_materials.update_one(
        {"id": material_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True}


@router.get("/{material_id}/download")
async def download_material(
    material_id: str,
    request: Request
):
    """Download a material file"""
    user = await get_current_user_from_token(request)
    db = get_database()
    storage = get_storage()
    
    material = await db.marketing_materials.find_one(
        {"id": material_id, "tenant_id": user["tenant_id"], "is_active": True}
    )
    
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["material_type"] == MaterialType.URL.value:
        return {"redirect_url": material["url"]}
    
    if not material.get("file_path"):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Increment download count
    await db.marketing_materials.update_one(
        {"id": material_id},
        {"$inc": {"download_count": 1}}
    )
    
    # Get file content
    content = await storage.download(material["file_path"])
    
    return StreamingResponse(
        iter([content]),
        media_type=material.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename={material.get('file_name', 'download')}"
        }
    )
