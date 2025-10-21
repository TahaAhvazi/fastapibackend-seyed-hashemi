from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base
from app.schemas.invoice import InvoiceStatus, PaymentType


class Invoice(Base):
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    payment_type = Column(Enum(PaymentType), nullable=False)
    payment_breakdown = Column(JSON, nullable=True)  # For mixed payment types
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    tracking_info = Column(JSON, nullable=True)  # carrier_name, tracking_code, shipping_date, number_of_packages
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    created_by_user = relationship("User")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    checks = relationship("Check", back_populates="related_invoice")


class InvoiceItem(Base):
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoice.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # متر / یارد / طاقه
    price = Column(Float, nullable=False)  # Price per unit
    
    # Roll-based information for detailed tracking
    rolls_count = Column(Float, nullable=True)  # تعداد طاقه‌ها
    pieces_per_roll = Column(Float, nullable=True)  # تعداد قطعات در هر طاقه
    detailed_rolls = Column(JSON, nullable=True)  # اطلاعات تفصیلی طاقه‌ها
    
    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
    
    @property
    def total_price(self):
        return self.quantity * self.price