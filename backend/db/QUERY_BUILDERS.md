# Query Builders Usage Guide

This document provides examples for using the typed query builders in `backend/db/query_builders.py`.

## Overview

The query builders provide a type-safe, fluent interface for constructing SQL queries. They automatically manage parameter placeholders and help prevent SQL injection vulnerabilities.

## Installation

The query builders are automatically available when you import from `backend.db`:

```python
from backend.db import SelectQuery, build_upsert, build_batch_upsert
from backend.db_helpers import fetch_all, execute, execute_many
```

## SelectQuery - Fluent Query Builder

### Basic SELECT

```python
from backend.db import SelectQuery
from backend.db_helpers import fetch_all

# Simple query
query, params = SelectQuery("users").build()
users = await fetch_all(query, *params)
# SELECT * FROM users

# Select specific columns
query, params = (SelectQuery("users")
    .columns("id", "name", "email")
    .build())
users = await fetch_all(query, *params)
# SELECT id, name, email FROM users
```

### WHERE Clauses

```python
# Single WHERE
query, params = (SelectQuery("users")
    .where("active = $1", True)
    .build())
users = await fetch_all(query, *params)
# SELECT * FROM users WHERE (active = $1)

# Multiple WHERE (combined with AND)
query, params = (SelectQuery("users")
    .where("active = $1", True)
    .where("role = $1", "admin")
    .order_by("created_at DESC")
    .build())
users = await fetch_all(query, *params)
# SELECT * FROM users WHERE (active = $1) AND (role = $2) ORDER BY created_at DESC

# Note: Each where() clause uses $1, $2, etc. counting from 1
# The builder automatically renumbers them across all clauses
```

### ORDER BY, LIMIT, OFFSET

```python
# Pagination
query, params = (SelectQuery("users")
    .columns("id", "name")
    .where("active = $1", True)
    .order_by("created_at DESC")
    .limit(20)
    .offset(40)
    .build())
users = await fetch_all(query, *params)
# SELECT id, name FROM users WHERE (active = $1) ORDER BY created_at DESC LIMIT 20 OFFSET 40
```

### DISTINCT

```python
# Get unique symbols
query, params = (SelectQuery("daily_bars")
    .columns("symbol")
    .distinct()
    .order_by("symbol ASC")
    .build())
symbols = await fetch_all(query, *params)
# SELECT DISTINCT symbol FROM daily_bars ORDER BY symbol ASC
```

## UPSERT Operations

### Single UPSERT

```python
from backend.db import build_upsert
from backend.db_helpers import execute

# Insert or update a daily bar
query, params = build_upsert(
    table="daily_bars",
    conflict_columns=["symbol", "date"],
    data={
        "symbol": "SPY",
        "date": "2025-01-20",
        "open": 548.50,
        "high": 552.00,
        "low": 547.00,
        "close": 550.25,
        "volume": 100000
    },
    update_columns=["open", "high", "low", "close", "volume"]
)
await execute(query, *params)

# Generates:
# INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
# VALUES ($1, $2, $3, $4, $5, $6, $7)
# ON CONFLICT (symbol, date) DO UPDATE SET
#     open = EXCLUDED.open,
#     high = EXCLUDED.high,
#     low = EXCLUDED.low,
#     close = EXCLUDED.close,
#     volume = EXCLUDED.volume
```

### Batch UPSERT

```python
from backend.db import build_batch_upsert
from backend.db_helpers import execute_many

# Insert or update multiple rows
query, args_list = build_batch_upsert(
    table="daily_bars",
    conflict_columns=["symbol", "date"],
    rows=[
        {"symbol": "SPY", "date": "2025-01-20", "close": 550.25, "volume": 100000},
        {"symbol": "QQQ", "date": "2025-01-20", "close": 450.10, "volume": 80000},
        {"symbol": "IWM", "date": "2025-01-20", "close": 210.50, "volume": 60000}
    ],
    update_columns=["close", "volume"]
)

# Execute in batch (more efficient)
await execute_many(query, args_list)

# Or execute one by one (less efficient but simpler)
for args in args_list:
    await execute(query, *args)
```

## Common Query Patterns

### Latest Date for Symbol

```python
from backend.db import build_latest_by_date
from backend.db_helpers import fetch_val

# Get latest date for a specific symbol
query, params = build_latest_by_date("daily_bars", symbol_value="SPY")
latest_date = await fetch_val(query, *params)
# SELECT MAX(date) FROM daily_bars WHERE symbol = $1

# Get latest date across all symbols
query, params = build_latest_by_date("daily_bars")
latest_date = await fetch_val(query, *params)
# SELECT MAX(date) FROM daily_bars
```

### Date Range Query

```python
from backend.db import build_date_range_query
from backend.db_helpers import fetch_all

# Get data for a symbol within date range
query, params = build_date_range_query(
    table="daily_bars",
    start_date="2025-01-01",
    end_date="2025-01-31",
    symbol="SPY",
    order_by="date ASC"
)
bars = await fetch_all(query, *params)
# SELECT * FROM daily_bars WHERE date >= $1 AND date <= $2 AND symbol = $3 ORDER BY date ASC

# Without symbol filter
query, params = build_date_range_query(
    table="daily_bars",
    start_date="2025-01-01",
    end_date="2025-01-31"
)
all_bars = await fetch_all(query, *params)
```

### Count Query

```python
from backend.db import build_count_query
from backend.db_helpers import fetch_val

# Count all rows
query, params = build_count_query("daily_bars")
total_count = await fetch_val(query, *params)
# SELECT COUNT(*) FROM daily_bars

# Count with filter
query, params = build_count_query(
    table="daily_bars",
    where_clause="symbol = $1 AND date >= $2",
    params=("SPY", "2025-01-01")
)
spy_count = await fetch_val(query, *params)
# SELECT COUNT(*) FROM daily_bars WHERE symbol = $1 AND date >= $2
```

## Real-World Examples

### Fetch Market Snapshot for Research

```python
from backend.db import SelectQuery, build_latest_by_date
from backend.db_helpers import fetch_all, fetch_val

async def get_market_snapshot_for_research(symbols: List[str]) -> Dict[str, Any]:
    """Get latest market data for all symbols."""

    # Get latest available date
    query, params = build_latest_by_date("daily_bars")
    latest_date = await fetch_val(query, *params)

    # Fetch data for all symbols on that date
    query, params = (SelectQuery("daily_bars")
        .where("date = $1", latest_date)
        .where("symbol = ANY($1)", symbols)
        .order_by("symbol ASC")
        .build())

    bars = await fetch_all(query, *params)

    return {
        "date": latest_date,
        "bars": bars
    }
```

### Update Daily Bars from API

```python
from backend.db import build_batch_upsert
from backend.db_helpers import execute_many

async def update_daily_bars(bars_data: List[Dict[str, Any]]):
    """Update daily bars using batch upsert."""

    # Build batch upsert query
    query, args_list = build_batch_upsert(
        table="daily_bars",
        conflict_columns=["symbol", "date"],
        rows=bars_data,
        update_columns=["open", "high", "low", "close", "volume"]
    )

    # Execute in batch
    await execute_many(query, args_list)

    print(f"Updated {len(args_list)} bars")
```

### Query Recent Performance

```python
from backend.db import build_date_range_query, SelectQuery
from backend.db_helpers import fetch_all

async def get_recent_performance(symbol: str, days: int = 30):
    """Get recent performance data for a symbol."""

    # Calculate date range
    from datetime import datetime, timedelta
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Fetch bars in date range
    query, params = build_date_range_query(
        table="daily_bars",
        start_date=str(start_date),
        end_date=str(end_date),
        symbol=symbol,
        order_by="date DESC"
    )

    bars = await fetch_all(query, *params)

    # Calculate metrics
    if len(bars) > 0:
        first_close = bars[-1]["close"]
        last_close = bars[0]["close"]
        return_pct = ((last_close - first_close) / first_close) * 100

        return {
            "symbol": symbol,
            "days": len(bars),
            "return_pct": return_pct,
            "bars": bars
        }

    return None
```

## Benefits

1. **Type Safety**: Better IDE autocomplete and type checking
2. **SQL Injection Prevention**: Automatic parameter binding
3. **Maintainability**: Easier to read and modify queries
4. **Consistency**: Standardized query patterns across codebase
5. **Testing**: Easy to unit test query generation without database

## Best Practices

1. **Always use placeholders** for values (never string interpolation)
2. **Use specific columns** instead of SELECT * when possible
3. **Add indexes** for columns used in WHERE clauses
4. **Use batch operations** for multiple inserts/updates
5. **Validate identifiers** when building queries from user input

## Advanced: Custom Validation

```python
from backend.db import validate_identifier

# Validate user-provided table/column names
table_name = user_input.strip()
if not validate_identifier(table_name):
    raise ValueError(f"Invalid table name: {table_name}")

# Safe to use now
query, params = SelectQuery(table_name).build()
```

## Migration from psycopg2

**Before (psycopg2):**
```python
import psycopg2

conn = psycopg2.connect(...)
cur = conn.cursor()
cur.execute(
    "SELECT * FROM users WHERE active = %s AND role = %s ORDER BY created_at DESC LIMIT %s",
    (True, "admin", 10)
)
users = cur.fetchall()
cur.close()
conn.close()
```

**After (asyncpg with query builders):**
```python
from backend.db import SelectQuery
from backend.db_helpers import fetch_all

query, params = (SelectQuery("users")
    .where("active = $1", True)
    .where("role = $1", "admin")
    .order_by("created_at DESC")
    .limit(10)
    .build())
users = await fetch_all(query, *params)
```

## Further Reading

- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQL Injection Prevention](https://owasp.org/www-community/attacks/SQL_Injection)
