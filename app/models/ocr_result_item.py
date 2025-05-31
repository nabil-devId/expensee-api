import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Numeric, ForeignKey, String, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class OCRResultItem(Base):
    """Model for individual line items extracted from OCR results of receipts.

    Represents each product or service line detected by OCR from a receipt image, including name, quantity, pricing, and associations to the parent OCR result.

    Columns:
        ocr_item_id (UUID): Unique identifier for the OCR result item.
        ocr_id (UUID): Reference to the parent OCR result (foreign key).
        name (str): Name or description of the item detected by OCR.
        quantity (Decimal): Quantity of the item (default is 1).
        unit_price (Decimal): Price per unit for the item.
        total_price (Decimal): Total price for this item (unit_price * quantity).
        purchase_date (date): Date of purchase as detected by OCR.
        created_at (datetime): Timestamp when the item record was created.
        updated_at (datetime): Timestamp when the item record was last updated.
    Relationships:
        ocr_results: The parent OCRResult this item belongs to.
    """
    __tablename__ = "ocr_result_items"

    ocr_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), default=1)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=False)
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    purchase_date = Column(Date, nullable=False, default=datetime.now(timezone.utc).date())
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationships
    ocr_result = relationship("OCRResult", back_populates="ocr_result_items")
    ocr_result = relationship("OCRResult", back_populates="ocr_result_items")