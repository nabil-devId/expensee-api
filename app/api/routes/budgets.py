from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import date, datetime
import calendar

from app.core.db import get_db
from app.api.dependencies import get_current_user
from app.models import User, Budget, Category, UserCategory, ExpenseHistory
from schemas.budget import (
    BudgetCreate, BudgetResponse, BudgetUpdateResponse, 
    BudgetListResponse, BudgetDeleteResponse,
    CategoryInfo,
    OverallBudget, BudgetWithSpending
)

router = APIRouter(tags=["budgets"])

def get_category_info(category=None, user_category=None):
    """
    Create a CategoryInfo object from either Category or UserCategory.
    """
    if category:
        return CategoryInfo(
            id=category.category_id,
            name=category.name,
            icon=category.icon,
            color=category.color,
            is_custom=False
        )
    elif user_category:
        return CategoryInfo(
            id=user_category.user_category_id,
            name=user_category.name,
            icon=user_category.icon,
            color=user_category.color,
            is_custom=True
        )
    return None


async def get_budget_with_spending(db: AsyncSession, budget: Budget, month: int, year: int):
    """
    Calculate spending for a budget within a date range.
    """
    # Base query for expenses in the period
    query = (
        select(func.sum(ExpenseHistory.total_amount))
        .where(
            ExpenseHistory.user_id == budget.user_id,
            ExpenseHistory.transaction_date >= date(year, month, 1),
            ExpenseHistory.transaction_date <= date(year, month, calendar.monthrange(year, month)[1]),
            or_(
                ExpenseHistory.category_id == budget.category_id,
                ExpenseHistory.user_category_id == budget.user_category_id
            )
        )
    )
    
    result = await db.execute(query)
    spending = result.scalar_one_or_none() or 0
    
    # Calculate remaining and percentage
    remaining = Decimal(budget.amount) - Decimal(spending)
    percentage_used = round((Decimal(spending) / Decimal(budget.amount)) * 100, 2) if Decimal(budget.amount) > 0 else 0
    
    # Get category info if applicable
    category_info = None
    if budget.category_id:
        category_info = get_category_info(category=budget.category)
    elif budget.user_category_id:
        category_info = get_category_info(user_category=budget.user_category)
    
    # Construct response
    return BudgetWithSpending(
        budget_id=budget.budget_id,
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        created_at=budget.created_at,
        budget_name=budget.budget_name,
        category=category_info,
        current_spending=spending,
        remaining=remaining,
        percentage_used=percentage_used
    )


async def get_overall_budget_spending(db: AsyncSession, user_id: UUID, month: int, year: int):
    """
    Calculate overall spending and budget metrics.
    """
    # Get total spending in the period
    query = (
        select(func.sum(ExpenseHistory.total_amount))
        .where(
            ExpenseHistory.user_id == user_id,
            ExpenseHistory.transaction_date >= date(year, month, 1),
            ExpenseHistory.transaction_date <= date(year, month, calendar.monthrange(year, month)[1])
        )
    )
    result = await db.execute(query)
    spending = result.scalar_one_or_none() or 0
    
    # Use budget.amount if a budget is provided, otherwise 0
    budget_query = (
        select(func.sum(Budget.amount))
        .where(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year
        )
    )
    budget_result = await db.execute(budget_query)
    budget_amount = budget_result.scalar_one_or_none() or 0
    
    # Calculate remaining and percentage
    remaining = budget_amount - Decimal(spending)
    percentage_used = round(Decimal(spending) / budget_amount, 2) * 100 if budget_amount > 0 else 0
    
    return OverallBudget(
        amount=budget_amount,
        current_spending=spending,
        remaining=remaining,
        percentage_used=percentage_used
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new budget for the user.
    """

    if not budget.category_id and not budget.user_category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either category_id or user_category_id must be provided"
        )
    if budget.category_id and budget.user_category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of category_id or user_category_id can be provided"
        )
    category_info = None
    # Validate category_id or user_category_id if provided
    if budget.category_id:
        result = await db.execute(select(Category).where(Category.category_id == budget.category_id))
        category_info = result.scalar_one_or_none()
        if not category_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    elif budget.user_category_id:
        result = await db.execute(
            select(UserCategory).where(
                UserCategory.user_category_id == budget.user_category_id,
                UserCategory.user_id == current_user.user_id
            )
        )
        category_info = result.scalar_one_or_none()
        if not category_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom category not found or you don't have permission to use it"
            )
    # Create new budget
    new_budget = Budget(
        user_id=current_user.user_id,
        category_id=budget.category_id,
        user_category_id=budget.user_category_id,
        budget_name=budget.budget_name,
        amount=budget.amount,
        month=budget.month,
        year=budget.year
    )
    
    db.add(new_budget)
    await db.commit()
    await db.refresh(new_budget)
    
    # Get category info for response

    if new_budget.category_id:
        category_info = get_category_info(category=new_budget.category)
    elif new_budget.user_category_id:
        category_info = get_category_info(user_category=new_budget.user_category)
    
    return BudgetResponse(
        budget_id=new_budget.budget_id,
        amount=new_budget.amount,
        month=new_budget.month,
        year=new_budget.year,
        budget_name=new_budget.budget_name,
        created_at=new_budget.created_at,
        category=category_info
    )


@router.get("", response_model=BudgetListResponse)
async def get_budgets(
    month: int = date.today().month,
    year: int = date.today().year,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all budgets for the user with spending information.
    """
    
    # Base query for user's budgets
    query = (
        select(Budget)
        .where(Budget.user_id == current_user.user_id)
    )
    
    # Filter by period if specified
    if month and year:
        query = query.where(
            Budget.month == month,
            Budget.year == year
        )
    
    result = await db.execute(query)
    budgets = result.scalars().all()
    
    # Find the overall budget (no category)
    overall_budget = await get_overall_budget_spending(db, current_user.user_id, month, year)
    budgets_with_spending = []
    
    for budget in budgets:
        budget_with_spending = await get_budget_with_spending(db, budget, month, year)
        budgets_with_spending.append(budget_with_spending)
    
    return BudgetListResponse(
        budgets=budgets_with_spending,
        overall_budget=overall_budget
    )



@router.get("/{budget_id}", response_model=BudgetUpdateResponse)
async def get_budget_detail(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a budget detail.
    """
    result = await db.execute(
        select(Budget).where(
            Budget.budget_id == budget_id,
            Budget.user_id == current_user.user_id
        )
    )
    existing_budget = result.scalar_one_or_none()
    
    if not existing_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found or you don't have permission to view it"
        )
    
    # Get category info for response
    category_info = None
    if existing_budget.category_id:
        category_info = get_category_info(category=existing_budget.category)
    elif existing_budget.user_category_id:
        category_info = get_category_info(user_category=existing_budget.user_category)
    
    return BudgetUpdateResponse(
        budget_id=existing_budget.budget_id,
        amount=existing_budget.amount,
        month=existing_budget.month,
        year=existing_budget.year,
        budget_name=existing_budget.budget_name,
        updated_at=existing_budget.updated_at,
        created_at=existing_budget.created_at,
        category=category_info
    )

@router.put("/{budget_id}", response_model=BudgetUpdateResponse)
async def update_budget(
    budget_id: UUID,
    budget_update: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a budget.
    """
    result = await db.execute(
        select(Budget).where(
            Budget.budget_id == budget_id,
            Budget.user_id == current_user.user_id
        )
    )
    existing_budget = result.scalar_one_or_none()
    
    if not existing_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found or you don't have permission to update it"
        )
    
    # Update budget fields
    existing_budget.amount = budget_update.amount
    existing_budget.month = budget_update.month
    existing_budget.year = budget_update.year
    existing_budget.category_id = budget_update.category_id
    existing_budget.user_category_id = budget_update.user_category_id
    existing_budget.budget_name = budget_update.budget_name
    
    await db.commit()
    await db.refresh(existing_budget)
    
    # Get category info for response
    category_info = None
    if existing_budget.category_id:
        category_info = get_category_info(category=existing_budget.category)
    elif existing_budget.user_category_id:
        category_info = get_category_info(user_category=existing_budget.user_category)
    
    return BudgetUpdateResponse(
        budget_id=existing_budget.budget_id,
        amount=existing_budget.amount,
        month=existing_budget.month,
        year=existing_budget.year,
        budget_name=existing_budget.budget_name,
        updated_at=existing_budget.updated_at,
        created_at=existing_budget.created_at,
        category=category_info
    )


@router.delete("/{budget_id}", response_model=BudgetDeleteResponse)
async def delete_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a budget.
    """
    result = await db.execute(
        select(Budget).where(
            Budget.budget_id == budget_id,
            Budget.user_id == current_user.user_id
        )
    )
    budget = result.scalar_one_or_none()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found or you don't have permission to delete it"
        )
    
    await db.delete(budget)
    await db.commit()
    return BudgetDeleteResponse()