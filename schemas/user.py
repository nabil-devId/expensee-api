from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, validator
from app.models.user import UserStatus


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    status: Optional[UserStatus] = UserStatus.ACTIVE
    is_superuser: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        # Check password strength
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    
    @validator('new_password')
    def password_strength(cls, v, values):
        if v is not None:
            # Check password strength
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            if not any(c.isupper() for c in v):
                raise ValueError('Password must contain at least one uppercase letter')
            if not any(c.islower() for c in v):
                raise ValueError('Password must contain at least one lowercase letter')
            if not any(c.isdigit() for c in v):
                raise ValueError('Password must contain at least one digit')
        return v


class UserInDBBase(UserBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# User statistics
class UserStatistics(BaseModel):
    total_expenses: int = 0
    total_amount: Decimal = Decimal('0.0')
    last_activity: Optional[datetime] = None


# User profile
class UserProfile(UserInDBBase):
    statistics: UserStatistics


# Additional properties to return via API
class User(UserInDBBase):
    pass


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    password_hash: str