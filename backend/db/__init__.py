"""Database access layer for LLM Trading."""

from .database import get_connection, DatabaseConnection
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
    "get_connection",
    "DatabaseConnection",
    "DatabaseConfig",
    "init_pool",
    "get_pool",
    "close_pool",
    "get_config",
    "check_pool_health",
    "SelectQuery",
    "build_upsert",
    "build_batch_upsert",
    "build_latest_by_date",
    "build_date_range_query",
    "build_count_query",
    "validate_identifier",
]
