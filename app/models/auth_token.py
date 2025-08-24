import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, String, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class TokenType(str, PyEnum):
    """Enum for token types.

    Values:
        ACCESS: Access token for API authentication.
        REFRESH: Refresh token for obtaining new access tokens.
    """
    ACCESS = "access"
    REFRESH = "refresh"


class AuthToken(Base):
    """Model for authentication tokens issued to users.

    Stores access and refresh tokens for user authentication, including expiration and device info.

    Columns:
        token_id (UUID): Unique identifier for the token.
        user_id (UUID): The user that owns this token.
        token (str): The actual token string (access or refresh).
        type (TokenType): Type of token (access or refresh).
        expires_at (datetime): Expiration timestamp of the token.
        created_at (datetime): Timestamp when the token was created.
        device_info (str): Information about the device where the token was issued (optional).
    Relationships:
        user: The user who owns the token.
    """
    __tablename__ = "auth_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token = Column(String, nullable=False, index=True)
    type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    device_info = Column(String, nullable=True)

    # Relationship
    user = relationship("User", backref="auth_tokens")
