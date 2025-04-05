from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
import time
import logging
from typing import Callable, Dict, Any

from app.utils.rate_limiter import auth_rate_limiter, api_rate_limiter, reset_password_rate_limiter

logger = logging.getLogger(__name__)


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to apply rate limiting
    """
    # Get IP address from request
    client_ip = request.client.host if request.client else "unknown"
    
    # Choose rate limiter based on endpoint path
    path = request.url.path
    
    if path.startswith("/api/v1/auth"):
        if path.endswith("/login"):
            limiter = auth_rate_limiter
            key = f"auth:{client_ip}"
        elif path.endswith("/forgot-password") or path.endswith("/reset-password"):
            limiter = reset_password_rate_limiter
            key = f"reset:{client_ip}"
        else:
            limiter = api_rate_limiter
            key = f"api:{client_ip}"
    else:
        limiter = api_rate_limiter
        key = f"api:{client_ip}"
    
    # Check if request should be rate limited
    is_limited, retry_after = limiter.is_rate_limited(key)
    
    if is_limited:
        logger.warning(f"Rate limited request from {client_ip} to {path}")
        return JSONResponse(
            content={
                "status": "error",
                "error_code": "rate_limit_exceeded",
                "message": "Too many requests, please try again later"
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)}
        )
    
    # Process the request
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(
            content={
                "status": "error", 
                "error_code": "server_error",
                "message": "An unexpected error occurred"
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def setup_middleware(app: FastAPI) -> None:
    """
    Setup all middleware for the application
    """
    app.middleware("http")(rate_limit_middleware)
