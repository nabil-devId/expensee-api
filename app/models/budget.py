import uuid
from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class Budget(Base):
    __tablename__ = "budgets"

    budget_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=True)
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("user_categories.user_category_id"), nullable=True)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    period = Column(String, nullable=False)  # 'monthly', 'quarterly', 'yearly'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # NULL for recurring budgets
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets", 
                           foreign_keys=[category_id])
    user_category = relationship("UserCategory", back_populates="budgets", 
                                foreign_keys=[user_category_id])
