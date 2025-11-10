from sqlalchemy import Column, Integer, String, Float, Text
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
    quantity_available = Column(Float, nullable=False, default=0)
    colors = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    
    @property
    def images_list(self):
        """Return list of image URLs"""
        return [img.image_url for img in self.images] if self.images else []