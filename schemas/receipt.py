from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.receipt import ProcessingStatus


# Shared properties
class ReceiptBase(BaseModel):
    merchant_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "IDR"
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None


# Properties to receive on receipt creation
class ReceiptCreate(ReceiptBase):
    pass


# Properties to receive on receipt update
class ReceiptUpdate(ReceiptBase):
    status: Optional[ProcessingStatus] = None
    extracted_data: Optional[Dict[str, Any]] = None
    categories: Optional[List[str]] = None


# Properties shared by models stored in DB
class ReceiptInDBBase(ReceiptBase):
    id: UUID
    user_id: UUID
    image_url: str
    original_filename: Optional[str]
    status: ProcessingStatus
    raw_text: Optional[str]
    extracted_data: Optional[Dict[str, Any]]
    categories: Optional[List[str]]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Properties to return to client
class Receipt(ReceiptInDBBase):
    pass


# Properties properties stored in DB
class ReceiptInDB(ReceiptInDBBase):
    pass


# Properties for image upload
class ReceiptImageUpload(BaseModel):
    filename: str