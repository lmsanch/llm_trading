# Async Database Patterns Guide

This guide documents async patterns used in the LLM Trading codebase after migrating from psycopg2 to asyncpg.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Pattern 1: Basic Async Query](#pattern-1-basic-async-query)
3. [Pattern 2: Service Layer Integration](#pattern-2-service-layer-integration)
4. [Pattern 3: Transaction Management](#pattern-3-transaction-management)
5. [Pattern 4: Batch Operations](#pattern-4-batch-operations)
6. [Pattern 5: JSONB Data Handling](#pattern-5-jsonb-data-handling)
7. [Common Gotchas](#common-gotchas)
8. [Migration Checklist](#migration-checklist)

---

## Quick Reference

### psycopg2 → asyncpg Cheat Sheet

| Aspect | psycopg2 (Old) | asyncpg (New) |
|--------|----------------|---------------|
| **Function type** | `def function()` | `async def function()` |
| **Calling** | `result = function()` | `result = await function()` |
| **Parameters** | `%s, %s, %s` | `$1, $2, $3` |
| **Connection** | `psycopg2.connect()` | `pool.acquire()` context |
| **Row access** | `row[0], row[1]` | `row["column"]` |
| **JSONB** | `Json(data)` | `data` (direct dict) |
| **Cursor** | `cursor.execute()` | Use helpers or `conn.execute()` |

### Helper Functions Quick Start

```python
from backend.db_helpers import fetch_one, fetch_all, fetch_val, execute

# Fetch single row (returns dict or None)
user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)

# Fetch all rows (returns list of dicts)
users = await fetch_all("SELECT * FROM users WHERE active = $1", True)

# Fetch single value (returns scalar)
count = await fetch_val("SELECT COUNT(*) FROM users")

# Execute INSERT/UPDATE/DELETE
await execute("INSERT INTO logs (message) VALUES ($1)", "Hello")
```

---

## Pattern 1: Basic Async Query

### ❌ Old Pattern (psycopg2)

```python
import psycopg2
from psycopg2.extras import RealDictCursor

def get_user(user_id):
    # Opens new connection every time (expensive!)
    conn = psycopg2.connect(...)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Uses %s placeholders
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        conn.close()  # Must manually close
```

**Problems:**
- 🐌 New connection every call (TCP handshake, auth overhead)
- 🔒 Blocks event loop (synchronous I/O)
- 🧹 Manual connection management (error-prone)
- 📝 Verbose boilerplate code

### ✅ New Pattern (asyncpg)

```python
from backend.db_helpers import fetch_one

async def get_user(user_id):
    # Uses connection pool (reuses connections)
    # Automatically acquires and releases connection
    # Non-blocking I/O (doesn't block event loop)
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

**Benefits:**
- ⚡ 50-90% faster (connection reuse)
- 🚀 Non-blocking (doesn't block event loop)
- 🎯 Clean, concise code
- 🛡️ Automatic error handling and cleanup

### Key Points

1. **Always use `async def`** for functions that access database
2. **Always `await`** database operations (returns a coroutine)
3. **Use `$1, $2, $3`** parameter placeholders (not `%s`)
4. **Access rows with dict keys** (not numeric indices)

---

## Pattern 2: Service Layer Integration

### Complete Async Chain

For a database query to work properly, **every layer must be async**:

```
API Route (async) → Service Method (async) → DB Function (async) → Pool
```

If any layer is **not async** or **doesn't await**, the chain breaks!

### ❌ Broken Chain

```python
# API Route (async)
@router.get("/users/{id}")
async def get_user_endpoint(id: int):
    user = await user_service.get_user(id)  # ✓ Awaits
    return user

# Service (async but doesn't await!)
class UserService:
    async def get_user(self, user_id: int):
        # ❌ BROKEN: Forgot to await!
        # Returns a coroutine, not the actual result
        user = get_user_from_db(user_id)
        return user  # Returns <coroutine object>, not dict!

# DB Function (async)
async def get_user_from_db(user_id: int):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

**Error:** `RuntimeWarning: coroutine 'get_user_from_db' was never awaited`

### ✅ Correct Chain

```python
# API Route (async)
@router.get("/users/{id}")
async def get_user_endpoint(id: int):
    user = await user_service.get_user(id)  # ✓ Awaits
    return user

# Service (async and awaits!)
class UserService:
    async def get_user(self, user_id: int):
        # ✓ CORRECT: Awaits the async function
        user = await get_user_from_db(user_id)
        return user  # Returns actual dict

# DB Function (async)
async def get_user_from_db(user_id: int):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

### Real-World Example

```python
# backend/api/market.py (API layer)
@router.get("/market/snapshot")
async def get_market_snapshot_endpoint():
    """API endpoint - must be async."""
    service = MarketService()
    snapshot = await service.get_market_snapshot()  # ✓ Awaits service
    return {"snapshot": snapshot}

# backend/services/market_service.py (Service layer)
class MarketService:
    async def get_market_snapshot(self):
        """Service method - must be async."""
        from backend.storage.data_fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        # ✓ Awaits database operation
        snapshot = await fetcher.get_market_snapshot_for_research()
        return snapshot

# backend/storage/data_fetcher.py (Data access layer)
class MarketDataFetcher:
    async def get_market_snapshot_for_research(self):
        """Data fetcher - must be async."""
        # ✓ Uses connection pool automatically
        prices = await fetch_all("SELECT * FROM daily_bars ORDER BY date DESC LIMIT 10")
        return {"prices": prices}
```

---

## Pattern 3: Transaction Management

### When to Use Transactions

Use transactions when you need **multiple operations to succeed or fail together**:

- ✓ Money transfers (debit one account, credit another)
- ✓ Multi-step data updates (delete + insert)
- ✓ Maintaining referential integrity

### ❌ Old Pattern (psycopg2)

```python
def transfer_money(from_id, to_id, amount):
    conn = psycopg2.connect(...)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE accounts SET balance = balance - %s WHERE id = %s",
            (amount, from_id)
        )
        cursor.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (amount, to_id)
        )
        conn.commit()  # Must manually commit
    except:
        conn.rollback()  # Must manually rollback
        raise
    finally:
        conn.close()
```

### ✅ New Pattern (asyncpg)

```python
from backend.db_helpers import transaction

async def transfer_money(from_id: int, to_id: int, amount: float):
    """Transfer money between accounts (atomic operation)."""
    # Context manager handles commit/rollback automatically
    async with transaction() as conn:
        # Debit sender account
        await conn.execute(
            "UPDATE accounts SET balance = balance - $1 WHERE id = $2",
            amount, from_id
        )
        # Credit receiver account
        await conn.execute(
            "UPDATE accounts SET balance = balance + $1 WHERE id = $2",
            amount, to_id
        )
        # Commits automatically on success
        # Rolls back automatically on exception
```

**Benefits:**
- 🔒 Automatic commit on success
- ↩️ Automatic rollback on exception
- 🧹 Automatic connection cleanup
- 🎯 Clear, readable code

---

## Pattern 4: Batch Operations

### When to Use Batch Operations

Use `execute_many` for inserting/updating **multiple rows**:

- ✓ Bulk inserts (logs, metrics, data imports)
- ✓ Batch updates (price updates, status changes)
- ⚠️ Not for small batches (<10 rows) - regular `execute` is fine

### ❌ Inefficient (Loop)

```python
# DON'T: Call execute in a loop (slow!)
for log_entry in log_entries:
    await execute(
        "INSERT INTO logs (level, message) VALUES ($1, $2)",
        log_entry["level"], log_entry["message"]
    )
# 100 rows = 100 round-trips to database!
```

**Problem:** Each `execute` call is a separate database operation (network round-trip).

### ✅ Efficient (Batch)

```python
from backend.db_helpers import execute_many

# DO: Use execute_many for batch operations
log_data = [
    ("INFO", "Server started"),
    ("ERROR", "Connection failed"),
    ("DEBUG", "Processing request"),
    # ... 100 more rows
]

# All rows inserted in single transaction (fast!)
await execute_many(
    "INSERT INTO logs (level, message) VALUES ($1, $2)",
    log_data
)
# 100 rows = 1 round-trip to database!
```

**Benefits:**
- ⚡ 10-100x faster for large batches
- 🔒 All operations in single transaction (atomic)
- 📦 Single network round-trip

### Real-World Example: Metrics Calculation

```python
# backend/storage/calculate_metrics.py
async def upsert_7day_log_returns(self, data_tuples: List[Tuple]):
    """
    Batch upsert 7-day log returns for all symbols.

    Uses execute_many for efficient batch operation.
    All rows succeed or fail together (transactional).
    """
    query = """
        INSERT INTO rolling_7day_log_returns (symbol, date, log_return_7d)
        VALUES ($1, $2, $3)
        ON CONFLICT (symbol, date) DO UPDATE
        SET log_return_7d = EXCLUDED.log_return_7d
    """
    # Batch operation: ~10-50 rows per call
    await execute_many(query, data_tuples)
```

---

## Pattern 5: JSONB Data Handling

### ❌ Old Pattern (psycopg2)

```python
import json
from psycopg2.extras import Json

# Had to wrap dicts with Json() adapter
data = {"key": "value", "nested": {"data": [1, 2, 3]}}
cursor.execute(
    "INSERT INTO logs (data) VALUES (%s)",
    (Json(data),)  # ❌ Required Json() wrapper
)
```

### ✅ New Pattern (asyncpg)

```python
# asyncpg automatically handles dict → JSONB conversion
data = {"key": "value", "nested": {"data": [1, 2, 3]}}

# Just pass dict directly - no wrapper needed!
await execute(
    "INSERT INTO logs (data) VALUES ($1)",
    data  # ✓ Direct dict, automatically serialized to JSONB
)
```

**Key Difference:** asyncpg automatically serializes Python dicts to JSONB and deserializes JSONB to Python dicts.

### Real-World Example: Saving PM Pitches

```python
# backend/db/pitch_db.py
async def save_pitches(week_id: str, pitches_raw: List[Dict[str, Any]]):
    """Save PM pitches with JSONB data."""
    for pitch in pitches_raw:
        # pitch is a dict - asyncpg handles JSONB conversion automatically
        await execute(
            """
            INSERT INTO pm_pitches
            (week_id, model, pitch_data, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            week_id,
            pitch.get("model"),
            pitch  # ✓ Direct dict → JSONB (no Json() wrapper!)
        )
```

### Reading JSONB Data

```python
# JSONB is automatically deserialized to Python dict
pitch = await fetch_one("SELECT * FROM pm_pitches WHERE id = $1", pitch_id)

# Access JSONB columns as regular dicts
pitch_data = pitch["pitch_data"]  # Already a dict!
conviction = pitch_data.get("conviction", 0)  # Regular dict access
```

---

## Common Gotchas

### 1. Forgetting `await`

```python
# ❌ WRONG: Returns coroutine, not result
user = fetch_one("SELECT * FROM users WHERE id = $1", 42)
print(user)  # <coroutine object fetch_one at 0x...>

# ✓ CORRECT: Awaits the coroutine
user = await fetch_one("SELECT * FROM users WHERE id = $1", 42)
print(user)  # {'id': 42, 'name': 'Alice', ...}
```

**Error:** `RuntimeWarning: coroutine 'fetch_one' was never awaited`

### 2. Wrong Parameter Placeholders

```python
# ❌ WRONG: %s is psycopg2 syntax
await fetch_one("SELECT * FROM users WHERE id = %s", 42)
# Error: syntax error at or near "%"

# ✓ CORRECT: $1, $2, $3 is asyncpg syntax
await fetch_one("SELECT * FROM users WHERE id = $1", 42)
```

### 3. Index-Based Row Access

```python
# ❌ WRONG: Rows are dicts, not tuples
row = await fetch_one("SELECT name, email FROM users WHERE id = $1", 42)
name = row[0]  # TypeError: 'dict' object is not subscriptable

# ✓ CORRECT: Use dict keys
name = row["name"]
email = row["email"]
```

### 4. Using `Json()` Wrapper

```python
from psycopg2.extras import Json

# ❌ WRONG: asyncpg doesn't need Json() wrapper
await execute("INSERT INTO logs (data) VALUES ($1)", Json(data))

# ✓ CORRECT: Pass dict directly
await execute("INSERT INTO logs (data) VALUES ($1)", data)
```

### 5. Creating Connections Manually

```python
import asyncpg

# ❌ WRONG: Never create connections manually
conn = await asyncpg.connect(...)
await conn.execute("INSERT INTO logs (message) VALUES ($1)", "test")
await conn.close()

# ✓ CORRECT: Always use the connection pool
from backend.db_helpers import execute
await execute("INSERT INTO logs (message) VALUES ($1)", "test")
```

### 6. Mixing Sync and Async Code

```python
# ❌ WRONG: Can't await in non-async function
def get_user(user_id):
    user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
    return user
# SyntaxError: 'await' outside async function

# ✓ CORRECT: Function must be async
async def get_user(user_id):
    user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
    return user
```

---

## Migration Checklist

When migrating a file from psycopg2 to asyncpg:

### 1. Update Imports

```python
# ❌ Remove
import psycopg2
from psycopg2.extras import RealDictCursor, Json

# ✓ Add
from backend.db_helpers import fetch_one, fetch_all, fetch_val, execute
```

### 2. Convert Function Signatures

```python
# ❌ Old
def get_user(user_id):

# ✓ New
async def get_user(user_id):
```

### 3. Update Database Calls

```python
# ❌ Old
conn = psycopg2.connect(...)
cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
row = cursor.fetchone()
conn.close()

# ✓ New
row = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

### 4. Fix Parameter Placeholders

```python
# ❌ Old: %s placeholders
"SELECT * FROM users WHERE id = %s AND active = %s"

# ✓ New: $1, $2 placeholders
"SELECT * FROM users WHERE id = $1 AND active = $2"
```

### 5. Update Row Access

```python
# ❌ Old: Index-based
name = row[0]
email = row[1]

# ✓ New: Dict-based
name = row["name"]
email = row["email"]
```

### 6. Remove JSONB Wrappers

```python
# ❌ Old
cursor.execute("INSERT INTO logs (data) VALUES (%s)", (Json(data),))

# ✓ New
await execute("INSERT INTO logs (data) VALUES ($1)", data)
```

### 7. Update All Callers

```python
# ❌ Old: Sync call
result = get_user(42)

# ✓ New: Async call
result = await get_user(42)
```

### 8. Verify Syntax

```bash
python -m py_compile backend/path/to/file.py
```

---

## Additional Resources

- **Main Documentation:** See `CLAUDE.md` → Database Architecture section
- **Helper Functions:** See docstrings in `backend/db_helpers.py`
- **Connection Pool:** See `backend/db/pool.py` for pool configuration
- **Real Examples:** Check any file in `backend/db/*_db.py` for conversion examples

---

## Questions?

If you're unsure about a pattern:

1. Check `backend/db/*_db.py` files for similar examples
2. Read the function docstrings in `backend/db_helpers.py`
3. Review test files in `tests/test_async_db.py` for usage patterns
4. See `CLAUDE.md` for comprehensive migration guide

**Golden Rule:** If a function accesses the database (or calls something that does), it must be `async` and you must `await` it!
