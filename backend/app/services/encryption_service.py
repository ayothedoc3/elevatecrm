"""
Encryption Service - AES encryption for API keys

Pluggable architecture for future vault/secrets manager integration.
V1 uses application-layer AES-256 encryption.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    AES-256 encryption service for sensitive data like API keys.
    
    The encryption key is derived from an app-level secret.
    Keys are never stored in plaintext and never returned to the frontend.
    """
    
    def __init__(self):
        # Get or generate the master encryption key
        self._master_key = self._get_or_create_master_key()
        self._fernet = self._create_fernet()
    
    def _get_or_create_master_key(self) -> bytes:
        """
        Get the master encryption key from environment.
        This key should be set in production and never changed once set.
        """
        # Try to get from environment
        key_str = os.environ.get("ENCRYPTION_MASTER_KEY")
        
        if key_str:
            # Decode from base64 if provided
            return base64.urlsafe_b64decode(key_str.encode())
        
        # For development, derive from SECRET_KEY
        # In production, ENCRYPTION_MASTER_KEY should be explicitly set
        secret_key = os.environ.get("SECRET_KEY", "elevate-crm-secret-key-change-in-production")
        
        # Use PBKDF2 to derive a proper encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"elevate-crm-encryption-salt-v1",  # Static salt for reproducibility
            iterations=100000,
        )
        return kdf.derive(secret_key.encode())
    
    def _create_fernet(self) -> Fernet:
        """Create a Fernet instance with the derived key"""
        # Fernet requires a 32-byte key encoded in base64
        key = base64.urlsafe_b64encode(self._master_key)
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            plaintext: The string to encrypt (e.g., an API key)
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""
        
        encrypted = self._fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: The encrypted string (base64 encoded)
            
        Returns:
            Original plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            raise ValueError("Failed to decrypt value. Key may have been rotated.")
    
    def mask_key(self, key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for display purposes.
        Shows only the last few characters.
        
        Args:
            key: The API key to mask
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked string like "••••••••abcd"
        """
        if not key or len(key) <= visible_chars:
            return "••••••••"
        
        masked_len = len(key) - visible_chars
        return "•" * min(masked_len, 12) + key[-visible_chars:]
    
    def generate_rotation_key(self) -> str:
        """Generate a new random key for key rotation purposes"""
        return secrets.token_urlsafe(32)
    
    def hash_key_for_audit(self, key: str) -> str:
        """
        Create a hash of a key for audit logging.
        This allows tracking key changes without storing the actual key.
        
        Args:
            key: The API key to hash
            
        Returns:
            SHA-256 hash (first 16 chars) for identification
        """
        if not key:
            return ""
        return hashlib.sha256(key.encode()).hexdigest()[:16]


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the singleton encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
