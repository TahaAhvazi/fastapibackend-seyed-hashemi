from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.schemas.user import User


class CheckStatus(str, Enum):
    IN_PROGRESS = "in_progress"  # در جریان وصول
    SPENT = "spent"  # خرج شده
    RETURNED = "returned"  # عودت شده
    CLEARED = "cleared"  # پاس شده


class CheckBase(BaseModel):
    check_number: Optional[str] = None
    customer_id: Optional[int] = None
    amount: Optional[float] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[CheckStatus] = None
    related_invoice_id: Optional[int] = None
    attachments: Optional[List[str]] = None


class CheckCreate(CheckBase):
    check_number: str
    customer_id: int
    amount: float
    issue_date: str
    due_date: str
    status: CheckStatus = CheckStatus.IN_PROGRESS

    class Config:
        json_schema_extra = {
            "example": {
                "check_number": "12345678",
                "customer_id": 1,
                "amount": 2800000,
                "issue_date": "1401-06-10",
                "due_date": "1401-09-10",
                "status": "in_progress",
                "related_invoice_id": 2,
                "attachments": ["uploads/checks/check_12345678.jpg"]
            }
        }


class CheckUpdate(CheckBase):
    pass

    class Config:
        json_schema_extra = {
            "example": {
                "status": "cleared",
                "attachments": ["uploads/checks/check_12345678.jpg", "uploads/checks/check_12345678_cleared.jpg"]
            }
        }


class Check(CheckBase):
    id: int
    created_by: int
    customer: Optional[Dict[str, Any]] = None
    related_invoice: Optional[Dict[str, Any]] = None
    created_by_user: Optional[User] = None  # Complete user information
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "check_number": "12345678",
                "customer_id": 1,
                "amount": 2800000,
                "issue_date": "1401-06-10",
                "due_date": "1401-09-10",
                "status": "in_progress",
                "related_invoice_id": 2,
                "attachments": ["uploads/checks/check_12345678.jpg"],
                "created_by": 1,
                "created_by_user": {
                    "id": 1,
                    "email": "admin@example.com",
                    "first_name": "محمد",  # Mohammad
                    "last_name": "احمدی",  # Ahmadi
                    "role": "admin",
                    "is_active": True
                },
                "created_at": "2023-01-15T10:30:00",
                "updated_at": "2023-01-15T10:30:00"
            }
        }


class CheckFilter(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[CheckStatus] = None
    related_invoice_id: Optional[int] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_due_date: Optional[str] = None
    end_due_date: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "in_progress",
                "start_due_date": "1401-06-01",
                "end_due_date": "1401-09-30"
            }
        }