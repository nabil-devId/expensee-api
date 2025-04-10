import os
import uuid
import tempfile
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from app.api.dependencies import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.expense_history import ExpenseHistory
from app.models.expense_item import ExpenseItem
from app.models.category import Category, UserCategory
from app.models.receipt import OCRResult

from schemas.exports import ExportFormat

router = APIRouter()


@router.get("/expenses")
async def export_expenses(
    start_date: date = Query(..., description="Start date for exporting expenses"),
    end_date: date = Query(..., description="End date for exporting expenses"),
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format (csv, pdf, xlsx)"),
    include_items: bool = Query(False, description="Include individual expense items"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export expenses in the specified format for the given date range.
    """
    try:
        # Build query filters
        query_filters = [
            ExpenseHistory.user_id == current_user.user_id,
            ExpenseHistory.transaction_date >= start_date,
            ExpenseHistory.transaction_date <= end_date
        ]
        
        # Query for expense history
        sys_cat_alias = aliased(Category)
        user_cat_alias = aliased(UserCategory)
        
        expenses_query = (
            select(
                ExpenseHistory.expense_id,
                ExpenseHistory.merchant_name,
                ExpenseHistory.total_amount,
                ExpenseHistory.transaction_date,
                ExpenseHistory.payment_method,
                ExpenseHistory.notes,
                ExpenseHistory.ocr_id,
                func.coalesce(sys_cat_alias.name, user_cat_alias.name, 'Uncategorized').label('category_name')
            )
            .outerjoin(sys_cat_alias, ExpenseHistory.category_id == sys_cat_alias.category_id)
            .outerjoin(user_cat_alias, ExpenseHistory.user_category_id == user_cat_alias.user_category_id)
            .where(and_(*query_filters))
            .order_by(ExpenseHistory.transaction_date.desc())
        )
        
        result = await db.execute(expenses_query)
        expense_records = result.all()
        
        # Prepare data for export
        expense_data = []
        
        for (
            expense_id, merchant_name, total_amount, transaction_date, 
            payment_method, notes, ocr_id, category_name
        ) in expense_records:
            expense_data.append({
                "Date": transaction_date,
                "Merchant": merchant_name or "Unknown",
                "Category": category_name,
                "Amount": float(total_amount),
                "Payment Method": payment_method or "Unknown",
                "Notes": notes or "",
                "Has Receipt": ocr_id is not None,
                "Expense ID": str(expense_id)
            })
        
        # If include_items is True, get individual expense items
        item_data = []
        if include_items:
            # Get all expense IDs
            expense_ids = [record[0] for record in expense_records]
            ocr_ids = [record[6] for record in expense_records if record[6] is not None]
            
            if ocr_ids:
                # Query for expense items
                items_query = (
                    select(
                        ExpenseItem.item_id,
                        ExpenseItem.ocr_id,
                        ExpenseItem.name,
                        ExpenseItem.quantity,
                        ExpenseItem.unit_price,
                        ExpenseItem.total_price,
                        ExpenseItem.purchase_date,
                        OCRResult.merchant_name
                    )
                    .join(OCRResult, ExpenseItem.ocr_id == OCRResult.ocr_id)
                    .where(ExpenseItem.ocr_id.in_(ocr_ids))
                    .order_by(ExpenseItem.purchase_date.desc())
                )
                
                result = await db.execute(items_query)
                item_records = result.all()
                
                for (
                    item_id, ocr_id, name, quantity, unit_price, 
                    total_price, purchase_date, merchant_name
                ) in item_records:
                    item_data.append({
                        "OCR ID": str(ocr_id),
                        "Item Name": name,
                        "Quantity": quantity,
                        "Unit Price": float(unit_price),
                        "Total Item Price": float(total_price),
                        "Purchase Date": purchase_date,
                        "Merchant": merchant_name or "Unknown",
                        "Item ID": str(item_id)
                    })
        
        # Create filename based on date range
        filename = f"expenses_{start_date}_{end_date}"
        
        # Export based on format
        if format == ExportFormat.CSV:
            # Create a CSV in memory
            output = BytesIO()
            
            # Write expenses to CSV
            expenses_df = pd.DataFrame(expense_data)
            expenses_df.to_csv(output, index=False)
            
            # If including items, add them after a separator
            if include_items and item_data:
                output.write(b"\n\n--- INDIVIDUAL ITEMS ---\n\n")
                items_df = pd.DataFrame(item_data)
                items_df.to_csv(output, index=False)
            
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
            )
            
        elif format == ExportFormat.XLSX:
            # Create an Excel file in memory
            output = BytesIO()
            
            # Create Excel writer
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # Write expenses sheet
                expenses_df = pd.DataFrame(expense_data)
                expenses_df.to_excel(writer, sheet_name="Expenses", index=False)
                
                # If including items, add a separate sheet
                if include_items and item_data:
                    items_df = pd.DataFrame(item_data)
                    items_df.to_excel(writer, sheet_name="Items", index=False)
            
            output.seek(0)
            
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
            )
            
        elif format == ExportFormat.PDF:
            # In a real implementation, we would generate a PDF here
            # For this version, we'll just return a placeholder
            return Response(
                content="PDF export not implemented in this version",
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename={filename}.txt"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Supported formats: csv, pdf, xlsx")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting expenses: {str(e)}")
