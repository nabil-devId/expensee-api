from typing import List, Optional, Union
from pydantic import BaseModel, Field, UUID4, condecimal
from datetime import date, datetime
from enum import Enum


class BudgetPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class BudgetStatus(str, Enum):
    UNDER_BUDGET = "under_budget"
    APPROACHING_LIMIT = "approaching_limit"
    OVER_BUDGET = "over_budget"


class CategoryInfo(BaseModel):
    id: UUID4
    name: str
    icon: str
    color: str
    is_custom: bool


class BudgetBase(BaseModel):
    amount: condecimal(ge=0, decimal_places=2)
    period: BudgetPeriod
    start_date: date
    end_date: Optional[date] = None


class BudgetCreate(BudgetBase):
    category_id: Optional[UUID4] = None
    user_category_id: Optional[UUID4] = None


class BudgetUpdate(BudgetBase):
    pass


class BudgetResponse(BudgetBase):
    budget_id: UUID4
    category: Optional[CategoryInfo] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetUpdateResponse(BudgetResponse):
    updated_at: datetime


class BudgetWithSpending(BudgetResponse):
    current_spending: condecimal(decimal_places=2)
    remaining: condecimal(decimal_places=2)
    percentage_used: condecimal(decimal_places=2)


class OverallBudget(BaseModel):
    budget_id: Optional[UUID4] = None
    amount: condecimal(ge=0, decimal_places=2)
    current_spending: condecimal(decimal_places=2)
    remaining: condecimal(decimal_places=2)
    percentage_used: condecimal(decimal_places=2)


class BudgetListResponse(BaseModel):
    budgets: List[BudgetWithSpending]
    overall_budget: Optional[OverallBudget] = None


class CategoryBudgetProgress(BaseModel):
    category: CategoryInfo
    budget_amount: condecimal(decimal_places=2)
    current_spending: condecimal(decimal_places=2)
    remaining: condecimal(decimal_places=2)
    percentage_used: condecimal(decimal_places=2)
    status: BudgetStatus


class BudgetProgressResponse(BaseModel):
    period_start: date
    period_end: date
    overall_budget: OverallBudget
    categories: List[CategoryBudgetProgress]


class BudgetDeleteResponse(BaseModel):
    status: str = "success"
    message: str = "Budget deleted successfully"
