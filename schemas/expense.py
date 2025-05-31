from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from decimal import Decimal



# Expense Item Schema
class ExpenseItemBase(BaseModel):
    name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class ExpenseItemCreate(ExpenseItemBase):
    ocr_id: UUID


class ExpenseItemInDB(ExpenseItemBase):
    item_id: UUID
    ocr_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
        
# Expense History Schema
class ExpenseHistoryBase(BaseModel):
    merchant_name: str
    total_amount: Decimal
    transaction_date: datetime
    payment_method: Optional[str] = None
    category_id: Optional[UUID] = None
    user_category_id: Optional[UUID] = None
    notes: Optional[str] = None


class ExpenseHistoryCreate(ExpenseHistoryBase):
    is_manual_entry: bool = True


class ExpenseHistoryInDB(ExpenseHistoryBase):
    expense_id: UUID
    user_id: UUID
    ocr_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    is_manual_entry: bool

    class Config:
        orm_mode = True
        from_attributes = True


class ExpenseHistoryResponse(ExpenseHistoryBase):
    expense_id: UUID
    has_receipt_image: bool
    created_at: datetime


class ExpenseHistoryDetails(ExpenseHistoryBase):
    expense_id: UUID
    ocr_id: Optional[UUID] = None
    receipt_image_url: Optional[str] = None
    items: List[ExpenseItemBase] = []
    created_at: datetime
    updated_at: datetime
    is_manual_entry: bool


class ExpenseSummary(BaseModel):
    total_expenses: Decimal
    avg_expense: Decimal
    max_expense: Decimal
    min_expense: Decimal
    expense_by_category: Dict[str, Decimal]


class PaginationInfo(BaseModel):
    total_count: int
    page: int
    limit: int
    total_pages: int


class ExpenseHistoryListResponse(BaseModel):
    expenses: List[ExpenseHistoryResponse]
    pagination: PaginationInfo
    summary: ExpenseSummary
