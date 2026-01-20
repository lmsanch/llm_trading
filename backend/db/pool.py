"""Async PostgreSQL connection pool management using asyncpg.

This module provides a singleton connection pool for efficient database access
throughout the application. The pool is initialized on FastAPI startup and
closed on shutdown.

Architecture:
    - Singleton pattern for connection pool (one pool per application)
    - Async/await based using asyncpg for non-blocking I/O
    - Automatic connection reuse and lifecycle management
    - Configurable pool size and timeouts

Usage:
    # In FastAPI startup event
    await init_pool()

    # In application code
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM table")

    # In FastAPI shutdown event
    await close_pool()

Environment Variables:
    DATABASE_URL: Full PostgreSQL connection string (preferred)
        Example: postgresql://user:pass@localhost:5432/dbname
    Or individual components:
        DATABASE_NAME: Database name (default: llm_trading)
        DATABASE_USER: Database user (default: luis)
        DATABASE_HOST: Database host (default: localhost)
        DATABASE_PORT: Database port (default: 5432)
        DATABASE_PASSWORD: Database password (optional)

    Pool configuration:
        DB_MIN_POOL_SIZE: Minimum connections (default: 10)
        DB_MAX_POOL_SIZE: Maximum connections (default: 50)
        DB_COMMAND_TIMEOUT: Query timeout in seconds (default: 60)
        DB_MAX_QUERIES: Queries per connection before recycling (default: 50000)
        DB_MAX_INACTIVE_CONNECTION_LIFETIME: Max idle time in seconds (default: 300)
"""

import os
import logging
from typing import Optional
import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration for PostgreSQL connection pool.

    Loads settings from environment variables with sensible defaults.
    Supports both DATABASE_URL connection string and individual parameters.
    """

    def __init__(self):
        """Initialize database configuration from environment variables."""
        # Connection parameters
        self.database_url = os.getenv("DATABASE_URL")

        # Individual connection components (used if DATABASE_URL not provided)
        self.database_name = os.getenv("DATABASE_NAME", "llm_trading")
        self.database_user = os.getenv("DATABASE_USER", "luis")
        self.database_host = os.getenv("DATABASE_HOST", "localhost")
        self.database_port = int(os.getenv("DATABASE_PORT", "5432"))
        self.database_password = os.getenv("DATABASE_PASSWORD")

        # Pool configuration
        self.min_pool_size = int(os.getenv("DB_MIN_POOL_SIZE", "10"))
        self.max_pool_size = int(os.getenv("DB_MAX_POOL_SIZE", "50"))
        self.command_timeout = float(os.getenv("DB_COMMAND_TIMEOUT", "60.0"))
        self.max_queries = int(os.getenv("DB_MAX_QUERIES", "50000"))
        self.max_inactive_connection_lifetime = float(
            os.getenv("DB_MAX_INACTIVE_CONNECTION_LIFETIME", "300.0")
        )

    def get_dsn(self) -> str:
        """
        Get PostgreSQL DSN (Data Source Name) for connection.

        Returns:
            str: PostgreSQL connection DSN

        Notes:
            - If DATABASE_URL is set, uses that
            - Otherwise constructs DSN from individual components
            - Password is optional
        """
        if self.database_url:
            return self.database_url

        # Construct DSN from components
        dsn_parts = [
            f"postgresql://{self.database_user}",
        ]

        if self.database_password:
            dsn_parts[0] += f":{self.database_password}"

        dsn_parts[0] += f"@{self.database_host}:{self.database_port}/{self.database_name}"

        return dsn_parts[0]

    def __repr__(self) -> str:
        """String representation (safe - no password)."""
        return (
            f"DatabaseConfig("
            f"host={self.database_host}, "
            f"port={self.database_port}, "
            f"database={self.database_name}, "
            f"user={self.database_user}, "
            f"pool_size={self.min_pool_size}-{self.max_pool_size})"
        )


# Global connection pool singleton
_pool: Optional[asyncpg.Pool] = None
_config: Optional[DatabaseConfig] = None


async def init_pool() -> asyncpg.Pool:
    """
    Initialize the global async connection pool.

    Should be called once during FastAPI startup event. Creates a connection
    pool that will be reused throughout the application lifetime.

    Returns:
        asyncpg.Pool: The initialized connection pool

    Raises:
        asyncpg.PostgresError: If pool initialization fails

    Example:
        @app.on_event("startup")
        async def startup_event():
            await init_pool()
            print("✓ Database pool initialized")

    Notes:
        - Safe to call multiple times (returns existing pool if already initialized)
        - Pool automatically manages connection lifecycle
        - Connections are created on-demand up to max_pool_size
    """
    global _pool, _config

    if _pool is not None:
        logger.info("Connection pool already initialized, returning existing pool")
        return _pool

    # Load configuration
    _config = DatabaseConfig()
    logger.info(f"Initializing connection pool with config: {_config}")

    try:
        # Create the connection pool
        _pool = await asyncpg.create_pool(
            dsn=_config.get_dsn(),
            min_size=_config.min_pool_size,
            max_size=_config.max_pool_size,
            command_timeout=_config.command_timeout,
            max_queries=_config.max_queries,
            max_inactive_connection_lifetime=_config.max_inactive_connection_lifetime,
        )

        # Test the connection
        async with _pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"✓ Database pool initialized successfully")
            logger.info(f"  PostgreSQL version: {version.split(',')[0]}")
            logger.info(f"  Pool size: {_config.min_pool_size}-{_config.max_pool_size} connections")

        return _pool

    except Exception as e:
        logger.error(f"✗ Failed to initialize database pool: {e}", exc_info=True)
        _pool = None
        _config = None
        raise


def get_pool() -> asyncpg.Pool:
    """
    Get the global async connection pool.

    Returns:
        asyncpg.Pool: The global connection pool

    Raises:
        RuntimeError: If pool has not been initialized (call init_pool() first)

    Example:
        async def query_data():
            pool = get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM table")
                return rows

    Notes:
        - Pool must be initialized with init_pool() before calling this
        - Use the 'async with pool.acquire()' pattern for connection management
        - Connections are automatically returned to the pool after use
    """
    if _pool is None:
        raise RuntimeError(
            "Database pool not initialized. Call init_pool() in FastAPI startup event."
        )
    return _pool


async def close_pool() -> None:
    """
    Close the global connection pool and release all connections.

    Should be called once during FastAPI shutdown event. Gracefully closes
    all active connections and cleans up resources.

    Example:
        @app.on_event("shutdown")
        async def shutdown_event():
            await close_pool()
            print("✓ Database pool closed")

    Notes:
        - Safe to call multiple times (no-op if pool already closed)
        - Waits for active connections to finish (graceful shutdown)
        - Automatically called on application termination
    """
    global _pool, _config

    if _pool is None:
        logger.info("Connection pool already closed or not initialized")
        return

    try:
        logger.info("Closing database connection pool...")
        await _pool.close()
        logger.info("✓ Database pool closed successfully")

    except Exception as e:
        logger.error(f"Error closing database pool: {e}", exc_info=True)

    finally:
        _pool = None
        _config = None


def get_config() -> Optional[DatabaseConfig]:
    """
    Get the current database configuration.

    Returns:
        DatabaseConfig or None: The configuration if pool is initialized

    Notes:
        - Useful for debugging and monitoring
        - Returns None if pool not yet initialized
    """
    return _config


async def check_pool_health() -> dict:
    """
    Check the health and status of the connection pool.

    Returns:
        dict: Pool health status including:
            - status: "healthy", "degraded", or "unavailable"
            - pool_size: Current number of connections
            - free_connections: Number of available connections
            - error: Error message if unhealthy

    Example:
        health = await check_pool_health()
        if health["status"] != "healthy":
            logger.warning(f"Pool unhealthy: {health}")

    Notes:
        - Used by health check endpoints
        - Safe to call frequently (lightweight operation)
    """
    if _pool is None:
        return {
            "status": "unavailable",
            "error": "Pool not initialized"
        }

    try:
        # Test pool connectivity
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        # Get pool statistics
        return {
            "status": "healthy",
            "pool_size": _pool.get_size(),
            "free_connections": _pool.get_idle_size(),
            "min_size": _config.min_pool_size if _config else None,
            "max_size": _config.max_pool_size if _config else None,
        }

    except Exception as e:
        logger.error(f"Pool health check failed: {e}", exc_info=True)
        return {
            "status": "degraded",
            "error": str(e),
            "pool_size": _pool.get_size() if _pool else 0,
        }
