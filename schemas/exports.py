from enum import Enum
from pydantic import BaseModel


class ExportFormat(str, Enum):
    CSV = "csv"
    PDF = "pdf"
    XLSX = "xlsx"


class ExportResponse(BaseModel):
    filename: str
    url: str
    mime_type: str
    size: int
