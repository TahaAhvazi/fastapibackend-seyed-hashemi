from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# Shared properties
class ProductBase(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    year_production: Optional[int] = None
    category: Optional[str] = None
    unit: Optional[str] = None  # متر / یارد / طاقه
    pieces_per_roll: Optional[int] = None
    quantity_available: Optional[float] = None
    colors: Optional[str] = None
    part_number: Optional[str] = None
    reorder_location: Optional[str] = None  # محل سفارش
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None


# Properties to receive via API on creation
class ProductCreate(ProductBase):
    code: str
    name: str
    category: str
    unit: str
    purchase_price: float
    sale_price: float
    quantity_available: float = 0

    class Config:
        json_schema_extra = {
            "example": {
                "code": "P006",
                "name": "پارچه ساتن ابریشمی",  # Silk Satin Fabric
                "description": "پارچه ساتن ابریشمی با کیفیت عالی برای لباس مجلسی",  # High quality silk satin fabric for formal dresses
                "image_url": "/uploads/satin.jpg",
                "year_production": 1401,
                "category": "ساتن",  # Satin
                "unit": "متر",  # Meter
                "pieces_per_roll": 50,
                "quantity_available": 300,
                "colors": "سفید، مشکی، آبی، قرمز",  # White, Black, Blue, Red
                "part_number": "STN-006",
                "reorder_location": "تهران، بازار",  # Tehran, Bazaar
                "purchase_price": 350000,
                "sale_price": 480000
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
                "sale_price": 520000
            }
        }


# Properties to return via API
class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 6,
                "code": "P006",
                "name": "پارچه ساتن ابریشمی",  # Silk Satin Fabric
                "description": "پارچه ساتن ابریشمی با کیفیت عالی برای لباس مجلسی",  # High quality silk satin fabric for formal dresses
                "image_url": "/uploads/satin.jpg",
                "year_production": 1401,
                "category": "ساتن",  # Satin
                "unit": "متر",  # Meter
                "pieces_per_roll": 50,
                "quantity_available": 300,
                "colors": "سفید، مشکی، آبی، قرمز",  # White, Black, Blue, Red
                "part_number": "STN-006",
                "reorder_location": "تهران، بازار",  # Tehran, Bazaar
                "purchase_price": 350000,
                "sale_price": 480000,
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }


# Properties for search and filter
class ProductFilter(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    in_stock: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "category": "ساتن",  # Satin
                "min_price": 300000,
                "max_price": 500000,
                "in_stock": True
            }
        }