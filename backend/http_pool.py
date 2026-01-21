"""HTTP client pool management using httpx with connection pooling.

This module provides shared httpx.AsyncClient instances for efficient HTTP
connections throughout the application. Connection pooling reduces overhead
from TCP handshake and TLS negotiation on every request.

Architecture:
    - Singleton pattern for HTTP clients (one per API service)
    - Async/await based using httpx for non-blocking I/O
    - Automatic connection reuse and lifecycle management
    - Configurable timeouts and pool limits

Usage:
    # In FastAPI startup event
    await init_http_clients()

    # In application code
    alpaca_client = get_alpaca_client()
    response = await alpaca_client.get(url, headers=headers)

    openrouter_client = get_openrouter_client()
    response = await openrouter_client.post(url, json=data)

    # In FastAPI shutdown event
    await close_http_clients()

Environment Variables:
    Connection pool settings:
        HTTP_MAX_CONNECTIONS: Max connections per client (default: 100)
        HTTP_MAX_KEEPALIVE_CONNECTIONS: Max keepalive connections (default: 20)
        HTTP_KEEPALIVE_EXPIRY: Keepalive expiry in seconds (default: 5.0)

    Timeout settings:
        HTTP_CONNECT_TIMEOUT: Connection timeout in seconds (default: 10.0)
        HTTP_READ_TIMEOUT: Read timeout in seconds (default: 30.0)
        HTTP_WRITE_TIMEOUT: Write timeout in seconds (default: 30.0)
        HTTP_POOL_TIMEOUT: Pool acquire timeout in seconds (default: 10.0)

    Protocol settings:
        HTTP2_ENABLED: Enable HTTP/2 support (default: true)

    Retry settings:
        HTTP_MAX_RETRIES: Max retry attempts (default: 3)
"""

import os
import logging
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class HttpClientConfig:
    """Configuration for httpx.AsyncClient connection pooling.

    Loads settings from environment variables with sensible defaults.
    Configures connection pool limits, timeouts, and protocol options
    for optimal performance with external APIs.
    """

    def __init__(self):
        """Initialize HTTP client configuration from environment variables."""
        # Connection pool settings
        self.max_connections = int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
        self.max_keepalive_connections = int(
            os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "20")
        )
        self.keepalive_expiry = float(os.getenv("HTTP_KEEPALIVE_EXPIRY", "5.0"))

        # Timeout settings (all in seconds)
        self.connect_timeout = float(os.getenv("HTTP_CONNECT_TIMEOUT", "10.0"))
        self.read_timeout = float(os.getenv("HTTP_READ_TIMEOUT", "30.0"))
        self.write_timeout = float(os.getenv("HTTP_WRITE_TIMEOUT", "30.0"))
        self.pool_timeout = float(os.getenv("HTTP_POOL_TIMEOUT", "10.0"))

        # Protocol settings
        self.http2_enabled = os.getenv("HTTP2_ENABLED", "true").lower() == "true"

        # Retry settings
        self.max_retries = int(os.getenv("HTTP_MAX_RETRIES", "3"))

    def get_limits(self) -> dict:
        """
        Get httpx Limits configuration.

        Returns:
            dict: Configuration dict for httpx.Limits()

        Example:
            config = HttpClientConfig()
            limits = httpx.Limits(**config.get_limits())
        """
        return {
            "max_connections": self.max_connections,
            "max_keepalive_connections": self.max_keepalive_connections,
            "keepalive_expiry": self.keepalive_expiry,
        }

    def get_timeout(self) -> dict:
        """
        Get httpx Timeout configuration.

        Returns:
            dict: Configuration dict for httpx.Timeout()

        Example:
            config = HttpClientConfig()
            timeout = httpx.Timeout(**config.get_timeout())
        """
        return {
            "connect": self.connect_timeout,
            "read": self.read_timeout,
            "write": self.write_timeout,
            "pool": self.pool_timeout,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"HttpClientConfig("
            f"max_connections={self.max_connections}, "
            f"max_keepalive={self.max_keepalive_connections}, "
            f"connect_timeout={self.connect_timeout}s, "
            f"read_timeout={self.read_timeout}s, "
            f"http2={self.http2_enabled})"
        )


# Global HTTP client singletons
_alpaca_client: Optional[httpx.AsyncClient] = None
_openrouter_client: Optional[httpx.AsyncClient] = None
_config: Optional[HttpClientConfig] = None


async def init_http_clients() -> tuple[httpx.AsyncClient, httpx.AsyncClient]:
    """
    Initialize the global HTTP client pool.

    Should be called once during FastAPI startup event. Creates shared
    httpx.AsyncClient instances that will be reused throughout the
    application lifetime.

    Returns:
        tuple[httpx.AsyncClient, httpx.AsyncClient]: (alpaca_client, openrouter_client)

    Raises:
        httpx.HTTPError: If client initialization fails

    Example:
        @app.on_event("startup")
        async def startup_event():
            await init_http_clients()
            print("✓ HTTP clients initialized")

    Notes:
        - Safe to call multiple times (returns existing clients if already initialized)
        - Clients automatically manage connection pooling and lifecycle
        - Connections are created on-demand up to max_connections limit
    """
    global _alpaca_client, _openrouter_client, _config

    if _alpaca_client is not None and _openrouter_client is not None:
        logger.info("HTTP clients already initialized, returning existing clients")
        return _alpaca_client, _openrouter_client

    # Load configuration
    _config = HttpClientConfig()
    logger.info(f"Initializing HTTP clients with config: {_config}")

    try:
        # Create httpx Limits and Timeout objects
        limits = httpx.Limits(**_config.get_limits())
        timeout = httpx.Timeout(**_config.get_timeout())

        # Create Alpaca API client
        _alpaca_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=_config.http2_enabled,
            follow_redirects=True,
        )

        # Create OpenRouter API client
        _openrouter_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=_config.http2_enabled,
            follow_redirects=True,
        )

        logger.info("✓ HTTP clients initialized successfully")
        logger.info(f"  Alpaca client: max_connections={_config.max_connections}")
        logger.info(f"  OpenRouter client: max_connections={_config.max_connections}")
        logger.info(f"  Connection pooling: enabled (keepalive={_config.keepalive_expiry}s)")
        logger.info(f"  HTTP/2 support: {_config.http2_enabled}")

        return _alpaca_client, _openrouter_client

    except Exception as e:
        logger.error(f"✗ Failed to initialize HTTP clients: {e}", exc_info=True)
        _alpaca_client = None
        _openrouter_client = None
        _config = None
        raise


def get_alpaca_client() -> httpx.AsyncClient:
    """
    Get the global Alpaca HTTP client.

    Returns:
        httpx.AsyncClient: The global Alpaca client

    Raises:
        RuntimeError: If clients have not been initialized (call init_http_clients() first)

    Example:
        async def fetch_quote(symbol: str):
            client = get_alpaca_client()
            response = await client.get(f"/v2/stocks/{symbol}/quotes/latest")
            return response.json()
    """
    if _alpaca_client is None:
        raise RuntimeError(
            "HTTP clients not initialized. Call init_http_clients() first "
            "(typically in FastAPI startup event)."
        )
    return _alpaca_client


def get_openrouter_client() -> httpx.AsyncClient:
    """
    Get the global OpenRouter HTTP client.

    Returns:
        httpx.AsyncClient: The global OpenRouter client

    Raises:
        RuntimeError: If clients have not been initialized (call init_http_clients() first)

    Example:
        async def query_model(prompt: str):
            client = get_openrouter_client()
            response = await client.post(
                "/api/v1/chat/completions",
                json={"prompt": prompt}
            )
            return response.json()
    """
    if _openrouter_client is None:
        raise RuntimeError(
            "HTTP clients not initialized. Call init_http_clients() first "
            "(typically in FastAPI startup event)."
        )
    return _openrouter_client


async def close_http_clients() -> None:
    """
    Close all HTTP clients and release resources.

    Should be called during FastAPI shutdown event. Gracefully closes all
    HTTP connections and releases resources.

    Example:
        @app.on_event("shutdown")
        async def shutdown_event():
            await close_http_clients()
            print("✓ HTTP clients closed")

    Notes:
        - Safe to call multiple times (no-op if clients already closed)
        - Waits for active connections to complete before closing
        - Releases all resources held by the clients
    """
    global _alpaca_client, _openrouter_client, _config

    if _alpaca_client is None and _openrouter_client is None:
        logger.info("HTTP clients not initialized, nothing to close")
        return

    try:
        logger.info("Closing HTTP clients...")

        # Close Alpaca client
        if _alpaca_client is not None:
            await _alpaca_client.aclose()
            logger.info("  ✓ Alpaca HTTP client closed")

        # Close OpenRouter client
        if _openrouter_client is not None:
            await _openrouter_client.aclose()
            logger.info("  ✓ OpenRouter HTTP client closed")

        logger.info("✓ HTTP clients closed successfully")

    except Exception as e:
        logger.error(f"✗ Error closing HTTP clients: {e}", exc_info=True)

    finally:
        # Clear the global client references
        _alpaca_client = None
        _openrouter_client = None
        _config = None


def get_config() -> Optional[HttpClientConfig]:
    """
    Get the current HTTP client configuration.

    Returns:
        HttpClientConfig or None: The configuration if clients are initialized

    Notes:
        - Useful for debugging and monitoring
        - Returns None if clients not yet initialized
    """
    return _config


async def check_http_clients_health() -> dict:
    """
    Check the health and status of HTTP clients.

    Returns:
        dict: HTTP clients health status including:
            - status: "healthy", "degraded", or "unavailable"
            - alpaca_client: Status of Alpaca client
            - openrouter_client: Status of OpenRouter client
            - error: Error message if unhealthy

    Example:
        health = await check_http_clients_health()
        if health["status"] != "healthy":
            logger.warning(f"HTTP clients unhealthy: {health}")

    Notes:
        - Used by health check endpoints
        - Safe to call frequently (lightweight operation)
        - Checks if clients are initialized and not closed
    """
    if _alpaca_client is None and _openrouter_client is None:
        return {
            "status": "unavailable",
            "error": "HTTP clients not initialized"
        }

    try:
        # Check client status
        alpaca_status = "closed" if _alpaca_client is None or _alpaca_client.is_closed else "open"
        openrouter_status = "closed" if _openrouter_client is None or _openrouter_client.is_closed else "open"

        # Determine overall status
        if alpaca_status == "open" and openrouter_status == "open":
            status = "healthy"
        elif alpaca_status == "open" or openrouter_status == "open":
            status = "degraded"
        else:
            status = "unavailable"

        return {
            "status": status,
            "alpaca_client": {
                "status": alpaca_status,
                "http2": _config.http2_enabled if _config else None,
                "max_connections": _config.max_connections if _config else None,
            },
            "openrouter_client": {
                "status": openrouter_status,
                "http2": _config.http2_enabled if _config else None,
                "max_connections": _config.max_connections if _config else None,
            },
        }

    except Exception as e:
        logger.error(f"HTTP clients health check failed: {e}", exc_info=True)
        return {
            "status": "degraded",
            "error": str(e),
        }
