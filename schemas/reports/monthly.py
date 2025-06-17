from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class MonthlyPeriod(BaseModel):
    year: int
    month: int
    label: str  # e.g., "April 2025"


class LargestExpense(BaseModel):
    amount: Decimal
    merchant_name: str
    date: datetime


class MonthlySummary(BaseModel):
    total_expenses: Decimal
    total_transactions: int
    avg_transaction: Decimal
    largest_expense: LargestExpense


class BudgetStatus(str, Enum):
    UNDER_BUDGET = "under_budget"
    OVER_BUDGET = "over_budget"


class CategoryBudgetInfo(BaseModel):
    amount: Decimal
    remaining: Decimal
    status: BudgetStatus


class CategoryBasicInfo(BaseModel):
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryBreakdown(BaseModel):
    category: CategoryBasicInfo
    amount: Decimal
    percentage: Decimal
    budget: Optional[CategoryBudgetInfo] = None


class DailyExpense(BaseModel):
    date: datetime
    amount: Decimal
    transaction_count: int


class RecurringExpense(BaseModel):
    merchant_name: str
    amount: Decimal
    category: str
    last_date: date
    frequency: str  # e.g., "Monthly", "Bi-weekly"


class ComparativePeriod(BaseModel):
    amount: Decimal
    change_percentage: Decimal


class ComparativeAnalysis(BaseModel):
    previous_period: ComparativePeriod
    year_ago_period: Optional[ComparativePeriod] = None


class MonthlyReport(BaseModel):
    period: MonthlyPeriod
    summary: MonthlySummary
    category_breakdown: List[CategoryBreakdown]
    daily_expenses: List[DailyExpense]
    recurring_expenses: List[RecurringExpense]
    comparative_analysis: ComparativeAnalysis
