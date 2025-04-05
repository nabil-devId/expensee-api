import asyncio
from sqlalchemy import text
from app.core.db import engine

async def check_categories():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT category_id, name, icon, color FROM categories;"))
        categories = [(str(row[0]), row[1], row[2], row[3]) for row in result]
        
        print(f"Found {len(categories)} default categories:")
        for cat_id, name, icon, color in categories:
            print(f"  - {name} (icon: {icon}, color: {color})")

if __name__ == "__main__":
    asyncio.run(check_categories())
