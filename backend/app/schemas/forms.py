from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.forms import FieldType


class FormFieldConfig(BaseModel):
    id: str
    type: FieldType
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    mapping: Optional[str] = None  # CRM field to map to (first_name, email, etc.)
    options: Optional[List[str]] = None  # For select fields
    validation: Optional[Dict[str, Any]] = None


class FormCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=100)
    fields: List[Dict[str, Any]] = []
    submit_button_text: str = "Submit"
    success_message: str = "Thank you for your submission!"
    redirect_url: Optional[str] = None
    create_contact: bool = True
    create_deal: bool = False
    assign_pipeline_id: Optional[str] = None
    assign_stage_id: Optional[str] = None
    assign_owner_id: Optional[str] = None
    default_tags: List[str] = []
    is_active: bool = True
    is_public: bool = True
    theme: str = "default"
    custom_css: Optional[str] = None


class FormUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    fields: Optional[List[Dict[str, Any]]] = None
    submit_button_text: Optional[str] = None
    success_message: Optional[str] = None
    redirect_url: Optional[str] = None
    create_contact: Optional[bool] = None
    create_deal: Optional[bool] = None
    assign_pipeline_id: Optional[str] = None
    assign_stage_id: Optional[str] = None
    assign_owner_id: Optional[str] = None
    default_tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    theme: Optional[str] = None
    custom_css: Optional[str] = None


class FormResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    slug: str
    is_active: bool
    is_public: bool
    fields: List[Dict[str, Any]] = []
    submit_button_text: str
    success_message: str
    redirect_url: Optional[str] = None
    create_contact: bool
    create_deal: bool
    assign_pipeline_id: Optional[str] = None
    assign_stage_id: Optional[str] = None
    assign_owner_id: Optional[str] = None
    default_tags: List[str] = []
    theme: str
    custom_css: Optional[str] = None
    submission_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FormListResponse(BaseModel):
    forms: List[FormResponse]
    total: int


class PublicFormResponse(BaseModel):
    """Public form data (no sensitive info)."""
    id: str
    name: str
    description: Optional[str] = None
    fields: List[Dict[str, Any]] = []
    submit_button_text: str
    theme: str
    custom_css: Optional[str] = None


class FormSubmissionCreate(BaseModel):
    data: Dict[str, Any]
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None


class FormSubmissionResponse(BaseModel):
    id: str
    tenant_id: str
    form_id: str
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    data: Dict[str, Any] = {}
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FormSubmissionListResponse(BaseModel):
    submissions: List[FormSubmissionResponse]
    total: int
    page: int
    page_size: int


# Landing Page schemas
class LandingPageSection(BaseModel):
    type: str  # 'hero', 'text', 'image', 'form', 'features', 'testimonial', 'cta'
    content: Dict[str, Any] = {}


class LandingPageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    content: Dict[str, Any] = {"sections": []}
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    theme: str = "default"
    custom_css: Optional[str] = None
    header_code: Optional[str] = None
    footer_code: Optional[str] = None
    form_id: Optional[str] = None
    is_published: bool = False


class LandingPageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[Dict[str, Any]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    theme: Optional[str] = None
    custom_css: Optional[str] = None
    header_code: Optional[str] = None
    footer_code: Optional[str] = None
    form_id: Optional[str] = None
    is_published: Optional[bool] = None


class LandingPageResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    is_published: bool
    content: Dict[str, Any] = {}
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    theme: str
    custom_css: Optional[str] = None
    header_code: Optional[str] = None
    footer_code: Optional[str] = None
    form_id: Optional[str] = None
    view_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LandingPageListResponse(BaseModel):
    pages: List[LandingPageResponse]
    total: int
