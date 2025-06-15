from sqlalchemy import Column, UUID, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base
import uuid


class UserCategory(Base):
    """Model for user-defined expense categories.

    Allows users to create custom categories for personalized expense tracking and budgeting.

    Columns:
        user_category_id (UUID): Unique identifier for the user category.
        user_id (UUID): The user who owns this category.
        name (str): Name of the custom category (e.g., 'Coffee', 'Subscriptions').
        icon (str): Icon representation for UI display.
        color (str): Color code for UI display.
        created_at (datetime): Timestamp when the category was created.
        updated_at (datetime): Timestamp when the category was last updated.
    Relationships:
        budgets: Budgets associated with this user category.
    """
    __tablename__ = "user_categories"

    user_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    color = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())

    # Relationships
    budgets = relationship("Budget", back_populates="user_category", primaryjoin="and_(UserCategory.user_category_id==Budget.user_category_id)")

    def __str__(self):
        return f"UserCategory(user_category_id={self.user_category_id}, user_id={self.user_id}, name={self.name}, icon={self.icon}, color={self.color}, created_at={self.created_at}, updated_at={self.updated_at})"
