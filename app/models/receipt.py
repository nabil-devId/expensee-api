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
    confidence_scores = relationship("OCRConfidence", back_populates="ocr_result", cascade="all, delete-orphan")
    training_feedback = relationship("OCRTrainingFeedback", back_populates="ocr_result", cascade="all, delete-orphan")


class OCRConfidence(Base):
    __tablename__ = "ocr_confidence"

    ocr_confidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=False)
    field_name = Column(String, nullable=False)  # e.g., 'merchant_name', 'total_amount', 'date'
    confidence_score = Column(Numeric(precision=3, scale=2), nullable=False)  # from 0.0 to 1.0
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ocr_result = relationship("OCRResult", back_populates="confidence_scores")


class OCRTrainingFeedback(Base):
    __tablename__ = "ocr_training_feedback"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    field_name = Column(String, nullable=False)
    original_value = Column(String, nullable=False)
    corrected_value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ocr_result = relationship("OCRResult", back_populates="training_feedback")
    user = relationship("User", backref="training_feedback")
