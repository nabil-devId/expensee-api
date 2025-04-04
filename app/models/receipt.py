import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (Boolean, Column, DateTime, Enum, Float, ForeignKey,
                        String, Text, Numeric)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class ReceiptStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class OCRResult(Base):
    __tablename__ = "ocr_results"

    ocr_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    image_path = Column(String, nullable=False)  # S3 path to receipt image
    merchant_name = Column(String, nullable=True)
    total_amount = Column(Numeric(precision=10, scale=2), nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    receipt_status = Column(Enum(ReceiptStatus), default=ReceiptStatus.PENDING)
    raw_ocr_data = Column(JSONB, nullable=True)  # Original OCR response
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="ocr_results")
    expense_items = relationship("ExpenseItem", back_populates="ocr_result", cascade="all, delete-orphan")
