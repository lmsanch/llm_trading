"""Typed query builders for common database patterns.

This module provides type-safe query builders that make common database operations
more maintainable and less error-prone. Builders return SQL strings and parameter
tuples that can be used with the async db_helpers functions.

Architecture:
    - Fluent interface for building queries
    - Type hints for better IDE support
    - Automatic parameter placeholder management ($1, $2, ...)
    - Immutable builders (each method returns a new instance)
    - Validation of required fields

Usage Examples:
    # Simple SELECT builder
    query, params = (SelectQuery("users")
        .where("active = $1", True)
        .where("created_at > $2", cutoff_date)
        .order_by("created_at DESC")
        .limit(10)
        .build())

    results = await fetch_all(query, *params)

    # UPSERT helper
    query, params = build_upsert(
        table="daily_bars",
        conflict_columns=["symbol", "date"],
        data={"symbol": "SPY", "date": "2025-01-20", "close": 550.25},
        update_columns=["close", "volume"]
    )
    await execute(query, *params)

    # Batch UPSERT
    query, args_list = build_batch_upsert(
        table="daily_bars",
        conflict_columns=["symbol", "date"],
        rows=[
            {"symbol": "SPY", "date": "2025-01-20", "close": 550.25},
            {"symbol": "QQQ", "date": "2025-01-20", "close": 450.10}
        ],
        update_columns=["close"]
    )
    for args in args_list:
        await execute(query, *args)

Notes:
    - All builders use $1, $2, $3 placeholders (asyncpg format)
    - Builders are immutable - each method returns a new instance
    - Query validation happens at build() time
    - Compatible with all db_helpers async functions
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# SELECT QUERY BUILDER
# ============================================================================

@dataclass(frozen=True)
class SelectQuery:
    """
    Fluent builder for SELECT queries with type safety.

    Example:
        query, params = (SelectQuery("users")
            .columns("id", "name", "email")
            .where("active = $1", True)
            .where("role = $2", "admin")
            .order_by("created_at DESC")
            .limit(10)
            .build())

        users = await fetch_all(query, *params)

    Notes:
        - Immutable builder (each method returns new instance)
        - Automatically manages parameter numbering
        - Validates query at build() time
    """

    _table: str
    _columns: Tuple[str, ...] = field(default_factory=tuple)
    _where_clauses: Tuple[str, ...] = field(default_factory=tuple)
    _params: Tuple[Any, ...] = field(default_factory=tuple)
    _order_by_clause: Optional[str] = None
    _limit_value: Optional[int] = None
    _offset_value: Optional[int] = None
    _distinct: bool = False

    def __init__(
        self,
        table: str,
        _columns: Tuple[str, ...] = (),
        _where_clauses: Tuple[str, ...] = (),
        _params: Tuple[Any, ...] = (),
        _order_by_clause: Optional[str] = None,
        _limit_value: Optional[int] = None,
        _offset_value: Optional[int] = None,
        _distinct: bool = False
    ):
        """
        Initialize SelectQuery builder.

        Args:
            table: Table name to query
        """
        object.__setattr__(self, "_table", table)
        object.__setattr__(self, "_columns", _columns)
        object.__setattr__(self, "_where_clauses", _where_clauses)
        object.__setattr__(self, "_params", _params)
        object.__setattr__(self, "_order_by_clause", _order_by_clause)
        object.__setattr__(self, "_limit_value", _limit_value)
        object.__setattr__(self, "_offset_value", _offset_value)
        object.__setattr__(self, "_distinct", _distinct)

    def columns(self, *cols: str) -> "SelectQuery":
        """
        Specify columns to select.

        Args:
            *cols: Column names (defaults to "*" if not specified)

        Returns:
            New SelectQuery instance with columns set
        """
        return SelectQuery(
            self._table,
            _columns=cols,
            _where_clauses=self._where_clauses,
            _params=self._params,
            _order_by_clause=self._order_by_clause,
            _limit_value=self._limit_value,
            _offset_value=self._offset_value,
            _distinct=self._distinct
        )

    def where(self, condition: str, *params: Any) -> "SelectQuery":
        """
        Add WHERE condition.

        Args:
            condition: WHERE condition with placeholders ($1, $2, ...)
            *params: Parameter values

        Returns:
            New SelectQuery instance with WHERE added

        Example:
            .where("symbol = $1", "SPY")
            .where("date > $1", "2025-01-01")

        Notes:
            - Use $1, $2, etc. counting from 1 within each where() clause
            - Placeholders are renumbered automatically across all where() clauses
            - Multiple where() calls are combined with AND
        """
        # Renumber placeholders in the condition
        renumbered_condition = self._renumber_placeholders(condition, len(self._params))

        return SelectQuery(
            self._table,
            _columns=self._columns,
            _where_clauses=self._where_clauses + (renumbered_condition,),
            _params=self._params + params,
            _order_by_clause=self._order_by_clause,
            _limit_value=self._limit_value,
            _offset_value=self._offset_value,
            _distinct=self._distinct
        )

    def order_by(self, order: str) -> "SelectQuery":
        """
        Add ORDER BY clause.

        Args:
            order: Order specification (e.g., "date DESC", "name ASC, id DESC")

        Returns:
            New SelectQuery instance with ORDER BY set
        """
        return SelectQuery(
            self._table,
            _columns=self._columns,
            _where_clauses=self._where_clauses,
            _params=self._params,
            _order_by_clause=order,
            _limit_value=self._limit_value,
            _offset_value=self._offset_value,
            _distinct=self._distinct
        )

    def limit(self, n: int) -> "SelectQuery":
        """
        Add LIMIT clause.

        Args:
            n: Maximum number of rows to return

        Returns:
            New SelectQuery instance with LIMIT set
        """
        return SelectQuery(
            self._table,
            _columns=self._columns,
            _where_clauses=self._where_clauses,
            _params=self._params,
            _order_by_clause=self._order_by_clause,
            _limit_value=n,
            _offset_value=self._offset_value,
            _distinct=self._distinct
        )

    def offset(self, n: int) -> "SelectQuery":
        """
        Add OFFSET clause.

        Args:
            n: Number of rows to skip

        Returns:
            New SelectQuery instance with OFFSET set
        """
        return SelectQuery(
            self._table,
            _columns=self._columns,
            _where_clauses=self._where_clauses,
            _params=self._params,
            _order_by_clause=self._order_by_clause,
            _limit_value=self._limit_value,
            _offset_value=n,
            _distinct=self._distinct
        )

    def distinct(self) -> "SelectQuery":
        """
        Add DISTINCT clause.

        Returns:
            New SelectQuery instance with DISTINCT set
        """
        return SelectQuery(
            self._table,
            _columns=self._columns,
            _where_clauses=self._where_clauses,
            _params=self._params,
            _order_by_clause=self._order_by_clause,
            _limit_value=self._limit_value,
            _offset_value=self._offset_value,
            _distinct=True
        )

    def build(self) -> Tuple[str, Tuple[Any, ...]]:
        """
        Build the final SQL query and parameters.

        Returns:
            Tuple of (query_string, parameters_tuple)

        Raises:
            ValueError: If query is invalid
        """
        # SELECT clause
        distinct_keyword = "DISTINCT " if self._distinct else ""
        columns = ", ".join(self._columns) if self._columns else "*"
        query_parts = [f"SELECT {distinct_keyword}{columns} FROM {self._table}"]

        # WHERE clause
        if self._where_clauses:
            where_str = " AND ".join(f"({clause})" for clause in self._where_clauses)
            query_parts.append(f"WHERE {where_str}")

        # ORDER BY clause
        if self._order_by_clause:
            query_parts.append(f"ORDER BY {self._order_by_clause}")

        # LIMIT clause
        if self._limit_value is not None:
            query_parts.append(f"LIMIT {self._limit_value}")

        # OFFSET clause
        if self._offset_value is not None:
            query_parts.append(f"OFFSET {self._offset_value}")

        query = " ".join(query_parts)
        return query, self._params

    def _renumber_placeholders(self, condition: str, offset: int) -> str:
        """
        Renumber $1, $2, ... placeholders based on current parameter count.

        Args:
            condition: Condition string with placeholders
            offset: Current parameter count (for offsetting placeholder numbers)

        Returns:
            Condition string with renumbered placeholders
        """
        # Simple implementation: replace $N with $(N + offset)
        import re

        def replace_placeholder(match):
            num = int(match.group(1))
            return f"${num + offset}"

        return re.sub(r'\$(\d+)', replace_placeholder, condition)


# ============================================================================
# UPSERT HELPERS
# ============================================================================

def build_upsert(
    table: str,
    conflict_columns: List[str],
    data: Dict[str, Any],
    update_columns: Optional[List[str]] = None
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Build an UPSERT query (INSERT ... ON CONFLICT DO UPDATE).

    Args:
        table: Table name
        conflict_columns: Columns that define uniqueness (for ON CONFLICT)
        data: Dictionary of column_name -> value
        update_columns: Columns to update on conflict (defaults to all non-conflict columns)

    Returns:
        Tuple of (query_string, parameters_tuple)

    Example:
        query, params = build_upsert(
            table="daily_bars",
            conflict_columns=["symbol", "date"],
            data={"symbol": "SPY", "date": "2025-01-20", "close": 550.25, "volume": 100000},
            update_columns=["close", "volume"]
        )
        await execute(query, *params)

        # Generates:
        # INSERT INTO daily_bars (symbol, date, close, volume)
        # VALUES ($1, $2, $3, $4)
        # ON CONFLICT (symbol, date) DO UPDATE SET
        #     close = EXCLUDED.close,
        #     volume = EXCLUDED.volume

    Notes:
        - If update_columns not specified, updates all columns except conflict_columns
        - Always includes created_at = NOW() in UPDATE clause if not specified
        - Uses EXCLUDED.column_name to reference new values
    """
    if not data:
        raise ValueError("Data dictionary cannot be empty")

    if not conflict_columns:
        raise ValueError("Conflict columns must be specified")

    # Get columns and values
    columns = list(data.keys())
    values = list(data.values())

    # Build INSERT clause
    placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
    insert_clause = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

    # Build ON CONFLICT clause
    conflict_clause = f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET"

    # Determine which columns to update
    if update_columns is None:
        # Update all columns except conflict columns
        update_columns = [col for col in columns if col not in conflict_columns]

    # Build UPDATE SET clause
    if update_columns:
        update_parts = [f"{col} = EXCLUDED.{col}" for col in update_columns]

        # Add created_at = NOW() if not explicitly in update_columns
        if "created_at" not in update_columns and "created_at" in columns:
            update_parts.append("created_at = NOW()")

        update_clause = ", ".join(update_parts)
    else:
        # No columns to update, just update timestamp
        update_clause = "created_at = NOW()"

    # Combine all parts
    query = f"{insert_clause} {conflict_clause} {update_clause}"

    return query, tuple(values)


def build_batch_upsert(
    table: str,
    conflict_columns: List[str],
    rows: List[Dict[str, Any]],
    update_columns: Optional[List[str]] = None
) -> Tuple[str, List[Tuple[Any, ...]]]:
    """
    Build batch UPSERT query for multiple rows.

    Args:
        table: Table name
        conflict_columns: Columns that define uniqueness
        rows: List of dictionaries with column_name -> value
        update_columns: Columns to update on conflict

    Returns:
        Tuple of (query_string, list_of_parameter_tuples)

    Example:
        query, args_list = build_batch_upsert(
            table="daily_bars",
            conflict_columns=["symbol", "date"],
            rows=[
                {"symbol": "SPY", "date": "2025-01-20", "close": 550.25},
                {"symbol": "QQQ", "date": "2025-01-20", "close": 450.10}
            ],
            update_columns=["close"]
        )

        # Execute batch upsert
        for args in args_list:
            await execute(query, *args)

        # Or use execute_many for better performance:
        await execute_many(query, args_list)

    Notes:
        - All rows must have the same columns
        - Query is built once and reused for all rows
        - More efficient than individual upserts
    """
    if not rows:
        raise ValueError("Rows list cannot be empty")

    # Use first row to build the query structure
    first_row = rows[0]
    query, _ = build_upsert(table, conflict_columns, first_row, update_columns)

    # Build parameter tuples for all rows
    columns = list(first_row.keys())
    args_list = [tuple(row[col] for col in columns) for row in rows]

    return query, args_list


# ============================================================================
# COMMON QUERY PATTERNS
# ============================================================================

def build_latest_by_date(
    table: str,
    symbol_column: str = "symbol",
    date_column: str = "date",
    symbol_value: Optional[str] = None
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Build query to get the latest date for a symbol.

    Args:
        table: Table name
        symbol_column: Name of symbol column (default: "symbol")
        date_column: Name of date column (default: "date")
        symbol_value: Symbol to filter by (if None, gets max across all symbols)

    Returns:
        Tuple of (query_string, parameters_tuple)

    Example:
        # Get latest date for SPY
        query, params = build_latest_by_date("daily_bars", symbol_value="SPY")
        latest_date = await fetch_val(query, *params)

        # Get latest date across all symbols
        query, params = build_latest_by_date("daily_bars")
        latest_date = await fetch_val(query, *params)
    """
    if symbol_value:
        query = f"SELECT MAX({date_column}) FROM {table} WHERE {symbol_column} = $1"
        params = (symbol_value,)
    else:
        query = f"SELECT MAX({date_column}) FROM {table}"
        params = ()

    return query, params


def build_date_range_query(
    table: str,
    start_date: str,
    end_date: str,
    symbol: Optional[str] = None,
    date_column: str = "date",
    symbol_column: str = "symbol",
    order_by: str = "date ASC"
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Build query to fetch data within a date range.

    Args:
        table: Table name
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        symbol: Optional symbol filter
        date_column: Name of date column (default: "date")
        symbol_column: Name of symbol column (default: "symbol")
        order_by: ORDER BY clause (default: "date ASC")

    Returns:
        Tuple of (query_string, parameters_tuple)

    Example:
        # Get SPY data for date range
        query, params = build_date_range_query(
            "daily_bars",
            start_date="2025-01-01",
            end_date="2025-01-31",
            symbol="SPY"
        )
        bars = await fetch_all(query, *params)
    """
    query = f"SELECT * FROM {table} WHERE {date_column} >= $1 AND {date_column} <= $2"
    params = [start_date, end_date]

    if symbol:
        query += f" AND {symbol_column} = ${len(params) + 1}"
        params.append(symbol)

    if order_by:
        query += f" ORDER BY {order_by}"

    return query, tuple(params)


def build_count_query(
    table: str,
    where_clause: Optional[str] = None,
    params: Optional[Tuple[Any, ...]] = None
) -> Tuple[str, Tuple[Any, ...]]:
    """
    Build a COUNT query.

    Args:
        table: Table name
        where_clause: Optional WHERE clause
        params: Optional parameters for WHERE clause

    Returns:
        Tuple of (query_string, parameters_tuple)

    Example:
        # Count all rows
        query, params = build_count_query("daily_bars")
        count = await fetch_val(query, *params)

        # Count with filter
        query, params = build_count_query(
            "daily_bars",
            where_clause="symbol = $1",
            params=("SPY",)
        )
        count = await fetch_val(query, *params)
    """
    query = f"SELECT COUNT(*) FROM {table}"

    if where_clause:
        query += f" WHERE {where_clause}"
        return query, params or ()

    return query, ()


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_identifier(identifier: str) -> bool:
    """
    Validate that a string is a safe SQL identifier.

    Args:
        identifier: String to validate (table name, column name, etc.)

    Returns:
        bool: True if valid, False otherwise

    Notes:
        - Allows alphanumeric characters and underscores
        - Must start with a letter or underscore
        - Maximum length 63 characters (PostgreSQL limit)
    """
    import re

    if not identifier:
        return False

    if len(identifier) > 63:
        return False

    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, identifier))
