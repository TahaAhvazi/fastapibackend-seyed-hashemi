from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.customer import Customer
from app.schemas.product import Product
from app.schemas.user import User


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    WAREHOUSE_PENDING = "warehouse_pending"
    ACCOUNTANT_PENDING = "accountant_pending"
    APPROVED = "approved"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentType(str, Enum):
    CASH = "cash"  # نقدی
    CHECK = "check"  # چکی
    MIXED = "mixed"  # ترکیبی


# Invoice Item schemas
class InvoiceItemBase(BaseModel):
    product_id: int
    quantity: float
    unit: str
    price: float


class InvoiceItemCreate(InvoiceItemBase):
    pass

    class Config:
        schema_extra = {
            "example": {
                "product_id": 1,
                "quantity": 5,
                "unit": "متر",  # Meter
                "price": 350000
            }
        }


class InvoiceItem(InvoiceItemBase):
    id: int
    invoice_id: int
    total_price: float
    product: Optional[Product] = None  # Complete product information

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "invoice_id": 1,
                "product_id": 1,
                "quantity": 5,
                "unit": "متر",  # Meter
                "price": 350000,
                "total_price": 1750000,
                "product": {
                    "id": 1,
                    "code": "P001",
                    "name": "پارچه کتان",  # Cotton Fabric
                    "description": "پارچه کتان با کیفیت عالی",  # High quality cotton fabric
                    "image_url": "/uploads/cotton.jpg",
                    "year_production": 1401,
                    "category": "کتان",  # Cotton
                    "unit": "متر",  # Meter
                    "pieces_per_roll": 50,
                    "quantity_available": 200,
                    "colors": "سفید، آبی، قرمز",  # White, Blue, Red
                    "part_number": "CTN-001",
                    "reorder_location": "تهران، بازار",  # Tehran, Bazaar
                    "purchase_price": 250000,
                    "sale_price": 350000,
                    "created_at": "2023-01-15T10:30:00",
                    "updated_at": "2023-01-15T10:30:00"
                }
            }
        }


# Invoice schemas
class InvoiceBase(BaseModel):
    customer_id: Optional[int] = None
    payment_type: Optional[PaymentType] = None
    payment_breakdown: Optional[Dict[str, float]] = None
    tracking_info: Optional[Dict[str, Any]] = None


class InvoiceCreate(InvoiceBase):
    customer_id: int
    payment_type: PaymentType
    items: List[InvoiceItemCreate]

    class Config:
        schema_extra = {
            "example": {
                "customer_id": 1,
                "payment_type": "cash",
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 5,
                        "unit": "متر",  # Meter
                        "price": 350000
                    },
                    {
                        "product_id": 2,
                        "quantity": 3,
                        "unit": "متر",  # Meter
                        "price": 280000
                    }
                ]
            }
        }


class InvoiceUpdate(InvoiceBase):
    status: Optional[InvoiceStatus] = None

    class Config:
        schema_extra = {
            "example": {
                "status": "approved",
                "payment_type": "mixed",
                "payment_breakdown": {
                    "cash": 500000,
                    "check": 1250000
                }
            }
        }


class InvoiceTrackingUpdate(BaseModel):
    carrier_name: str
    tracking_code: str
    shipping_date: str
    number_of_packages: int

    class Config:
        schema_extra = {
            "example": {
                "carrier_name": "پست پیشتاز",  # Express Post
                "tracking_code": "EXP12345678",
                "shipping_date": "1401-06-15",
                "number_of_packages": 2
            }
        }


class Invoice(InvoiceBase):
    id: int
    invoice_number: str
    created_by: int
    subtotal: float
    total: float
    status: InvoiceStatus
    items: List[InvoiceItem] = []
    customer: Optional[Customer] = None  # Complete customer information
    created_by_user: Optional[User] = None  # Complete user information
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "invoice_number": "INV-1401-004",
                "customer_id": 1,
                "created_by": 1,
                "subtotal": 1750000,
                "total": 1750000,
                "payment_type": "cash",
                "status": "warehouse_pending",
                "customer": {
                    "id": 1,
                    "first_name": "رضا",  # Reza
                    "last_name": "کریمی",  # Karimi
                    "full_name": "رضا کریمی",  # Reza Karimi
                    "address": "تهران، خیابان شریعتی، کوچه بهار، پلاک ۲۰",  # Tehran, Shariati St, Bahar Alley, No. 20
                    "phone": "09121234567",
                    "city": "تهران",  # Tehran
                    "province": "تهران",  # Tehran
                    "bank_accounts": [
                        {
                            "id": 1,
                            "customer_id": 1,
                            "bank_name": "بانک ملی",  # Bank Melli
                            "account_number": "0123456789",
                            "iban": "IR123456789012345678901234"
                        }
                    ],
                    "created_at": "2023-01-15T10:30:00",
                    "updated_at": "2023-01-15T10:30:00"
                },
                "created_by_user": {
                    "id": 1,
                    "email": "admin@example.com",
                    "first_name": "محمد",  # Mohammad
                    "last_name": "احمدی",  # Ahmadi
                    "role": "admin",
                    "is_active": True
                },
                "items": [
                    {
                        "id": 1,
                        "invoice_id": 1,
                        "product_id": 1,
                        "quantity": 5,
                        "unit": "متر",  # Meter
                        "price": 350000,
                        "total_price": 1750000
                    }
                ],
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }


# Invoice filter
class InvoiceFilter(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[InvoiceStatus] = None
    payment_type: Optional[PaymentType] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_by: Optional[int] = None

    class Config:
        schema_extra = {
            "example": {
                "status": "warehouse_pending",
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            }
        }