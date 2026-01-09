"""Authentication module for API key validation."""

import os
import secrets
from typing import List
from fastapi import HTTPException, Header, Request
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# ============================================================================
# Configuration
# ============================================================================

def get_valid_api_keys() -> List[str]:
    """
    Get valid API keys from environment variable.

    Returns:
        List of valid API keys. Keys are read from API_KEYS environment
        variable as a comma-separated list.
    """
    api_keys_env = os.getenv("API_KEYS", "")
    if not api_keys_env:
        return []

    # Split by comma and strip whitespace
    keys = [key.strip() for key in api_keys_env.split(",") if key.strip()]
    return keys


# ============================================================================
# Security Utilities
# ============================================================================

def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Args:
        val1: First string to compare
        val2: Second string to compare

    Returns:
        True if strings are equal, False otherwise
    """
    return secrets.compare_digest(val1.encode(), val2.encode())


def validate_api_key(api_key: str) -> bool:
    """
    Validate an API key against the list of valid keys.

    Args:
        api_key: The API key to validate

    Returns:
        True if the API key is valid, False otherwise
    """
    valid_keys = get_valid_api_keys()

    if not valid_keys:
        # If no API keys are configured, reject all requests
        return False

    # Use constant-time comparison to prevent timing attacks
    for valid_key in valid_keys:
        if constant_time_compare(api_key, valid_key):
            return True

    return False


# ============================================================================
# Authentication Dependencies
# ============================================================================

# Define the API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """
    FastAPI dependency to validate API key from X-API-Key header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not validate_api_key(x_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


# ============================================================================
# Middleware
# ============================================================================

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate API keys on all requests.

    This middleware checks the X-API-Key header on all incoming requests
    and returns 401 Unauthorized if the key is missing or invalid.

    Exempted endpoints (health checks):
    - /
    - /health
    - /api/health
    """

    # Endpoints that don't require authentication
    EXEMPT_PATHS = {"/", "/health", "/api/health"}

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and validate API key.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response from the next handler or 401 error
        """
        # Check if this path is exempt from authentication
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Missing API key. Please provide X-API-Key header."
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if not validate_api_key(api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # API key is valid, proceed with the request
        response = await call_next(request)
        return response
