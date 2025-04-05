from typing import Any, List
import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.dependencies import get_current_active_superuser, get_current_active_user
from app.core.db import get_db
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserStatus
from app.models.expense_history import ExpenseHistory
from schemas.user import User as UserSchema, UserProfile, UserStatistics
from schemas.user import UserCreate, UserUpdate
from schemas.receipt import ErrorResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserSchema)
async def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user
    """
    return current_user


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get user profile with statistics
    """
    # Get user expense statistics
    query = select(
        func.count(ExpenseHistory.expense_id).label("total_expenses"),
        func.sum(ExpenseHistory.total_amount).label("total_amount"),
        func.max(ExpenseHistory.created_at).label("last_activity")
    ).where(ExpenseHistory.user_id == current_user.user_id)
    
    result = await db.execute(query)
    stats = result.one()
    
    # Create statistics object
    statistics = UserStatistics(
        total_expenses=stats.total_expenses or 0,
        total_amount=stats.total_amount or Decimal("0.0"),
        last_activity=stats.last_activity
    )
    
    # Create profile response
    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        status=current_user.status,
        is_superuser=current_user.is_superuser,
        statistics=statistics
    )


@router.patch("/profile", response_model=UserSchema)
async def update_user_profile(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update user profile
    """
    # For security-sensitive changes, require current password
    if user_in.email is not None or user_in.new_password is not None:
        if not user_in.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "validation_error",
                    "message": "Current password is required for email or password changes"
                }
            )
        
        # Verify current password
        if not verify_password(user_in.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "validation_error",
                    "message": "Current password is incorrect"
                }
            )
    
    # Update user attributes based on input
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
    
    if user_in.new_password is not None:
        current_user.password_hash = get_password_hash(user_in.new_password)
    
    # Don't allow regular users to change their status
    # Only allow them to update specific attributes
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update current user (legacy endpoint, use /profile instead)
    """
    # Redirect to the new profile endpoint
    return await update_user_profile(db=db, user_in=user_in, current_user=current_user)


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
