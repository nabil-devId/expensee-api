from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.core.db import get_db
from app.api.dependencies import get_current_user
from app.models import User, Category, UserCategory
from schemas.category import (
    CategoryCreate, CategoryResponse, CategoryListResponse,
    UserCategoryCreate, UserCategoryResponse, UserCategoryUpdateResponse,
    CategoryDeleteResponse
)

router = APIRouter(tags=["categories"])


@router.get("", response_model=CategoryListResponse)
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories including default categories and user's custom categories.
    """
    # Get default categories
    result = await db.execute(select(Category))
    default_categories = result.scalars().all()
    
    # Get user's custom categories
    result = await db.execute(
        select(UserCategory).where(UserCategory.user_id == current_user.user_id)
    )
    user_categories = result.scalars().all()
    
    return CategoryListResponse(
        default_categories=default_categories,
        user_categories=user_categories
    )


@router.post("", response_model=UserCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_category(
    category: UserCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new custom category for the user.
    """
    new_category = UserCategory(
        user_id=current_user.user_id,
        name=category.name,
        icon=category.icon,
        color=category.color
    )
    
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    
    return new_category


@router.put("/{user_category_id}", response_model=UserCategoryUpdateResponse)
async def update_custom_category(
    user_category_id: UUID,
    category: UserCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a custom category.
    """
    result = await db.execute(
        select(UserCategory).where(
            UserCategory.user_category_id == user_category_id,
            UserCategory.user_id == current_user.user_id
        )
    )
    existing_category = result.scalar_one_or_none()
    
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or you don't have permission to update it"
        )
    
    existing_category.name = category.name
    existing_category.icon = category.icon
    existing_category.color = category.color
    
    await db.commit()
    await db.refresh(existing_category)
    
    return existing_category


@router.delete("/{user_category_id}", response_model=CategoryDeleteResponse)
async def delete_custom_category(
    user_category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a custom category.
    """
    result = await db.execute(
        select(UserCategory).where(
            UserCategory.user_category_id == user_category_id,
            UserCategory.user_id == current_user.user_id
        )
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or you don't have permission to delete it"
        )
    
    await db.delete(category)
    await db.commit()
    
    return CategoryDeleteResponse()
