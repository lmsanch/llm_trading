# Async Database Quick Reference

One-page cheat sheet for asyncpg patterns. For detailed guide, see [ASYNC_PATTERNS.md](ASYNC_PATTERNS.md).

---

## Before You Start

✅ **Always remember:**
1. Use `async def` for functions that access database
2. Use `await` when calling async functions
3. Use `$1, $2, $3` placeholders (not `%s`)
4. Access rows with dict keys (not `row[0]`)

---

## Common Operations

### Fetch Single Row

```python
from backend.db_helpers import fetch_one

async def get_user(user_id: int):
    # Returns dict or None
    user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
    if user:
        name = user["name"]  # Dict access
    return user
```

### Fetch All Rows

```python
from backend.db_helpers import fetch_all

async def get_active_users():
    # Returns list of dicts
    users = await fetch_all("SELECT * FROM users WHERE active = $1", True)
    for user in users:
        print(user["name"])  # Dict access
    return users
```

### Fetch Single Value

```python
from backend.db_helpers import fetch_val

async def count_users():
    # Returns scalar value
    count = await fetch_val("SELECT COUNT(*) FROM users")
    return count
```

### Execute INSERT/UPDATE/DELETE

```python
from backend.db_helpers import execute

async def create_user(name: str, email: str):
    # Returns status string
    await execute(
        "INSERT INTO users (name, email) VALUES ($1, $2)",
        name, email
    )
```

### Execute with RETURNING

```python
from backend.db_helpers import execute_with_returning

async def create_user_with_id(name: str, email: str):
    # Returns dict with RETURNING columns
    result = await execute_with_returning(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, created_at",
        name, email
    )
    return result["id"]
```

### Batch Operations

```python
from backend.db_helpers import execute_many

async def create_users(user_data: List[Tuple[str, str]]):
    # Much faster than loop: 100 rows = 1 DB round-trip
    await execute_many(
        "INSERT INTO users (name, email) VALUES ($1, $2)",
        user_data  # List of tuples: [("Alice", "alice@example.com"), ...]
    )
```

### Transactions

```python
from backend.db_helpers import transaction

async def transfer_money(from_id: int, to_id: int, amount: float):
    # Automatically commits on success, rolls back on error
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

---

## psycopg2 → asyncpg Migration

| psycopg2 | asyncpg |
|----------|---------|
| `def function()` | `async def function()` |
| `result = function()` | `result = await function()` |
| `%s, %s, %s` | `$1, $2, $3` |
| `row[0], row[1]` | `row["name"], row["email"]` |
| `Json(data)` | `data` (for JSONB) |
| `psycopg2.connect()` | Use helpers or `get_pool()` |

---

## Complete Async Chain

**All layers must be async!**

```python
# ✓ API Layer (async)
@router.get("/users/{id}")
async def get_user_endpoint(id: int):
    user = await user_service.get_user(id)  # Must await!
    return user

# ✓ Service Layer (async)
class UserService:
    async def get_user(self, user_id: int):
        user = await get_user_from_db(user_id)  # Must await!
        return user

# ✓ Database Layer (async)
async def get_user_from_db(user_id: int):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

---

## Common Mistakes

### ❌ Forgot `await`

```python
# WRONG: Returns coroutine, not result
user = fetch_one("SELECT * FROM users WHERE id = $1", 42)
```

```python
# CORRECT: Awaits the coroutine
user = await fetch_one("SELECT * FROM users WHERE id = $1", 42)
```

### ❌ Wrong placeholders

```python
# WRONG: %s is psycopg2 syntax
await fetch_one("SELECT * FROM users WHERE id = %s", 42)
```

```python
# CORRECT: $1 is asyncpg syntax
await fetch_one("SELECT * FROM users WHERE id = $1", 42)
```

### ❌ Index-based access

```python
# WRONG: Rows are dicts, not tuples
row = await fetch_one("SELECT name, email FROM users WHERE id = $1", 42)
name = row[0]  # TypeError!
```

```python
# CORRECT: Use dict keys
name = row["name"]
email = row["email"]
```

### ❌ Non-async function

```python
# WRONG: Can't await in non-async function
def get_user(user_id):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
# SyntaxError!
```

```python
# CORRECT: Function must be async
async def get_user(user_id):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
```

---

## JSONB Handling

### Writing JSONB

```python
# asyncpg handles dict → JSONB automatically
data = {"key": "value", "nested": {"data": [1, 2, 3]}}

# Just pass dict directly (no Json() wrapper!)
await execute(
    "INSERT INTO logs (data) VALUES ($1)",
    data  # Automatically serialized to JSONB
)
```

### Reading JSONB

```python
# JSONB automatically deserialized to dict
row = await fetch_one("SELECT * FROM logs WHERE id = $1", log_id)

# Access as regular dict
data = row["data"]  # Already a dict!
value = data["key"]  # Regular dict access
```

---

## Direct Pool Usage (Advanced)

When you need fine-grained control:

```python
from backend.db.pool import get_pool

async def custom_query():
    pool = get_pool()

    # Acquire connection from pool
    async with pool.acquire() as conn:
        # Use connection for multiple operations
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", 42)
        logs = await conn.fetch("SELECT * FROM logs WHERE user_id = $1", 42)

        # Connection automatically returned to pool
        return dict(user), [dict(log) for log in logs]
```

---

## Testing

```python
import pytest

@pytest.mark.asyncio
async def test_get_user():
    """Test async database function."""
    user = await get_user(42)
    assert user["name"] == "Alice"
```

---

## Resources

- **Detailed Guide:** [ASYNC_PATTERNS.md](ASYNC_PATTERNS.md) - Complete patterns documentation
- **Helper Functions:** [backend/db_helpers.py](backend/db_helpers.py) - Source code with docstrings
- **Connection Pool:** [backend/db/pool.py](backend/db/pool.py) - Pool configuration and lifecycle
- **Project Docs:** [CLAUDE.md](../../CLAUDE.md) - Database Architecture section
- **Examples:** `backend/db/*_db.py` - Real-world converted files

---

## Golden Rule

**If a function accesses the database (or calls something that does), it must be `async` and you must `await` it!**

```
Database Access → Must be async → Must await → Don't forget!
```

---

*Last updated: 2026-01-20*
