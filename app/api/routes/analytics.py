import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, and_, between, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.expense_history import ExpenseHistory
from app.models.category import Category, UserCategory
from app.models.budget import Budget

from schemas.analytics.trends import (
    PeriodType, TrendResponse, DataPoint, AmountInfo,
    CategoryDistributionResponse, CategoryDistributionItem, CategoryInfo,
    MerchantAnalysisResponse, MerchantAnalysisItem, CategoryUsageInfo
)

router = APIRouter()


async def get_period_start_end(
    period: PeriodType, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None
) -> tuple[date, date]:
    """
    Calculate start and end dates based on period type and optional date range.
    """
    today = date.today()
    
    # If both dates are provided, use them as is
    if start_date and end_date:
        return start_date, end_date
    
    # If only end_date is provided, calculate start_date based on period
    elif end_date and not start_date:
        if period == PeriodType.WEEKLY:
            start_date = end_date - timedelta(days=7*12)  # 12 weeks
        elif period == PeriodType.MONTHLY:
            # Go back 12 months
            year = end_date.year - (1 if end_date.month <= 12 else 0)
            month = end_date.month - 12 if end_date.month > 12 else 12 + end_date.month - 12
            start_date = date(year, month, 1)
        else:  # YEARLY
            start_date = date(end_date.year - 3, 1, 1)  # 3 years back
    
    # If only start_date is provided, calculate end_date based on period
    elif start_date and not end_date:
        end_date = today
    
    # If no dates are provided, calculate both based on period
    else:
        if period == PeriodType.WEEKLY:
            end_date = today
            start_date = end_date - timedelta(days=7*12)  # 12 weeks
        elif period == PeriodType.MONTHLY:
            end_date = today
            # Go back 12 months
            year = end_date.year - (1 if end_date.month <= 12 else 0)
            month = end_date.month - 12 if end_date.month > 12 else 12 + end_date.month - 12
            start_date = date(year, month, 1)
        else:  # YEARLY
            end_date = today
            start_date = date(end_date.year - 3, 1, 1)  # 3 years back
    
    return start_date, end_date


async def get_period_format(period: PeriodType):
    """Get the SQL date format for a period type"""
    if period == PeriodType.WEEKLY:
        # Group by week (week number + year)
        return "YYYY-WW"
    elif period == PeriodType.MONTHLY:
        # Group by month (year + month)
        return "YYYY-MM"
    else:  # YEARLY
        # Group by year
        return "YYYY"


@router.get("/trends", response_model=TrendResponse)
async def get_expense_trends(
    period: PeriodType = Query(PeriodType.MONTHLY, description="Time period for trends"),
    start_date: Optional[date] = Query(None, description="Start date for trends"),
    end_date: Optional[date] = Query(None, description="End date for trends"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> TrendResponse:
    """
    Get expense trends over time based on specified parameters.
    """
    try:
        # Get start and end dates based on period
        start_date, end_date = await get_period_start_end(period, start_date, end_date)
        
        # Build base query filters
        query_filters = [
            ExpenseHistory.user_id == current_user.user_id,
            ExpenseHistory.transaction_date >= start_date,
            ExpenseHistory.transaction_date <= end_date
        ]
        
        # Add category filter if specified
        if category_id:
            # Check if it's a system category or user category
            category_query = select(Category).where(Category.category_id == category_id)
            category_result = await db.execute(category_query)
            category = category_result.scalar_one_or_none()
            
            if category:
                query_filters.append(ExpenseHistory.category_id == category_id)
            else:
                # Check if it's a user category
                user_cat_query = select(UserCategory).where(
                    UserCategory.user_category_id == category_id,
                    UserCategory.user_id == current_user.user_id
                )
                user_cat_result = await db.execute(user_cat_query)
                user_category = user_cat_result.scalar_one_or_none()
                
                if user_category:
                    query_filters.append(ExpenseHistory.user_category_id == category_id)
                else:
                    raise HTTPException(status_code=404, detail=f"Category with ID {category_id} not found")
        
        # Create queries based on the period type
        if period == PeriodType.WEEKLY:
            # Group by week
            # We'll extract the date, week, and then group by the week
            query = (
                select(
                    func.date_trunc('week', ExpenseHistory.transaction_date).label('period_start'),
                    func.sum(ExpenseHistory.total_amount).label('amount'),
                    func.count().label('count')
                )
                .where(and_(*query_filters))
                .group_by(func.date_trunc('week', ExpenseHistory.transaction_date))
                .order_by(func.date_trunc('week', ExpenseHistory.transaction_date))
            )
        elif period == PeriodType.MONTHLY:
            # Group by month

            sub_query = (
                select(
                    func.date_trunc('month', ExpenseHistory.transaction_date).label('period_start'),
                    ExpenseHistory.total_amount
                )
                .select_from(ExpenseHistory)
                .where(and_(*query_filters))
                .subquery()
            )
            query = (
                select(
                    sub_query.c.period_start,
                    func.sum(sub_query.c.total_amount).label('amount'),
                    func.count()
                )
                .group_by(sub_query.c.period_start)
                .order_by(sub_query.c.period_start)
            )
        else:  # YEARLY
            # Group by year
            query = (
                select(
                    func.date_trunc('year', ExpenseHistory.transaction_date).label('period_start'),
                    func.sum(ExpenseHistory.total_amount).label('amount'),
                    func.count().label('count')
                )
                .where(and_(*query_filters))
                .group_by(func.date_trunc('year', ExpenseHistory.transaction_date))
                .order_by(func.date_trunc('year', ExpenseHistory.transaction_date))
            )
        
        # Execute the query
        result = await db.execute(query)
        period_data = result.all()
        
        # Format the data points
        data_points = [
            DataPoint(
                date=period_start.date(),
                total_amount=amount,
                count=count
            )
            for period_start, amount, count in period_data
        ]
        
        # Calculate total and average
        total_amount = sum(dp.total_amount for dp in data_points) if data_points else Decimal("0.0")
        average_per_period = total_amount / len(data_points) if data_points else Decimal("0.0")
        
        # Find max and min amounts
        max_point = max(data_points, key=lambda x: x.total_amount) if data_points else None
        min_point = min(data_points, key=lambda x: x.total_amount) if data_points else None
        
        max_amount = AmountInfo(
            date=max_point.date,
            amount=max_point.total_amount
        ) if max_point else AmountInfo(date=start_date, amount=Decimal("0.0"))
        
        min_amount = AmountInfo(
            date=min_point.date,
            amount=min_point.total_amount
        ) if min_point else AmountInfo(date=start_date, amount=Decimal("0.0"))
        
        # Calculate trend percentage
        trend_percentage = Decimal("0.0")
        if len(data_points) >= 2:
            first_amount = data_points[0].total_amount
            last_amount = data_points[-1].total_amount
            
            if first_amount > Decimal("0.0"):
                trend_percentage = ((last_amount - first_amount) / first_amount) * Decimal("100.0")
            
        return TrendResponse(
            period=period,
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            total_amount=total_amount,
            average_per_period=average_per_period,
            max_amount=max_amount,
            min_amount=min_amount,
            trend_percentage=trend_percentage
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating expense trends: {str(e)}")


@router.get("/category-distribution", response_model=CategoryDistributionResponse)
async def get_category_distribution(
    start_date: Optional[date] = Query(None, description="Start date for category distribution"),
    end_date: Optional[date] = Query(None, description="End date for category distribution"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> CategoryDistributionResponse:
    """
    Get expense distribution by category for the specified date range.
    """
    try:
        # Set default date range if not provided
        if not start_date:
            # Default to first day of current month
            today = date.today()
            start_date = date(today.year, today.month, 1)
        
        if not end_date:
            end_date = date.today()
        
        # Get all expenses within the date range
        query_filters = [
            ExpenseHistory.user_id == current_user.user_id,
            ExpenseHistory.transaction_date >= start_date,
            ExpenseHistory.transaction_date <= end_date
        ]
        
        # Get total amount for the period
        total_query = (
            select(func.sum(ExpenseHistory.total_amount))
            .where(and_(*query_filters))
        )
        result = await db.execute(total_query)
        total_amount = result.scalar_one_or_none() or Decimal("0.0")
        
        # Get system categories distribution
        sys_category_query = (
            select(
                Category.category_id,
                Category.name,
                Category.icon,
                Category.color,
                func.sum(ExpenseHistory.total_amount).label('amount'),
                func.count().label('count')
            )
            .join(ExpenseHistory, ExpenseHistory.category_id == Category.category_id)
            .where(and_(*query_filters))
            .group_by(Category.category_id)
            .order_by(desc(func.sum(ExpenseHistory.total_amount)))
        )
        
        result = await db.execute(sys_category_query)
        sys_category_records = result.all()
        
        # Get user categories distribution
        user_category_query = (
            select(
                UserCategory.user_category_id,
                UserCategory.name,
                UserCategory.icon,
                UserCategory.color,
                func.sum(ExpenseHistory.total_amount).label('amount'),
                func.count().label('count')
            )
            .join(ExpenseHistory, ExpenseHistory.user_category_id == UserCategory.user_category_id)
            .where(and_(*query_filters))
            .group_by(UserCategory.user_category_id)
            .order_by(desc(func.sum(ExpenseHistory.total_amount)))
        )
        
        result = await db.execute(user_category_query)
        user_category_records = result.all()
        
        # Get uncategorized expenses
        uncategorized_query = (
            select(
                func.sum(ExpenseHistory.total_amount).label('amount'),
                func.count().label('count')
            )
            .where(
                and_(
                    *query_filters,
                    ExpenseHistory.category_id.is_(None),
                    ExpenseHistory.user_category_id.is_(None)
                )
            )
        )
        
        result = await db.execute(uncategorized_query)
        uncategorized_record = result.one_or_none()
        
        # Combine and format results
        categories = []
        
        # Process system categories
        for cat_id, name, icon, color, amount, count in sys_category_records:
            percentage = (amount / total_amount) * Decimal("100.0") if total_amount > 0 else Decimal("0.0")
            
            categories.append(
                CategoryDistributionItem(
                    category=CategoryInfo(
                        id=str(cat_id),
                        name=name,
                        icon=icon,
                        color=color
                    ),
                    amount=amount,
                    percentage=percentage,
                    count=count
                )
            )
        
        # Process user categories
        for cat_id, name, icon, color, amount, count in user_category_records:
            percentage = (amount / total_amount) * Decimal("100.0") if total_amount > 0 else Decimal("0.0")
            
            categories.append(
                CategoryDistributionItem(
                    category=CategoryInfo(
                        id=str(cat_id),
                        name=name,
                        icon=icon,
                        color=color
                    ),
                    amount=amount,
                    percentage=percentage,
                    count=count
                )
            )
        
        # Add uncategorized if exists
        if uncategorized_record and uncategorized_record.amount:
            amount, count = uncategorized_record
            if amount:
                percentage = (amount / total_amount) * Decimal("100.0") if total_amount > 0 else Decimal("0.0")
                
                categories.append(
                    CategoryDistributionItem(
                        category=CategoryInfo(
                            id="uncategorized",
                            name="Uncategorized",
                            icon=None,
                            color="#CCCCCC"
                        ),
                        amount=amount,
                        percentage=percentage,
                        count=count
                    )
                )
        
        # Sort categories by amount
        categories.sort(key=lambda x: x.amount, reverse=True)
        
        return CategoryDistributionResponse(
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            categories=categories
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating category distribution: {str(e)}")


@router.get("/merchants", response_model=MerchantAnalysisResponse)
async def get_merchant_analysis(
    start_date: Optional[date] = Query(None, description="Start date for merchant analysis"),
    end_date: Optional[date] = Query(None, description="End date for merchant analysis"),
    limit: int = Query(10, ge=1, le=50, description="Number of top merchants to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MerchantAnalysisResponse:
    """
    Get analysis of expenses by merchant for the specified date range.
    """
    try:
        # Set default date range if not provided
        if not start_date:
            # Default to first day of current month
            today = date.today()
            start_date = date(today.year, today.month, 1)
        
        if not end_date:
            end_date = date.today()
        
        # Build base query filters
        query_filters = [
            ExpenseHistory.user_id == current_user.user_id,
            ExpenseHistory.transaction_date >= start_date,
            ExpenseHistory.transaction_date <= end_date,
            ExpenseHistory.merchant_name.isnot(None)  # Make sure merchant name exists
        ]
        
        # Get total amount for the period
        total_query = (
            select(func.sum(ExpenseHistory.total_amount))
            .where(and_(*query_filters))
        )
        result = await db.execute(total_query)
        total_amount = result.scalar_one_or_none() or Decimal("0.0")
        
        # Get total unique merchants
        merchant_count_query = (
            select(func.count(func.distinct(ExpenseHistory.merchant_name)))
            .where(and_(*query_filters))
        )
        result = await db.execute(merchant_count_query)
        total_merchants = result.scalar_one_or_none() or 0
        
        # Get top merchants by total amount
        top_merchants_query = (
            select(
                ExpenseHistory.merchant_name,
                func.sum(ExpenseHistory.total_amount).label('total_amount'),
                func.count().label('transaction_count')
            )
            .where(and_(*query_filters))
            .group_by(ExpenseHistory.merchant_name)
            .order_by(desc('total_amount'))
            .limit(limit)
        )
        
        result = await db.execute(top_merchants_query)
        top_merchant_records = result.all()
        
        # Process each top merchant
        top_merchants = []
        
        sys_cat_alias = aliased(Category)
        user_cat_alias = aliased(UserCategory)
        
        for merchant_name, total_amount, transaction_count in top_merchant_records:
            # Calculate percentage of total
            percentage = (total_amount / total_amount) * Decimal("100.0") if total_amount > 0 else Decimal("0.0")
            
            # Calculate average transaction
            avg_transaction = total_amount / transaction_count if transaction_count > 0 else Decimal("0.0")
            
            sub_categories_query = (
                select(
                    func.coalesce(sys_cat_alias.name, user_cat_alias.name, 'Uncategorized').label('category'),
                    ExpenseHistory.expense_id
                )
                .select_from(ExpenseHistory)
                .outerjoin(sys_cat_alias, sys_cat_alias.category_id == ExpenseHistory.category_id)
                .outerjoin(user_cat_alias, user_cat_alias.user_category_id == ExpenseHistory.user_category_id)
                .where(
                    and_(*query_filters, ExpenseHistory.merchant_name == merchant_name)
                )
                .subquery()
            )
            # Get categories used with this merchant
            categories_query = (
                select(
                    sub_categories_query.c.category.label('category_name'),
                    func.count().label('count')
                )
                .group_by(sub_categories_query.c.category)
                .order_by(desc('count'))
            )
            
            categories_result = await db.execute(categories_query)
            category_records = categories_result.all()
            
            categories = [
                CategoryUsageInfo(
                    name=category_name,
                    count=count
                )
                for category_name, count in category_records
            ]
            
            top_merchants.append(
                MerchantAnalysisItem(
                    merchant_name=merchant_name,
                    total_amount=total_amount,
                    percentage=percentage,
                    transaction_count=transaction_count,
                    avg_transaction=avg_transaction,
                    categories=categories
                )
            )
        
        return MerchantAnalysisResponse(
            start_date=start_date,
            end_date=end_date,
            total_merchants=total_merchants,
            top_merchants=top_merchants
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating merchant analysis: {str(e)}")
