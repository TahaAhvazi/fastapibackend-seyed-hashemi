from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.schemas.product import Product


class CartStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


# Cart Item schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: float
    unit: str
    price: float

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('تعداد باید بیشتر از صفر باشد')
        return v

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('قیمت باید بیشتر از صفر باشد')
        return v


class CartItemCreate(CartItemBase):
    pass


class CartItem(CartItemBase):
    id: int
    cart_id: int
    total_price: float
    product: Optional[Product] = None

    class Config:
        from_attributes = True


# Cart schemas
class CartBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    customer_email: Optional[str] = Field(None, max_length=100)
    customer_address: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('customer_phone')
    @classmethod
    def validate_phone(cls, v):
        # Remove any non-digit characters for validation
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) < 10:
            raise ValueError('شماره تلفن باید حداقل 10 رقم باشد')
        return v

    @field_validator('customer_email')
    @classmethod
    def validate_email(cls, v):
        if v is not None and v.strip():
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('فرمت ایمیل صحیح نیست')
        return v


class CartCreate(CartBase):
    items: List[CartItemCreate] = Field(..., min_items=1)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_name": "احمد محمدی",
                "customer_phone": "09123456789",
                "customer_email": "ahmad@example.com",
                "customer_address": "تهران، خیابان ولیعصر، پلاک 123",
                "notes": "لطفاً در بسته‌بندی دقت کنید",
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 5,
                        "unit": "متر",
                        "price": 350000
                    },
                    {
                        "product_id": 2,
                        "quantity": 3,
                        "unit": "یارد",
                        "price": 280000
                    }
                ]
            }
        }


class CartUpdate(BaseModel):
    status: CartStatus


class Cart(CartBase):
    id: int
    total_amount: float
    status: CartStatus
    items: List[CartItem] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "customer_name": "احمد محمدی",
                "customer_phone": "09123456789",
                "customer_email": "ahmad@example.com",
                "customer_address": "تهران، خیابان ولیعصر، پلاک 123",
                "notes": "لطفاً در بسته‌بندی دقت کنید",
                "total_amount": 2590000,
                "status": "pending",
                "items": [
                    {
                        "id": 1,
                        "cart_id": 1,
                        "product_id": 1,
                        "quantity": 5,
                        "unit": "متر",
                        "price": 350000,
                        "total_price": 1750000,
                        "product": {
                            "id": 1,
                            "code": "P001",
                            "name": "پارچه کتان",
                            "description": "پارچه کتان با کیفیت عالی",
                            "image_url": "/uploads/cotton.jpg",
                            "year_production": 1401,
                            "category": "کتان",
                            "unit": "متر",
                            "pieces_per_roll": 50,
                            "is_available": True,
                            "colors": "سفید، آبی، قرمز",
                            "part_number": "CTN-001",
                            "reorder_location": "تهران، بازار",
                            "purchase_price": 250000,
                            "sale_price": 350000,
                            "created_at": "2023-01-15T10:30:00",
                            "updated_at": "2023-01-15T10:30:00"
                        }
                    }
                ],
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }


class CartResponse(BaseModel):
    id: int
    message: str
    total_amount: float

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "message": "سفارش شما با موفقیت ثبت شد. کد پیگیری: #1",
                "total_amount": 2590000
            }
        }
