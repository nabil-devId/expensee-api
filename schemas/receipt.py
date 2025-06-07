from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.receipt import ReceiptStatus
from schemas.category import CategoryResponse, UserCategoryResponse


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
class OCRResultItemResponse(BaseModel):
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


# OCR Confidence Schema
class OCRConfidenceBase(BaseModel):
    field_name: str
    confidence_score: Decimal


class OCRConfidenceCreate(OCRConfidenceBase):
    ocr_id: UUID


class OCRConfidenceInDB(OCRConfidenceBase):
    ocr_confidence_id: UUID
    ocr_id: UUID
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


# OCR Training Feedback Schema
class OCRFeedbackCorrection(BaseModel):
    field_name: str
    original_value: str
    corrected_value: str


class OCRFeedbackRequest(BaseModel):
    corrections: List[OCRFeedbackCorrection]


class OCRFeedbackResponse(BaseModel):
    status: str
    message: str
    feedback_id: UUID


class OCRResultResponse(OCRResultBase):
    ocr_id: UUID
    items: List[OCRResultItemResponse] = []
    image_url: str
    receipt_status: ReceiptStatus
    category: Optional[CategoryResponse] = None
    user_category: Optional[UserCategoryResponse] = None


# Accept OCR Results Request
class AcceptOCRRequest(BaseModel):
    merchant_name: Optional[str] = None
    total_amount: Optional[Decimal] = None
    transaction_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    category_id: Optional[UUID]
    user_category_id: Optional[UUID]
    items: List[OCRResultItemResponse]
    notes: Optional[str] = None


class AcceptOCRResponse(BaseModel):
    expense_id: UUID
    ocr_id: UUID
    message: str
    status: str

# Error Response Schema
class ErrorResponse(BaseModel):
    status: str = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class OCRResultCategory(BaseModel):
    category_id: UUID
    category_name: str
    is_user_category: bool