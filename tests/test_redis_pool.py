"""Unit tests for async Redis client (backend/redis_client.py).

This module tests:
- RedisConfig initialization with various configurations
- Pool initialization and lifecycle
- Connection health checks
- Error handling for uninitialized pool
- AsyncRedisClient operations (get, set, delete, exists, ping)
- Pool cleanup and resource management
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

# Import the redis_client module
from backend import redis_client


@pytest.fixture(autouse=True)
async def cleanup_redis_pool():
    """Cleanup Redis pool after each test to ensure test isolation."""
    yield
    # Clean up after test
    if redis_client._redis_pool is not None:
        await redis_client.close_redis_pool()
    # Reset global state
    redis_client._redis_pool = None
    redis_client._redis_config = None


@pytest.fixture
def mock_redis_env(monkeypatch):
    """Provide mock Redis environment variables."""
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "test_password")
    monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "5")
    monkeypatch.setenv("REDIS_SOCKET_TIMEOUT", "10")
    monkeypatch.setenv("REDIS_SOCKET_CONNECT_TIMEOUT", "10")
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "true")


@pytest.fixture
def mock_redis_env_no_password(monkeypatch):
    """Provide mock Redis environment variables without password."""
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)
    monkeypatch.setenv("REDIS_MAX_CONNECTIONS", "10")


# ==================== RedisConfig Tests ====================


@pytest.mark.unit
def test_redis_config_from_env(mock_redis_env):
    """Test RedisConfig initialization from environment variables."""
    config = redis_client.RedisConfig()

    assert config.host == "localhost"
    assert config.port == 6379
    assert config.db == 1
    assert config.password == "test_password"
    assert config.max_connections == 5
    assert config.socket_timeout == 10
    assert config.socket_connect_timeout == 10
    assert config.retry_on_timeout is True


@pytest.mark.unit
def test_redis_config_defaults(monkeypatch):
    """Test RedisConfig with default values."""
    # Clear all Redis env vars
    for var in ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD",
                "REDIS_MAX_CONNECTIONS", "REDIS_SOCKET_TIMEOUT",
                "REDIS_SOCKET_CONNECT_TIMEOUT", "REDIS_RETRY_ON_TIMEOUT"]:
        monkeypatch.delenv(var, raising=False)

    config = redis_client.RedisConfig()

    assert config.host == "localhost"
    assert config.port == 6379
    assert config.db == 0
    assert config.password is None
    assert config.max_connections == 10
    assert config.socket_timeout == 5
    assert config.socket_connect_timeout == 5
    assert config.retry_on_timeout is True


@pytest.mark.unit
def test_redis_config_retry_on_timeout_false(monkeypatch):
    """Test RedisConfig with retry_on_timeout set to false."""
    monkeypatch.setenv("REDIS_RETRY_ON_TIMEOUT", "false")

    config = redis_client.RedisConfig()

    assert config.retry_on_timeout is False


@pytest.mark.unit
def test_redis_config_repr(mock_redis_env):
    """Test RedisConfig string representation doesn't include password."""
    config = redis_client.RedisConfig()
    repr_str = repr(config)

    assert "localhost" in repr_str
    assert "6379" in repr_str
    assert "db=1" in repr_str
    assert "max_connections=5" in repr_str
    # Password should NOT be in repr
    assert "test_password" not in repr_str


# ==================== Pool Initialization Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_redis_pool_success(mock_redis_env):
    """Test successful Redis pool initialization."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock) as mock_from_url:
        result = await redis_client.init_redis_pool()

        # Verify pool was created
        assert result is not None
        assert redis_client._redis_pool is not None
        assert redis_client._redis_config is not None

        # Verify from_url was called with correct parameters
        mock_from_url.assert_called_once()
        call_args = mock_from_url.call_args

        # Check URL format
        redis_url = call_args[0][0]
        assert "redis://" in redis_url
        assert ":test_password@" in redis_url
        assert "localhost:6379/1" in redis_url

        # Check kwargs
        assert call_args[1]["max_connections"] == 5
        assert call_args[1]["socket_timeout"] == 10
        assert call_args[1]["socket_connect_timeout"] == 10
        assert call_args[1]["retry_on_timeout"] is True
        assert call_args[1]["decode_responses"] is True

        # Verify ping was called
        mock_redis_instance.ping.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_redis_pool_no_password(mock_redis_env_no_password):
    """Test Redis pool initialization without password."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock) as mock_from_url:
        result = await redis_client.init_redis_pool()

        assert result is not None

        # Check URL format (should not include password)
        redis_url = mock_from_url.call_args[0][0]
        assert "redis://localhost:6379/0" == redis_url
        assert "@" not in redis_url  # No password means no @ symbol


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_redis_pool_idempotent(mock_redis_env):
    """Test that init_redis_pool is idempotent (safe to call multiple times)."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock) as mock_from_url:
        # Initialize pool first time
        pool1 = await redis_client.init_redis_pool()

        # Initialize pool second time
        pool2 = await redis_client.init_redis_pool()

        # Should return same pool instance
        assert pool1 is pool2
        # from_url should only be called once
        mock_from_url.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_redis_pool_connection_failure(mock_redis_env):
    """Test pool initialization failure when ping fails."""
    # Mock aioredis.from_url to return a pool that fails ping
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(side_effect=Exception("Connection refused"))

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        with pytest.raises(Exception, match="Connection refused"):
            await redis_client.init_redis_pool()

        # Pool should remain None after failure
        assert redis_client._redis_pool is None
        assert redis_client._redis_config is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_redis_pool_from_url_failure(mock_redis_env):
    """Test pool initialization failure when from_url raises exception."""
    async def failing_from_url(*args, **kwargs):
        raise Exception("Failed to create pool")

    with patch("backend.redis_client.aioredis.from_url", side_effect=failing_from_url):
        with pytest.raises(Exception, match="Failed to create pool"):
            await redis_client.init_redis_pool()

        # Pool should remain None after failure
        assert redis_client._redis_pool is None
        assert redis_client._redis_config is None


# ==================== Pool Access Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_redis_pool_success(mock_redis_env):
    """Test getting pool after initialization."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        await redis_client.init_redis_pool()

        # Get pool should work
        result = redis_client.get_redis_pool()
        assert result is not None
        assert result is mock_redis_instance


@pytest.mark.unit
def test_get_redis_pool_not_initialized():
    """Test getting pool before initialization raises error."""
    # Ensure pool is not initialized
    redis_client._redis_pool = None

    with pytest.raises(RuntimeError, match="Redis pool has not been initialized"):
        redis_client.get_redis_pool()


# ==================== Pool Health Check Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_redis_health_not_initialized():
    """Test health check when pool not initialized."""
    redis_client._redis_pool = None

    health = await redis_client.check_redis_health()

    assert health["status"] == "unavailable"
    assert "error" in health
    assert "not initialized" in health["error"].lower()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_redis_health_success(mock_redis_env):
    """Test health check with healthy pool."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        await redis_client.init_redis_pool()

        health = await redis_client.check_redis_health()

        assert health["status"] == "healthy"
        assert health["host"] == "localhost"
        assert health["port"] == 6379
        assert health["db"] == 1
        assert health["max_connections"] == 5

        # Ping should have been called twice: once for init, once for health check
        assert mock_redis_instance.ping.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_redis_health_degraded(mock_redis_env):
    """Test health check when ping fails."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    # First ping succeeds (for init), second fails (for health check)
    mock_redis_instance.ping = AsyncMock(side_effect=[True, Exception("Connection lost")])

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        await redis_client.init_redis_pool()

        health = await redis_client.check_redis_health()

        assert health["status"] == "degraded"
        assert "error" in health
        assert "Connection lost" in health["error"]
        assert health["host"] == "localhost"
        assert health["port"] == 6379


# ==================== Pool Closure Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_redis_pool_success(mock_redis_env):
    """Test successful pool closure."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)
    mock_redis_instance.close = AsyncMock()

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        await redis_client.init_redis_pool()

        # Verify pool is initialized
        assert redis_client._redis_pool is not None

        # Close pool
        await redis_client.close_redis_pool()

        # Verify pool was closed
        mock_redis_instance.close.assert_called_once()
        assert redis_client._redis_pool is None
        assert redis_client._redis_config is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_redis_pool_idempotent():
    """Test that close_redis_pool is idempotent (safe to call multiple times)."""
    redis_client._redis_pool = None
    redis_client._redis_config = None

    # Should not raise error
    await redis_client.close_redis_pool()

    # Pool should still be None
    assert redis_client._redis_pool is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_redis_pool_with_error(mock_redis_env):
    """Test pool closure when close() raises an error."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)
    mock_redis_instance.close = AsyncMock(side_effect=Exception("Close failed"))

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        await redis_client.init_redis_pool()

        # Close should not raise, but should log error
        await redis_client.close_redis_pool()

        # Pool should be reset even if close failed
        assert redis_client._redis_pool is None
        assert redis_client._redis_config is None


# ==================== AsyncRedisClient Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_ping_success():
    """Test AsyncRedisClient ping with successful response."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.ping()

    assert result is True
    mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_ping_failure():
    """Test AsyncRedisClient ping with connection failure."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.ping()

    assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_get_hit():
    """Test AsyncRedisClient get with cache hit."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="cached_value")

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.get("test_key")

    assert result == "cached_value"
    mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_get_miss():
    """Test AsyncRedisClient get with cache miss."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.get("test_key")

    assert result is None
    mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_get_error():
    """Test AsyncRedisClient get with error."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.get("test_key")

    assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_set_success():
    """Test AsyncRedisClient set without TTL."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.set("test_key", "test_value")

    assert result is True
    mock_redis.set.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_set_with_ttl():
    """Test AsyncRedisClient set with TTL."""
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock(return_value=True)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.set("test_key", "test_value", ttl=3600)

    assert result is True
    mock_redis.setex.assert_called_once_with("test_key", 3600, "test_value")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_set_error():
    """Test AsyncRedisClient set with error."""
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.set("test_key", "test_value")

    assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_delete_success():
    """Test AsyncRedisClient delete with successful deletion."""
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=2)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.delete("key1", "key2")

    assert result == 2
    mock_redis.delete.assert_called_once_with("key1", "key2")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_delete_error():
    """Test AsyncRedisClient delete with error."""
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(side_effect=Exception("Redis error"))

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.delete("key1")

    assert result == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_exists_success():
    """Test AsyncRedisClient exists with keys that exist."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=2)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.exists("key1", "key2")

    assert result == 2
    mock_redis.exists.assert_called_once_with("key1", "key2")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_exists_not_found():
    """Test AsyncRedisClient exists with keys that don't exist."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.exists("nonexistent")

    assert result == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_exists_error():
    """Test AsyncRedisClient exists with error."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(side_effect=Exception("Redis error"))

    client = redis_client.AsyncRedisClient(mock_redis)
    result = await client.exists("key1")

    assert result == 0


# ==================== Integration-style Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_full_redis_pool_lifecycle(mock_redis_env):
    """Test complete pool lifecycle: init -> use -> close."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)
    mock_redis_instance.get = AsyncMock(return_value="test_value")
    mock_redis_instance.set = AsyncMock(return_value=True)
    mock_redis_instance.close = AsyncMock()

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        # Step 1: Initialize pool
        await redis_client.init_redis_pool()
        assert redis_client._redis_pool is not None

        # Step 2: Get pool and use it
        pool = redis_client.get_redis_pool()

        # Set a value
        await pool.set("test_key", "test_value")
        mock_redis_instance.set.assert_called_once()

        # Get a value
        value = await pool.get("test_key")
        assert value == "test_value"
        mock_redis_instance.get.assert_called_once()

        # Step 3: Check health
        health = await redis_client.check_redis_health()
        assert health["status"] == "healthy"

        # Step 4: Close pool
        await redis_client.close_redis_pool()
        assert redis_client._redis_pool is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_redis_client_operations_workflow():
    """Test a realistic workflow using AsyncRedisClient."""
    mock_redis = AsyncMock()

    # Configure mock responses
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.exists = AsyncMock(return_value=0)  # Key doesn't exist initially
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value="stored_value")
    mock_redis.delete = AsyncMock(return_value=1)

    client = redis_client.AsyncRedisClient(mock_redis)

    # Step 1: Check connection
    assert await client.ping() is True

    # Step 2: Check if key exists (should not)
    assert await client.exists("my_key") == 0

    # Step 3: Set a value
    assert await client.set("my_key", "stored_value", ttl=300) is True

    # Step 4: Get the value
    value = await client.get("my_key")
    assert value == "stored_value"

    # Step 5: Delete the key
    deleted = await client.delete("my_key")
    assert deleted == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_concurrent_redis_operations(mock_redis_env):
    """Test multiple concurrent Redis operations."""
    # Mock aioredis.from_url
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)
    mock_redis_instance.get = AsyncMock(side_effect=["value1", "value2", "value3"])
    mock_redis_instance.close = AsyncMock()

    async def from_url_mock(*args, **kwargs):
        return mock_redis_instance

    with patch("backend.redis_client.aioredis.from_url", side_effect=from_url_mock):
        await redis_client.init_redis_pool()

        # Perform concurrent operations
        async def get_value(key):
            pool = redis_client.get_redis_pool()
            return await pool.get(key)

        results = await asyncio.gather(
            get_value("key1"),
            get_value("key2"),
            get_value("key3")
        )

        assert results == ["value1", "value2", "value3"]
        assert mock_redis_instance.get.call_count == 3

        await redis_client.close_redis_pool()
