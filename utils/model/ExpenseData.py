from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class ExpenseData(BaseModel):
    merchant: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    total_amount: float
    items: Optional[List["ExpenseItem"]] = None
    receipt_text: str  # Original OCR text
    confidence: float  # Confidence score

class ExpenseItem(BaseModel):
    name: str
    quantity: Optional[float] = 1.0
    unit_price: float
    total_price: float