from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base


class Customer(Base):
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String, nullable=False)
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bank_accounts = relationship("BankAccount", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="customer")
    checks = relationship("Check", back_populates="customer")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class BankAccount(Base):
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    iban = Column(String, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="bank_accounts")