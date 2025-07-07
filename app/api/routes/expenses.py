import uuid
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc, and_, exists
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.expense_history import ExpenseHistory
from app.models.ocr_result import OCRResult
from app.models.expense_item import ExpenseItem
from app.models.category import Category
from app.models.user_category import UserCategory
from schemas.expense import ExpenseSummary
from schemas.expense import ExpenseItemBase
import logging
from schemas.expense import ExpenseHistoryCreate, ExpenseHistoryResponse, PaginationInfo, ExpenseHistoryListResponse, ExpenseHistoryDetails
from schemas.expense import ExpenseCategory, ExpenseUserCategory, ExpenseHistoryUpdate
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ExpenseHistoryListResponse)
async def get_expense_history(
    from_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
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
        if sort_by not in ["transaction_date", "total_amount", "merchant_name","created_at"]:
            sort_by = "transaction_date"  # Default sort
            
        sort_column = getattr(ExpenseHistory, sort_by)
        if sort_order.lower() == "asc":
            sort_column = asc(sort_column)
        else:
            sort_column = desc(sort_column)
            
        # Get paginated expenses
        query = (
            select(ExpenseHistory)
            .where(and_(*query_filters))
            .order_by(sort_column)
            .offset((page - 1) * limit)
            .limit(limit)
        )
        
        result = await db.execute(query)
        expense_records = result.scalars().all()
        
        # Format response
        expenses = []
        for expense in expense_records:
            print('expensesrrrr', expense)
            expenses.append(
                ExpenseHistoryResponse(
                    expense_id=expense.expense_id,
                    merchant_name=expense.merchant_name,
                    total_amount=expense.total_amount,
                    transaction_date=expense.transaction_date,
                    category=ExpenseCategory(category_id=expense.category.category_id, name=expense.category.name, icon=expense.category.icon, color=expense.category.color) if expense.category else None,
                    user_category=ExpenseUserCategory(user_category_id=expense.user_category.user_category_id, name=expense.user_category.name, icon=expense.user_category.icon, color=expense.user_category.color) if expense.user_category else None,
                    payment_method=expense.payment_method,
                    notes=expense.notes,
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
        category_query = (
            select(
                Category.name.label("category_name"), 
                UserCategory.name.label("user_category_name"), 
                func.sum(ExpenseHistory.total_amount).label("amount")
            )
            .select_from(ExpenseHistory)
            .outerjoin(Category, Category.category_id == ExpenseHistory.category_id)
            .outerjoin(UserCategory, UserCategory.user_category_id == ExpenseHistory.user_category_id)
            .where(and_(*query_filters))
            .group_by(
                Category.name,
                UserCategory.name
            )
        )
        
        result = await db.execute(category_query)
        category_records = result.all()
        
        expense_by_category = {
            (category_name or user_category_name or "Uncategorized"): amount
            for category_name, user_category_name, amount in category_records
        }

        print('expense_by_categoryxxxx', expense_by_category)
        
        # Create summary object with defaults for empty results
        # make the 0 after . only 2

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
        logger.error(f"Error retrieving expense history: {str(e)}")
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
            select(ExpenseHistory, OCRResult.image_path, Category.name.label("category_name"), UserCategory.name.label("user_category_name"))
            .outerjoin(OCRResult, ExpenseHistory.ocr_id == OCRResult.ocr_id)
            .outerjoin(Category, ExpenseHistory.category_id == Category.category_id)
            .outerjoin(UserCategory, ExpenseHistory.user_category_id == UserCategory.user_category_id)
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
            
        expense, image_url, category_name, user_category_name = expense_record
        
        # Get expense items if they exist
        items = []
        if expense.expense_id:
            query = select(ExpenseItem).where(ExpenseItem.expense_history_id == expense.expense_id)
            result = await db.execute(query)
            expense_items = result.scalars().all()
            
            items = [
                ExpenseItemBase(
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
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
            category=ExpenseCategory(category_id=expense.category.category_id, name=expense.category.name, icon=expense.category.icon, color=expense.category.color) if expense.category else None,
            user_category=ExpenseUserCategory(user_category_id=expense.user_category.user_category_id, name=expense.user_category.name) if expense.user_category else None,
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
@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
async def create_expense(
    expense: ExpenseHistoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Validate category selection
        if not expense.category_id and not expense.user_category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "bad_request",
                    "message": "Category or user category must be provided",
                    "details": {"error": "Category or user category is required"}
                }
            )

        if expense.category_id and expense.user_category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "bad_request",
                    "message": "Choose one, either category or user category",
                    "details": None
                }
            )

        if expense.category_id:
            result = await db.execute(
                select(Category).where(Category.category_id == expense.category_id)
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "error_code": "category_not_found",
                        "message": "Category not found"
                    }
                )

        if expense.user_category_id:
            result = await db.execute(
                select(UserCategory).where(
                    UserCategory.user_category_id == expense.user_category_id,
                    UserCategory.user_id == current_user.user_id
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "error_code": "user_category_not_found",
                        "message": "User category not found or not accessible"
                    }
                )
        
        expense_history = ExpenseHistory(
            user_id=current_user.user_id,
            ocr_id=None,
            merchant_name=expense.merchant_name or "Unknown Merchant",
            total_amount=expense.total_amount or 0,
            transaction_date=expense.transaction_date or datetime.utcnow(),
            payment_method=expense.payment_method or "Unknown",
            category_id=expense.category_id,
            user_category_id=expense.user_category_id,
            notes=expense.notes,
            is_manual_entry=True
        )
        items = []

        for item in expense.items:
            expense_item = ExpenseItem(
                user_id=current_user.user_id,
                name=item.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                purchase_date=expense.transaction_date,
                expense_history_id=expense_history.expense_id
            )
            items.append(expense_item)
        expense_history.expense_items = items

        db.add(expense_history)
        await db.commit()
        await db.refresh(expense_history)

        return expense_history
    except HTTPException as e:
        logger.error(f"HTTP exception in create_expense: {str(e)}")
        raise e
    except Exception as ex:
        logger.error(f"Error in create_expense: {str(ex)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "internal_server_error",
                "message": "An error occurred while creating the expense"
            }
        )

@router.delete("/{expense_id}", status_code=200)
async def drop_expense(
    expense_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    try:
        query = select(ExpenseHistory).where(
            User.user_id == current_user.user_id,
            ExpenseHistory.expense_id == expense_id
        )
        
        result = await db.execute(query)
        expense_history = result.scalar_one_or_none()

        if not expense_history:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "bad_request",
                    "message": "Expense not found"
                }
            )

        await db.delete(expense_history)
        await db.commit()
        await db.flush()
        return
    except Exception as ex:
        raise ex

@router.put("/{expense_id}", status_code=200)
async def update_expense(
    expense_id: uuid.UUID,
    expense: ExpenseHistoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        # Validate category selection
        if not expense.category_id and not expense.user_category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "bad_request",
                    "message": "Category or user category must be provided",
                    "details": {"error": "Category or user category is required"}
                }
            )

        if expense.category_id and expense.user_category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "error_code": "bad_request",
                    "message": "Choose one, either category or user category",
                    "details": None
                }
            )

        if expense.category_id:
            result = await db.execute(
                select(Category).where(Category.category_id == expense.category_id)
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "error_code": "category_not_found",
                        "message": "Category not found"
                    }
                )

        if expense.user_category_id:
            result = await db.execute(
                select(UserCategory).where(
                    UserCategory.user_category_id == expense.user_category_id,
                    UserCategory.user_id == current_user.user_id
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "error_code": "user_category_not_found",
                        "message": "User category not found or not accessible"
                    }
                )

        query = select(ExpenseHistory).where(
            ExpenseHistory.expense_id == expense_id,
            ExpenseHistory.user_id == current_user.user_id
        ).options(
            selectinload(ExpenseHistory.expense_items)
        )
        result = await db.execute(query)
        expense_history = result.scalar_one_or_none()

        if not expense_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "error_code": "resource_not_found",
                    "message": "Expense not found"
                }
            )

        # Update the fields
        expense_history.merchant_name = expense.merchant_name or expense_history.merchant_name
        expense_history.total_amount = expense.total_amount or expense_history.total_amount
        expense_history.transaction_date = expense.transaction_date or expense_history.transaction_date
        expense_history.payment_method = expense.payment_method or expense_history.payment_method
        expense_history.category_id = expense.category_id or None
        expense_history.user_category_id = expense.user_category_id or None
        expense_history.notes = expense.notes or expense_history.notes
        expense_history.is_manual_entry = True

        new_items = [
            ExpenseItem(
                name=item.name,
                user_id=current_user.user_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                purchase_date=expense.transaction_date or expense_history.transaction_date
            ) for item in expense.items
        ]

        expense_history.expense_items = new_items

        await db.commit()
        await db.refresh(expense_history)
        return {
            "code": 200,
            "message": "update successfully"
        }
    except Exception as ex:
        raise ex
