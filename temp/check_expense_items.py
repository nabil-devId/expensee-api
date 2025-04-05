import asyncio
from sqlalchemy import text
from app.core.db import engine

async def check_expense_items_columns():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'expense_items'
            ORDER BY ordinal_position;
        """))
        columns = [(row[0], row[1]) for row in result]
        
        print("Columns in expense_items table:")
        for name, data_type in columns:
            print(f"  - {name} ({data_type})")
        
        # Check if our new columns exist
        new_columns = ['user_id', 'category_id', 'user_category_id', 'purchase_date', 'amount']
        for col in new_columns:
            if any(col == name for name, _ in columns):
                print(f"✓ Column '{col}' exists")
            else:
                print(f"✗ Column '{col}' does not exist")

if __name__ == "__main__":
    asyncio.run(check_expense_items_columns())
