"""Execution events database operations.

ASYNC PATTERNS USED:
    This module demonstrates event logging with asyncpg for trade execution events.
    See backend/db/ASYNC_PATTERNS.md for complete documentation.

    Key patterns:
    - JSONB columns: Pass dicts directly (no Json() wrapper needed)
    - Complete async chain: API → Service → DB → Pool
    - All functions are async and use await
    - Parameter placeholders use $1, $2, $3 (not %s)
    - Row access uses dict keys (not numeric indices)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import async database helpers
from backend.db_helpers import fetch_one, fetch_all, fetch_val, execute

logger = logging.getLogger(__name__)


async def log_execution_event(
    week_id: str,
    event_type: str,
    account: str,
    event_data: Dict[str, Any],
    occurred_at: Optional[datetime] = None
) -> str:
    """
    Log an execution event to the database.

    Saves a trade execution event to the execution_events table for audit trail
    and analysis. Events are immutable once logged (event sourcing pattern).

    Args:
        week_id: Week identifier (YYYY-MM-DD format)
        event_type: Type of event (e.g., 'order_placed', 'order_filled', 'order_failed',
                   'order_retried', 'baseline_account_skipped')
        account: Account name (e.g., 'CHATGPT', 'COUNCIL', 'DEEPSEEK')
        event_data: Full event data as dict (will be stored as JSONB)
        occurred_at: Timestamp when event occurred (defaults to NOW() if not provided)

    Database Tables:
        - execution_events: Stores execution events with columns:
            id, week_id, event_type, account, event_data, occurred_at, created_at

    Returns:
        UUID of the created event record (as string)

    Raises:
        Exception: If database operation fails (logged and raised)

    Example:
        event_id = await log_execution_event(
            week_id="2025-01-15",
            event_type="order_placed",
            account="CHATGPT",
            event_data={
                "symbol": "SPY",
                "side": "buy",
                "qty": 10,
                "order_id": "abc123"
            }
        )
    """
    try:
        # Use NOW() if occurred_at not provided
        occurred_at = occurred_at or datetime.utcnow()

        logger.info(
            f"Logging execution event: {event_type} for account {account} (week {week_id})"
        )

        # ASYNC PATTERN: Execute INSERT with RETURNING clause
        # - Use pool.acquire() for operations that need RETURNING values
        # - Parameters use $1, $2, $3 placeholders (not %s)
        # - JSONB column (event_data): Pass dict directly (no json.dumps needed)
        # - fetchrow() returns the RETURNING result as a Record
        from backend.db.pool import get_pool
        pool = get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO execution_events
                (week_id, event_type, account, event_data, occurred_at, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id
                """,
                week_id,
                event_type,
                account,
                event_data,  # Pass dict directly for JSONB column
                occurred_at
            )
            event_id = str(row["id"]) if row else None

        logger.info(f"Execution event logged successfully: {event_id}")
        return event_id

    except Exception as e:
        logger.error(f"Error logging execution event: {e}", exc_info=True)
        raise


async def get_execution_history(
    limit: Optional[int] = 100,
    event_type: Optional[str] = None,
    account: Optional[str] = None,
    week_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get execution event history with optional filters.

    Retrieves execution events ordered by occurrence time (most recent first).
    Supports filtering by event type, account, and week.

    Args:
        limit: Maximum number of events to return (default: 100, None for unlimited)
        event_type: Filter by event type (optional)
        account: Filter by account name (optional)
        week_id: Filter by week identifier (optional)

    Returns:
        List of event dictionaries. Each dict contains:
            - id: Event UUID
            - week_id: Week identifier
            - event_type: Type of event
            - account: Account name
            - event_data: Full event data (dict)
            - occurred_at: When event occurred
            - created_at: When event was logged
        Returns empty list if no events found.

    Database Tables:
        - execution_events: Contains execution event data

    Example:
        # Get all failed orders
        failed = await get_execution_history(event_type="order_failed")

        # Get recent events for COUNCIL account
        recent = await get_execution_history(account="COUNCIL", limit=10)
    """
    try:
        # Build query with optional filters
        conditions = []
        params = []
        param_num = 1

        if event_type:
            conditions.append(f"event_type = ${param_num}")
            params.append(event_type)
            param_num += 1

        if account:
            conditions.append(f"account = ${param_num}")
            params.append(account)
            param_num += 1

        if week_id:
            conditions.append(f"week_id = ${param_num}")
            params.append(week_id)
            param_num += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = f"LIMIT ${param_num}" if limit else ""
        if limit:
            params.append(limit)

        query = f"""
            SELECT
                id,
                week_id,
                event_type,
                account,
                event_data,
                occurred_at,
                created_at
            FROM execution_events
            {where_clause}
            ORDER BY occurred_at DESC
            {limit_clause}
        """

        # ASYNC PATTERN: fetch_all returns list of dicts
        # - Row access uses dict keys: row["event_type"]
        # - JSONB columns automatically deserialized to Python dicts
        rows = await fetch_all(query, *params)

        logger.info(
            f"Retrieved {len(rows)} execution events "
            f"(filters: type={event_type}, account={account}, week={week_id})"
        )
        return rows

    except Exception as e:
        logger.error(f"Error fetching execution history: {e}", exc_info=True)
        return []


async def get_events_by_account(
    account: str,
    week_id: Optional[str] = None,
    limit: Optional[int] = 100
) -> List[Dict[str, Any]]:
    """
    Get execution events for a specific account.

    Convenience wrapper around get_execution_history() that filters by account.
    Useful for analyzing account-specific trading activity.

    Args:
        account: Account name to filter by (e.g., 'CHATGPT', 'COUNCIL')
        week_id: Optional week identifier filter
        limit: Maximum number of events to return (default: 100)

    Returns:
        List of event dictionaries for the specified account,
        ordered by occurrence time (most recent first).

    Example:
        # Get all events for COUNCIL account this week
        events = await get_events_by_account("COUNCIL", week_id="2025-01-15")
    """
    return await get_execution_history(
        limit=limit,
        account=account,
        week_id=week_id
    )


async def get_events_by_week(
    week_id: str,
    event_type: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get execution events for a specific week.

    Convenience wrapper around get_execution_history() that filters by week.
    Useful for weekly postmortem analysis and performance review.

    Args:
        week_id: Week identifier (YYYY-MM-DD format)
        event_type: Optional event type filter
        limit: Maximum number of events to return (default: unlimited for weekly view)

    Returns:
        List of event dictionaries for the specified week,
        ordered by occurrence time (most recent first).

    Example:
        # Get all events for week of 2025-01-15
        events = await get_events_by_week("2025-01-15")

        # Get only failed orders for the week
        failed = await get_events_by_week("2025-01-15", event_type="order_failed")
    """
    return await get_execution_history(
        limit=limit,
        event_type=event_type,
        week_id=week_id
    )


async def get_latest_event_by_account(account: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent execution event for an account.

    Args:
        account: Account name (e.g., 'CHATGPT', 'COUNCIL')

    Returns:
        Most recent event dict for the account, or None if no events exist.

    Example:
        latest = await get_latest_event_by_account("COUNCIL")
        if latest:
            print(f"Last event: {latest['event_type']} at {latest['occurred_at']}")
    """
    try:
        query = """
            SELECT
                id,
                week_id,
                event_type,
                account,
                event_data,
                occurred_at,
                created_at
            FROM execution_events
            WHERE account = $1
            ORDER BY occurred_at DESC
            LIMIT 1
        """

        row = await fetch_one(query, account)
        return row

    except Exception as e:
        logger.error(f"Error fetching latest event for account {account}: {e}", exc_info=True)
        return None


async def count_events_by_type(
    week_id: Optional[str] = None,
    account: Optional[str] = None
) -> Dict[str, int]:
    """
    Get count of events grouped by event type.

    Useful for analytics and monitoring - shows distribution of event types
    for troubleshooting and performance analysis.

    Args:
        week_id: Optional week identifier filter
        account: Optional account name filter

    Returns:
        Dictionary mapping event_type to count, e.g.:
        {
            "order_placed": 5,
            "order_filled": 4,
            "order_failed": 1
        }

    Example:
        # Get event counts for this week
        counts = await count_events_by_type(week_id="2025-01-15")
        print(f"Orders placed: {counts.get('order_placed', 0)}")
    """
    try:
        conditions = []
        params = []
        param_num = 1

        if week_id:
            conditions.append(f"week_id = ${param_num}")
            params.append(week_id)
            param_num += 1

        if account:
            conditions.append(f"account = ${param_num}")
            params.append(account)
            param_num += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT event_type, COUNT(*) as count
            FROM execution_events
            {where_clause}
            GROUP BY event_type
            ORDER BY count DESC
        """

        rows = await fetch_all(query, *params)

        # Convert to dict for easy lookup
        result = {row["event_type"]: row["count"] for row in rows}

        logger.info(f"Event counts retrieved: {result}")
        return result

    except Exception as e:
        logger.error(f"Error counting events by type: {e}", exc_info=True)
        return {}
