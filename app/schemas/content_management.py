from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.product import Product

# ==================== Organization Member ====================

class OrganizationMemberBase(BaseModel):
    full_name: Optional[str] = None
    duty: Optional[str] = None

class OrganizationMemberCreate(OrganizationMemberBase):
    full_name: str = Field(..., description="نام کامل عضو")
    duty: str = Field(..., description="وظیفه/سمت")

class OrganizationMemberUpdate(BaseModel):
    full_name: Optional[str] = None
    duty: Optional[str] = None

class OrganizationMember(OrganizationMemberBase):
    id: int
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ==================== Content Video ====================

class ContentVideoBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class ContentVideoCreate(ContentVideoBase):
    title: str = Field(..., description="عنوان ویدیو")
    description: Optional[str] = None

class ContentVideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class ContentVideo(ContentVideoBase):
    id: int
    video_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ==================== Campaign ====================

class CampaignBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class CampaignCreate(CampaignBase):
    title: str = Field(..., description="عنوان کمپین")
    description: Optional[str] = None
    product_ids: List[int] = Field(default=[], description="لیست آیدی محصولات")

class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    product_ids: Optional[List[int]] = None

class Campaign(CampaignBase):
    id: int
    banner_url: str
    products: List[Product] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
