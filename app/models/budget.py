import uuid
from sqlalchemy import Column, ForeignKey, Numeric, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class Budget(Base):
    """Model for user budgets.

    Represents budget allocations for users, linked to categories and time periods.

    Columns:
        budget_id (UUID): Unique identifier for the budget entry.
        user_id (UUID): The user that owns this budget.
        category_id (UUID): The predefined category this budget is for (nullable).
        user_category_id (UUID): The custom user category this budget is for (nullable).
        month (int): Month for which the budget applies.
        year (int): Year for which the budget applies.
        amount (Decimal): The budgeted amount.
        created_at (datetime): Timestamp when the budget was created.
        updated_at (datetime): Timestamp when the budget was last updated.
    Relationships:
        user: The user who owns this budget.
        category: The predefined category related to this budget.
        user_category: The custom user category related to this budget.
    
    Important:
        one of category_id or user_category_id must be set
    """
    __tablename__ = "budgets"

    budget_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("user_categories.user_category_id"), nullable=True)
    budget_name = Column(String, nullable=False)
    month = Column(Numeric(precision=2), nullable=False)
    year = Column(Numeric(precision=4), nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="budgets", foreign_keys=[category_id], lazy="selectin")
    user_category = relationship("UserCategory", back_populates="budgets", foreign_keys=[user_category_id], lazy="selectin")
