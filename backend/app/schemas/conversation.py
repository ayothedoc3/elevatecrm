from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.conversation import MessageChannel, MessageDirection, MessageStatus


class MessageCreate(BaseModel):
    conversation_id: Optional[str] = None  # If None, creates new conversation
    contact_id: str
    channel: MessageChannel
    to_address: str  # Email or phone
    subject: Optional[str] = None  # For email
    body: str
    body_html: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    tenant_id: str
    conversation_id: str
    channel: MessageChannel
    direction: MessageDirection
    status: MessageStatus
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    subject: Optional[str] = None
    body: str
    body_html: Optional[str] = None
    attachments: List[Dict[str, Any]] = []
    sent_by_user_id: Optional[str] = None
    sent_by_name: Optional[str] = None
    external_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    tenant_id: str
    contact_id: str
    deal_id: Optional[str] = None
    channel: MessageChannel
    subject: Optional[str] = None
    is_open: bool
    is_read: bool
    assigned_to_id: Optional[str] = None
    message_count: int
    unread_count: int
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Populated fields
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int


class InboxStats(BaseModel):
    total_conversations: int
    unread_conversations: int
    email_count: int
    sms_count: int
