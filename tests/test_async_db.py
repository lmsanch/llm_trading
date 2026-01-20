"""Integration tests for async database operations (backend/db_helpers.py).

This module tests the async database helper functions against a real PostgreSQL database:
- fetch_one, fetch_all, fetch_val
- execute, execute_many
- execute_with_returning, execute_many_with_returning
- transaction() context manager
- Connection pool behavior under concurrent load
- Error handling and rollback scenarios
- JSONB data handling
- Real-world query patterns from the application

REQUIREMENTS:
-------------
These are integration tests that require a running PostgreSQL database with proper
credentials configured.

To run these tests:
1. Ensure PostgreSQL is running
2. Set environment variables in .env:
   - DATABASE_URL (e.g., postgresql://user:password@localhost:5432/llm_trading), OR
   - DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT
3. Ensure the database user has CREATE TABLE and DML permissions

The tests will automatically:
- Create temporary test tables (test_users, test_logs, test_accounts, test_json_data)
- Clean up test data after each test
- Drop test tables after completion
- Skip tests if database connection fails

To run:
    pytest tests/test_async_db.py -v              # Run all integration tests
    pytest tests/test_async_db.py -v -k "fetch"   # Run only fetch tests
    pytest tests/test_async_db.py -v --tb=short   # Run with short traceback
"""

import asyncio
import json
import pytest
import pytest_asyncio
from datetime import datetime, date
from typing import List, Dict, Any

from backend.db.pool import init_pool, close_pool, get_pool, check_pool_health
from backend.db_helpers import (
    fetch_one,
    fetch_all,
    fetch_val,
    execute,
    execute_many,
    transaction,
    execute_with_returning,
    execute_many_with_returning,
)


# ==================== Test Setup/Teardown ====================


@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the test module.

    Required for module-scoped async fixtures to work properly.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def db_pool(event_loop):
    """Initialize database pool for all tests in this module.

    Note: Requires a running PostgreSQL database with proper credentials
    configured in environment variables.
    """
    # Initialize pool (uses environment variables for connection)
    try:
        await init_pool()
    except Exception as e:
        pytest.skip(f"Could not connect to test database: {e}")

    yield

    # Clean up pool after all tests
    await close_pool()


@pytest_asyncio.fixture(autouse=True)
async def clean_test_tables():
    """Create and clean up test tables for each test."""
    pool = get_pool()

    # Create test tables before each test
    async with pool.acquire() as conn:
        # Drop tables if they exist
        await conn.execute("DROP TABLE IF EXISTS test_users CASCADE")
        await conn.execute("DROP TABLE IF EXISTS test_logs CASCADE")
        await conn.execute("DROP TABLE IF EXISTS test_accounts CASCADE")
        await conn.execute("DROP TABLE IF EXISTS test_json_data CASCADE")

        # Create test_users table
        await conn.execute("""
            CREATE TABLE test_users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                age INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create test_logs table
        await conn.execute("""
            CREATE TABLE test_logs (
                id SERIAL PRIMARY KEY,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create test_accounts table (for transaction tests)
        await conn.execute("""
            CREATE TABLE test_accounts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                balance NUMERIC(12, 2) NOT NULL
            )
        """)

        # Create test_json_data table (for JSONB tests)
        await conn.execute("""
            CREATE TABLE test_json_data (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                data JSONB NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    yield

    # Clean up after each test
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS test_users CASCADE")
        await conn.execute("DROP TABLE IF EXISTS test_logs CASCADE")
        await conn.execute("DROP TABLE IF EXISTS test_accounts CASCADE")
        await conn.execute("DROP TABLE IF EXISTS test_json_data CASCADE")


# ==================== fetch_one Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_one_single_row(db_pool):
    """Test fetch_one returns a single row as dict."""
    # Insert test data
    await execute(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        "Alice", "alice@example.com", 30
    )

    # Fetch single row
    user = await fetch_one("SELECT * FROM test_users WHERE email = $1", "alice@example.com")

    assert user is not None
    assert user["name"] == "Alice"
    assert user["email"] == "alice@example.com"
    assert user["age"] == 30
    assert "id" in user
    assert "created_at" in user


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_one_no_result(db_pool):
    """Test fetch_one returns None when no row matches."""
    user = await fetch_one("SELECT * FROM test_users WHERE email = $1", "nonexistent@example.com")

    assert user is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_one_with_multiple_params(db_pool):
    """Test fetch_one with multiple query parameters."""
    await execute(
        "INSERT INTO test_users (name, email, age, active) VALUES ($1, $2, $3, $4)",
        "Bob", "bob@example.com", 25, True
    )

    user = await fetch_one(
        "SELECT * FROM test_users WHERE age > $1 AND active = $2",
        20, True
    )

    assert user is not None
    assert user["name"] == "Bob"
    assert user["age"] == 25
    assert user["active"] is True


# ==================== fetch_all Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_all_multiple_rows(db_pool):
    """Test fetch_all returns all matching rows."""
    # Insert multiple users
    await execute_many(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        [
            ("Alice", "alice@example.com", 30),
            ("Bob", "bob@example.com", 25),
            ("Charlie", "charlie@example.com", 35),
        ]
    )

    # Fetch all users
    users = await fetch_all("SELECT * FROM test_users ORDER BY age")

    assert len(users) == 3
    assert users[0]["name"] == "Bob"
    assert users[1]["name"] == "Alice"
    assert users[2]["name"] == "Charlie"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_all_empty_result(db_pool):
    """Test fetch_all returns empty list when no rows match."""
    users = await fetch_all("SELECT * FROM test_users WHERE age > $1", 100)

    assert users == []
    assert isinstance(users, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_all_with_filter(db_pool):
    """Test fetch_all with WHERE clause filtering."""
    await execute_many(
        "INSERT INTO test_users (name, email, age, active) VALUES ($1, $2, $3, $4)",
        [
            ("Alice", "alice@example.com", 30, True),
            ("Bob", "bob@example.com", 25, False),
            ("Charlie", "charlie@example.com", 35, True),
        ]
    )

    # Fetch only active users
    active_users = await fetch_all("SELECT * FROM test_users WHERE active = $1 ORDER BY name", True)

    assert len(active_users) == 2
    assert active_users[0]["name"] == "Alice"
    assert active_users[1]["name"] == "Charlie"


# ==================== fetch_val Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_val_count(db_pool):
    """Test fetch_val for COUNT queries."""
    await execute_many(
        "INSERT INTO test_users (name, email) VALUES ($1, $2)",
        [
            ("Alice", "alice@example.com"),
            ("Bob", "bob@example.com"),
            ("Charlie", "charlie@example.com"),
        ]
    )

    count = await fetch_val("SELECT COUNT(*) FROM test_users")

    assert count == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_val_max(db_pool):
    """Test fetch_val for MAX queries."""
    await execute_many(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        [
            ("Alice", "alice@example.com", 30),
            ("Bob", "bob@example.com", 25),
            ("Charlie", "charlie@example.com", 35),
        ]
    )

    max_age = await fetch_val("SELECT MAX(age) FROM test_users")

    assert max_age == 35


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_val_single_column(db_pool):
    """Test fetch_val for single column value."""
    await execute(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        "Alice", "alice@example.com", 30
    )

    name = await fetch_val("SELECT name FROM test_users WHERE email = $1", "alice@example.com")

    assert name == "Alice"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_val_no_result(db_pool):
    """Test fetch_val returns None when no row matches."""
    result = await fetch_val("SELECT name FROM test_users WHERE email = $1", "nonexistent@example.com")

    assert result is None


# ==================== execute Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_insert(db_pool):
    """Test execute for INSERT operations."""
    status = await execute(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        "Alice", "alice@example.com", 30
    )

    assert "INSERT" in status

    # Verify insert
    user = await fetch_one("SELECT * FROM test_users WHERE email = $1", "alice@example.com")
    assert user is not None
    assert user["name"] == "Alice"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_update(db_pool):
    """Test execute for UPDATE operations."""
    # Insert user
    await execute(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        "Alice", "alice@example.com", 30
    )

    # Update user
    status = await execute(
        "UPDATE test_users SET age = $1 WHERE email = $2",
        31, "alice@example.com"
    )

    assert "UPDATE" in status

    # Verify update
    user = await fetch_one("SELECT * FROM test_users WHERE email = $1", "alice@example.com")
    assert user["age"] == 31


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_delete(db_pool):
    """Test execute for DELETE operations."""
    # Insert user
    await execute(
        "INSERT INTO test_users (name, email) VALUES ($1, $2)",
        "Alice", "alice@example.com"
    )

    # Delete user
    status = await execute("DELETE FROM test_users WHERE email = $1", "alice@example.com")

    assert "DELETE" in status

    # Verify deletion
    user = await fetch_one("SELECT * FROM test_users WHERE email = $1", "alice@example.com")
    assert user is None


# ==================== execute_many Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_many_batch_insert(db_pool):
    """Test execute_many for batch INSERT operations."""
    await execute_many(
        "INSERT INTO test_logs (level, message) VALUES ($1, $2)",
        [
            ("INFO", "Server started"),
            ("ERROR", "Connection failed"),
            ("DEBUG", "Processing request"),
            ("WARN", "Slow query detected"),
        ]
    )

    # Verify all rows inserted
    count = await fetch_val("SELECT COUNT(*) FROM test_logs")
    assert count == 4

    # Verify content
    logs = await fetch_all("SELECT * FROM test_logs ORDER BY id")
    assert logs[0]["level"] == "INFO"
    assert logs[1]["level"] == "ERROR"
    assert logs[2]["level"] == "DEBUG"
    assert logs[3]["level"] == "WARN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_many_batch_update(db_pool):
    """Test execute_many for batch UPDATE operations."""
    # Insert test data
    await execute_many(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        [
            ("Alice", "alice@example.com", 30),
            ("Bob", "bob@example.com", 25),
            ("Charlie", "charlie@example.com", 35),
        ]
    )

    # Get IDs
    users = await fetch_all("SELECT id, name FROM test_users ORDER BY name")

    # Batch update ages
    await execute_many(
        "UPDATE test_users SET age = $1 WHERE id = $2",
        [
            (31, users[0]["id"]),
            (26, users[1]["id"]),
            (36, users[2]["id"]),
        ]
    )

    # Verify updates
    alice = await fetch_one("SELECT * FROM test_users WHERE name = $1", "Alice")
    assert alice["age"] == 31


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_many_rollback_on_error(db_pool):
    """Test execute_many rolls back all operations on error."""
    # Try to insert with one duplicate email (should fail)
    try:
        await execute_many(
            "INSERT INTO test_users (name, email) VALUES ($1, $2)",
            [
                ("Alice", "alice@example.com"),
                ("Bob", "bob@example.com"),
                ("Charlie", "alice@example.com"),  # Duplicate email
            ]
        )
        pytest.fail("Expected exception for duplicate email")
    except Exception:
        pass  # Expected

    # Verify no rows were inserted (transaction rolled back)
    count = await fetch_val("SELECT COUNT(*) FROM test_users")
    assert count == 0


# ==================== transaction Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_commit(db_pool):
    """Test transaction commits on success."""
    # Insert initial accounts
    await execute_many(
        "INSERT INTO test_accounts (name, balance) VALUES ($1, $2)",
        [("Alice", 1000.00), ("Bob", 500.00)]
    )

    # Transfer money in transaction
    async with transaction() as conn:
        await conn.execute(
            "UPDATE test_accounts SET balance = balance - $1 WHERE name = $2",
            100.00, "Alice"
        )
        await conn.execute(
            "UPDATE test_accounts SET balance = balance + $1 WHERE name = $2",
            100.00, "Bob"
        )

    # Verify balances updated
    alice = await fetch_one("SELECT * FROM test_accounts WHERE name = $1", "Alice")
    bob = await fetch_one("SELECT * FROM test_accounts WHERE name = $1", "Bob")

    assert alice["balance"] == 900.00
    assert bob["balance"] == 600.00


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_rollback_on_error(db_pool):
    """Test transaction rolls back on error."""
    # Insert initial accounts
    await execute_many(
        "INSERT INTO test_accounts (name, balance) VALUES ($1, $2)",
        [("Alice", 1000.00), ("Bob", 500.00)]
    )

    # Try transfer with error in middle
    try:
        async with transaction() as conn:
            await conn.execute(
                "UPDATE test_accounts SET balance = balance - $1 WHERE name = $2",
                100.00, "Alice"
            )
            # Simulate error
            raise ValueError("Simulated error")
            await conn.execute(
                "UPDATE test_accounts SET balance = balance + $1 WHERE name = $2",
                100.00, "Bob"
            )
    except ValueError:
        pass  # Expected

    # Verify no changes (rollback)
    alice = await fetch_one("SELECT * FROM test_accounts WHERE name = $1", "Alice")
    bob = await fetch_one("SELECT * FROM test_accounts WHERE name = $1", "Bob")

    assert alice["balance"] == 1000.00
    assert bob["balance"] == 500.00


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_fetch_operations(db_pool):
    """Test using fetch operations within a transaction."""
    await execute_many(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        [("Alice", "alice@example.com", 30), ("Bob", "bob@example.com", 25)]
    )

    async with transaction() as conn:
        # Fetch within transaction
        rows = await conn.fetch("SELECT * FROM test_users WHERE age > $1", 20)
        assert len(rows) == 2

        # Update within transaction
        await conn.execute("UPDATE test_users SET age = age + 1")

        # Fetch updated values
        updated = await conn.fetchval("SELECT MAX(age) FROM test_users")
        assert updated == 31


# ==================== execute_with_returning Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_with_returning_insert(db_pool):
    """Test execute_with_returning for INSERT with auto-generated ID."""
    result = await execute_with_returning(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3) RETURNING id, name, created_at",
        "Alice", "alice@example.com", 30
    )

    assert result is not None
    assert "id" in result
    assert result["name"] == "Alice"
    assert "created_at" in result
    assert isinstance(result["id"], int)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_with_returning_update(db_pool):
    """Test execute_with_returning for UPDATE returning old value."""
    # Insert user
    await execute(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        "Alice", "alice@example.com", 30
    )

    # Update and return old age
    result = await execute_with_returning(
        "UPDATE test_users SET age = $1 WHERE email = $2 RETURNING age",
        31, "alice@example.com"
    )

    # Note: RETURNING returns the NEW value, not old
    assert result is not None
    assert result["age"] == 31


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_with_returning_no_match(db_pool):
    """Test execute_with_returning returns None when no rows affected."""
    result = await execute_with_returning(
        "UPDATE test_users SET age = $1 WHERE email = $2 RETURNING id",
        31, "nonexistent@example.com"
    )

    assert result is None


# ==================== execute_many_with_returning Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_many_with_returning(db_pool):
    """Test execute_many_with_returning for batch inserts with IDs."""
    results = await execute_many_with_returning(
        "INSERT INTO test_users (name, email) VALUES ($1, $2) RETURNING id, name",
        [
            ("Alice", "alice@example.com"),
            ("Bob", "bob@example.com"),
            ("Charlie", "charlie@example.com"),
        ]
    )

    assert len(results) == 3
    assert all("id" in r for r in results)
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"
    assert results[2]["name"] == "Charlie"
    # IDs should be sequential
    assert results[1]["id"] == results[0]["id"] + 1
    assert results[2]["id"] == results[1]["id"] + 1


# ==================== JSONB Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jsonb_insert_and_fetch(db_pool):
    """Test inserting and fetching JSONB data."""
    test_data = {
        "user_id": 123,
        "preferences": {"theme": "dark", "notifications": True},
        "tags": ["vip", "premium"],
    }

    result = await execute_with_returning(
        "INSERT INTO test_json_data (key, data) VALUES ($1, $2) RETURNING id",
        "user_prefs", test_data
    )

    assert result is not None

    # Fetch and verify
    row = await fetch_one("SELECT * FROM test_json_data WHERE key = $1", "user_prefs")

    assert row is not None
    assert row["data"] == test_data
    assert row["data"]["user_id"] == 123
    assert row["data"]["preferences"]["theme"] == "dark"
    assert "premium" in row["data"]["tags"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jsonb_query_operations(db_pool):
    """Test JSONB query operations (->>, @>, etc.)."""
    # Insert test data
    await execute_many(
        "INSERT INTO test_json_data (key, data) VALUES ($1, $2)",
        [
            ("config1", {"env": "prod", "version": "1.0"}),
            ("config2", {"env": "dev", "version": "2.0"}),
            ("config3", {"env": "prod", "version": "2.0"}),
        ]
    )

    # Query using JSONB operators
    prod_configs = await fetch_all(
        "SELECT * FROM test_json_data WHERE data @> $1",
        json.dumps({"env": "prod"})
    )

    assert len(prod_configs) == 2

    # Query using ->> operator
    version = await fetch_val(
        "SELECT data->>'version' FROM test_json_data WHERE key = $1",
        "config1"
    )
    assert version == "1.0"


# ==================== Concurrent Operations Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_reads(db_pool):
    """Test multiple concurrent read operations."""
    # Insert test data
    await execute_many(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        [
            ("Alice", "alice@example.com", 30),
            ("Bob", "bob@example.com", 25),
            ("Charlie", "charlie@example.com", 35),
        ]
    )

    # Execute multiple concurrent queries
    tasks = [
        fetch_all("SELECT * FROM test_users WHERE age > $1", 20),
        fetch_one("SELECT * FROM test_users WHERE name = $1", "Alice"),
        fetch_val("SELECT COUNT(*) FROM test_users"),
        fetch_all("SELECT * FROM test_users ORDER BY age"),
    ]

    results = await asyncio.gather(*tasks)

    assert len(results[0]) == 3  # fetch_all with age > 20
    assert results[1]["name"] == "Alice"  # fetch_one
    assert results[2] == 3  # COUNT
    assert len(results[3]) == 3  # fetch_all ordered


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_writes(db_pool):
    """Test multiple concurrent write operations."""
    # Execute multiple concurrent inserts
    tasks = [
        execute(
            "INSERT INTO test_logs (level, message) VALUES ($1, $2)",
            "INFO", f"Message {i}"
        )
        for i in range(10)
    ]

    await asyncio.gather(*tasks)

    # Verify all inserts completed
    count = await fetch_val("SELECT COUNT(*) FROM test_logs")
    assert count == 10


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_pool_under_load(db_pool):
    """Test connection pool behavior under high concurrent load."""
    # Insert initial data
    await execute_many(
        "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
        [(f"User{i}", f"user{i}@example.com", 20 + i) for i in range(100)]
    )

    # Simulate high load with many concurrent operations
    async def random_operation(i: int):
        """Perform random database operation."""
        if i % 3 == 0:
            return await fetch_all("SELECT * FROM test_users WHERE age > $1", 25)
        elif i % 3 == 1:
            return await fetch_val("SELECT COUNT(*) FROM test_users WHERE age < $1", 50)
        else:
            return await fetch_one("SELECT * FROM test_users WHERE email = $1", f"user{i % 100}@example.com")

    # Execute 100 concurrent operations
    tasks = [random_operation(i) for i in range(100)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 100
    assert all(r is not None for r in results[::3])  # Every 3rd should return data


# ==================== Error Handling Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_syntax_error_handling(db_pool):
    """Test proper error handling for SQL syntax errors."""
    with pytest.raises(Exception) as exc_info:
        await fetch_all("SELECT * FROMM test_users")  # Typo: FROMM

    assert "syntax error" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_violation_handling(db_pool):
    """Test proper error handling for constraint violations."""
    await execute(
        "INSERT INTO test_users (name, email) VALUES ($1, $2)",
        "Alice", "alice@example.com"
    )

    # Try to insert duplicate email (UNIQUE constraint)
    with pytest.raises(Exception) as exc_info:
        await execute(
            "INSERT INTO test_users (name, email) VALUES ($1, $2)",
            "Alice2", "alice@example.com"
        )

    assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_type_mismatch_handling(db_pool):
    """Test proper error handling for type mismatches."""
    with pytest.raises(Exception):
        await execute(
            "INSERT INTO test_users (name, email, age) VALUES ($1, $2, $3)",
            "Alice", "alice@example.com", "not_a_number"  # age should be INTEGER
        )


# ==================== Pool Health Check Test ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pool_health_check_healthy(db_pool):
    """Test pool health check returns healthy status with real pool."""
    health = await check_pool_health()

    assert health["status"] == "healthy"
    assert "pool_size" in health
    assert "free_connections" in health
    assert health["pool_size"] >= 0
    assert health["free_connections"] >= 0


# ==================== Real Application Pattern Tests ====================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_report_pattern(db_pool):
    """Test database pattern used for research reports (real application pattern)."""
    # Simulate research report insert pattern
    research_data = {
        "provider": "perplexity",
        "market_summary": "Markets are bullish...",
        "key_themes": ["tech rally", "inflation concerns"],
    }

    result = await execute_with_returning(
        """
        INSERT INTO test_json_data (key, data, metadata)
        VALUES ($1, $2, $3)
        RETURNING id, created_at
        """,
        "research_report_1",
        research_data,
        {"week_id": "2025-01-20", "status": "completed"}
    )

    assert result is not None
    assert "id" in result

    # Fetch latest report pattern
    latest = await fetch_one(
        "SELECT * FROM test_json_data ORDER BY created_at DESC LIMIT 1"
    )

    assert latest["data"] == research_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pitch_persistence_pattern(db_pool):
    """Test database pattern used for PM pitch persistence."""
    # Insert pitch data (similar to real application)
    pitches = [
        ("SPY", "LONG", {"conviction": 1.5, "horizon": "1w"}),
        ("TLT", "SHORT", {"conviction": 0.8, "horizon": "1w"}),
        ("QQQ", "FLAT", {"conviction": 0.0, "horizon": "1w"}),
    ]

    results = await execute_many_with_returning(
        """
        INSERT INTO test_json_data (key, data)
        VALUES ($1, $2)
        RETURNING id, key
        """,
        [(pitch[0], {"direction": pitch[1], "details": pitch[2]}) for pitch in pitches]
    )

    assert len(results) == 3

    # Query active pitches pattern
    active_pitches = await fetch_all(
        "SELECT * FROM test_json_data WHERE data->>'direction' != 'FLAT'"
    )

    assert len(active_pitches) == 2
