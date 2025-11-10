from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


# Shared properties
class ProductBase(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None  # متر / یارد / طاقه
    quantity_available: Optional[float] = None
    colors: Optional[str] = None


# Properties to receive via API on creation
# Note: This schema is not used directly in the endpoint anymore
# The endpoint uses Form data for multipart/form-data uploads
class ProductCreate(ProductBase):
    code: str = Field(..., min_length=1, description="کد محصول")
    name: str = Field(..., min_length=1, description="نام محصول")
    category: str = Field(..., min_length=1, description="دسته‌بندی محصول (مثال: ساتن، کتان، ابریشم)")
    unit: str = Field(..., min_length=1, description="واحد اندازه‌گیری (مثال: متر، یارد، طاقه)")
    quantity_available: float = Field(default=0, ge=0, description="موجودی موجود")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "P006",
                "name": "پارچه ساتن ابریشمی",  # Silk Satin Fabric
                "description": "پارچه ساتن ابریشمی با کیفیت عالی برای لباس مجلسی",  # High quality silk satin fabric for formal dresses
                "category": "ساتن",  # Satin
                "unit": "متر",  # Meter
                "quantity_available": 300,
                "colors": "سفید، مشکی، آبی، قرمز"  # White, Black, Blue, Red
            }
        }


# Properties to receive via API on update
class ProductUpdate(ProductBase):
    pass

    class Config:
        json_schema_extra = {
            "example": {
                "name": "پارچه ساتن ابریشمی درجه یک",  # Premium Silk Satin Fabric
                "quantity_available": 250,
                "colors": "سفید، مشکی"
            }
        }


# Properties to return via API
class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    images: Optional[List[str]] = Field(default=None, description="لیست URL های عکس‌های محصول")

    @model_validator(mode='before')
    @classmethod
    def extract_images(cls, data):
        """Extract images from relationship if present"""
        if isinstance(data, dict):
            # If images is already a list of strings (URLs), keep it as is
            if 'images' in data and isinstance(data['images'], list):
                # Check if first item is a string (URL) - if so, it's already processed
                if data['images'] and isinstance(data['images'][0], str):
                    return data
            
            # If images relationship is loaded, extract image URLs
            if 'images' in data and hasattr(data['images'], '__iter__'):
                # Check if it's a list of ProductImage objects
                images_list = []
                for img in data['images']:
                    if hasattr(img, 'image_url'):
                        images_list.append(img.image_url)
                    elif isinstance(img, dict) and 'image_url' in img:
                        images_list.append(img['image_url'])
                data['images'] = images_list if images_list else None
        else:
            # If data is a model instance, check if images is already loaded
            # Use __dict__ to avoid triggering lazy loading
            if hasattr(data, '__dict__'):
                data_dict = {}
                for key, value in data.__dict__.items():
                    if not key.startswith('_'):
                        data_dict[key] = value
                
                # Check if images relationship is already loaded in __dict__
                if 'images' in data_dict:
                    images_list = [img.image_url for img in data_dict['images']] if data_dict['images'] else []
                    data_dict['images'] = images_list if images_list else None
                else:
                    # Images not loaded, set to None to avoid lazy loading
                    data_dict['images'] = None
                
                return data_dict
        return data

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 6,
                "code": "P006",
                "name": "پارچه ساتن ابریشمی",  # Silk Satin Fabric
                "description": "پارچه ساتن ابریشمی با کیفیت عالی برای لباس مجلسی",  # High quality silk satin fabric for formal dresses
                "category": "ساتن",  # Satin
                "unit": "متر",  # Meter
                "quantity_available": 300,
                "colors": "سفید، مشکی، آبی، قرمز",  # White, Black, Blue, Red
                "images": ["/uploads/products/P006_20231110_123456.jpg", "/uploads/products/P006_20231110_123457.jpg"],
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }


# Properties for search and filter
class ProductFilter(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    in_stock: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "category": "ساتن",  # Satin
                "in_stock": True
            }
        }