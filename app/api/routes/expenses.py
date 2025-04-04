import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc, and_, between

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.receipt import OCRResult
from app.models.expense_history import ExpenseHistory
from app.models.expense_item import ExpenseItem

from schemas.receipt import (
    ExpenseHistoryResponse, ExpenseHistoryDetails, ExpenseHistoryListResponse,
    PaginationInfo, ExpenseSummary, ExpenseItemBase, ErrorResponse
)

router = APIRouter()


@router.get("", response_model=ExpenseHistoryListResponse)
async def get_expense_history(
    from_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    merchant: Optional[str] = Query(None, description="Filter by merchant name"),
    min_amount: Optional[float] = Query(None, description="Filter by minimum amount"),
    max_amount: Optional[float] = Query(None, description="Filter by maximum amount"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("transaction_date", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ExpenseHistoryListResponse:
    """Get expense history with optional filtering and pagination"""
    try:
        # Build the query with filters
        query_filters = [ExpenseHistory.user_id == current_user.user_id]
        
        if from_date:
            query_filters.append(ExpenseHistory.transaction_date >= from_date)
            
        if to_date:
            query_filters.append(ExpenseHistory.transaction_date <= to_date)
            
        if category:
            query_filters.append(ExpenseHistory.category.ilike(f"%{category}%"))
            
        if merchant:
            query_filters.append(ExpenseHistory.merchant_name.ilike(f"%{merchant}%"))
            
        if min_amount is not None:
            query_filters.append(ExpenseHistory.total_amount >= min_amount)
            
        if max_amount is not None:
            query_filters.append(ExpenseHistory.total_amount <= max_amount)
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(ExpenseHistory).where(and_(*query_filters))
        result = await db.execute(count_query)
        total_count = result.scalar()
        
        # Handle sort order
        if sort_by not in ["transaction_date", "total_amount", "merchant_name", "category", "created_at"]:
            sort_by = "transaction_date"  # Default sort
            
        sort_column = getattr(ExpenseHistory, sort_by)
        if sort_order.lower() == "asc":
            sort_column = asc(sort_column)
        else:
            sort_column = desc(sort_column)
            
        # Get paginated expenses
        query = (
            select(ExpenseHistory, OCRResult.image_path)
            .outerjoin(OCRResult, ExpenseHistory.ocr_id == OCRResult.ocr_id)
            .where(and_(*query_filters))
            .order_by(sort_column)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        
        result = await db.execute(query)
        expense_records = result.all()
        
        # Format response
        expenses = []
        for expense, image_path in expense_records:
            expenses.append(
                ExpenseHistoryResponse(
                    expense_id=expense.expense_id,
                    merchant_name=expense.merchant_name,
                    total_amount=expense.total_amount,
                    transaction_date=expense.transaction_date,
                    category=expense.category,
                    payment_method=expense.payment_method,
                    notes=expense.notes,
                    has_receipt_image=image_path is not None,
                    created_at=expense.created_at
                )
            )
            
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        pagination = PaginationInfo(
            total_count=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
        # Calculate summary statistics
        summary_query = select(
            func.sum(ExpenseHistory.total_amount).label("total"),
            func.avg(ExpenseHistory.total_amount).label("avg"),
            func.max(ExpenseHistory.total_amount).label("max"),
            func.min(ExpenseHistory.total_amount).label("min")
        ).where(and_(*query_filters))
        
        result = await db.execute(summary_query)
        summary_record = result.one()
        
        # Get expense by category
        category_query = select(
            ExpenseHistory.category,
            func.sum(ExpenseHistory.total_amount).label("amount")
        ).where(and_(*query_filters)).group_by(ExpenseHistory.category)
        
        result = await db.execute(category_query)
        category_records = result.all()
        
        expense_by_category = {
            category: amount
            for category, amount in category_records
        }
        
        # Create summary object with defaults for empty results
        summary = ExpenseSummary(
            total_expenses=summary_record.total or Decimal("0.0"),
            avg_expense=summary_record.avg or Decimal("0.0"),
            max_expense=summary_record.max or Decimal("0.0"),
            min_expense=summary_record.min or Decimal("0.0"),
            expense_by_category=expense_by_category
        )
        
        return ExpenseHistoryListResponse(
            expenses=expenses,
            pagination=pagination,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error retrieving expense history",
                "details": {"error": str(e)}
            }
        )


@router.get("/{expense_id}", response_model=ExpenseHistoryDetails)
async def get_expense_detail(
    expense_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> ExpenseHistoryDetails:
    """Get detailed information about a specific expense"""
    try:
        # Get expense record
        query = (
            select(ExpenseHistory, OCRResult.image_path)
            .outerjoin(OCRResult, ExpenseHistory.ocr_id == OCRResult.ocr_id)
            .where(
                ExpenseHistory.expense_id == expense_id,
                ExpenseHistory.user_id == current_user.user_id
            )
        )
        
        result = await db.execute(query)
        expense_record = result.first()
        
        if not expense_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "error_code": "resource_not_found",
                    "message": "Expense not found"
                }
            )
            
        expense, image_url = expense_record
        
        # Get expense items if they exist
        items = []
        if expense.ocr_id:
            query = select(ExpenseItem).where(ExpenseItem.ocr_id == expense.ocr_id)
            result = await db.execute(query)
            expense_items = result.scalars().all()
            
            items = [
                ExpenseItemBase(
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    category=item.category
                )
                for item in expense_items
            ]
            
        return ExpenseHistoryDetails(
            expense_id=expense.expense_id,
            ocr_id=expense.ocr_id,
            merchant_name=expense.merchant_name,
            total_amount=expense.total_amount,
            transaction_date=expense.transaction_date,
            payment_method=expense.payment_method,
            category=expense.category,
            notes=expense.notes,
            receipt_image_url=image_url,
            items=items,
            created_at=expense.created_at,
            updated_at=expense.updated_at,
            is_manual_entry=expense.is_manual_entry
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "server_error",
                "message": "Error retrieving expense details",
                "details": {"error": str(e)}
            }
        )
