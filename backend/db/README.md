# Database Module

This directory contains async database operations using asyncpg connection pooling.

## Quick Start

```python
from backend.db_helpers import fetch_one, fetch_all, execute

# Fetch single row
async def get_user(user_id: int):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)

# Fetch all rows
async def get_all_users():
    return await fetch_all("SELECT * FROM users ORDER BY name")

# Execute INSERT/UPDATE/DELETE
async def create_user(name: str, email: str):
    await execute(
        "INSERT INTO users (name, email) VALUES ($1, $2)",
        name, email
    )
```

## Documentation

📚 **Start here based on your needs:**

### New to Async Database Patterns?
→ **[ASYNC_QUICK_REFERENCE.md](ASYNC_QUICK_REFERENCE.md)** - One-page cheat sheet

### Need Detailed Examples?
→ **[ASYNC_PATTERNS.md](ASYNC_PATTERNS.md)** - Complete patterns guide with examples

### Migrating from psycopg2?
→ **[ASYNC_PATTERNS.md](ASYNC_PATTERNS.md)** - See "Migration Checklist" section

### Looking for Project-Wide Docs?
→ **[../../CLAUDE.md](../../CLAUDE.md)** - See "Database Architecture" section

## Key Files

| File | Purpose |
|------|---------|
| `pool.py` | Connection pool management (singleton) |
| `db_helpers.py` | High-level async query utilities |
| `query_builders.py` | Type-safe query builders (optional) |
| `*_db.py` | Domain-specific database operations |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ API Layer (FastAPI routes)                             │
│   - Async endpoints                                     │
│   - Request/response handling                           │
└────────────────────────┬────────────────────────────────┘
                         │ await
┌────────────────────────▼────────────────────────────────┐
│ Service Layer (Business logic)                          │
│   - Async service methods                               │
│   - Data transformation                                 │
└────────────────────────┬────────────────────────────────┘
                         │ await
┌────────────────────────▼────────────────────────────────┐
│ Database Layer (backend/db/)                            │
│   - Async database functions                            │
│   - Uses db_helpers or pool directly                    │
└────────────────────────┬────────────────────────────────┘
                         │ await
┌────────────────────────▼────────────────────────────────┐
│ Connection Pool (asyncpg.Pool)                          │
│   - Manages connections                                 │
│   - Automatic reuse                                     │
│   - Non-blocking I/O                                    │
└─────────────────────────────────────────────────────────┘
```

## Connection Pool

The connection pool is initialized on FastAPI startup and closed on shutdown:

```python
# backend/main.py
@app.on_event("startup")
async def startup_event():
    await init_pool()  # Initialize pool
    logger.info("✓ Database pool initialized")

@app.on_event("shutdown")
async def shutdown_event():
    await close_pool()  # Close pool
    logger.info("✓ Database pool closed")
```

**Configuration:** See environment variables in `.env`

```bash
# Connection (use DATABASE_URL OR individual components)
DATABASE_URL=postgresql://user:pass@localhost:5432/llm_trading

# Pool settings
DB_MIN_POOL_SIZE=10
DB_MAX_POOL_SIZE=50
DB_COMMAND_TIMEOUT=60.0
```

## Helper Functions

Located in `db_helpers.py`:

- `fetch_one(query, *args)` - Fetch single row as dict
- `fetch_all(query, *args)` - Fetch all rows as list of dicts
- `fetch_val(query, *args)` - Fetch single value
- `execute(query, *args)` - Execute INSERT/UPDATE/DELETE
- `execute_many(query, args_list)` - Batch operations
- `transaction()` - Async context manager for transactions
- `execute_with_returning(query, *args)` - Execute with RETURNING clause
- `execute_many_with_returning(query, args_list)` - Batch with RETURNING

All functions automatically handle connection pool acquisition and release.

## Common Patterns

### Pattern 1: Simple Query

```python
async def get_user(user_id: int):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

### Pattern 2: Batch Insert

```python
async def create_logs(log_entries: List[Tuple[str, str]]):
    await execute_many(
        "INSERT INTO logs (level, message) VALUES ($1, $2)",
        log_entries
    )
```

### Pattern 3: Transaction

```python
async def transfer_money(from_id: int, to_id: int, amount: float):
    async with transaction() as conn:
        await conn.execute(
            "UPDATE accounts SET balance = balance - $1 WHERE id = $2",
            amount, from_id
        )
        await conn.execute(
            "UPDATE accounts SET balance = balance + $1 WHERE id = $2",
            amount, to_id
        )
```

## Key Differences from psycopg2

| Aspect | psycopg2 (Old) | asyncpg (New) |
|--------|----------------|---------------|
| **Function type** | `def function()` | `async def function()` |
| **Calling** | `result = function()` | `result = await function()` |
| **Parameters** | `%s, %s` | `$1, $2` |
| **Row access** | `row[0], row[1]` | `row["name"], row["email"]` |
| **JSONB** | `Json(data)` | `data` (direct dict) |
| **Connection** | `psycopg2.connect()` | Use helpers or `pool.acquire()` |

## Testing

Unit tests: `tests/test_db_pool.py`
Integration tests: `tests/test_async_db.py`
Load tests: `tests/test_load_pool.py`

```bash
# Run database tests
pytest tests/test_async_db.py -v

# Run load tests
pytest tests/test_load_pool.py -v
```

## Health Monitoring

Check pool health via API endpoint:

```bash
curl http://localhost:8200/api/health
```

Response includes pool status:
```json
{
  "status": "healthy",
  "database": {
    "status": "healthy",
    "pool_size": 15,
    "free_connections": 12,
    "min_size": 10,
    "max_size": 50
  }
}
```

## Performance Benefits

Using asyncpg connection pool provides:

- ⚡ **50-90% faster queries** (connection reuse)
- 🚀 **Non-blocking I/O** (doesn't block event loop)
- 📈 **Higher throughput** (concurrent requests)
- 🔒 **Better resource management** (controlled connection limit)
- 💪 **Graceful degradation** (queues requests when pool exhausted)

## Best Practices

1. ✅ Always use `async def` for database functions
2. ✅ Always `await` database operations
3. ✅ Use `$1, $2, $3` parameter placeholders
4. ✅ Access rows with dict keys: `row["column"]`
5. ✅ Use `execute_many()` for batch operations
6. ✅ Use `transaction()` context manager for multi-step operations
7. ✅ Pass dicts directly to JSONB columns (no `Json()` wrapper)

## Common Gotchas

❌ **Forgetting await:** `user = fetch_one(...)` → Returns coroutine, not result
✅ **Correct:** `user = await fetch_one(...)`

❌ **Wrong placeholders:** `"... WHERE id = %s"` → psycopg2 syntax
✅ **Correct:** `"... WHERE id = $1"` → asyncpg syntax

❌ **Index access:** `name = row[0]` → Rows are dicts, not tuples
✅ **Correct:** `name = row["name"]`

❌ **Manual connections:** `conn = await asyncpg.connect(...)` → Don't create connections manually
✅ **Correct:** Use helpers or `pool.acquire()`

## Need Help?

1. Check [ASYNC_QUICK_REFERENCE.md](ASYNC_QUICK_REFERENCE.md) for quick examples
2. Read [ASYNC_PATTERNS.md](ASYNC_PATTERNS.md) for detailed patterns
3. Review `backend/db/*_db.py` for real-world examples
4. See [CLAUDE.md](../../CLAUDE.md) for project-wide documentation

**Golden Rule:** If it touches the database, it must be `async` and you must `await` it!
