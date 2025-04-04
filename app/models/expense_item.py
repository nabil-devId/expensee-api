import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class ExpenseItem(Base):
    __tablename__ = "expense_items"

    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=False)
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    ocr_result = relationship("OCRResult", back_populates="expense_items")
