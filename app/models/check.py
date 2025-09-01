from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.db.base_class import Base
from app.schemas.check import CheckStatus


class Check(Base):
    id = Column(Integer, primary_key=True, index=True)
    check_number = Column(String, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    amount = Column(Float, nullable=False)
    issue_date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    due_date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    status = Column(Enum(CheckStatus), default=CheckStatus.IN_PROGRESS, nullable=False)
    related_invoice_id = Column(Integer, ForeignKey("invoice.id"), nullable=True)
    attachments = Column(JSON, nullable=True)  # List of file paths
    created_by = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="checks")
    related_invoice = relationship("Invoice", back_populates="checks")
    created_by_user = relationship("User")