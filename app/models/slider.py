from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base


class Slider(Base):
    """مدل برای مدیریت عکس‌های اسلایدر"""
    __tablename__ = "sliders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)  # عنوان اختیاری
    image_url = Column(String, nullable=False)  # مسیر عکس در uploads
    link = Column(String, nullable=True)  # لینک اختیاری برای کلیک روی اسلایدر
    description = Column(Text, nullable=True)  # توضیحات اختیاری
    is_active = Column(Boolean, default=True, nullable=False)  # فعال/غیرفعال
    display_order = Column(Integer, default=0, nullable=False)  # ترتیب نمایش
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

