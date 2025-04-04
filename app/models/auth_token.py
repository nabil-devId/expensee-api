import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, String, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class TokenType(str, PyEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token = Column(String, nullable=False, index=True)
    type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    device_info = Column(String, nullable=True)

    # Relationship
    user = relationship("User", backref="auth_tokens")
