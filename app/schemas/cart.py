from enum import Enum
from typing import Optional, List, Dict, Any
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
    product_id: int = Field(..., description="شناسه محصول")
    quantity: float = Field(..., gt=0, description="تعداد/متراژ محصول")
    unit: str = Field(..., description="واحد اندازه‌گیری (متر، یارد، طاقه)")
    price: float = Field(..., gt=0, description="قیمت هر واحد")
    selected_series: Optional[List[int]] = Field(
        None, 
        description="لیست شماره‌های سری انتخاب شده - الزامی برای محصولات سری (مثال: [1, 2, 3])"
    )
    selected_color: Optional[str] = Field(
        None, 
        description="رنگ انتخاب شده - الزامی برای محصولات غیرسری (مثال: 'قرمز')"
    )

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
    items: List[CartItemCreate] = Field(
        ..., 
        min_items=1,
        description="لیست آیتم‌های سفارش. توجه: برای محصولات سری باید selected_series و برای محصولات غیرسری باید selected_color ارسال شود."
    )

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
                        "quantity": 50,
                        "unit": "متر",
                        "price": 350000,
                        "selected_series": [1, 2, 3, 4, 5],
                        "selected_color": None
                    },
                    {
                        "product_id": 2,
                        "quantity": 15,
                        "unit": "متر",
                        "price": 280000,
                        "selected_series": None,
                        "selected_color": "قرمز"
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


# Order details schema
class SeriesDetail(BaseModel):
    """جزئیات سری برای محصولات سری"""
    series_number: int
    quantity: float  # متراژ این سری
    unit: str


class ColorDetail(BaseModel):
    """جزئیات رنگ برای محصولات غیرسری"""
    color: str
    quantity: float  # متراژ این رنگ
    unit: str


class OrderItemDetail(BaseModel):
    """جزئیات هر آیتم سفارش"""
    product_id: int
    product_name: str
    product_code: str
    is_series: bool
    total_quantity: float  # کل متراژ
    unit: str
    price_per_unit: float
    total_price: float
    # برای محصولات سری
    series_details: Optional[List[SeriesDetail]] = None
    # برای محصولات غیرسری
    color_detail: Optional[ColorDetail] = None


class CartResponse(BaseModel):
    id: int
    message: str
    total_amount: float
    order_details: List[OrderItemDetail] = Field(default=[], description="جزئیات سفارش")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "message": "سفارش شما با موفقیت ثبت شد. کد پیگیری: #1",
                "total_amount": 2590000,
                "order_details": [
                    {
                        "product_id": 1,
                        "product_name": "پارچه کتان",
                        "product_code": "P001",
                        "is_series": True,
                        "total_quantity": 50,
                        "unit": "متر",
                        "price_per_unit": 350000,
                        "total_price": 17500000,
                        "series_details": [
                            {"series_number": 1, "quantity": 10, "unit": "متر"},
                            {"series_number": 2, "quantity": 10, "unit": "متر"},
                            {"series_number": 3, "quantity": 10, "unit": "متر"},
                            {"series_number": 4, "quantity": 10, "unit": "متر"},
                            {"series_number": 5, "quantity": 10, "unit": "متر"}
                        ],
                        "color_detail": None
                    },
                    {
                        "product_id": 2,
                        "product_name": "پارچه ساتن",
                        "product_code": "P002",
                        "is_series": False,
                        "total_quantity": 15,
                        "unit": "متر",
                        "price_per_unit": 280000,
                        "total_price": 4200000,
                        "series_details": None,
                        "color_detail": {
                            "color": "قرمز",
                            "quantity": 15,
                            "unit": "متر"
                        }
                    }
                ]
            }
        }
