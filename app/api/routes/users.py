from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies import get_current_active_superuser, get_current_active_user
from app.core.db import get_db
from app.core.security import get_password_hash
from app.models.user import User, UserStatus
from schemas.user import User as UserSchema
from schemas.user import UserCreate, UserUpdate
from schemas.receipt import ErrorResponse

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user
    """
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update current user
    """
    # Update user attributes based on input
    if user_in.password is not None:
        current_user.password_hash = get_password_hash(user_in.password)
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.email is not None:
        # Check if email is already taken by another user
        if user_in.email != current_user.email:
            result = await db.execute(select(User).where(User.email == user_in.email))
            existing_user = result.scalars().first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "error_code": "validation_error",
                        "message": "Email already in use"
                    }
                )
        current_user.email = user_in.email
    if user_in.status is not None:
        current_user.status = user_in.status
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("", response_model=List[UserSchema])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Retrieve users. Only for superusers.
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
async def read_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific user by id
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "error",
                "error_code": "authorization_failed",
                "message": "The user doesn't have enough privileges"
            }
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "error",
                "error_code": "resource_not_found",
                "message": "The user with this id does not exist in the system"
            }
        )
    return user


@router.patch("/{user_id}/status", response_model=UserSchema)
async def update_user_status(
    user_id: UUID,
    status: UserStatus,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update user status. Only for superusers.
    """
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "error",
                "error_code": "resource_not_found",
                "message": "The user with this id does not exist in the system"
            }
        )
    
    user.status = status
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user