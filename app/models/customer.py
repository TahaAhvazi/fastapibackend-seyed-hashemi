from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base


class Customer(Base):
    id = Column(Integer, primary_key=True, index=True)
    person_code = Column(String, nullable=True, unique=True, index=True)  # کد شخص از Excel
    person_type = Column(String, nullable=True)  # نوع شخصیت: آقای، خانم
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)  # نام شرکت (اگر شرکت باشد)
    address = Column(Text, nullable=True)
    phone = Column(String, nullable=True)  # تلفن ثابت
    mobile = Column(String, nullable=True)  # موبایل
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    # Balance fields
    current_balance = Column(Float, default=0.0, nullable=False)  # Positive = creditor, Negative = debtor
    balance_notes = Column(Text, nullable=True)  # Notes about balance adjustments
    # Authentication
    hashed_password = Column(String, nullable=True)  # Password hash for customer login
    # Excel columns - تمام ستون‌های Excel برای ذخیره جزئیات
    excel_data = Column(JSON, nullable=True)  # JSON object containing all Excel columns with their values
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bank_accounts = relationship("BankAccount", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="customer")
    checks = relationship("Check", back_populates="customer")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_creditor(self):
        """Returns True if customer is a creditor (positive balance)"""
        return self.current_balance > 0
    
    @property
    def is_debtor(self):
        """Returns True if customer is a debtor (negative balance)"""
        return self.current_balance < 0
    
    @property
    def balance_status(self):
        """Returns balance status as string"""
        if self.current_balance > 0:
            return "بستانکار"  # Creditor
        elif self.current_balance < 0:
            return "بدهکار"  # Debtor
        else:
            return "صفر"  # Zero


class BankAccount(Base):
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    iban = Column(String, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="bank_accounts")