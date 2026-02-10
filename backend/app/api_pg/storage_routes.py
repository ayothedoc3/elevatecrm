from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api_pg.deps import get_current_user

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/files/{file_path:path}")
async def serve_storage_file(
    file_path: str,
    user: dict = Depends(get_current_user),
):
    base_path = "/app/backend/uploads"
    full_path = os.path.join(base_path, file_path)

    # Prevent directory traversal
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(full_path)

