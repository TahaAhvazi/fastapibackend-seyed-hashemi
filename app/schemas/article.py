from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# Shared properties
class ArticleBase(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    is_published: Optional[bool] = False


# Properties to receive via API on creation
class ArticleCreate(ArticleBase):
    title: str = Field(..., min_length=1, description="عنوان مقاله")
    slug: str = Field(..., min_length=1, description="slug برای URL")
    content: str = Field(..., min_length=1, description="محتوای مقاله")
    excerpt: Optional[str] = None
    is_published: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "title": "مقاله نمونه",
                "slug": "article-sample",
                "content": "محتوای کامل مقاله...",
                "excerpt": "خلاصه مقاله",
                "is_published": True
            }
        }


# Properties to receive via API on update
class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    is_published: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "مقاله به‌روز شده",
                "content": "محتوای جدید...",
                "is_published": True
            }
        }


# Properties to return via API
class Article(ArticleBase):
    id: int
    cover_image_url: Optional[str] = None
    views_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "مقاله نمونه",
                "slug": "article-sample",
                "content": "محتوای کامل مقاله...",
                "excerpt": "خلاصه مقاله",
                "cover_image_url": "/uploads/articles/article1.jpg",
                "is_published": True,
                "views_count": 0,
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }

