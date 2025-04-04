import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from utils.aws import process_receipt_with_textract, upload_image_to_s3

# Set up logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.receipt import OCRResult, ReceiptStatus
from app.models.expense_history import ExpenseHistory
from app.models.expense_item import ExpenseItem

from schemas.receipt import (
    ReceiptUploadRequest, ReceiptUploadResponse, ReceiptStatusResponse,
    OCRResultCreate, OCRResultResponse, OCRResultItem, OCRResultInDB,
    AcceptOCRRequest, AcceptOCRResponse, ExpenseHistoryCreate,
    ExpenseItemCreate, ExpenseHistoryResponse, ExpenseHistoryDetails,
    ExpenseHistoryListResponse, PaginationInfo, ExpenseSummary, ErrorResponse
)

router = APIRouter()


@router.post("/upload", response_model=ReceiptUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_receipt(
    file: UploadFile = File(...),
    user_notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ReceiptUploadResponse:
    """Upload a receipt image for OCR processing"""
    try:
        # 1. Validate file format
        allowed_extensions = [".jpg", ".jpeg", ".png", ".pdf"]
        file_ext = file.filename.lower()[file.filename.rfind("."):] if "." in file.filename else ""
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "validation_error",
                    "message": f"Invalid file format. Allowed formats: {', '.join(allowed_extensions)}"
                }
            )
        
        # 2. Process the file
        file_content = await file.read()
        s3_url = await upload_image_to_s3(file_content, file.filename)
        
        # 3. Create entry in ocr_results table
        ocr_id = uuid.uuid4()
        ocr_result = OCRResult(
            ocr_id=ocr_id,
            user_id=current_user.user_id,
            image_path=s3_url,
            receipt_status=ReceiptStatus.PENDING,
        )
        
        db.add(ocr_result)
        await db.commit()
        await db.refresh(ocr_result)
        
        # 4. Trigger OCR processing job (asynchronous)
        # Note: In a real implementation, this would be a background task or queue job
        # For now, we'll implement a simple synchronous processing to simulate the flow
        try:
            # Process the receipt (this would typically be done asynchronously)
            ocr_data = await process_receipt_with_textract(s3_url)
            
            # Update the OCR result with the processed data
            ocr_result.merchant_name = ocr_data.get('merchant_name')
            ocr_result.total_amount = ocr_data.get('total_amount')
            ocr_result.transaction_date = datetime.strptime(ocr_data.get('transaction_date'), '%Y-%m-%d') if ocr_data.get('transaction_date') else None
            ocr_result.payment_method = ocr_data.get('payment_method')
            ocr_result.raw_ocr_data = ocr_data.get('raw_response')
            ocr_result.receipt_status = ReceiptStatus.PROCESSED
            
            # Save the updates
            await db.commit()
            await db.refresh(ocr_result)
            
            # Create expense items based on the OCR result
            if ocr_data.get('items'):
                for item_data in ocr_data.get('items'):
                    expense_item = ExpenseItem(
                        ocr_id=ocr_id,
                        name=item_data.get('name', 'Unknown Item'),
                        quantity=item_data.get('quantity', 1),
                        unit_price=item_data.get('price', 0),
                        total_price=item_data.get('total', item_data.get('price', 0) * item_data.get('quantity', 1))
                    )
                    db.add(expense_item)
                
                await db.commit()
        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            # Don't fail the request if OCR processing fails - the user can still get their receipt ID
        
        # Return the appropriate response based on the OCR processing status
        if ocr_result.receipt_status == ReceiptStatus.PROCESSED:
            return ReceiptUploadResponse(
                ocr_id=ocr_id,
                status="complete",
                message="Receipt processed successfully",
                estimated_completion_time=None
            )
        else:
            return ReceiptUploadResponse(
                ocr_id=ocr_id,
                status="pending",
                message="Receipt uploaded and queued for processing",
                estimated_completion_time=30  # Mock estimate
            )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error processing receipt",
                "details": {"error": str(e)}
            }
        )


@router.get("/{ocr_id}/status", response_model=ReceiptStatusResponse)
async def get_receipt_status(
    ocr_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ReceiptStatusResponse:
    """Get the processing status of a receipt OCR job"""
    try:
        # Get OCR result record
        query = select(OCRResult).where(
            OCRResult.ocr_id == ocr_id,
            OCRResult.user_id == current_user.user_id
        )
        result = await db.execute(query)
        ocr_result = result.scalars().first()
        
        if not ocr_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "error_code": "resource_not_found",
                    "message": "Receipt not found"
                }
            )
        
        # Return status info
        status_response = ReceiptStatusResponse(
            ocr_id=ocr_result.ocr_id,
            status=ocr_result.receipt_status.value,
            message=f"Receipt is {ocr_result.receipt_status.value}",
        )
        
        # Add estimated time if still processing
        if ocr_result.receipt_status in [ReceiptStatus.PENDING, ReceiptStatus.PROCESSED]:
            status_response.estimated_completion_time = 15  # Mock estimate
            
        return status_response
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error retrieving receipt status",
                "details": {"error": str(e)}
            }
        )


@router.get("/{ocr_id}", response_model=OCRResultResponse)
async def get_receipt_ocr_results(
    ocr_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> OCRResultResponse:
    """Get the OCR results for a processed receipt"""
    try:
        # Get OCR result record
        query = select(OCRResult).where(
            OCRResult.ocr_id == ocr_id,
            OCRResult.user_id == current_user.user_id
        )
        result = await db.execute(query)
        ocr_result = result.scalars().first()
        
        if not ocr_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "error_code": "resource_not_found",
                    "message": "Receipt not found"
                }
            )
            
        # Get expense items if they exist
        query = select(ExpenseItem).where(ExpenseItem.ocr_id == ocr_id)
        result = await db.execute(query)
        expense_items = result.scalars().all()
        
        # Convert to response format
        items = [
            OCRResultItem(
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                category=item.category
            )
            for item in expense_items
        ]
        
        # In a real system, we'd have more fields populated
        # For now we'll return what we have, with some mock data if needed
        confidence_score = 0.95  # Mock confidence score
            
        return OCRResultResponse(
            ocr_id=ocr_result.ocr_id,
            merchant_name=ocr_result.merchant_name or "Unknown Merchant",
            total_amount=ocr_result.total_amount,
            transaction_date=ocr_result.transaction_date or datetime.utcnow(),
            payment_method=ocr_result.payment_method,
            items=items,
            confidence_score=confidence_score,
            image_url=ocr_result.image_path,
            receipt_status=ocr_result.receipt_status
        )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error retrieving OCR results",
                "details": {"error": str(e)}
            }
        )


@router.post("/{ocr_id}/accept", response_model=AcceptOCRResponse)
async def accept_ocr_results(
    request: AcceptOCRRequest,
    ocr_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AcceptOCRResponse:
    """Accept OCR results and create an expense record"""
    try:
        # Verify OCR record exists and belongs to user
        query = select(OCRResult).where(
            OCRResult.ocr_id == ocr_id,
            OCRResult.user_id == current_user.user_id
        )
        result = await db.execute(query)
        ocr_result = result.scalars().first()
        
        if not ocr_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "error_code": "resource_not_found",
                    "message": "Receipt not found"
                }
            )
        
        # Update OCR result status
        ocr_result.receipt_status = ReceiptStatus.ACCEPTED
        ocr_result.merchant_name = request.merchant_name or ocr_result.merchant_name
        ocr_result.total_amount = request.total_amount or ocr_result.total_amount
        ocr_result.transaction_date = request.transaction_date or ocr_result.transaction_date
        ocr_result.payment_method = request.payment_method or ocr_result.payment_method
        
        # Create expense history record
        expense_history = ExpenseHistory(
            user_id=current_user.user_id,
            ocr_id=ocr_id,
            merchant_name=request.merchant_name or ocr_result.merchant_name or "Unknown Merchant",
            total_amount=request.total_amount or ocr_result.total_amount or 0,
            transaction_date=request.transaction_date or ocr_result.transaction_date or datetime.utcnow(),
            payment_method=request.payment_method or ocr_result.payment_method,
            category=request.category,
            notes=request.notes,
            is_manual_entry=False
        )
        
        db.add(expense_history)
        await db.flush()  # Get the expense_id before committing
        
        # Process expense items
        # First, clear any existing items (if updating)
        query = select(ExpenseItem).where(ExpenseItem.ocr_id == ocr_id)
        result = await db.execute(query)
        existing_items = result.scalars().all()
        
        for item in existing_items:
            await db.delete(item)
        
        # Add new items
        for item in request.items:
            expense_item = ExpenseItem(
                ocr_id=ocr_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                category=item.category or request.category  # Use item category or default to expense category
            )
            db.add(expense_item)
        
        await db.commit()  # Commit all changes
        
        return AcceptOCRResponse(
            expense_id=expense_history.expense_id,
            ocr_id=ocr_id,
            message="Expense successfully recorded",
            status="success"
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error accepting OCR results",
                "details": {"error": str(e)}
            }
        )
