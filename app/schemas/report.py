from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime, timedelta


class DateRangeParams(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            }
        }


class IncomeReport(BaseModel):
    total_revenue: float
    total_cost: float
    profit: float
    invoice_count: int
    period: str

    class Config:
        schema_extra = {
            "example": {
                "total_revenue": 5750000,
                "total_cost": 3500000,
                "profit": 2250000,
                "invoice_count": 3,
                "period": "1401-06-01 تا 1401-06-31"  # From 2022-08-23 to 2022-09-22
            }
        }


class ProductSalesReport(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    quantity_sold: float
    total_revenue: float
    profit: float

    class Config:
        schema_extra = {
            "example": {
                "product_id": 1,
                "product_code": "P001",
                "product_name": "پارچه مخمل سلطنتی",  # Royal Velvet Fabric
                "quantity_sold": 15,
                "total_revenue": 5250000,
                "profit": 1500000
            }
        }


class CustomerSalesReport(BaseModel):
    customer_id: int
    customer_name: str
    total_purchases: float
    invoice_count: int
    last_purchase_date: str

    class Config:
        schema_extra = {
            "example": {
                "customer_id": 1,
                "customer_name": "علی محمدی",  # Ali Mohammadi
                "total_purchases": 3500000,
                "invoice_count": 2,
                "last_purchase_date": "1401-06-15"  # 2022-09-06
            }
        }


class DashboardSummary(BaseModel):
    total_revenue_current_month: float
    total_revenue_previous_month: float
    revenue_change_percentage: float
    pending_invoices_count: int
    checks_in_progress_count: int
    low_stock_products_count: int
    top_selling_products: List[Dict[str, Any]]
    recent_invoices: List[Dict[str, Any]]

    class Config:
        schema_extra = {
            "example": {
                "total_revenue_current_month": 5750000,
                "total_revenue_previous_month": 4500000,
                "revenue_change_percentage": 27.78,
                "pending_invoices_count": 2,
                "checks_in_progress_count": 3,
                "low_stock_products_count": 1,
                "top_selling_products": [
                    {
                        "product_id": 1,
                        "product_name": "پارچه مخمل سلطنتی",  # Royal Velvet Fabric
                        "quantity_sold": 15
                    },
                    {
                        "product_id": 2,
                        "product_name": "پارچه کتان طبیعی",  # Natural Linen Fabric
                        "quantity_sold": 10
                    }
                ],
                "recent_invoices": [
                    {
                        "invoice_id": 3,
                        "invoice_number": "INV-1401-003",
                        "customer_name": "محمد رضایی",  # Mohammad Rezaei
                        "total": 1200000,
                        "status": "warehouse_pending"
                    },
                    {
                        "invoice_id": 2,
                        "invoice_number": "INV-1401-002",
                        "customer_name": "فاطمه حسینی",  # Fatemeh Hosseini
                        "total": 2800000,
                        "status": "approved"
                    }
                ]
            }
        }