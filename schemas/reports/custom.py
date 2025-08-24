from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class GroupByType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    CATEGORY = "category"
    MERCHANT = "merchant"


class ExportFormat(str, Enum):
    JSON = "json"
    PDF = "pdf"
    CSV = "csv"


class CustomReportRequest(BaseModel):
    start_date: date
    end_date: date
    include_categories: Optional[List[UUID]] = None
    include_merchants: Optional[List[str]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    payment_methods: Optional[List[str]] = None
    format: ExportFormat = ExportFormat.JSON
    group_by: Optional[GroupByType] = None


class ReportParameters(BaseModel):
    start_date: date
    end_date: date
    include_categories: Optional[List[UUID]] = None
    include_merchants: Optional[List[str]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    payment_methods: Optional[List[str]] = None
    group_by: Optional[GroupByType] = None


class ReportSummary(BaseModel):
    total_expenses: Decimal
    total_transactions: int
    avg_transaction: Decimal
    period_days: int
    avg_daily_expense: Decimal


class GroupedData(BaseModel):
    group_key: str  # Date, category name, or merchant name based on group_by
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal


class DetailedExpense(BaseModel):
    expense_id: UUID
    date: date
    merchant_name: str
    category: str
    amount: Decimal
    payment_method: str


class CustomReport(BaseModel):
    report_id: UUID
    parameters: ReportParameters
    summary: ReportSummary
    grouped_data: List[GroupedData]
    detailed_expenses: List[DetailedExpense]
