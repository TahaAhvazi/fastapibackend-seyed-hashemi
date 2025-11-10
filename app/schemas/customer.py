from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

# Generic type for pagination
T = TypeVar('T')


# Bank Account schemas
class BankAccountBase(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None


class BankAccountCreate(BankAccountBase):
    bank_name: str
    account_number: str

    class Config:
        json_schema_extra = {
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
        from_attributes = True


# Customer schemas
class CustomerBase(BaseModel):
    person_code: Optional[str] = None
    person_type: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None


class CustomerCreate(CustomerBase):
    first_name: str
    last_name: str
    current_balance: Optional[float] = 0.0
    balance_notes: Optional[str] = None
    excel_data: Optional[Dict[str, Any]] = None
    bank_accounts: Optional[List[BankAccountCreate]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "person_code": "916",
                "person_type": None,
                "first_name": "غلامرضا",
                "last_name": "افخمی",
                "company_name": None,
                "address": "اردبیل-خیابان سی متری-پارچه دیبا",
                "phone": None,
                "mobile": "9123045426",
                "city": None,
                "province": None,
                "current_balance": 677860000,
                "balance_notes": None,
                "excel_data": {
                    "گروه شخص": "1",
                    "کد شخص": "916",
                    "نوع شخصیت": None,
                    "پیشوند": "آقای",
                    "نام / نام شرکت": "غلامرضا",
                    "نام خانوادگی / مدیر عامل": "افخمی",
                    "تاریخ تولد": None,
                    "معرف": None,
                    "تلفن 1": None,
                    "موبایل": "9123045426",
                    "نام شرکت": None,
                    "نوع مودی": None,
                    "کد شهر": "-1",
                    "آدرس": "اردبیل-خیابان سی متری-پارچه دیبا",
                    "توضیحات": "دفتر کل:239",
                    "ارز": "1",
                    "نرخ ارز": "1.0",
                    "ماهیت اول دوره": "1.0",
                    "مانده": "677860000.0",
                    "اعتبار": "-1",
                    "فاكس": None,
                    "شماره اقتصادی": None,
                    "شماره ثبت": None
                },
                "bank_accounts": [
                    {
                        "bank_name": "بانک ملی",
                        "account_number": "0123456789",
                        "iban": "IR123456789012345678901234"
                    }
                ]
            }
        }


class CustomerUpdate(CustomerBase):
    current_balance: Optional[float] = None
    balance_notes: Optional[str] = None
    excel_data: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "person_code": "916",
                "person_type": None,
                "first_name": "غلامرضا",
                "last_name": "افخمی",
                "company_name": None,
                "address": "اردبیل-خیابان سی متری-پارچه دیبا",
                "phone": None,
                "mobile": "9123045426",
                "city": None,
                "province": None,
                "current_balance": 677860000,
                "balance_notes": "به‌روزرسانی مانده حساب",
                "excel_data": {
                    "گروه شخص": "1",
                    "کد شخص": "916",
                    "نوع شخصیت": None,
                    "پیشوند": "آقای",
                    "نام / نام شرکت": "غلامرضا",
                    "نام خانوادگی / مدیر عامل": "افخمی",
                    "تاریخ تولد": None,
                    "معرف": None,
                    "تلفن 1": None,
                    "موبایل": "9123045426",
                    "نام شرکت": None,
                    "نوع مودی": None,
                    "کد شهر": "-1",
                    "آدرس": "اردبیل-خیابان سی متری-پارچه دیبا",
                    "توضیحات": "دفتر کل:239",
                    "ارز": "1",
                    "نرخ ارز": "1.0",
                    "ماهیت اول دوره": "1.0",
                    "مانده": "677860000.0",
                    "اعتبار": "-1",
                    "فاكس": None,
                    "شماره اقتصادی": None,
                    "شماره ثبت": None
                }
            }
        }


class Customer(CustomerBase):
    id: int
    full_name: str
    current_balance: float
    balance_notes: Optional[str] = None
    is_creditor: bool
    is_debtor: bool
    balance_status: str
    excel_data: Optional[Dict[str, Any]] = None  # تمام ستون‌های Excel
    bank_accounts: List[BankAccount] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
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
        json_schema_extra = {
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
        json_schema_extra = {
            "example": {
                "province": "تهران",  # Tehran
                "min_balance": 1000000,
                "has_checks_in_progress": True
            }
        }


# Balance management schemas
class CustomerBalanceUpdate(BaseModel):
    balance_adjustment: float  # Positive to increase balance, negative to decrease
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "balance_adjustment": 500000,  # Add 500,000 to balance
                "notes": "پیش‌پرداخت از مشتری"
            }
        }


class CustomerBalanceSet(BaseModel):
    new_balance: float
    notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "new_balance": 2000000,  # Set balance to 2,000,000
                "notes": "تصحیح مانده حساب"
            }
        }


class CustomerBalanceInfo(BaseModel):
    current_balance: float
    is_creditor: bool
    is_debtor: bool
    balance_status: str
    balance_notes: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "current_balance": 1500000,
                "is_creditor": True,
                "is_debtor": False,
                "balance_status": "بستانکار",
                "balance_notes": "پیش‌پرداخت برای سفارش آینده"
            }
        }


# Pagination response
class PaginatedCustomerResponse(BaseModel):
    items: List[Customer]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "first_name": "رضا",
                        "last_name": "کریمی",
                        "full_name": "رضا کریمی",
                        "address": "تهران، خیابان شریعتی",
                        "phone": "09121234567",
                        "city": "تهران",
                        "province": "تهران",
                        "current_balance": 1500000,
                        "is_creditor": True,
                        "is_debtor": False,
                        "balance_status": "بستانکار",
                        "bank_accounts": [],
                        "created_at": "2023-01-15T10:30:00",
                        "updated_at": "2023-01-15T10:30:00"
                    }
                ],
                "total": 150,
                "page": 1,
                "per_page": 20,
                "total_pages": 8,
                "has_next": True,
                "has_prev": False
            }
        }