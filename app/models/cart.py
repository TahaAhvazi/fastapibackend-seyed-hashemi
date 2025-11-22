from sqlalchemy import Column, Integer, String, Float, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base


class Cart(Base):
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    customer_address = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum("pending", "reviewed", "approved", "rejected", name="cart_status"), default="pending", nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("cart.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # متر / یارد / طاقه
    price = Column(Float, nullable=False)  # Price per unit
    # Series and Color fields
    selected_series = Column(JSON, nullable=True)  # لیست شماره‌های سری انتخاب شده (فقط برای محصولات سری)
    selected_color = Column(String, nullable=True)  # رنگ انتخاب شده (فقط برای محصولات غیرسری)
    
    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
    
    @property
    def total_price(self):
        return self.quantity * self.price
