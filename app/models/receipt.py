import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (Boolean, Column, DateTime, Enum, Float, ForeignKey,
                        String, Text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class ProcessingStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    image_url = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    merchant_name = Column(String, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String, default="IDR")
    transaction_date = Column(DateTime, nullable=True)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    raw_text = Column(Text, nullable=True)
    extracted_data = Column(JSONB, nullable=True)
    categories = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="receipts")


# Add the back-reference to the User model
from app.models.user import User
User.receipts = relationship("Receipt", back_populates="user", cascade="all, delete-orphan")