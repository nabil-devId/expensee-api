from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
import logging
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from app.api.routes.api import api_router
from app.core.config import settings
from app.core.middleware import setup_middleware
import json
import time
from starlette.responses import Response
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

SENSITIVE_KEYS = ['password', 'token', 'secret', 'authorization', 'api_key']
def redact_sensitive_data(data):
    if isinstance(data, dict):
        return {
            k: '[REDACTED]' if k.lower() in SENSITIVE_KEYS else redact_sensitive_data(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    else:
        return data

# --- Logging Setup ---
def setup_logging():
    logger = logging.getLogger("api_logger")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler('api.log', maxBytes=100000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

logger = setup_logging()


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
        "persistAuthorization": True, # Add this line to persist auth
        "usePkceWithAuthorizationCodeGrant": True,
        "useBasicAuthenticationWithAccessCodeGrant": True,
        "clientId": "",
        "clientSecret": "",
        "tokenUrl": f"{settings.API_V1_PREFIX}/auth/login",
    }
)

@app.middleware("http")
async def robust_logging_middleware(request: Request, call_next):
    start_time = time.time()

    # --- Request Logging ---
    # This is the correct way to read the body without consuming it
    request_body_raw = await request.body()
    request_body_log = "N/A"
    if request_body_raw:
        try:
            # Check if it's JSON and redact
            if "application/json" in request.headers.get("content-type", ""):
                json_body = json.loads(request_body_raw)
                redacted_body = redact_sensitive_data(json_body)
                request_body_log = json.dumps(redacted_body)
            else:
                # For other content types, just decode
                request_body_log = request_body_raw.decode('utf-8')
        except Exception:
            request_body_log = "Could not parse request body"

    logger.info(
        f"--> {request.method} {request.url.path} | "
        f"Headers: {json.dumps(redact_sensitive_data(dict(request.headers)))} | "
        f"Body: {request_body_log}"
    )

    # The `call_next` function processes the request and returns a response
    response = await call_next(request)

    # --- Response Logging ---
    process_time = (time.time() - start_time) * 1000
    
    # Consume the response body to log it
    response_body_raw = b""
    async for chunk in response.body_iterator:
        response_body_raw += chunk
    
    response_body_log = "N/A"
    if response_body_raw:
        try:
             # Check if it's JSON and redact
            if "application/json" in response.headers.get("content-type", ""):
                json_body = json.loads(response_body_raw)
                redacted_body = redact_sensitive_data(json_body)
                response_body_log = json.dumps(redacted_body)
            else:
                response_body_log = response_body_raw.decode('utf-8')
        except Exception:
            response_body_log = "Could not parse response body"
    
    if len(response_body_log) > 1000: # Truncate long bodies
        response_body_log = response_body_log[:1000] + '... (truncated)'

    logger.info(
        f"<-- {response.status_code} ({process_time:.2f}ms) | "
        f"Body: {response_body_log}"
    )

    # Return a new response with the consumed body, so the client gets it
    return Response(
        content=response_body_raw,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )
# Custom exception handler for FastAPI's HTTPException
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    # Log the full details of the exception
    logger.error(
        f"HTTPException encountered: Status Code: {exc.status_code}, Detail: {exc.detail}, Request URL: {request.url}"
    )
    # If you want to log the original stack trace that led to the HTTPException
    # you would need to have captured it before raising the HTTPException,
    # for example, by logging `traceback.format_exc()` at the point of the original error.
    # For now, this logs the HTTPException itself.

    # Return the JSON response as intended
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=exc.headers
    )

# Generic exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log the full traceback for any unhandled exceptions
    logger.exception(
        f"Unhandled exception for request: {request.url}. Details: {exc}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_code": "server_error",
            "message": "An unexpected server error occurred.",
            "details": {"error": str(exc)} # Only include generic detail for security
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