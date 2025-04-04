import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey, Text, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class ExpenseHistory(Base):
    __tablename__ = "expense_history"

    expense_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=True)
    merchant_name = Column(String, nullable=False)
    total_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    payment_method = Column(String, nullable=True)
    category = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_manual_entry = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", backref="expenses")
    ocr_result = relationship("OCRResult", backref="expense")
