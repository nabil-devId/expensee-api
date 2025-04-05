from fastapi import APIRouter

from app.api.routes import auth, users, receipts, expenses, categories, budgets

api_router = APIRouter()

# Include the different routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["budgets"])