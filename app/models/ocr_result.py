import uuid
from sqlalchemy import Column, DateTime, Enum, Numeric, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.receipt import ReceiptStatus


class OCRResult(Base):
    """Model for OCR results from receipt images.

    Stores data extracted from receipt images by OCR, including merchant name,
    total amount, transaction date, and related user and feedback information.

    Columns:
        ocr_id (UUID): Unique identifier for the OCR result.
        user_id (UUID): The user who uploaded the receipt.
        image_path (str): S3 or storage path to the receipt image.
        merchant_name (str): Name of the merchant detected by OCR.
        total_amount (Decimal): Total amount detected on the receipt.
        transaction_date (datetime): Date and time of the transaction.
        payment_method (str): Payment method detected (e.g., cash, card).
        receipt_status (ReceiptStatus): Processing status of the receipt (pending, processed, etc).
        raw_ocr_data (JSONB): Raw OCR response data (for debugging or retraining).
        created_at (datetime): Timestamp when the OCR result was created.
        updated_at (datetime): Timestamp when the OCR result was last updated.
    Relationships:
        user: The user who uploaded the receipt.
        confidence_scores: OCR confidence scores for each field.
        training_feedback: User feedback for improving OCR.
    """
    __tablename__ = "ocr_results"

    ocr_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    image_path = Column(String, nullable=False)  # S3 path to receipt image
    merchant_name = Column(String, nullable=True)
    total_amount = Column(Numeric(precision=10, scale=2), nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("user_categories.user_category_id"), nullable=True)
    receipt_status = Column(Enum(ReceiptStatus), default=ReceiptStatus.PENDING)
    raw_ocr_data = Column(JSONB, nullable=True)  # Original OCR response
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="ocr_results")
    ocr_result_items = relationship("OCRResultItem", back_populates="ocr_result")
    category = relationship("Category", backref="ocr_results")
    user_category = relationship("UserCategory", backref="ocr_results")
