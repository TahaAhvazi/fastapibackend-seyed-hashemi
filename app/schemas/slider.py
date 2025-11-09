from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# Shared properties
class SliderBase(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True
    display_order: Optional[int] = 0


# Properties to receive via API on creation
class SliderCreate(SliderBase):
    title: Optional[str] = None
    link: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "title": "اسلایدر شماره 1",
                "link": "https://example.com",
                "description": "توضیحات اسلایدر",
                "is_active": True,
                "display_order": 1
            }
        }


# Properties to receive via API on update
class SliderUpdate(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "اسلایدر به‌روز شده",
                "is_active": False,
                "display_order": 2
            }
        }


# Properties to return via API
class Slider(SliderBase):
    id: int
    image_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "اسلایدر شماره 1",
                "image_url": "/uploads/slider/slider1.jpg",
                "link": "https://example.com",
                "description": "توضیحات اسلایدر",
                "is_active": True,
                "display_order": 1,
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }

