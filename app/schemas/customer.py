from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# Bank Account schemas
class BankAccountBase(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None


class BankAccountCreate(BankAccountBase):
    bank_name: str
    account_number: str

    class Config:
        schema_extra = {
            "example": {
                "bank_name": "بانک ملی",  # Bank Melli
                "account_number": "0123456789",
                "iban": "IR123456789012345678901234"
            }
        }


class BankAccountUpdate(BankAccountBase):
    pass


class BankAccount(BankAccountBase):
    id: int
    customer_id: int

    class Config:
        orm_mode = True


# Customer schemas
class CustomerBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None


class CustomerCreate(CustomerBase):
    first_name: str
    last_name: str
    phone: str
    bank_accounts: Optional[List[BankAccountCreate]] = None

    class Config:
        schema_extra = {
            "example": {
                "first_name": "رضا",  # Reza
                "last_name": "کریمی",  # Karimi
                "address": "تهران، خیابان شریعتی، کوچه بهار، پلاک ۲۰",  # Tehran, Shariati St, Bahar Alley, No. 20
                "phone": "09121234567",
                "city": "تهران",  # Tehran
                "province": "تهران",  # Tehran
                "bank_accounts": [
                    {
                        "bank_name": "بانک ملی",  # Bank Melli
                        "account_number": "0123456789",
                        "iban": "IR123456789012345678901234"
                    }
                ]
            }
        }


class CustomerUpdate(CustomerBase):
    pass

    class Config:
        schema_extra = {
            "example": {
                "address": "تهران، خیابان ولیعصر، کوچه گلستان، پلاک ۱۵",  # Tehran, Valiasr St, Golestan Alley, No. 15
                "phone": "09129876543"
            }
        }


class Customer(CustomerBase):
    id: int
    full_name: str
    bank_accounts: List[BankAccount] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
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
            }
        }


# Customer detail with financial information
class CustomerDetail(Customer):
    total_purchases: float
    total_paid: float
    balance: float
    invoices_count: int
    checks_in_progress_count: int

    class Config:
        schema_extra = {
            "example": {
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
                "updated_at": "2023-01-15T10:30:00",
                "total_purchases": 5000000,
                "total_paid": 3500000,
                "balance": 1500000,
                "invoices_count": 3,
                "checks_in_progress_count": 1
            }
        }


# Customer filter
class CustomerFilter(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    min_balance: Optional[float] = None
    max_balance: Optional[float] = None
    has_checks_in_progress: Optional[bool] = None

    class Config:
        schema_extra = {
            "example": {
                "province": "تهران",  # Tehran
                "min_balance": 1000000,
                "has_checks_in_progress": True
            }
        }