from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ProductImageBase(BaseModel):
    image_url: str


class ProductImageCreate(ProductImageBase):
    pass


class ProductImage(ProductImageBase):
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True

