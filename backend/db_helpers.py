"""Async database helper utilities using asyncpg connection pool.

This module provides high-level async utilities for common database operations,
abstracting away connection pool management and providing a clean API for
querying PostgreSQL.

Architecture:
    - All functions are async and use the global connection pool
    - Connection acquisition/release is automatic via context managers
    - Results are returned as dicts (similar to RealDictCursor behavior)
    - Transactions are supported via async context manager
    - Proper error handling and resource cleanup

Usage Examples:
    # Fetch single row
    user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)

    # Fetch all rows
    users = await fetch_all("SELECT * FROM users WHERE active = $1", True)

    # Execute INSERT/UPDATE/DELETE
    await execute(
        "INSERT INTO users (name, email) VALUES ($1, $2)",
        "Alice", "alice@example.com"
    )

    # Batch operations
    await execute_many(
        "INSERT INTO logs (message, level) VALUES ($1, $2)",
        [("Error occurred", "ERROR"), ("Info message", "INFO")]
    )

    # Transactions
    async with transaction() as conn:
        await conn.execute("UPDATE accounts SET balance = balance - $1 WHERE id = $2", 100, 1)
        await conn.execute("UPDATE accounts SET balance = balance + $1 WHERE id = $2", 100, 2)

Notes:
    - Uses $1, $2, $3 parameter placeholders (asyncpg format), not %s (psycopg2 format)
    - All database operations automatically return connections to the pool
    - Query timeout is configured at pool level (default: 60s)
    - For complex queries, consider using the pool directly for fine-grained control
"""

import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from contextlib import asynccontextmanager
import asyncpg

from backend.db.pool import get_pool

logger = logging.getLogger(__name__)


# ============================================================================
# FETCH OPERATIONS (SELECT)
# ============================================================================

async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """
    Fetch a single row from the database.

    Args:
        query: SQL query with $1, $2, ... placeholders
        *args: Query parameters

    Returns:
        Dict with column names as keys, or None if no row found

    Example:
        user = await fetch_one("SELECT * FROM users WHERE id = $1", 42)
        if user:
            print(f"Found user: {user['name']}")

    Notes:
        - Returns None if query produces no rows
        - Automatically converts asyncpg.Record to dict
        - Connection is automatically returned to pool after query
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    except Exception as e:
        logger.error(f"Error in fetch_one: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """
    Fetch all rows from the database.

    Args:
        query: SQL query with $1, $2, ... placeholders
        *args: Query parameters

    Returns:
        List of dicts with column names as keys (empty list if no rows)

    Example:
        active_users = await fetch_all(
            "SELECT * FROM users WHERE active = $1 ORDER BY created_at DESC",
            True
        )
        for user in active_users:
            print(user['name'])

    Notes:
        - Returns empty list if query produces no rows
        - All rows are loaded into memory (use with caution for large result sets)
        - Connection is automatically returned to pool after query
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error in fetch_all: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise


async def fetch_val(query: str, *args) -> Any:
    """
    Fetch a single value from the database.

    Args:
        query: SQL query with $1, $2, ... placeholders (should return single column)
        *args: Query parameters

    Returns:
        The value from the first column of the first row, or None if no row

    Example:
        count = await fetch_val("SELECT COUNT(*) FROM users WHERE active = $1", True)
        print(f"Active users: {count}")

        max_id = await fetch_val("SELECT MAX(id) FROM users")

    Notes:
        - Useful for COUNT, MAX, MIN, aggregate queries
        - Returns None if query produces no rows
        - Only returns the first column value (other columns are ignored)
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    except Exception as e:
        logger.error(f"Error in fetch_val: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise


# ============================================================================
# EXECUTE OPERATIONS (INSERT/UPDATE/DELETE)
# ============================================================================

async def execute(query: str, *args) -> str:
    """
    Execute a query that modifies data (INSERT/UPDATE/DELETE).

    Args:
        query: SQL query with $1, $2, ... placeholders
        *args: Query parameters

    Returns:
        Status string from database (e.g., "INSERT 0 1", "UPDATE 5", "DELETE 2")

    Example:
        # Insert
        await execute(
            "INSERT INTO users (name, email) VALUES ($1, $2)",
            "Alice", "alice@example.com"
        )

        # Update
        status = await execute(
            "UPDATE users SET active = $1 WHERE id = $2",
            False, 42
        )
        print(status)  # "UPDATE 1"

        # Delete
        await execute("DELETE FROM logs WHERE created_at < $1", cutoff_date)

    Notes:
        - For single INSERT/UPDATE/DELETE operations
        - For batch operations, use execute_many() instead
        - Connection is automatically returned to pool after query
        - Query runs in autocommit mode (no explicit transaction)
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    except Exception as e:
        logger.error(f"Error in execute: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise


async def execute_many(query: str, args_list: List[tuple]) -> None:
    """
    Execute a query multiple times with different parameters (batch operation).

    Args:
        query: SQL query with $1, $2, ... placeholders
        args_list: List of tuples, each containing parameters for one execution

    Returns:
        None

    Example:
        # Batch insert
        await execute_many(
            "INSERT INTO logs (level, message) VALUES ($1, $2)",
            [
                ("INFO", "Server started"),
                ("ERROR", "Connection failed"),
                ("DEBUG", "Processing request"),
            ]
        )

        # Batch update
        await execute_many(
            "UPDATE products SET price = $1 WHERE id = $2",
            [(99.99, 1), (149.99, 2), (79.99, 3)]
        )

    Notes:
        - Much more efficient than calling execute() in a loop
        - All operations run in a single transaction (all succeed or all fail)
        - Ideal for bulk inserts/updates
        - For very large batches (>1000 rows), consider using COPY instead
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            await conn.executemany(query, args_list)

    except Exception as e:
        logger.error(f"Error in execute_many: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Batch size: {len(args_list)}")
        raise


# ============================================================================
# TRANSACTION MANAGEMENT
# ============================================================================

@asynccontextmanager
async def transaction() -> AsyncIterator[asyncpg.Connection]:
    """
    Async context manager for database transactions.

    Yields:
        asyncpg.Connection: Database connection with active transaction

    Raises:
        Exception: If transaction fails (automatically rolled back)

    Example:
        # Transfer money between accounts
        async with transaction() as conn:
            await conn.execute(
                "UPDATE accounts SET balance = balance - $1 WHERE id = $2",
                100.0, sender_id
            )
            await conn.execute(
                "UPDATE accounts SET balance = balance + $1 WHERE id = $2",
                100.0, receiver_id
            )
            # Commits automatically on success

        # On exception, transaction is automatically rolled back

    Notes:
        - Transaction is committed automatically on successful exit
        - Transaction is rolled back automatically on exception
        - Use conn.execute(), conn.fetch(), etc. within the transaction
        - Nested transactions are supported (savepoints)
        - Connection is automatically returned to pool after transaction
    """
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                yield conn
            except Exception as e:
                logger.error(f"Transaction failed: {e}", exc_info=True)
                # Rollback happens automatically via conn.transaction()
                raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def execute_with_returning(query: str, *args) -> Optional[Dict[str, Any]]:
    """
    Execute INSERT/UPDATE/DELETE with RETURNING clause.

    Args:
        query: SQL query with RETURNING clause
        *args: Query parameters

    Returns:
        Dict with returned column values, or None if no row returned

    Example:
        # Get auto-generated ID
        result = await execute_with_returning(
            "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, created_at",
            "Alice", "alice@example.com"
        )
        print(f"Created user with ID: {result['id']}")

        # Update and get old value
        old_value = await execute_with_returning(
            "UPDATE settings SET value = $1 WHERE key = $2 RETURNING value",
            "new_value", "setting_key"
        )

    Notes:
        - Combines execute() and fetch_one() in a single operation
        - Useful for getting auto-generated IDs or old values
        - Returns None if query affects no rows
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    except Exception as e:
        logger.error(f"Error in execute_with_returning: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Args: {args}")
        raise


async def execute_many_with_returning(query: str, args_list: List[tuple]) -> List[Dict[str, Any]]:
    """
    Execute batch operation with RETURNING clause.

    Args:
        query: SQL query with RETURNING clause
        args_list: List of tuples, each containing parameters for one execution

    Returns:
        List of dicts with returned values

    Example:
        # Batch insert with IDs
        results = await execute_many_with_returning(
            "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
            [("Alice", "alice@example.com"), ("Bob", "bob@example.com")]
        )
        for result in results:
            print(f"Created user ID: {result['id']}")

    Notes:
        - Returns list of results in same order as input
        - All operations run in a single transaction
        - Useful for bulk inserts that need generated IDs
    """
    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                results = []
                for args in args_list:
                    row = await conn.fetchrow(query, *args)
                    if row:
                        results.append(dict(row))
                return results

    except Exception as e:
        logger.error(f"Error in execute_many_with_returning: {e}", exc_info=True)
        logger.error(f"Query: {query}")
        logger.error(f"Batch size: {len(args_list)}")
        raise
