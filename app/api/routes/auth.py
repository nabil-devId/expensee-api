from datetime import datetime, timedelta
from typing import Any, Dict
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core import security
from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserStatus
from app.models.auth_token import AuthToken, TokenType
from app.models.password_reset import PasswordReset
from app.utils.email import send_password_reset_email
from schemas.token import Token, TokenCreate, RefreshTokenRequest, ForgotPasswordRequest, ForgotPasswordResponse, ResetPasswordRequest, ResetPasswordResponse
from schemas.user import User as UserSchema
from schemas.user import UserCreate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_agent: str = Body(None, embed=True)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Query user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_code": "authentication_failed",
                "message": "Incorrect email or password"
            }
        )
    elif user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_code": "authentication_failed",
                "message": f"User account is {user.status}"
            }
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    
    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)  # 30 days for refresh token
    
    access_token_exp = datetime.utcnow() + access_token_expires
    refresh_token_exp = datetime.utcnow() + refresh_token_expires
    
    # Create JWT tokens
    access_token = security.create_access_token(
        user.user_id, expires_delta=access_token_expires
    )
    refresh_token = security.create_access_token(
        user.user_id, expires_delta=refresh_token_expires
    )
    
    # Store tokens in database
    db_access_token = AuthToken(
        user_id=user.user_id,
        token=access_token,
        type=TokenType.ACCESS,
        expires_at=access_token_exp,
        device_info=user_agent
    )
    
    db_refresh_token = AuthToken(
        user_id=user.user_id,
        token=refresh_token,
        type=TokenType.REFRESH,
        expires_at=refresh_token_exp,
        device_info=user_agent
    )
    
    db.add(db_access_token)
    db.add(db_refresh_token)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_at": access_token_exp
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    user_agent: str = Body(None, embed=True)
) -> Any:
    """
    Refresh access token using refresh token
    """
    try:
        # Verify refresh token
        payload = security.jwt.decode(
            request.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error_code": "authentication_failed",
                    "message": "Invalid refresh token"
                }
            )
        
        # Check if token exists in database and is valid
        query = select(AuthToken).where(
            AuthToken.token == request.refresh_token,
            AuthToken.type == TokenType.REFRESH,
            AuthToken.expires_at > datetime.utcnow()
        )
        result = await db.execute(query)
        token_record = result.scalars().first()
        
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error_code": "authentication_failed",
                    "message": "Refresh token not found or expired"
                }
            )
        
        # Check if user exists and is active
        query = select(User).where(User.user_id == token_record.user_id)
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "error_code": "authentication_failed",
                    "message": "User not found or inactive"
                }
            )
        
        # Generate new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_exp = datetime.utcnow() + access_token_expires
        
        access_token = security.create_access_token(
            user.user_id, expires_delta=access_token_expires
        )
        
        # Store new access token in database
        db_access_token = AuthToken(
            user_id=user.user_id,
            token=access_token,
            type=TokenType.ACCESS,
            expires_at=access_token_exp,
            device_info=user_agent or token_record.device_info
        )
        
        db.add(db_access_token)
        await db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": request.refresh_token,  # Keep the same refresh token
            "token_type": "bearer",
            "expires_at": access_token_exp
        }
        
    except security.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error_code": "authentication_failed",
                "message": "Invalid refresh token"
            }
        )


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register_new_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Create new user
    """
    # Check if user with this email already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_code": "validation_error",
                "message": "A user with this email already exists"
            }
        )
    
    # Create new user
    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        status=UserStatus.ACTIVE,
        is_superuser=user_in.is_superuser,
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.post("/logout")
async def logout(
    token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Logout by invalidating the token
    """
    try:
        # Find and delete the token
        query = select(AuthToken).where(AuthToken.token == token)
        result = await db.execute(query)
        token_record = result.scalars().first()
        
        if token_record:
            await db.delete(token_record)
            await db.commit()
        
        return {"status": "success", "message": "Successfully logged out"}
        
    except Exception:
        # Don't raise error on logout even if something went wrong
        return {"status": "success", "message": "Successfully logged out"}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
) -> ForgotPasswordResponse:
    """
    Request a password reset link
    """
    # Check if email exists
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    # Always return the same response regardless of whether the email was found
    # This prevents email enumeration attacks
    if not user:
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return ForgotPasswordResponse(
            status="success",
            message="If the email exists, a reset link has been sent"
        )
    
    # Create a password reset token
    token, token_record = PasswordReset.create_token(user.user_id)
    
    # Save token to database
    db.add(token_record)
    await db.commit()
    
    # Construct reset URL
    # In a real app, this would be a frontend URL
    base_url = str(req.base_url)
    # Use the correct API path with prefix
    reset_url = f"{base_url}{settings.API_V1_PREFIX.lstrip('/')}/auth/reset-password"
    
    # Send email with reset link
    email_sent = await send_password_reset_email(
        user.email,
        token,
        reset_url
    )
    
    if not email_sent:
        logger.error(f"Failed to send password reset email to {user.email}")
    
    return ForgotPasswordResponse(
        status="success",
        message="If the email exists, a reset link has been sent"
    )


@router.get("/reset-password")
async def get_reset_password(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle the initial reset password request from email link
    This endpoint verifies the token and redirects to the frontend reset page
    """
    # Find token in database
    query = select(PasswordReset).where(
        PasswordReset.token == token,
        PasswordReset.is_used == False  # noqa: E712
    )
    result = await db.execute(query)
    token_record = result.scalars().first()
    
    if not token_record or token_record.is_expired:
        # In a real app, redirect to an error page
        return {
            "status": "error",
            "message": "Invalid or expired reset token"
        }
    
    # In a real app, this would redirect to a frontend page where the user can enter a new password
    # For now, we'll just return a success message with instructions
    return {
        "status": "success",
        "message": "Token is valid. Please use the POST endpoint with your new password to complete the reset.",
        "token": token
    }


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> ResetPasswordResponse:
    """
    Reset password using token from email
    """
    # Find token in database
    query = select(PasswordReset).where(
        PasswordReset.token == request.token,
        PasswordReset.is_used == False  # noqa: E712
    )
    result = await db.execute(query)
    token_record = result.scalars().first()
    
    if not token_record or token_record.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_code": "validation_error",
                "message": "Invalid or expired reset token"
            }
        )
    
    # Get the user
    query = select(User).where(User.user_id == token_record.user_id)
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_code": "validation_error",
                "message": "User not found"
            }
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    db.add(user)
    
    # Mark token as used
    token_record.is_used = True
    db.add(token_record)
    
    # Invalidate all refresh tokens for the user
    query = select(AuthToken).where(
        AuthToken.user_id == user.user_id,
        AuthToken.type == TokenType.REFRESH
    )
    result = await db.execute(query)
    refresh_tokens = result.scalars().all()
    
    for token in refresh_tokens:
        await db.delete(token)
    
    await db.commit()
    
    return ResetPasswordResponse(
        status="success",
        message="Password has been reset successfully"
    )
