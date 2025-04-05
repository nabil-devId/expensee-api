import uuid
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class PasswordReset(Base):
    __tablename__ = "password_reset_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token = Column(String, nullable=False, index=True, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(String, default=False)  # Track if token has been used

    # Relationships
    user = relationship("User", backref="password_reset_tokens")

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired"""
        return datetime.utcnow() > self.expires_at

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
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        
        return token, token_record
