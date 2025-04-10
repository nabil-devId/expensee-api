import os
import uuid
import tempfile
import calendar
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import func, desc, and_, or_, between, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.expense_history import ExpenseHistory
from app.models.category import Category, UserCategory
from app.models.budget import Budget

from schemas.reports.monthly import (
    MonthlyReport, MonthlyPeriod, MonthlySummary, LargestExpense,
    CategoryBreakdown, CategoryBasicInfo, CategoryBudgetInfo, BudgetStatus,
    DailyExpense, RecurringExpense, ComparativeAnalysis, ComparativePeriod
)
from schemas.reports.custom import (
    CustomReportRequest, CustomReport, ReportParameters, ReportSummary,
    GroupedData, DetailedExpense, GroupByType, ExportFormat
)

router = APIRouter()


def get_month_name(month: int) -> str:
    """Return the full month name for a given month number."""
    return calendar.month_name[month]


def calculate_date_range(year: int, month: int) -> Tuple[date, date]:
    """Calculate start and end date for a given year and month."""
    start_date = date(year, month, 1)
    
    # Get the last day of the month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    
    end_date = next_month - timedelta(days=1)
    
    return start_date, end_date


async def get_recurring_expenses(
    db: AsyncSession, 
    user_id: uuid.UUID,
    start_date: date,
    end_date: date
) -> List[RecurringExpense]:
    """
    Identify recurring expenses based on merchant name and similar amounts.
    """
    # First, get merchants that appear multiple times
    merchant_frequency_query = (
        select(
            ExpenseHistory.merchant_name,
            func.count().label('freq')
        )
        .where(
            ExpenseHistory.user_id == user_id,
            ExpenseHistory.merchant_name.isnot(None)
        )
        .group_by(ExpenseHistory.merchant_name)
        .having(func.count() >= 2)  # At least appeared twice
    )
    
    result = await db.execute(merchant_frequency_query)
    frequent_merchants = result.all()
    
    recurring_expenses = []
    
    for merchant_name, _ in frequent_merchants:
        # For each frequent merchant, check if amounts are similar
        merchant_expenses_query = (
            select(
                ExpenseHistory.transaction_date,
                ExpenseHistory.total_amount,
                func.coalesce(Category.name, UserCategory.name, 'Uncategorized').label('category_name')
            )
            .outerjoin(Category, ExpenseHistory.category_id == Category.category_id)
            .outerjoin(UserCategory, ExpenseHistory.user_category_id == UserCategory.user_category_id)
            .where(
                ExpenseHistory.user_id == user_id,
                ExpenseHistory.merchant_name == merchant_name
            )
            .order_by(ExpenseHistory.transaction_date)
        )
        
        result = await db.execute(merchant_expenses_query)
        merchant_expenses = result.all()
        
        # Group by similar amounts (within 10%)
        amount_groups = {}
        
        for exp_date, amount, category in merchant_expenses:
            matched = False
            
            for group_amount in list(amount_groups.keys()):
                # If amount is within 10% of a group amount, add it to that group
                if abs(amount - group_amount) / group_amount <= 0.1:
                    amount_groups[group_amount].append((exp_date, amount, category))
                    matched = True
                    break
            
            if not matched:
                # Create a new group
                amount_groups[amount] = [(exp_date, amount, category)]
        
        # Find groups with recurring patterns
        for group_amount, expenses in amount_groups.items():
            if len(expenses) < 2:
                continue
            
            # Check for recurring pattern
            dates = [exp[0] for exp in expenses]
            if len(dates) >= 2:
                # Calculate average days between transactions
                days_between = []
                for i in range(1, len(dates)):
                    delta = (dates[i] - dates[i-1]).days
                    days_between.append(delta)
                
                avg_days = sum(days_between) / len(days_between)
                
                # Determine frequency based on average days between
                frequency = "Unknown"
                if 25 <= avg_days <= 35:
                    frequency = "Monthly"
                elif 13 <= avg_days <= 16:
                    frequency = "Bi-weekly"
                elif 6 <= avg_days <= 8:
                    frequency = "Weekly"
                
                # Only include if we have a recognizable frequency and the expense appears in our period
                last_date = dates[-1]
                if frequency != "Unknown" and start_date <= last_date <= end_date:
                    # Use the most common category
                    categories = [exp[2] for exp in expenses]
                    category_counts = {}
                    for cat in categories:
                        category_counts[cat] = category_counts.get(cat, 0) + 1
                    
                    most_common_category = max(category_counts.items(), key=lambda x: x[1])[0]
                    
                    recurring_expenses.append(
                        RecurringExpense(
                            merchant_name=merchant_name,
                            amount=group_amount,
                            category=most_common_category,
                            last_date=last_date,
                            frequency=frequency
                        )
                    )
    
    return recurring_expenses


@router.get("/monthly")
async def generate_monthly_report(
    year: Optional[int] = Query(None, description="Year for the report"),
    month: Optional[int] = Query(None, description="Month for the report (1-12)"),
    format: str = Query("json", description="Format of the report (json or pdf)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a monthly expense report.
    """
    try:
        # Set default year and month if not provided
        today = date.today()
        if not year:
            year = today.year
        if not month:
            month = today.month
        
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Calculate date range for the month
        start_date, end_date = calculate_date_range(year, month)
        
        # Create period label
        month_name = get_month_name(month)
        period_label = f"{month_name} {year}"
        
        # Query base filters
        query_filters = [
            ExpenseHistory.user_id == current_user.user_id,
            ExpenseHistory.transaction_date >= start_date,
            ExpenseHistory.transaction_date <= end_date
        ]
        
        # 1. Get summary information
        summary_query = (
            select(
                func.sum(ExpenseHistory.total_amount).label('total'),
                func.count().label('count'),
                func.avg(ExpenseHistory.total_amount).label('avg'),
                func.max(ExpenseHistory.total_amount).label('max')
            )
            .where(and_(*query_filters))
        )
        
        result = await db.execute(summary_query)
        total, count, avg, max_amount = result.one()
        
        # Default values if no data
        total = total or Decimal("0.0")
        count = count or 0
        avg = avg or Decimal("0.0")
        
        # 2. Get largest expense
        largest_expense_query = (
            select(
                ExpenseHistory.total_amount,
                ExpenseHistory.merchant_name,
                ExpenseHistory.transaction_date
            )
            .where(and_(*query_filters))
            .order_by(desc(ExpenseHistory.total_amount))
            .limit(1)
        )
        
        result = await db.execute(largest_expense_query)
        largest_expense_record = result.first()
        
        largest_expense = None
        if largest_expense_record:
            amount, merchant, exp_date = largest_expense_record
            largest_expense = LargestExpense(
                amount=amount,
                merchant_name=merchant or "Unknown",
                date=exp_date
            )
        else:
            largest_expense = LargestExpense(
                amount=Decimal("0.0"),
                merchant_name="N/A",
                date=start_date
            )
        
        # Create summary
        summary = MonthlySummary(
            total_expenses=total,
            total_transactions=count,
            avg_transaction=round(avg, 2),
            largest_expense=largest_expense
        )
        
        # 3. Get category breakdown
        sys_cat_alias = aliased(Category)
        user_cat_alias = aliased(UserCategory)
        
        # Create aliased expressions for reuse in both SELECT and GROUP BY
        cat_id_expr = func.coalesce(sys_cat_alias.category_id, user_cat_alias.user_category_id).label('cat_id')
        name_expr = func.coalesce(sys_cat_alias.name, user_cat_alias.name, 'Uncategorized').label('name')
        icon_expr = func.coalesce(sys_cat_alias.icon, user_cat_alias.icon, 'default_icon').label('icon')
        color_expr = func.coalesce(sys_cat_alias.color, user_cat_alias.color, '#CCCCCC').label('color')
        
        # Fixed case statement - updated to use the new syntax
        is_system_category_case = case(
            (ExpenseHistory.category_id.isnot(None), True),
            else_=False
        ).label('is_system_category')
        
        # Create a subquery to handle the GROUP BY operations
        subquery = (
            select(
                cat_id_expr,
                name_expr,
                icon_expr,
                color_expr,
                func.sum(ExpenseHistory.total_amount).label('amount'),
                is_system_category_case
            )
            .select_from(ExpenseHistory)
            .outerjoin(sys_cat_alias, ExpenseHistory.category_id == sys_cat_alias.category_id)
            .outerjoin(user_cat_alias, ExpenseHistory.user_category_id == user_cat_alias.user_category_id)
            .where(and_(*query_filters))
            .group_by(
                cat_id_expr,
                name_expr,
                icon_expr,
                color_expr,
                is_system_category_case
            )
            .alias('category_summary')
        )
        
        # Final query
        category_query = (
            select(subquery)
            .order_by(desc('amount'))
        )
        
        result = await db.execute(category_query)
        category_records = result.all()
        
        # 4. Get budgets for the categories
        budget_map = {}
        
        # Get all budgets active for this period
        budget_query = (
            select(Budget)
            .where(
                Budget.user_id == current_user.user_id,
                or_(
                    and_(
                        Budget.start_date <= start_date,
                        or_(
                            Budget.end_date.is_(None),
                            Budget.end_date >= start_date
                        )
                    ),
                    and_(
                        Budget.start_date <= end_date,
                        or_(
                            Budget.end_date.is_(None),
                            Budget.end_date >= end_date
                        )
                    )
                )
            )
        )
        
        result = await db.execute(budget_query)
        budgets = result.scalars().all()
        
        # Build a map of category ID to budget
        for budget in budgets:
            if budget.category_id:
                budget_map[str(budget.category_id)] = budget
            elif budget.user_category_id:
                budget_map[str(budget.user_category_id)] = budget
        
        # Build category breakdown
        category_breakdown = []
        for cat_id, name, icon, color, amount, is_system in category_records:
            # Skip null category ID (happens with uncategorized expenses)
            if cat_id is None:
                cat_id = 'uncategorized'
                
            # Calculate percentage of total
            percentage = (amount / total) * Decimal("100.0") if total > 0 else Decimal("0.0")
            
            # Check if there's a budget for this category
            budget_info = None
            if str(cat_id) in budget_map:
                budget = budget_map[str(cat_id)]
                budget_amount = budget.amount
                remaining = budget_amount - amount
                
                budget_info = CategoryBudgetInfo(
                    amount=budget_amount,
                    remaining=remaining,
                    status=BudgetStatus.UNDER_BUDGET if remaining >= 0 else BudgetStatus.OVER_BUDGET
                )
            
            category_breakdown.append(
                CategoryBreakdown(
                    category=CategoryBasicInfo(
                        name=name,
                        icon=icon,
                        color=color
                    ),
                    amount=amount,
                    percentage=round(percentage, 2),
                    budget=budget_info
                )
            )
        
        # 5. Get daily expenses
        daily_query = (
            select(
                ExpenseHistory.transaction_date,
                func.sum(ExpenseHistory.total_amount).label('amount'),
                func.count().label('count')
            )
            .where(and_(*query_filters))
            .group_by(ExpenseHistory.transaction_date)
            .order_by(ExpenseHistory.transaction_date)
        )
        
        result = await db.execute(daily_query)
        daily_records = result.all()
        
        daily_expenses = [
            DailyExpense(
                date=day,
                amount=amount,
                transaction_count=count
            )
            for day, amount, count in daily_records
        ]
        
        # 6. Get recurring expenses
        recurring_expenses = await get_recurring_expenses(db, current_user.user_id, start_date, end_date)
        
        # 7. Calculate comparative analysis
        
        # Previous month
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year = year - 1
            
        prev_start, prev_end = calculate_date_range(prev_year, prev_month)
        
        prev_query = (
            select(func.sum(ExpenseHistory.total_amount))
            .where(
                ExpenseHistory.user_id == current_user.user_id,
                ExpenseHistory.transaction_date >= prev_start,
                ExpenseHistory.transaction_date <= prev_end
            )
        )
        
        result = await db.execute(prev_query)
        prev_amount = result.scalar_one_or_none() or Decimal("0.0")
        
        # Calculate percentage change
        prev_change = Decimal("0.0")
        if prev_amount > 0:
            prev_change = ((total - prev_amount) / prev_amount) * Decimal("100.0")
        
        # Year ago
        year_ago_year = year - 1
        year_ago_start, year_ago_end = calculate_date_range(year_ago_year, month)
        
        year_ago_query = (
            select(func.sum(ExpenseHistory.total_amount))
            .where(
                ExpenseHistory.user_id == current_user.user_id,
                ExpenseHistory.transaction_date >= year_ago_start,
                ExpenseHistory.transaction_date <= year_ago_end
            )
        )
        
        result = await db.execute(year_ago_query)
        year_ago_amount = result.scalar_one_or_none() or Decimal("0.0")
        
        # Calculate percentage change
        year_ago_change = Decimal("0.0")
        if year_ago_amount > 0:
            year_ago_change = ((total - year_ago_amount) / year_ago_amount) * Decimal("100.0")
        
        # Create comparative analysis
        comparative_analysis = ComparativeAnalysis(
            previous_period=ComparativePeriod(
                amount=prev_amount,
                change_percentage=prev_change
            ),
            year_ago_period=ComparativePeriod(
                amount=year_ago_amount,
                change_percentage=year_ago_change
            ) if year_ago_amount > 0 else None
        )
        
        # Assemble the complete report
        report = MonthlyReport(
            period=MonthlyPeriod(
                year=year,
                month=month,
                label=period_label
            ),
            summary=summary,
            category_breakdown=category_breakdown,
            daily_expenses=daily_expenses,
            recurring_expenses=recurring_expenses,
            comparative_analysis=comparative_analysis
        )
        
        # Return based on requested format
        if format.lower() == "json":
            return report
        elif format.lower() == "pdf":
            # In a real implementation, we would generate a PDF here
            # For now, we'll just return a placeholder
            return Response(
                content="PDF generation not implemented in this version",
                media_type="text/plain"
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Supported formats: json, pdf")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating monthly report: {str(e)}")


@router.post("/custom")
async def generate_custom_report(
    report_params: CustomReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a custom expense report based on specified parameters.
    """
    try:
        # Build query filters based on parameters
        query_filters = [
            ExpenseHistory.user_id == current_user.user_id,
            ExpenseHistory.transaction_date >= report_params.start_date,
            ExpenseHistory.transaction_date <= report_params.end_date
        ]
        
        # Add optional filters
        if report_params.include_categories:
            # Filter for either system or user categories
            category_filter = []
            for cat_id in report_params.include_categories:
                category_filter.append(ExpenseHistory.category_id == cat_id)
                category_filter.append(ExpenseHistory.user_category_id == cat_id)
            
            if category_filter:
                query_filters.append(or_(*category_filter))
        
        if report_params.include_merchants:
            merchant_filter = []
            for merchant in report_params.include_merchants:
                merchant_filter.append(ExpenseHistory.merchant_name.ilike(f"%{merchant}%"))
            
            if merchant_filter:
                query_filters.append(or_(*merchant_filter))
        
        if report_params.min_amount is not None:
            query_filters.append(ExpenseHistory.total_amount >= report_params.min_amount)
        
        if report_params.max_amount is not None:
            query_filters.append(ExpenseHistory.total_amount <= report_params.max_amount)
        
        if report_params.payment_methods:
            payment_method_filter = []
            for method in report_params.payment_methods:
                payment_method_filter.append(ExpenseHistory.payment_method.ilike(f"%{method}%"))
            
            if payment_method_filter:
                query_filters.append(or_(*payment_method_filter))
        
        # 1. Get summary information
        summary_query = (
            select(
                func.sum(ExpenseHistory.total_amount).label('total'),
                func.count().label('count'),
                func.avg(ExpenseHistory.total_amount).label('avg')
            )
            .where(and_(*query_filters))
        )
        
        result = await db.execute(summary_query)
        total, count, avg = result.one()
        
        # Default values if no data
        total = total or Decimal("0.0")
        count = count or 0
        avg = avg or Decimal("0.0")
        
        # Calculate days in period
        days_in_period = (report_params.end_date - report_params.start_date).days + 1
        avg_daily = total / days_in_period if days_in_period > 0 else Decimal("0.0")
        
        # 2. Get grouped data based on the group_by parameter
        grouped_data = []
        
        if report_params.group_by:
            if report_params.group_by == GroupByType.DAY:
                # Group by day
                group_query = (
                    select(
                        ExpenseHistory.transaction_date.label('group_key'),
                        func.sum(ExpenseHistory.total_amount).label('amount'),
                        func.count().label('count')
                    )
                    .where(and_(*query_filters))
                    .group_by(ExpenseHistory.transaction_date)
                    .order_by(ExpenseHistory.transaction_date)
                )
                
                result = await db.execute(group_query)
                group_records = result.all()
                
                for date_val, amount, count in group_records:
                    percentage = (amount / total) * Decimal("100.0") if total > 0 else Decimal("0.0")
                    grouped_data.append(
                        GroupedData(
                            group_key=date_val.isoformat(),
                            total_amount=amount,
                            transaction_count=count,
                            percentage=percentage
                        )
                    )
                
            elif report_params.group_by == GroupByType.WEEK:
                # Group by week
                group_query = (
                    select(
                        func.date_trunc('week', ExpenseHistory.transaction_date).label('week_start'),
                        func.sum(ExpenseHistory.total_amount).label('amount'),
                        func.count().label('count')
                    )
                    .where(and_(*query_filters))
                    .group_by(func.date_trunc('week', ExpenseHistory.transaction_date))
                    .order_by(func.date_trunc('week', ExpenseHistory.transaction_date))
                )
                
                result = await db.execute(group_query)
                group_records = result.all()
                
                for week_start, amount, count in group_records:
                    week_start_date = week_start.date()
                    week_end_date = week_start_date + timedelta(days=6)
                    percentage = (amount / total) * Decimal("100.0") if total > 0 else Decimal("0.0")
                    
                    grouped_data.append(
                        GroupedData(
                            group_key=f"{week_start_date.isoformat()} to {week_end_date.isoformat()}",
                            total_amount=amount,
                            transaction_count=count,
                            percentage=percentage
                        )
                    )
                
            elif report_params.group_by == GroupByType.MONTH:
                # Group by month
                group_query = (
                    select(
                        func.date_trunc('month', ExpenseHistory.transaction_date).label('month_start'),
                        func.sum(ExpenseHistory.total_amount).label('amount'),
                        func.count().label('count')
                    )
                    .where(and_(*query_filters))
                    .group_by(func.date_trunc('month', ExpenseHistory.transaction_date))
                    .order_by(func.date_trunc('month', ExpenseHistory.transaction_date))
                )
                
                result = await db.execute(group_query)
                group_records = result.all()
                
                for month_start, amount, count in group_records:
                    month_start_date = month_start.date()
                    month_name = month_start_date.strftime("%B %Y")
                    percentage = (amount / total) * Decimal("100.0") if total > 0 else Decimal("0.0")
                    
                    grouped_data.append(
                        GroupedData(
                            group_key=month_name,
                            total_amount=amount,
                            transaction_count=count,
                            percentage=percentage
                        )
                    )
                
            elif report_params.group_by == GroupByType.CATEGORY:
                # Group by category
                sys_cat_alias = aliased(Category)
                user_cat_alias = aliased(UserCategory)
                
                group_query = (
                    select(
                        func.coalesce(sys_cat_alias.name, user_cat_alias.name, 'Uncategorized').label('category_name'),
                        func.sum(ExpenseHistory.total_amount).label('amount'),
                        func.count().label('count')
                    )
                    .select_from(ExpenseHistory)
                    .outerjoin(sys_cat_alias, ExpenseHistory.category_id == sys_cat_alias.category_id)
                    .outerjoin(user_cat_alias, ExpenseHistory.user_category_id == user_cat_alias.user_category_id)
                    .where(and_(*query_filters))
                    .group_by(func.coalesce(sys_cat_alias.name, user_cat_alias.name, 'Uncategorized'))
                    .order_by(desc('amount'))
                )
                
                result = await db.execute(group_query)
                group_records = result.all()
                
                for category_name, amount, count in group_records:
                    percentage = (amount / total) * Decimal("100.0") if total > 0 else Decimal("0.0")
                    
                    grouped_data.append(
                        GroupedData(
                            group_key=category_name,
                            total_amount=amount,
                            transaction_count=count,
                            percentage=percentage
                        )
                    )
                
            elif report_params.group_by == GroupByType.MERCHANT:
                # Group by merchant
                group_query = (
                    select(
                        ExpenseHistory.merchant_name,
                        func.sum(ExpenseHistory.total_amount).label('amount'),
                        func.count().label('count')
                    )
                    .where(and_(*query_filters))
                    .group_by(ExpenseHistory.merchant_name)
                    .order_by(desc('amount'))
                )
                
                result = await db.execute(group_query)
                group_records = result.all()
                
                for merchant_name, amount, count in group_records:
                    percentage = (amount / total) * Decimal("100.0") if total > 0 else Decimal("0.0")
                    
                    grouped_data.append(
                        GroupedData(
                            group_key=merchant_name or "Unknown",
                            total_amount=amount,
                            transaction_count=count,
                            percentage=percentage
                        )
                    )
        
        # 3. Get detailed expenses
        detailed_query = (
            select(
                ExpenseHistory.expense_id,
                ExpenseHistory.transaction_date,
                ExpenseHistory.merchant_name,
                func.coalesce(Category.name, UserCategory.name, 'Uncategorized').label('category_name'),
                ExpenseHistory.total_amount,
                ExpenseHistory.payment_method
            )
            .outerjoin(Category, ExpenseHistory.category_id == Category.category_id)
            .outerjoin(UserCategory, ExpenseHistory.user_category_id == UserCategory.user_category_id)
            .where(and_(*query_filters))
            .order_by(ExpenseHistory.transaction_date.desc())
        )
        
        result = await db.execute(detailed_query)
        expense_records = result.all()
        
        detailed_expenses = [
            DetailedExpense(
                expense_id=expense_id,
                date=transaction_date,
                merchant_name=merchant_name or "Unknown",
                category=category_name,
                amount=amount,
                payment_method=payment_method or "Unknown"
            )
            for expense_id, transaction_date, merchant_name, category_name, amount, payment_method in expense_records
        ]
        
        # Create the report
        report = CustomReport(
            report_id=uuid.uuid4(),
            parameters=ReportParameters(
                start_date=report_params.start_date,
                end_date=report_params.end_date,
                include_categories=report_params.include_categories,
                include_merchants=report_params.include_merchants,
                min_amount=report_params.min_amount,
                max_amount=report_params.max_amount,
                payment_methods=report_params.payment_methods,
                group_by=report_params.group_by
            ),
            summary=ReportSummary(
                total_expenses=total,
                total_transactions=count,
                avg_transaction=round(avg, 2),
                period_days=days_in_period,
                avg_daily_expense=avg_daily
            ),
            grouped_data=grouped_data,
            detailed_expenses=detailed_expenses
        )
        
        # Handle different formats
        if report_params.format == ExportFormat.JSON:
            return report
        
        elif report_params.format == ExportFormat.CSV:
            # Create a DataFrame for the detailed expenses
            expense_data = []
            for expense in detailed_expenses:
                expense_data.append({
                    "Date": expense.date,
                    "Merchant": expense.merchant_name,
                    "Category": expense.category,
                    "Amount": float(expense.amount),
                    "Payment Method": expense.payment_method
                })
            
            df = pd.DataFrame(expense_data)
            
            # Create a CSV in memory
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            # Generate a filename
            filename = f"custom_report_{report_params.start_date}_{report_params.end_date}.csv"
            
            return Response(
                content=csv_buffer.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
        elif report_params.format == ExportFormat.PDF:
            # In a real implementation, we would generate a PDF here
            # For this version, we'll just return a placeholder
            return Response(
                content="PDF generation not implemented in this version",
                media_type="text/plain"
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Supported formats: json, pdf, csv")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating custom report: {str(e)}")
