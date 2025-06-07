import uuid
from sqlalchemy import Column, DateTime, String, ForeignKey, Text, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class ExpenseHistory(Base):
    """Model for historical expense records.

    Tracks expenses over time, including manual and OCR-derived entries, for reporting and analytics.

    Columns:
        expense_id (UUID): Unique identifier for the expense record.
        user_id (UUID): The user who made the expense.
        ocr_id (UUID): Associated OCR result for this expense (nullable).
        merchant_name (str): Name of the merchant.
        total_amount (Decimal): Total amount spent.
        transaction_date (datetime): Date and time of the transaction.
        payment_method (str): Payment method used (e.g., cash, credit card).
        category_id (UUID): Associated predefined category (nullable).
        user_category_id (UUID): Associated custom user category (nullable).
        notes (str): Additional notes about the expense.
        created_at (datetime): Timestamp when the record was created.
        updated_at (datetime): Timestamp when the record was last updated.
        is_manual_entry (bool): Whether this entry was added manually or via OCR.
    Relationships:
        user: The user who made the expense.
        ocr_result: The OCR result associated with this expense.
        category: The predefined category for this expense.
        user_category: The custom user category for this expense.
    
    Important:
        one of category_id or user_category_id must be set
    """
    __tablename__ = "expense_history"

    expense_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    ocr_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.ocr_id"), nullable=True)
    merchant_name = Column(String, nullable=False)
    total_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    payment_method = Column(String, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("user_categories.user_category_id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())
    is_manual_entry = Column(Boolean, default=False)

    # Relationships
    ocr_result = relationship("OCRResult", backref="expense")
    category = relationship("Category", foreign_keys=[category_id], lazy="joined", backref="category")
    user_category = relationship("UserCategory", foreign_keys=[user_category_id], lazy="joined", backref="user_category")
    expense_items = relationship("ExpenseItem", backref="expense_history")
