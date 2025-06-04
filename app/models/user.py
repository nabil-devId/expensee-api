import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, String, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class UserStatus(str, PyEnum):
    """Enum for user status.

    Values:
        ACTIVE: User account is active and can log in.
        INACTIVE: User account is inactive (cannot log in).
        SUSPENDED: User account is suspended due to policy or security reasons.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    """Model for application users.

    Stores user credentials, profile information, status, and relationships to other entities.

    Columns:
        user_id (UUID): Unique identifier for the user.
        email (str): User's email address (unique).
        password_hash (str): Hashed password for authentication.
        full_name (str): Full name of the user.
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.
        last_login (datetime): Timestamp of the user's last login.
        status (UserStatus): Current status of the user (active, inactive, suspended).
        is_superuser (bool): Whether the user has admin privileges.
    Relationships:
        custom_categories: User's custom expense categories.
        budgets: Budgets owned by the user.
        expense_history: Expense history associated with the user.
    """
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, name="user_id")
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    is_superuser = Column(Boolean, default=False)  # Keep this for admin functionality
    
    # Relationships
    custom_categories = relationship("UserCategory", backref="user")
    budgets = relationship("Budget", backref="user")
    expense_history = relationship("ExpenseHistory", backref="user")
