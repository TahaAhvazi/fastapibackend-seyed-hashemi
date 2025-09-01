from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base
from app.schemas.inventory import TransactionReason


class InventoryTransaction(Base):
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    change_quantity = Column(Float, nullable=False)  # Positive for additions, negative for reductions
    reason = Column(Enum(TransactionReason), nullable=False)
    reference_id = Column(Integer, nullable=True)  # Invoice ID or other reference
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product")
    created_by_user = relationship("User")