import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class ExpenseItem(Base):
    __tablename__ = "expense_items"

    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)  # Same as total_price
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("user_categories.user_category_id"), nullable=True)
    purchase_date = Column(Date, nullable=False, default=datetime.utcnow().date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ocr_result = relationship("OCRResult", back_populates="expense_items")
    user = relationship("User", back_populates="expense_items")
    category = relationship("Category", foreign_keys=[category_id])
    user_category = relationship("UserCategory", foreign_keys=[user_category_id])
