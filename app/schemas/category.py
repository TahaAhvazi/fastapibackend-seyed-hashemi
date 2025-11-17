from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visible: Optional[bool] = None
    image_url: Optional[str] = Field(default=None, description="آدرس تصویر دسته‌بندی")


class CategoryCreate(CategoryBase):
    name: str
    visible: Optional[bool] = True


class CategoryUpdate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

