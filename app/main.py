from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
import logging

from app.api.routes.api import api_router
from app.core.config import settings
from app.core.middleware import setup_middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for expense tracking application with receipt scanning capabilities",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    # Add base URL to the OpenAPI schema
    servers=[
        {"url": settings.SERVER_HOST or "/", "description": "Default server"}
    ],
    # Add security scheme for JWT Authentication
    openapi_tags=[
        {"name": "authentication", "description": "Authentication operations"},
        {"name": "users", "description": "Operations with users"},
        {"name": "receipts", "description": "Receipt processing operations"},
        {"name": "expenses", "description": "Expense management operations"},
        {"name": "categories", "description": "Category management operations"},
        {"name": "budgets", "description": "Budget management operations"},
        {"name": "analytics", "description": "Analytics and data visualization operations"},
        {"name": "reports", "description": "Report generation operations"},
        {"name": "exports", "description": "Data export operations"},
    ],
    # Add security scheme
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "useBasicAuthenticationWithAccessCodeGrant": True,
        "clientId": "",
        "clientSecret": "",
        "tokenUrl": f"{settings.API_V1_PREFIX}/auth/login",
    }
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Set up rate limiting middleware
setup_middleware(app)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    return JSONResponse(content={"status": "ok"})


@app.get("/", tags=["root"])
async def root():
    return JSONResponse(
        content={
            "message": "Welcome to Expense Tracker API! See /docs for the API documentation."
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting application")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)