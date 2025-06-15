import uuid
import logging
from typing import Optional
from datetime import datetime
from utils.gemini import find_category, process_receipt_with_gemini, preprocess_image, upload_to_gcs

# Set up logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status, Path, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User

from app.models.expense_history import ExpenseHistory
from app.models.expense_item import ExpenseItem
from schemas.receipt import OCRResultResponse, OCRResultItemResponse
from app.models.ocr_result import OCRResult
from app.models.ocr_result_item import OCRResultItem
from app.models.category import Category
from app.models.user_category import UserCategory
from app.models.receipt import ReceiptStatus

from schemas.receipt import (
    ReceiptUploadResponse, ReceiptStatusResponse,
    AcceptOCRRequest, AcceptOCRResponse,
    OCRFeedbackRequest, OCRFeedbackResponse
)

router = APIRouter()

@router.post("/gemini/upload", response_model=ReceiptUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_gemini(
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
        
        # 3. Trigger OCR processing job (for later will asynchronous)
        try:
            # Process the receipt (this would typically be done asynchronously)
            preprocessed_image = preprocess_image(file_content)
            gcs_uri = upload_to_gcs(preprocessed_image)
            gcs_url = gcs_uri.replace("gs://", "https://storage.googleapis.com/")
            ocr_data = process_receipt_with_gemini(preprocessed_image)

            ocr_id = uuid.uuid4()
            ocr_result = OCRResult(
                ocr_id=ocr_id,
                user_id=current_user.user_id,
                image_path=gcs_url,
                receipt_status=ReceiptStatus.PENDING,
            )
            db.add(ocr_result)
            await db.commit()
            await db.refresh(ocr_result)
            # Update the OCR result with the processed data
            ocr_result.merchant_name = ocr_data.get('merchant_name', 'Unknown')
            ocr_result.total_amount = int(ocr_data.get('total_amount', '0').replace('.', ''))
            ocr_result.transaction_date = datetime.strptime(ocr_data.get('transaction_date'), '%Y-%m-%d') if ocr_data.get('transaction_date') else None
            ocr_result.payment_method = ocr_data.get('payment_method')

            ocr_result.receipt_status = ReceiptStatus.PROCESSED

            category_query = select(Category)  # Select entire Category object
            result_category = await db.execute(category_query)
            categories = result_category.scalars().all()

            final_categories = []

            for cat in categories:
                final_categories.append({"category_id": cat.category_id, "category_name": cat.name})
            
            user_category_query = select(UserCategory).where(UserCategory.user_id == current_user.user_id)  # Select entire Category object
            result_user_category = await db.execute(user_category_query)
            user_categories = result_user_category.scalars().all()

            final_user_categories = []

            for user_cat in user_categories:
                final_user_categories.append({"category_id": user_cat.user_category_id, "category_name": user_cat.name})

            super_final_categories = {
                "categories": final_categories,
                "user_categories": final_user_categories
            }

            res = find_category(expense_history_raw=str(ocr_data), category=str(super_final_categories))

            if res.is_user_category is True:
                ocr_result.user_category_id = res.category_id
            else:
                ocr_result.category_id = res.category_id
            
            # Save the updates
            await db.commit()
            await db.refresh(ocr_result)

            # Create expense items based on the OCR result
            if ocr_data.get('items'):
                for item_data in ocr_data.get('items'):
                    expense_item = OCRResultItem(
                        ocr_id=ocr_id,
                        name=item_data.get('name', 'Unknown Item'),
                        quantity=item_data.get('quantity', 1),
                        unit_price=int(item_data.get('price', '0').replace('.', '')),
                        total_price=item_data.get('total', int(item_data.get('price', '0').replace('.', '')) * int(item_data.get('quantity', 1))),
                    )
                    db.add(expense_item)
            
        except Exception as e:
            logger.error(f"Error processing receipt: {str(e)}")
            # Don't fail the request if OCR processing fails - the user can still get their receipt ID
        
        # Return the appropriate response based on the OCR processing status
        if ocr_result.receipt_status == ReceiptStatus.PROCESSED:
            return ReceiptUploadResponse(
                ocr_id=ocr_id,
                status="complete",
                message="Receipt processed successfully"
            )
        else:
            # Ensure estimated_time is never null
            return ReceiptUploadResponse(
                ocr_id=ocr_id,
                status="pending",
                message="Receipt uploaded and queued for processing"
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
        ).options(selectinload(OCRResult.ocr_result_items), selectinload(OCRResult.category), selectinload(OCRResult.user_category))
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

        items = []

        for item in ocr_result.ocr_result_items:
            items.append(
                OCRResultItemResponse(
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
            )
            
        return OCRResultResponse(
            ocr_id=ocr_result.ocr_id,
            merchant_name=ocr_result.merchant_name or "Unknown Merchant",
            total_amount=ocr_result.total_amount,
            transaction_date=ocr_result.transaction_date or datetime.utcnow(),
            payment_method=ocr_result.payment_method,
            items=items,
            image_url=ocr_result.image_path,
            receipt_status=ocr_result.receipt_status,
            category=ocr_result.category,
            user_category=ocr_result.user_category
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


@router.post("/{ocr_id}/feedback", response_model=OCRFeedbackResponse)
async def submit_ocr_feedback(
    ocr_id: uuid.UUID = Path(...),
    feedback: OCRFeedbackRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> OCRFeedbackResponse:
    """Submit feedback on OCR results for model training"""
    try:
        # Verify OCR record exists and belongs to user
        query = select(OCRResult).where(
            OCRResult.ocr_id == ocr_id,
            OCRResult.user_id == current_user.user_id
        )
        result = await db.execute(query)
        ocr_result = result.scalar_one_or_none()
        
        if not ocr_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "error_code": "resource_not_found",
                    "message": "Receipt not found"
                }
            )
        
        # Create feedback entries
        feedback_id = uuid.uuid4()
        
        # Save to database
        await db.commit()
        
        return OCRFeedbackResponse(
            status="success",
            message="Feedback submitted successfully",
            feedback_id=feedback_id
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error submitting OCR feedback",
                "details": {"error": str(e)}
            }
        )


@router.post("/{ocr_id}/accept", response_model=AcceptOCRResponse)
async def accept_ocr_results(
    request: AcceptOCRRequest = Body(...),
    ocr_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AcceptOCRResponse:
    """Accept OCR results and create an expense record"""
    try:

        # Verify category

        if not request.category_id and not request.user_category_id: 
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "category_not_specified",
                    "message": "Category not specified"
                }
            )
        # Verify OCR record exists and belongs to user
        query = select(OCRResult).where(
            OCRResult.ocr_id == ocr_id,
            OCRResult.user_id == current_user.user_id
        )
        result = await db.execute(query)
        ocr_result = result.scalar_one()
        if ocr_result.receipt_status == ReceiptStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "ocr_result_has_been_accepted",
                    "message": "OCR result has been accepted"
                }
            )
        
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

        if request.category_id:
            fetchCategoryQuery = select(Category).where(
                Category.category_id == request.category_id
            )
            category = await db.execute(fetchCategoryQuery)
        else:
            category = None

        if request.user_category_id:
            fetchUserCategoryQuery = select(UserCategory).where(
                UserCategory.user_category_id == request.user_category_id
            )
            userCategory = await db.execute(fetchUserCategoryQuery)
        else:
            userCategory = None

        if not category and not userCategory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "category_not_found",
                    "message": "Category not found"
                }
            )
    
        # Create expense history record
        expense_history = ExpenseHistory(
            user_id=current_user.user_id,
            ocr_id=ocr_id,
            merchant_name=request.merchant_name or ocr_result.merchant_name or "Unknown Merchant",
            total_amount=request.total_amount or ocr_result.total_amount or 0,
            transaction_date=request.transaction_date or ocr_result.transaction_date or datetime.utcnow(),
            payment_method=request.payment_method or ocr_result.payment_method,
            category_id=request.category_id if request.category_id else None,
            user_category_id=request.user_category_id if request.user_category_id else None,
            notes=request.notes,
            is_manual_entry=False
        )
        expense_items = []
        # Add new items
        for item in request.items:
            expense_item = ExpenseItem(
                user_id=current_user.user_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )
            expense_items.append(expense_item)
        
        db.add(expense_history)  # Add ExpenseHistory to the session

        # Assign the items. If ExpenseHistory.expense_items relationship has appropriate cascade
        # (e.g., save-update), this will also mark items for addition.
        expense_history.expense_items = expense_items

        # If cascade is not sufficient to add items to the session automatically,
        # you might need to explicitly add them:
        # for item in expense_items:
        #    db.add(item)
        # or db.add_all(expense_items)

        await db.commit()  # Commit the session
        await db.refresh(expense_history)  # Refresh expense_history
        # Optionally refresh items if needed
        # for item in expense_history.expense_items:
        #     await db.refresh(item)
        
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
