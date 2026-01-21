"""Unit tests for PostgreSQL connection pool (backend/db/pool.py).

This module tests:
- Pool initialization with various configurations
- Connection acquisition and release
- Pool health checks
- Error handling for uninitialized pool
- Concurrent connection acquisition
- Pool lifecycle management (startup/shutdown)
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import the pool module
from backend.db import pool


# Helper to create proper async context manager for connection acquisition
class MockAcquireContext:
    """Mock async context manager for pool.acquire()."""
    def __init__(self, mock_conn):
        self.mock_conn = mock_conn

    async def __aenter__(self):
        return self.mock_conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

def create_acquire_context(mock_conn):
    """Create a proper async context manager for pool.acquire()."""
    return MockAcquireContext(mock_conn)


@pytest.fixture(autouse=True)
async def cleanup_pool():
    """Cleanup pool after each test to ensure test isolation."""
    yield
    # Clean up after test
    if pool._pool is not None:
        await pool.close_pool()
    # Reset global state
    pool._pool = None
    pool._config = None


@pytest.fixture
def mock_db_env(monkeypatch):
    """Provide mock database environment variables."""
    monkeypatch.setenv("DATABASE_NAME", "test_db")
    monkeypatch.setenv("DATABASE_USER", "test_user")
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_PASSWORD", "test_password")
    monkeypatch.setenv("DB_MIN_POOL_SIZE", "5")
    monkeypatch.setenv("DB_MAX_POOL_SIZE", "20")
    monkeypatch.setenv("DB_COMMAND_TIMEOUT", "30.0")
    monkeypatch.setenv("DB_MAX_QUERIES", "10000")
    monkeypatch.setenv("DB_MAX_INACTIVE_CONNECTION_LIFETIME", "150.0")


@pytest.fixture
def mock_db_url_env(monkeypatch):
    """Provide mock DATABASE_URL environment variable."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")


# ==================== DatabaseConfig Tests ====================


@pytest.mark.unit
def test_database_config_from_components(mock_db_env):
    """Test DatabaseConfig initialization from individual components."""
    config = pool.DatabaseConfig()

    assert config.database_name == "test_db"
    assert config.database_user == "test_user"
    assert config.database_host == "localhost"
    assert config.database_port == 5432
    assert config.database_password == "test_password"
    assert config.min_pool_size == 5
    assert config.max_pool_size == 20
    assert config.command_timeout == 30.0
    assert config.max_queries == 10000
    assert config.max_inactive_connection_lifetime == 150.0


@pytest.mark.unit
def test_database_config_defaults(monkeypatch):
    """Test DatabaseConfig with default values."""
    # Clear all database env vars
    for var in ["DATABASE_URL", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)

    config = pool.DatabaseConfig()

    assert config.database_name == "llm_trading"
    assert config.database_user == "luis"
    assert config.database_host == "localhost"
    assert config.database_port == 5432
    assert config.database_password is None
    assert config.min_pool_size == 10
    assert config.max_pool_size == 50


@pytest.mark.unit
def test_database_config_get_dsn_from_url(mock_db_url_env):
    """Test DSN generation from DATABASE_URL."""
    config = pool.DatabaseConfig()
    dsn = config.get_dsn()

    assert dsn == "postgresql://user:pass@localhost:5432/testdb"


@pytest.mark.unit
def test_database_config_get_dsn_from_components(monkeypatch):
    """Test DSN generation from individual components."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_NAME", "test_db")
    monkeypatch.setenv("DATABASE_USER", "test_user")
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_PASSWORD", "test_password")

    config = pool.DatabaseConfig()
    dsn = config.get_dsn()

    expected = "postgresql://test_user:test_password@localhost:5432/test_db"
    assert dsn == expected


@pytest.mark.unit
def test_database_config_get_dsn_without_password(monkeypatch):
    """Test DSN generation without password."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_NAME", "test_db")
    monkeypatch.setenv("DATABASE_USER", "test_user")
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)

    config = pool.DatabaseConfig()
    dsn = config.get_dsn()

    expected = "postgresql://test_user@localhost:5432/test_db"
    assert dsn == expected


@pytest.mark.unit
def test_database_config_repr(mock_db_env):
    """Test DatabaseConfig string representation doesn't include password."""
    config = pool.DatabaseConfig()
    repr_str = repr(config)

    assert "test_user" in repr_str
    assert "localhost" in repr_str
    assert "test_db" in repr_str
    assert "5-20" in repr_str
    # Password should NOT be in repr
    assert "test_password" not in repr_str


# ==================== Pool Initialization Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_pool_success(mock_db_env):
    """Test successful pool initialization."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock) as mock_create:
        result = await pool.init_pool()

        # Verify pool was created
        assert result is not None
        assert pool._pool is not None
        assert pool._config is not None

        # Verify create_pool was called with correct parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert "dsn" in call_kwargs
        assert call_kwargs["min_size"] == 5
        assert call_kwargs["max_size"] == 20
        assert call_kwargs["command_timeout"] == 30.0
        assert call_kwargs["max_queries"] == 10000
        assert call_kwargs["max_inactive_connection_lifetime"] == 150.0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_pool_idempotent(mock_db_env):
    """Test that init_pool is idempotent (safe to call multiple times)."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock) as mock_create:
        # Initialize pool first time
        pool1 = await pool.init_pool()

        # Initialize pool second time
        pool2 = await pool.init_pool()

        # Should return same pool instance
        assert pool1 is pool2
        # create_pool should only be called once
        mock_create.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_pool_failure(mock_db_env):
    """Test pool initialization failure handling."""
    # Mock asyncpg.create_pool to raise an exception
    async def failing_create(**kwargs):
        raise Exception("Connection failed")

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=failing_create):
        with pytest.raises(Exception, match="Connection failed"):
            await pool.init_pool()

        # Pool should remain None after failure
        assert pool._pool is None
        assert pool._config is None


# ==================== Pool Access Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_pool_success(mock_db_env):
    """Test getting pool after initialization."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        # Get pool should work
        result = pool.get_pool()
        assert result is not None
        assert result is mock_pool_instance


@pytest.mark.unit
def test_get_pool_not_initialized():
    """Test getting pool before initialization raises error."""
    # Ensure pool is not initialized
    pool._pool = None

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        pool.get_pool()


@pytest.mark.unit
def test_get_config_when_not_initialized():
    """Test getting config when pool not initialized."""
    pool._config = None

    result = pool.get_config()
    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_config_when_initialized(mock_db_env):
    """Test getting config after pool initialization."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        config = pool.get_config()
        assert config is not None
        assert isinstance(config, pool.DatabaseConfig)
        assert config.database_name == "test_db"


# ==================== Pool Acquisition Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pool_acquire_and_release(mock_db_env):
    """Test acquiring and releasing connections from pool."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        # Acquire connection
        pool_obj = pool.get_pool()
        async with pool_obj.acquire() as conn:
            # Connection should be available
            assert conn is not None
            result = await conn.fetchval("SELECT 1")
            assert result == "PostgreSQL 14.0"

        # Verify acquire was called
        mock_pool_instance.acquire.assert_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pool_concurrent_acquisitions(mock_db_env):
    """Test multiple concurrent connection acquisitions."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn1 = AsyncMock()
    mock_conn1.fetchval = AsyncMock(return_value=1)
    mock_conn2 = AsyncMock()
    mock_conn2.fetchval = AsyncMock(return_value=2)

    # Mock initial connection test
    test_conn = AsyncMock()
    test_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")

    # Create acquire side effect that returns different contexts
    acquire_contexts = [
        create_acquire_context(test_conn),
        create_acquire_context(mock_conn1),
        create_acquire_context(mock_conn2)
    ]
    mock_pool_instance.acquire = MagicMock(side_effect=acquire_contexts)

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        # Acquire multiple connections concurrently
        async def use_connection(expected_val):
            pool_obj = pool.get_pool()
            async with pool_obj.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result

        results = await asyncio.gather(
            use_connection(1),
            use_connection(2)
        )

        assert len(results) == 2
        # Pool acquire should have been called 3 times (1 for init + 2 for concurrent)
        assert mock_pool_instance.acquire.call_count == 3


# ==================== Pool Health Check Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_pool_health_not_initialized():
    """Test health check when pool not initialized."""
    pool._pool = None

    health = await pool.check_pool_health()

    assert health["status"] == "unavailable"
    assert "error" in health
    assert "not initialized" in health["error"].lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_pool_health_success(mock_db_env):
    """Test health check with healthy pool."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_pool_instance.get_size.return_value = 10
    mock_pool_instance.get_idle_size.return_value = 7

    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    # Mock for init and health check
    init_conn = AsyncMock()
    init_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")

    acquire_contexts = [
        create_acquire_context(init_conn),
        create_acquire_context(mock_conn)
    ]
    mock_pool_instance.acquire = MagicMock(side_effect=acquire_contexts)

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        health = await pool.check_pool_health()

        assert health["status"] == "healthy"
        assert health["pool_size"] == 10
        assert health["free_connections"] == 7
        assert health["min_size"] == 5
        assert health["max_size"] == 20


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_pool_health_degraded(mock_db_env):
    """Test health check when pool query fails."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_pool_instance.get_size.return_value = 10

    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(side_effect=Exception("Query failed"))

    # First call for init (success), second for health check (failure)
    init_conn = AsyncMock()
    init_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")

    acquire_contexts = [
        create_acquire_context(init_conn),
        create_acquire_context(mock_conn)
    ]
    mock_pool_instance.acquire = MagicMock(side_effect=acquire_contexts)

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        health = await pool.check_pool_health()

        assert health["status"] == "degraded"
        assert "error" in health
        assert "Query failed" in health["error"]
        assert health["pool_size"] == 10


# ==================== Pool Closure Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_pool_success(mock_db_env):
    """Test successful pool closure."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))
    mock_pool_instance.close = AsyncMock()

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        # Verify pool is initialized
        assert pool._pool is not None

        # Close pool
        await pool.close_pool()

        # Verify pool was closed
        mock_pool_instance.close.assert_called_once()
        assert pool._pool is None
        assert pool._config is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_pool_idempotent():
    """Test that close_pool is idempotent (safe to call multiple times)."""
    pool._pool = None
    pool._config = None

    # Should not raise error
    await pool.close_pool()

    # Pool should still be None
    assert pool._pool is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_pool_with_error(mock_db_env):
    """Test pool closure when close() raises an error."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))
    mock_pool_instance.close = AsyncMock(side_effect=Exception("Close failed"))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        await pool.init_pool()

        # Close should not raise, but should log error
        await pool.close_pool()

        # Pool should be reset even if close failed
        assert pool._pool is None
        assert pool._config is None


# ==================== Integration-style Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_full_pool_lifecycle(mock_db_env):
    """Test complete pool lifecycle: init -> use -> close."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")

    # Multiple acquire calls needed: init, use, health check
    acquire_contexts = [
        create_acquire_context(mock_conn),
        create_acquire_context(mock_conn),
        create_acquire_context(mock_conn)
    ]
    mock_pool_instance.acquire = MagicMock(side_effect=acquire_contexts)
    mock_pool_instance.close = AsyncMock()
    mock_pool_instance.get_size.return_value = 10
    mock_pool_instance.get_idle_size.return_value = 5

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock):
        # Step 1: Initialize pool
        await pool.init_pool()
        assert pool._pool is not None

        # Step 2: Get pool and use it
        pool_obj = pool.get_pool()
        async with pool_obj.acquire() as conn:
            result = await conn.fetchval("SELECT version()")
            assert result == "PostgreSQL 14.0"

        # Step 3: Check health
        health = await pool.check_pool_health()
        assert health["status"] == "healthy"

        # Step 4: Close pool
        await pool.close_pool()
        assert pool._pool is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pool_with_database_url(mock_db_url_env):
    """Test pool initialization with DATABASE_URL."""
    # Mock asyncpg.create_pool
    mock_pool_instance = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")
    mock_pool_instance.acquire = MagicMock(return_value=create_acquire_context(mock_conn))

    async def create_pool_mock(**kwargs):
        return mock_pool_instance

    with patch("backend.db.pool.asyncpg.create_pool", side_effect=create_pool_mock) as mock_create:
        await pool.init_pool()

        # Verify DSN from DATABASE_URL was used
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["dsn"] == "postgresql://user:pass@localhost:5432/testdb"
