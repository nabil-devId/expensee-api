from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, case, text
from uuid import UUID
from datetime import date, datetime, timedelta
import calendar

from app.core.db import get_db
from app.api.dependencies import get_current_user
from app.models import User, Budget, Category, UserCategory, ExpenseItem, ExpenseHistory
from schemas.budget import (
    BudgetCreate, BudgetResponse, BudgetUpdateResponse, 
    BudgetListResponse, BudgetProgressResponse, BudgetDeleteResponse,
    BudgetPeriod, BudgetStatus, CategoryInfo, CategoryBudgetProgress,
    OverallBudget, BudgetWithSpending
)

router = APIRouter(tags=["budgets"])


def get_period_dates(period: BudgetPeriod, date_for: date = None):
    """
    Calculate start and end dates for a given period.
    """
    if date_for is None:
        date_for = date.today()
    
    if period == BudgetPeriod.MONTHLY:
        start_date = date(date_for.year, date_for.month, 1)
        # Get last day of the month
        last_day = calendar.monthrange(date_for.year, date_for.month)[1]
        end_date = date(date_for.year, date_for.month, last_day)
    
    elif period == BudgetPeriod.QUARTERLY:
        # Determine which quarter the date is in
        quarter = (date_for.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        
        start_date = date(date_for.year, start_month, 1)
        last_day = calendar.monthrange(date_for.year, end_month)[1]
        end_date = date(date_for.year, end_month, last_day)
    
    elif period == BudgetPeriod.YEARLY:
        start_date = date(date_for.year, 1, 1)
        end_date = date(date_for.year, 12, 31)
    
    return start_date, end_date


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


async def get_budget_with_spending(db: AsyncSession, budget: Budget, start_date: date, end_date: date):
    """
    Calculate spending for a budget within a date range.
    """
    # Base query for expenses in the period
    query = (
        select(func.sum(ExpenseHistory.total_amount))
        .where(
            ExpenseHistory.user_id == budget.user_id,
            ExpenseHistory.transaction_date >= start_date,
            ExpenseHistory.transaction_date <= end_date
        )
    )
    
    # Add category filter if this is a category budget
    if budget.category_id:
        query = query.where(ExpenseHistory.category_id == budget.category_id)
    elif budget.user_category_id:
        query = query.where(ExpenseHistory.user_category_id == budget.user_category_id)
    
    result = await db.execute(query)
    spending = result.scalar_one_or_none() or 0
    
    # Calculate remaining and percentage
    remaining = float(budget.amount) - float(spending)
    percentage_used = round((float(spending) / float(budget.amount)) * 100, 2) if float(budget.amount) > 0 else 0
    
    # Get category info if applicable
    category_info = None
    if budget.category_id:
        result = await db.execute(select(Category).where(Category.category_id == budget.category_id))
        category = result.scalar_one_or_none()
        if category:
            category_info = get_category_info(category=category)
    elif budget.user_category_id:
        result = await db.execute(select(UserCategory).where(UserCategory.user_category_id == budget.user_category_id))
        user_category = result.scalar_one_or_none()
        if user_category:
            category_info = get_category_info(user_category=user_category)
    
    # Construct response
    return BudgetWithSpending(
        budget_id=budget.budget_id,
        amount=budget.amount,
        period=budget.period,
        start_date=budget.start_date,
        end_date=budget.end_date,
        created_at=budget.created_at,
        category=category_info,
        current_spending=spending,
        remaining=remaining,
        percentage_used=percentage_used
    )


async def get_overall_budget_spending(db: AsyncSession, user_id: UUID, start_date: date, end_date: date, budget=None):
    """
    Calculate overall spending and budget metrics.
    """
    # Get total spending in the period
    query = (
        select(func.sum(ExpenseItem.total_price))
        .where(
            ExpenseItem.user_id == user_id,
            ExpenseItem.purchase_date >= start_date,
            ExpenseItem.purchase_date <= end_date
        )
    )
    result = await db.execute(query)
    spending = result.scalar_one_or_none() or 0
    
    # Use budget.amount if a budget is provided, otherwise 0
    budget_amount = float(budget.amount) if budget else 0
    
    # Calculate remaining and percentage
    remaining = budget_amount - float(spending)
    percentage_used = round(float(spending) / budget_amount, 2) * 100 if budget_amount > 0 else 0
    
    return OverallBudget(
        budget_id=budget.budget_id if budget else None,
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
    # Validate category_id or user_category_id if provided
    if budget.category_id:
        result = await db.execute(select(Category).where(Category.category_id == budget.category_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    
    if budget.user_category_id:
        result = await db.execute(
            select(UserCategory).where(
                UserCategory.user_category_id == budget.user_category_id,
                UserCategory.user_id == current_user.user_id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom category not found or you don't have permission to use it"
            )
    
    # Create new budget
    new_budget = Budget(
        user_id=current_user.user_id,
        category_id=budget.category_id,
        user_category_id=budget.user_category_id,
        amount=budget.amount,
        period=budget.period,
        start_date=budget.start_date,
        end_date=budget.end_date
    )
    
    db.add(new_budget)
    await db.commit()
    await db.refresh(new_budget)
    
    # Get category info for response
    category_info = None
    if new_budget.category_id:
        result = await db.execute(select(Category).where(Category.category_id == new_budget.category_id))
        category = result.scalar_one_or_none()
        if category:
            category_info = get_category_info(category=category)
    elif new_budget.user_category_id:
        result = await db.execute(select(UserCategory).where(UserCategory.user_category_id == new_budget.user_category_id))
        user_category = result.scalar_one_or_none()
        if user_category:
            category_info = get_category_info(user_category=user_category)
    
    return BudgetResponse(
        budget_id=new_budget.budget_id,
        amount=new_budget.amount,
        period=new_budget.period,
        start_date=new_budget.start_date,
        end_date=new_budget.end_date,
        created_at=new_budget.created_at,
        category=category_info
    )


@router.get("", response_model=BudgetListResponse)
async def get_budgets(
    period: Optional[BudgetPeriod] = None,
    active_on: Optional[date] = Query(None, description="Date to check active budgets"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all budgets for the user with spending information.
    """
    if active_on is None:
        active_on = date.today()
    
    # Base query for user's budgets
    query = (
        select(Budget)
        .where(Budget.user_id == current_user.user_id)
    )
    
    # Filter by period if specified
    if period:
        query = query.where(Budget.period == period)
    
    # Filter for active budgets on the specified date
    query = query.where(
        and_(
            Budget.start_date <= active_on,
            or_(
                Budget.end_date == None,
                Budget.end_date >= active_on
            )
        )
    )
    
    result = await db.execute(query)
    budgets = result.scalars().all()
    
    # Find the overall budget (no category)
    overall_budget = None
    budgets_with_spending = []
    
    for budget in budgets:
        start_date, end_date = get_period_dates(budget.period, active_on)
        
        # Check if this is an overall budget (no category)
        if budget.category_id is None and budget.user_category_id is None:
            overall_budget = await get_overall_budget_spending(db, current_user.user_id, start_date, end_date, budget)
        else:
            # Add category budget with spending info
            budget_with_spending = await get_budget_with_spending(db, budget, start_date, end_date)
            budgets_with_spending.append(budget_with_spending)
    
    # If no overall budget was found, calculate overall spending without a budget
    if overall_budget is None:
        # Use the period of the first budget or default to monthly
        if budgets and period is None:
            first_period = budgets[0].period
        else:
            first_period = period or BudgetPeriod.MONTHLY
            
        start_date, end_date = get_period_dates(first_period, active_on)
        overall_budget = await get_overall_budget_spending(db, current_user.user_id, start_date, end_date)
    
    return BudgetListResponse(
        budgets=budgets_with_spending,
        overall_budget=overall_budget
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
    existing_budget.period = budget_update.period
    existing_budget.start_date = budget_update.start_date
    existing_budget.end_date = budget_update.end_date
    existing_budget.category_id = budget_update.category_id
    existing_budget.user_category_id = budget_update.user_category_id
    
    await db.commit()
    await db.refresh(existing_budget)
    
    # Get category info for response
    category_info = None
    if existing_budget.category_id:
        result = await db.execute(select(Category).where(Category.category_id == existing_budget.category_id))
        category = result.scalar_one_or_none()
        if category:
            category_info = get_category_info(category=category)
    elif existing_budget.user_category_id:
        result = await db.execute(select(UserCategory).where(UserCategory.user_category_id == existing_budget.user_category_id))
        user_category = result.scalar_one_or_none()
        if user_category:
            category_info = get_category_info(user_category=user_category)
    
    return BudgetUpdateResponse(
        budget_id=existing_budget.budget_id,
        amount=existing_budget.amount,
        period=existing_budget.period,
        start_date=existing_budget.start_date,
        end_date=existing_budget.end_date,
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


@router.get("/progress", response_model=BudgetProgressResponse)
async def get_budget_progress(
    period: BudgetPeriod = BudgetPeriod.MONTHLY,
    date_param: Optional[date] = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get budget progress for all categories.
    """
    if date_param is None:
        date_param = date.today()
        
    # Get date range for the period
    start_date, end_date = get_period_dates(period, date_param)
    
    # Find all active budgets for the period
    query = (
        select(Budget)
        .where(
            Budget.user_id == current_user.user_id,
            Budget.period == period,
            Budget.start_date <= date_param,
            or_(
                Budget.end_date == None,
                Budget.end_date >= date_param
            )
        )
    )
    
    result = await db.execute(query)
    budgets = result.scalars().all()
    
    # Find overall budget and category budgets
    overall_budget = None
    category_budgets = []
    
    for budget in budgets:
        if budget.category_id is None and budget.user_category_id is None:
            # This is an overall budget
            overall_budget = budget
        else:
            # This is a category budget
            category_budgets.append(budget)
    
    # Calculate overall spending
    overall_budget_spending = await get_overall_budget_spending(
        db, current_user.user_id, start_date, end_date, overall_budget
    )
    
    # Process each category budget
    categories_progress = []
    
    for budget in category_budgets:
        # Get category info
        category_info = None
        if budget.category_id:
            result = await db.execute(select(Category).where(Category.category_id == budget.category_id))
            category = result.scalar_one_or_none()
            if category:
                category_info = get_category_info(category=category)
        elif budget.user_category_id:
            result = await db.execute(select(UserCategory).where(UserCategory.user_category_id == budget.user_category_id))
            user_category = result.scalar_one_or_none()
            if user_category:
                category_info = get_category_info(user_category=user_category)
        
        if not category_info:
            continue
            
        # Calculate spending for this category
        query = (
            select(func.sum(ExpenseHistory.total_amount))
            .where(
                ExpenseHistory.user_id == current_user.user_id,
                ExpenseHistory.transaction_date >= start_date,
                ExpenseHistory.transaction_date <= end_date
            )
        )
        
        if budget.category_id:
            query = query.where(ExpenseHistory.category_id == budget.category_id)
        elif budget.user_category_id:
            query = query.where(ExpenseHistory.user_category_id == budget.user_category_id)
        
        result = await db.execute(query)
        spending = result.scalar_one_or_none() or 0
        
        # Calculate metrics
        remaining = float(budget.amount) - float(spending)
        percentage_used = round((float(spending) / float(budget.amount)) * 100, 2) if float(budget.amount) > 0 else 0
        
        # Determine status
        status = BudgetStatus.UNDER_BUDGET
        if percentage_used >= 100:
            status = BudgetStatus.OVER_BUDGET
        elif percentage_used >= 75:
            status = BudgetStatus.APPROACHING_LIMIT
        
        categories_progress.append(
            CategoryBudgetProgress(
                category=category_info,
                budget_amount=budget.amount,
                current_spending=spending,
                remaining=remaining,
                percentage_used=percentage_used,
                status=status
            )
        )
    
    return BudgetProgressResponse(
        period_start=start_date,
        period_end=end_date,
        overall_budget=overall_budget_spending,
        categories=categories_progress
    )
