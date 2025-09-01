from sqlalchemy import Column, Integer, String, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base


class Product(Base):
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    year_production = Column(Integer, nullable=True)
    category = Column(String, nullable=False)
    unit = Column(String, nullable=False)  # متر / یارد / طاقه
    pieces_per_roll = Column(Integer, nullable=True)
    quantity_available = Column(Float, nullable=False, default=0)
    colors = Column(String, nullable=True)
    part_number = Column(String, nullable=True)
    reorder_location = Column(String, nullable=True)  # محل سفارش
    purchase_price = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())