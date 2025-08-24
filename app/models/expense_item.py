import uuid
from sqlalchemy import Column, DateTime, String, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class ExpenseItem(Base):
    """Model for individual expense items extracted from receipts.

    Represents each line item or product on a receipt, including price, quantity, and associations to users and OCR results.

    Columns:
        item_id (UUID): Unique identifier for the expense item.
        expense_history_id (UUID): Associated expense history for this item.
        user_id (UUID): The user who made the purchase.
        name (str): Name or description of the item.
        quantity (int): Number of units purchased.
        unit_price (Decimal): Price per unit.
        total_price (Decimal): Total price for this item (quantity * unit_price).
        purchase_date (date): Date of purchase.
        created_at (datetime): Timestamp when the item was created.
        updated_at (datetime): Timestamp when the item was last updated.
    Relationships:
        expense_history: The expense history this item belongs to.
        user: The user who purchased the item.
    """
    __tablename__ = "expense_items"

    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_history_id = Column(UUID(as_uuid=True), ForeignKey("expense_history.expense_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=False)  # For what? this will be same as total_price for now, we will remove for later
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    purchase_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())
