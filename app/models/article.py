from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base


class Article(Base):
    """مدل برای مدیریت مقالات سایت"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)  # عنوان مقاله
    slug = Column(String, unique=True, index=True, nullable=False)  # slug برای URL
    content = Column(Text, nullable=False)  # محتوای مقاله
    cover_image_url = Column(String, nullable=True)  # عکس کاور در uploads
    excerpt = Column(Text, nullable=True)  # خلاصه مقاله
    is_published = Column(Boolean, default=False, nullable=False)  # منتشر شده/نشده
    views_count = Column(Integer, default=0, nullable=False)  # تعداد بازدید
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

