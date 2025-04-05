from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.receipt import ReceiptStatus


# Receipt Upload Request and Response
class ReceiptUploadRequest(BaseModel):
    user_notes: Optional[str] = None


class ReceiptUploadResponse(BaseModel):
    ocr_id: UUID
    status: str
    message: str
    estimated_completion_time: Optional[int] = None  # in seconds


class ReceiptStatusResponse(BaseModel):
    ocr_id: UUID
    status: str
    message: str
    estimated_completion_time: Optional[int] = None  # in seconds if pending/processing


# OCR Result Item Schema
class OCRResultItem(BaseModel):
    name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

# OCR Result Schema
class OCRResultBase(BaseModel):
    merchant_name: Optional[str] = None
    total_amount: Optional[Decimal] = None
    transaction_date: Optional[datetime] = None
    payment_method: Optional[str] = None


class OCRResultCreate(OCRResultBase):
    user_id: UUID
    image_path: str
    receipt_status: ReceiptStatus = ReceiptStatus.PENDING
    raw_ocr_data: Optional[Dict[str, Any]] = None


class OCRResultUpdate(OCRResultBase):
    receipt_status: Optional[ReceiptStatus] = None
    raw_ocr_data: Optional[Dict[str, Any]] = None


class OCRResultInDB(OCRResultBase):
    ocr_id: UUID
    user_id: UUID
    image_path: str
    receipt_status: ReceiptStatus
    raw_ocr_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class OCRResultResponse(OCRResultBase):
    ocr_id: UUID
    items: List[OCRResultItem] = []
    confidence_score: Optional[Decimal] = None
    image_url: str
    receipt_status: ReceiptStatus


# Accept OCR Results Request
class AcceptOCRRequest(BaseModel):
    merchant_name: Optional[str] = None
    total_amount: Optional[Decimal] = None
    transaction_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    category_id: Optional[UUID]
    user_category_id: Optional[UUID]
    items: List[OCRResultItem]
    notes: Optional[str] = None


class AcceptOCRResponse(BaseModel):
    expense_id: UUID
    ocr_id: UUID
    message: str
    status: str


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
    category: str
    notes: Optional[str] = None


class ExpenseHistoryCreate(ExpenseHistoryBase):
    user_id: UUID
    ocr_id: Optional[UUID] = None
    is_manual_entry: bool = False


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


# Error Response Schema
class ErrorResponse(BaseModel):
    status: str = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None