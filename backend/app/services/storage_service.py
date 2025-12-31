"""
Storage Service - Abstraction layer for file storage

Supports:
- Local file storage (default)
- AWS S3 (configurable)
- Azure Blob Storage (configurable)

Designed with adapter pattern for easy switching between providers.
"""

import os
import uuid
import aiofiles
import aiofiles.os
from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Tuple
from datetime import datetime, timezone
from enum import Enum
import mimetypes
import hashlib


class StorageProvider(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"


class StorageAdapter(ABC):
    """Abstract base class for storage adapters"""
    
    @abstractmethod
    async def upload(self, file_content: bytes, filename: str, content_type: str, folder: str = "") -> dict:
        """Upload a file and return metadata"""
        pass
    
    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """Download file content"""
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def get_url(self, file_path: str, expiry_seconds: int = 3600) -> str:
        """Get a URL for accessing the file"""
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage adapter"""
    
    def __init__(self, base_path: str = "/app/backend/uploads"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _get_full_path(self, file_path: str) -> str:
        return os.path.join(self.base_path, file_path)
    
    async def upload(self, file_content: bytes, filename: str, content_type: str, folder: str = "") -> dict:
        # Generate unique filename
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        
        # Create folder if needed
        if folder:
            folder_path = os.path.join(self.base_path, folder)
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder, unique_name)
        else:
            file_path = unique_name
        
        full_path = self._get_full_path(file_path)
        
        # Write file
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(file_content)
        
        # Calculate hash
        file_hash = hashlib.md5(file_content).hexdigest()
        
        return {
            "file_path": file_path,
            "original_name": filename,
            "size_bytes": len(file_content),
            "content_type": content_type,
            "hash": file_hash,
            "provider": StorageProvider.LOCAL.value,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def download(self, file_path: str) -> bytes:
        full_path = self._get_full_path(file_path)
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()
    
    async def delete(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        try:
            await aiofiles.os.remove(full_path)
            return True
        except FileNotFoundError:
            return False
    
    async def get_url(self, file_path: str, expiry_seconds: int = 3600) -> str:
        # For local storage, return a relative URL that the backend serves
        return f"/api/storage/files/{file_path}"
    
    async def exists(self, file_path: str) -> bool:
        full_path = self._get_full_path(file_path)
        return os.path.exists(full_path)


class S3StorageAdapter(StorageAdapter):
    """AWS S3 storage adapter - placeholder for future implementation"""
    
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str):
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        # Will initialize boto3 client here when enabled
    
    async def upload(self, file_content: bytes, filename: str, content_type: str, folder: str = "") -> dict:
        raise NotImplementedError("S3 storage not yet implemented. Set STORAGE_PROVIDER=local or configure S3 credentials.")
    
    async def download(self, file_path: str) -> bytes:
        raise NotImplementedError("S3 storage not yet implemented.")
    
    async def delete(self, file_path: str) -> bool:
        raise NotImplementedError("S3 storage not yet implemented.")
    
    async def get_url(self, file_path: str, expiry_seconds: int = 3600) -> str:
        raise NotImplementedError("S3 storage not yet implemented.")
    
    async def exists(self, file_path: str) -> bool:
        raise NotImplementedError("S3 storage not yet implemented.")


class AzureStorageAdapter(StorageAdapter):
    """Azure Blob Storage adapter - placeholder for future implementation"""
    
    def __init__(self, connection_string: str, container: str):
        self.connection_string = connection_string
        self.container = container
        # Will initialize Azure client here when enabled
    
    async def upload(self, file_content: bytes, filename: str, content_type: str, folder: str = "") -> dict:
        raise NotImplementedError("Azure storage not yet implemented. Set STORAGE_PROVIDER=local or configure Azure credentials.")
    
    async def download(self, file_path: str) -> bytes:
        raise NotImplementedError("Azure storage not yet implemented.")
    
    async def delete(self, file_path: str) -> bool:
        raise NotImplementedError("Azure storage not yet implemented.")
    
    async def get_url(self, file_path: str, expiry_seconds: int = 3600) -> str:
        raise NotImplementedError("Azure storage not yet implemented.")
    
    async def exists(self, file_path: str) -> bool:
        raise NotImplementedError("Azure storage not yet implemented.")


# Storage factory
_storage_instance: Optional[StorageAdapter] = None

def get_storage() -> StorageAdapter:
    """Get the configured storage adapter instance"""
    global _storage_instance
    
    if _storage_instance is None:
        provider = os.environ.get("STORAGE_PROVIDER", "local").lower()
        
        if provider == "s3":
            _storage_instance = S3StorageAdapter(
                bucket=os.environ.get("S3_BUCKET", ""),
                region=os.environ.get("S3_REGION", "us-east-1"),
                access_key=os.environ.get("AWS_ACCESS_KEY_ID", ""),
                secret_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "")
            )
        elif provider == "azure":
            _storage_instance = AzureStorageAdapter(
                connection_string=os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""),
                container=os.environ.get("AZURE_STORAGE_CONTAINER", "uploads")
            )
        else:
            _storage_instance = LocalStorageAdapter()
    
    return _storage_instance


# Utility functions
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
ALLOWED_DOC_TYPES = {"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def validate_file(filename: str, content_type: str, size: int, allowed_types: set = None) -> Tuple[bool, str]:
    """Validate file before upload"""
    if size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
    
    if allowed_types and content_type not in allowed_types:
        return False, f"File type '{content_type}' not allowed"
    
    return True, "OK"


def get_content_type(filename: str) -> str:
    """Get content type from filename"""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"
