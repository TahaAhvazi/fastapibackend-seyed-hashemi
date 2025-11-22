from sqlalchemy import Column, Integer, String, Float, Text, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Product(Base):
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)
    unit = Column(String, nullable=False)  # متر / یارد / طاقه
    colors = Column(String, nullable=True)
    # New fields
    is_available = Column(Boolean, nullable=False, default=True)  # موجود/ناموجود برای ثبت محصول
    shrinkage = Column(String, nullable=True)  # ابرفت
    visible = Column(Boolean, nullable=False, default=True)  # نمایش در سایت
    width = Column(String, nullable=True)  # عرض
    usage = Column(String, nullable=True)  # کاربرد
    season = Column(String, nullable=True)  # فصل
    weave_type = Column(String, nullable=True)  # نوع بافت
    # Series and Color fields
    is_series = Column(Boolean, nullable=False, default=False)  # آیا محصول سری است؟
    # For series products
    series_inventory = Column(JSON, nullable=True)  # لیست موجودی سری (مثلاً [10, 20, 30])
    series_numbers = Column(JSON, nullable=True)  # لیست شماره‌های سری (مثلاً [1, 2, 3, ..., 10])
    # For non-series products (with color variants)
    available_colors = Column(JSON, nullable=True)  # لیست رنگ‌های موجود (مثلاً ["قرمز", "آبی", "سبز"])
    color_inventory = Column(JSON, nullable=True)  # لیست موجودی هر رنگ (مثلاً ["5", "10", "3"])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    
    @property
    def images_list(self):
        """Return list of image URLs"""
        return [img.image_url for img in self.images] if self.images else []