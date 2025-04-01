from typing import Any, Dict, List
from utils.aws import fetch_image_from_s3, process_receipt_with_textract, upload_image_to_s3

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies import get_current_active_superuser, get_current_active_user
from app.core.db import get_db
from app.core.security import get_password_hash
from app.models.user import User
from schemas.user import User as UserSchema
from schemas.user import UserCreate, UserUpdate

router = APIRouter()


# change response model to void
@router.post("/upload", response_model=Dict[str, Any]) 
async def upload_receipt(
    file: UploadFile = File(...),
    # current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    
    file_content = await file.read()
    s3_url = await upload_image_to_s3(file_content, file.filename)

    image_bytes = await fetch_image_from_s3(s3_url)

    # Textract AWS
    # receipt = await process_receipt_with_textract(s3_url)
    
    # return receipt


