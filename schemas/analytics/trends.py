from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PeriodType(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class DataPoint(BaseModel):
    date: date
    total_amount: Decimal
    count: int


class AmountInfo(BaseModel):
    date: date
    amount: Decimal


class TrendResponse(BaseModel):
    period: PeriodType
    start_date: date
    end_date: date
    data_points: List[DataPoint]
    total_amount: Decimal
    average_per_period: Decimal
    max_amount: AmountInfo
    min_amount: AmountInfo
    trend_percentage: Decimal = Field(..., description="Positive or negative percentage change")


class CategoryInfo(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryDistributionItem(BaseModel):
    category: CategoryInfo
    amount: Decimal
    percentage: Decimal
    count: int


class CategoryDistributionResponse(BaseModel):
    start_date: date
    end_date: date
    total_amount: Decimal
    categories: List[CategoryDistributionItem]


class CategoryUsageInfo(BaseModel):
    name: str
    count: int


class MerchantAnalysisItem(BaseModel):
    merchant_name: str
    total_amount: Decimal
    percentage: Decimal
    transaction_count: int
    avg_transaction: Decimal
    categories: List[CategoryUsageInfo]


class MerchantAnalysisResponse(BaseModel):
    start_date: date
    end_date: date
    total_merchants: int
    top_merchants: List[MerchantAnalysisItem]
