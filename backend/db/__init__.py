"""Database access layer for LLM Trading.

This module provides async connection pooling and database utilities.

Main exports:
- DatabaseConfig: Pool configuration
- init_pool: Initialize connection pool (call on startup)
- get_pool: Get the connection pool
- close_pool: Close connection pool (call on shutdown)
- check_pool_health: Health check for monitoring

For database queries, use the helper functions in backend/db_helpers.py:
- fetch_one, fetch_all, fetch_val, execute, transaction

For advanced queries, use query builders:
- SelectQuery, build_upsert, build_batch_upsert, etc.

⚠️ Note: get_connection and DatabaseConnection are deprecated legacy utilities
using psycopg2. They are no longer exported. Use the async pool instead.
"""

from .pool import (
    DatabaseConfig,
    init_pool,
    get_pool,
    close_pool,
    get_config,
    check_pool_health,
)
from .query_builders import (
    SelectQuery,
    build_upsert,
    build_batch_upsert,
    build_latest_by_date,
    build_date_range_query,
    build_count_query,
    validate_identifier,
)

__all__ = [
    # Connection pool (main API)
    "DatabaseConfig",
    "init_pool",
    "get_pool",
    "close_pool",
    "get_config",
    "check_pool_health",
    # Query builders (optional helpers)
    "SelectQuery",
    "build_upsert",
    "build_batch_upsert",
    "build_latest_by_date",
    "build_date_range_query",
    "build_count_query",
    "validate_identifier",
]
