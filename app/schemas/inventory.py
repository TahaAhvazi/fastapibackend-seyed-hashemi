from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TransactionReason(str, Enum):
    SALE_RESERVATION = "sale_reservation"  # رزرو برای فروش
    SHIPPING = "shipping"  # ارسال
    RESTOCK = "restock"  # موجودی مجدد
    ADJUSTMENT = "adjustment"  # تعدیل
    RETURN = "return"  # برگشت


class InventoryTransactionBase(BaseModel):
    product_id: int
    change_quantity: float
    reason: TransactionReason
    reference_id: Optional[int] = None
    notes: Optional[str] = None


class InventoryTransactionCreate(InventoryTransactionBase):
    pass

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 1,
                "change_quantity": -5,  # Negative for reduction
                "reason": "sale_reservation",
                "reference_id": 1,  # Invoice ID
                "notes": "رزرو برای فاکتور شماره INV-1401-004"  # Reserved for invoice number INV-1401-004
            }
        }


class InventoryTransaction(InventoryTransactionBase):
    id: int
    created_by: int
    created_at: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "product_id": 1,
                "change_quantity": -5,
                "reason": "sale_reservation",
                "reference_id": 1,
                "notes": "رزرو برای فاکتور شماره INV-1401-004",  # Reserved for invoice number INV-1401-004
                "created_by": 3,  # Warehouse user ID
                "created_at": "2023-01-15T10:30:00"
            }
        }


class ProductQuantity(BaseModel):
    product_id: int
    product_name: str
    is_available: bool
    reserved_quantity: float

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": 1,
                "product_name": "پارچه مخمل سلطنتی",  # Royal Velvet Fabric
                "is_available": True,
                "reserved_quantity": 5.0
            }
        }


class ReserveStock(BaseModel):
    invoice_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": 1
            }
        }