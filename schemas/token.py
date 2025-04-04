from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field
from app.models.auth_token import TokenType


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_at: datetime


class TokenPayload(BaseModel):
    sub: UUID  # user_id
    exp: datetime  # expiration time


class TokenCreate(BaseModel):
    user_id: UUID
    token: str
    type: TokenType
    expires_at: datetime
    device_info: Optional[str] = None


class TokenInDB(BaseModel):
    token_id: UUID
    user_id: UUID
    token: str
    type: TokenType
    expires_at: datetime
    created_at: datetime
    device_info: Optional[str] = None
    
    class Config:
        orm_mode = True
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str