"""
Marketing Lists API Routes

Handles marketing list operations:
- Create, read, update, delete lists
- Static lists (manual contact management)
- Smart lists (dynamic filtering)
"""

from fastapi import APIRouter, HTTPException, Query, Request
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid
import json

from app.db.mongodb import get_database

router = APIRouter(prefix="/lists", tags=["Marketing Lists"])


# ==================== SCHEMAS ====================

class ListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    type: str = "static"  # "static" or "smart"
    filters: Optional[Dict[str, Any]] = None


class ListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class AddContactsRequest(BaseModel):
    contact_ids: List[str]


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


# ==================== LIST ENDPOINTS ====================

@router.get("")
async def get_lists(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    search: Optional[str] = None
):
    """Get all marketing lists for the tenant"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Build query
    query = {"tenant_id": tenant_id}

    if type:
        query["type"] = type

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    # Get total count
    total = await db.lists.count_documents(query)

    # Get paginated lists
    skip = (page - 1) * page_size
    lists_cursor = db.lists.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
    lists = await lists_cursor.to_list(length=page_size)

    # Get contact counts for each list
    for lst in lists:
        if lst.get("type") == "static":
            # Count members in list_members collection
            count = await db.list_members.count_documents({"list_id": lst["id"]})
            lst["contact_count"] = count
        else:
            # For smart lists, count contacts matching filters
            # This is a simplified version - in production would apply actual filters
            lst["contact_count"] = 0

    return {
        "lists": lists,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("", status_code=201)
async def create_list(
    request: Request,
    data: ListCreate
):
    """Create a new marketing list"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()
    now = datetime.now(timezone.utc).isoformat()

    list_id = str(uuid.uuid4())

    new_list = {
        "id": list_id,
        "tenant_id": tenant_id,
        "name": data.name,
        "description": data.description,
        "type": data.type,
        "filters": data.filters if data.type == "smart" else None,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }

    await db.lists.insert_one(new_list)

    # Remove _id from response
    new_list.pop("_id", None)
    new_list["contact_count"] = 0

    return new_list


@router.get("/{list_id}")
async def get_list(
    request: Request,
    list_id: str
):
    """Get a single list by ID"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    lst = await db.lists.find_one(
        {"id": list_id, "tenant_id": tenant_id},
        {"_id": 0}
    )

    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    # Get contact count
    if lst.get("type") == "static":
        count = await db.list_members.count_documents({"list_id": list_id})
        lst["contact_count"] = count
    else:
        lst["contact_count"] = 0

    return lst


@router.put("/{list_id}")
async def update_list(
    request: Request,
    list_id: str,
    data: ListUpdate
):
    """Update a marketing list"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Check list exists
    lst = await db.lists.find_one({"id": list_id, "tenant_id": tenant_id})
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    # Build update
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.filters is not None and lst.get("type") == "smart":
        update_data["filters"] = data.filters

    await db.lists.update_one(
        {"id": list_id},
        {"$set": update_data}
    )

    # Return updated list
    updated = await db.lists.find_one({"id": list_id}, {"_id": 0})
    return updated


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    request: Request,
    list_id: str
):
    """Delete a marketing list"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Check list exists
    result = await db.lists.delete_one({"id": list_id, "tenant_id": tenant_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="List not found")

    # Also delete list members for static lists
    await db.list_members.delete_many({"list_id": list_id})

    return None


# ==================== LIST MEMBERS ENDPOINTS ====================

@router.get("/{list_id}/contacts")
async def get_list_contacts(
    request: Request,
    list_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get contacts in a list"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Verify list exists and belongs to tenant
    lst = await db.lists.find_one({"id": list_id, "tenant_id": tenant_id})
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    if lst.get("type") == "static":
        # Get contacts via list_members
        skip = (page - 1) * page_size
        members_cursor = db.list_members.find({"list_id": list_id}, {"_id": 0}).skip(skip).limit(page_size)
        members = await members_cursor.to_list(length=page_size)

        contact_ids = [m["contact_id"] for m in members]

        # Get contact details
        contacts = []
        if contact_ids:
            contacts_cursor = db.contacts.find({"id": {"$in": contact_ids}}, {"_id": 0})
            contacts = await contacts_cursor.to_list(length=page_size)

        total = await db.list_members.count_documents({"list_id": list_id})

        return {
            "contacts": contacts,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    else:
        # Smart list - apply filters to contacts
        # Simplified version - in production would apply actual filter logic
        return {
            "contacts": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }


@router.post("/{list_id}/contacts", status_code=201)
async def add_contacts_to_list(
    request: Request,
    list_id: str,
    data: AddContactsRequest
):
    """Add contacts to a static list"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Verify list exists and is static
    lst = await db.lists.find_one({"id": list_id, "tenant_id": tenant_id})
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    if lst.get("type") != "static":
        raise HTTPException(status_code=400, detail="Cannot manually add contacts to a smart list")

    now = datetime.now(timezone.utc).isoformat()
    added = 0

    for contact_id in data.contact_ids:
        # Check if already in list
        existing = await db.list_members.find_one({"list_id": list_id, "contact_id": contact_id})
        if not existing:
            await db.list_members.insert_one({
                "id": str(uuid.uuid4()),
                "list_id": list_id,
                "contact_id": contact_id,
                "added_at": now
            })
            added += 1

    return {"added": added, "total_requested": len(data.contact_ids)}


@router.delete("/{list_id}/contacts/{contact_id}", status_code=204)
async def remove_contact_from_list(
    request: Request,
    list_id: str,
    contact_id: str
):
    """Remove a contact from a static list"""
    user = await get_current_user_from_token(request)
    tenant_id = user.get("tenant_id")

    db = get_database()

    # Verify list exists
    lst = await db.lists.find_one({"id": list_id, "tenant_id": tenant_id})
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    if lst.get("type") != "static":
        raise HTTPException(status_code=400, detail="Cannot manually remove contacts from a smart list")

    result = await db.list_members.delete_one({"list_id": list_id, "contact_id": contact_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not in list")

    return None
