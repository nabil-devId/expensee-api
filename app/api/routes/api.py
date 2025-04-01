from fastapi import APIRouter

from app.api.routes import auth, users, receipts

api_router = APIRouter()

# Include the different routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])