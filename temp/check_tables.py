import asyncio
from sqlalchemy import text
from app.core.db import engine

async def check_tables():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"))
        tables = [row[0] for row in result]
        print("Tables in database:", tables)
        
        # Check if our new tables exist
        required_tables = ['categories', 'user_categories', 'budgets']
        for table in required_tables:
            if table in tables:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' does not exist")

if __name__ == "__main__":
    asyncio.run(check_tables())
