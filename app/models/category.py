import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class Category(Base):
    """Model for expense categories.

    Represents predefined categories for organizing expenses and budgets.

    Columns:
        category_id (UUID): Unique identifier for the category.
        name (str): Name of the category (e.g., 'Food', 'Transport').
        icon (str): Icon representation for UI display.
        color (str): Color code for UI display.
        created_at (datetime): Timestamp when the category was created.
        updated_at (datetime): Timestamp when the category was last updated.
    Relationships:
        budgets: Budgets associated with this category.
    """
    __tablename__ = "categories"

    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    color = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now(timezone.utc))
    updated_at = Column(TIMESTAMP, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # Relationship with budgets
    budgets = relationship("Budget", back_populates="category", primaryjoin="and_(Category.category_id==Budget.category_id)")
