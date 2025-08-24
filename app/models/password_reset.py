import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base


class PasswordReset(Base):
    """Model for password reset tokens.

    Stores password reset tokens for users, including expiration and usage status.

    Columns:
        token_id (UUID): Unique identifier for the password reset token.
        user_id (UUID): The user who requested the password reset.
        token (str): The password reset token string.
        expires_at (datetime): Expiration timestamp for the token.
        created_at (datetime): Timestamp when the token was created.
        is_used (bool): Whether the token has been used.
    Relationships:
        user: The user who owns the token.
    """
    __tablename__ = "password_reset_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token = Column(String, nullable=False, index=True, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    is_used = Column(Boolean, default=False)  # Track if token has been used

    # Relationships
    user = relationship("User", backref="password_reset_tokens")

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired"""
        return datetime.now(timezone.utc) > self.expires_at

    @classmethod
    def create_token(cls, user_id: uuid.UUID) -> tuple[str, "PasswordReset"]:
        """
        Create a new password reset token
        
        Args:
            user_id: User ID to create token for
            
        Returns:
            Tuple of (token string, PasswordReset object)
        """
        # Generate a secure token
        token = str(uuid.uuid4())
        
        # Create token record with 30 minute expiration
        token_record = cls(
            user_id=user_id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)
        )
        
        return token, token_record
