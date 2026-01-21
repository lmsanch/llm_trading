"""Integration tests for async Redis cache decorator (backend/cache/decorator.py).

This module tests:
- @cached decorator with async functions
- Cache hit/miss scenarios
- TTL expiration behavior
- Custom key builders
- Different serialization formats (JSON, msgpack)
- Compression for large payloads
- Error handling when Redis is unavailable
- invalidate_cache() and invalidate_cache_async() functions
- Sync function caching (backward compatibility)
"""

import asyncio
import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from backend.cache.decorator import cached, invalidate_cache, invalidate_cache_async
from backend import redis_client


# ==================== Fixtures ====================


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
def mock_redis_pool():
    """Create a mock Redis pool for testing cache operations."""
    mock_pool = AsyncMock()

    # Mock basic Redis operations
    mock_pool.get = AsyncMock(return_value=None)
    mock_pool.set = AsyncMock(return_value=True)
    mock_pool.setex = AsyncMock(return_value=True)
    mock_pool.delete = AsyncMock(return_value=1)
    mock_pool.exists = AsyncMock(return_value=1)
    mock_pool.keys = AsyncMock(return_value=[])
    mock_pool.ping = AsyncMock(return_value=True)

    return mock_pool


@pytest.fixture
async def initialized_redis_pool(mock_redis_pool):
    """Initialize Redis pool with mock for testing."""
    # Set global pool
    redis_client._redis_pool = mock_redis_pool
    redis_client._redis_config = redis_client.RedisConfig()

    yield mock_redis_pool

    # Cleanup is handled by cleanup_redis_pool fixture


# ==================== Basic Cache Operations ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_async_function_cache_miss(initialized_redis_pool):
    """Test @cached decorator with async function on cache miss."""
    call_count = 0

    @cached(key="test:data", ttl=3600)
    async def get_data():
        nonlocal call_count
        call_count += 1
        return {"value": 42}

    # Mock Redis to return None (cache miss)
    initialized_redis_pool.get.return_value = None

    # Call function
    result = await get_data()

    # Verify function was called
    assert call_count == 1
    assert result == {"value": 42}

    # Verify cache operations
    initialized_redis_pool.get.assert_called_once_with("test:data")
    initialized_redis_pool.setex.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_async_function_cache_hit(initialized_redis_pool):
    """Test @cached decorator with async function on cache hit."""
    call_count = 0

    @cached(key="test:data", ttl=3600)
    async def get_data():
        nonlocal call_count
        call_count += 1
        return {"value": 42}

    # Mock Redis to return cached value
    cached_value = json.dumps({"value": 42})
    initialized_redis_pool.get.return_value = cached_value

    # Call function
    result = await get_data()

    # Verify function was NOT called (cache hit)
    assert call_count == 0
    assert result == {"value": 42}

    # Verify only get was called, not set
    initialized_redis_pool.get.assert_called_once_with("test:data")
    initialized_redis_pool.setex.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_static_key(initialized_redis_pool):
    """Test @cached decorator with static key."""
    @cached(key="static:key", ttl=60)
    async def get_static_data():
        return {"static": True}

    initialized_redis_pool.get.return_value = None

    await get_static_data()

    # Verify static key was used
    initialized_redis_pool.get.assert_called_once_with("static:key")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_dynamic_key_builder(initialized_redis_pool):
    """Test @cached decorator with dynamic key builder."""
    @cached(
        key_builder=lambda user_id: f"user:profile:{user_id}",
        ttl=3600
    )
    async def get_user_profile(user_id: str):
        return {"user_id": user_id, "name": "Test User"}

    initialized_redis_pool.get.return_value = None

    await get_user_profile("123")

    # Verify dynamic key was built correctly
    initialized_redis_pool.get.assert_called_once_with("user:profile:123")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_multiple_args(initialized_redis_pool):
    """Test @cached decorator with multiple function arguments."""
    @cached(
        key_builder=lambda symbol, date: f"market:price:{symbol}:{date}",
        ttl=300
    )
    async def get_price(symbol: str, date: str):
        return {"symbol": symbol, "date": date, "price": 100.0}

    initialized_redis_pool.get.return_value = None

    await get_price("SPY", "2025-01-01")

    # Verify key includes both arguments
    initialized_redis_pool.get.assert_called_once_with("market:price:SPY:2025-01-01")


# ==================== TTL Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_ttl(initialized_redis_pool):
    """Test @cached decorator sets TTL correctly."""
    @cached(key="test:ttl", ttl=3600)
    async def get_data_with_ttl():
        return {"value": 42}

    initialized_redis_pool.get.return_value = None

    await get_data_with_ttl()

    # Verify setex was called with correct TTL
    call_args = initialized_redis_pool.setex.call_args
    assert call_args[0][0] == "test:ttl"  # key
    assert call_args[0][1] == 3600  # ttl


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_without_ttl(initialized_redis_pool):
    """Test @cached decorator without TTL (no expiration)."""
    @cached(key="test:no_ttl")
    async def get_data_no_ttl():
        return {"value": 42}

    initialized_redis_pool.get.return_value = None

    await get_data_no_ttl()

    # Verify set was called (not setex)
    initialized_redis_pool.set.assert_called_once()
    initialized_redis_pool.setex.assert_not_called()


# ==================== Serialization Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_json_format(initialized_redis_pool):
    """Test @cached decorator with JSON serialization."""
    @cached(key="test:json", format="json")
    async def get_json_data():
        return {"format": "json", "value": 42}

    initialized_redis_pool.get.return_value = None

    result = await get_json_data()

    # Verify result is correct
    assert result == {"format": "json", "value": 42}

    # Verify data was serialized as JSON
    call_args = initialized_redis_pool.set.call_args
    serialized_value = call_args[0][1]
    assert isinstance(serialized_value, str)
    deserialized = json.loads(serialized_value)
    assert deserialized == {"format": "json", "value": 42}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_msgpack_format(initialized_redis_pool):
    """Test @cached decorator with msgpack serialization."""
    @cached(key="test:msgpack", format="msgpack")
    async def get_msgpack_data():
        return {"format": "msgpack", "value": 42}

    initialized_redis_pool.get.return_value = None

    await get_msgpack_data()

    # Verify data was serialized (msgpack is base64 encoded)
    call_args = initialized_redis_pool.set.call_args
    serialized_value = call_args[0][1]
    assert isinstance(serialized_value, str)
    # Should be base64 encoded
    try:
        base64.b64decode(serialized_value)
    except Exception:
        pytest.fail("Expected base64 encoded msgpack data")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_compression(initialized_redis_pool):
    """Test @cached decorator with compression enabled."""
    @cached(
        key="test:compressed",
        compress=True,
        compression_threshold=10  # Low threshold for testing
    )
    async def get_large_data():
        return {"data": "x" * 1000}  # Large enough to trigger compression

    initialized_redis_pool.get.return_value = None

    await get_large_data()

    # Verify data was compressed and base64 encoded
    call_args = initialized_redis_pool.set.call_args
    serialized_value = call_args[0][1]
    assert isinstance(serialized_value, str)
    # Should be base64 encoded
    try:
        decoded = base64.b64decode(serialized_value)
        # Compressed data should be smaller than original
        assert len(decoded) < 1000
    except Exception:
        pytest.fail("Expected base64 encoded compressed data")


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_fallback_on_redis_unavailable(initialized_redis_pool):
    """Test @cached decorator falls back to function when Redis is unavailable."""
    call_count = 0

    @cached(key="test:fallback", ttl=60)
    async def get_data_with_fallback():
        nonlocal call_count
        call_count += 1
        return {"fallback": True}

    # Mock Redis to raise exception
    initialized_redis_pool.get.side_effect = Exception("Redis unavailable")

    # Function should still work (fallback)
    result = await get_data_with_fallback()

    assert call_count == 1
    assert result == {"fallback": True}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_fallback_on_deserialization_error(initialized_redis_pool):
    """Test @cached decorator falls back on deserialization error."""
    call_count = 0

    @cached(key="test:deserialize", ttl=60)
    async def get_data():
        nonlocal call_count
        call_count += 1
        return {"value": 42}

    # Mock Redis to return invalid JSON
    initialized_redis_pool.get.return_value = "invalid json {"

    # Should fall back to calling function
    result = await get_data()

    assert call_count == 1
    assert result == {"value": 42}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_fallback_on_set_failure(initialized_redis_pool):
    """Test @cached decorator continues on cache set failure."""
    @cached(key="test:set_failure", ttl=60)
    async def get_data():
        return {"value": 42}

    initialized_redis_pool.get.return_value = None
    initialized_redis_pool.setex.side_effect = Exception("Redis write failed")

    # Function should still return result
    result = await get_data()
    assert result == {"value": 42}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_fallback_on_key_builder_error(initialized_redis_pool):
    """Test @cached decorator falls back when key builder fails."""
    call_count = 0

    @cached(
        key_builder=lambda x: x["invalid_key"],  # Will raise KeyError
        ttl=60
    )
    async def get_data(data):
        nonlocal call_count
        call_count += 1
        return {"result": "success"}

    # Should fall back to calling function without caching
    result = await get_data({"valid_key": "value"})

    assert call_count == 1
    assert result == {"result": "success"}
    # Redis should not be called if key building fails
    initialized_redis_pool.get.assert_not_called()


# ==================== Sync Function Tests ====================


@pytest.mark.unit
def test_cached_sync_function_cache_miss():
    """Test @cached decorator with sync function on cache miss."""
    call_count = 0

    @cached(key="test:sync:miss", ttl=60)
    def get_sync_data():
        nonlocal call_count
        call_count += 1
        return {"sync": True}

    # Mock sync Redis client
    with patch('backend.cache.decorator.get_redis_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_get_client.return_value = mock_client

        result = get_sync_data()

        assert call_count == 1
        assert result == {"sync": True}
        mock_client.get.assert_called_once()


@pytest.mark.unit
def test_cached_sync_function_cache_hit():
    """Test @cached decorator with sync function on cache hit."""
    call_count = 0

    @cached(key="test:sync:hit", ttl=60)
    def get_sync_data():
        nonlocal call_count
        call_count += 1
        return {"sync": True}

    # Mock sync Redis client
    with patch('backend.cache.decorator.get_redis_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.get.return_value = json.dumps({"sync": True})
        mock_get_client.return_value = mock_client

        result = get_sync_data()

        # Function should not be called (cache hit)
        assert call_count == 0
        assert result == {"sync": True}


# ==================== Cache Invalidation Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalidate_cache_async_by_key(initialized_redis_pool):
    """Test invalidate_cache_async() with specific key."""
    initialized_redis_pool.delete.return_value = 1

    count = await invalidate_cache_async(key="test:invalidate")

    assert count == 1
    initialized_redis_pool.delete.assert_called_once_with("test:invalidate")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalidate_cache_async_by_pattern(initialized_redis_pool):
    """Test invalidate_cache_async() with pattern matching."""
    # Mock keys matching pattern
    initialized_redis_pool.keys.return_value = [
        "research:report:1",
        "research:report:2",
        "research:report:3"
    ]
    initialized_redis_pool.delete.return_value = 3

    count = await invalidate_cache_async(pattern="research:*")

    assert count == 3
    initialized_redis_pool.keys.assert_called_once_with("research:*")
    initialized_redis_pool.delete.assert_called_once_with(
        "research:report:1",
        "research:report:2",
        "research:report:3"
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalidate_cache_async_pattern_no_matches(initialized_redis_pool):
    """Test invalidate_cache_async() when pattern matches no keys."""
    initialized_redis_pool.keys.return_value = []

    count = await invalidate_cache_async(pattern="nonexistent:*")

    assert count == 0
    initialized_redis_pool.delete.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalidate_cache_async_requires_key_or_pattern():
    """Test invalidate_cache_async() raises error without key or pattern."""
    with pytest.raises(ValueError, match="Either 'key' or 'pattern' must be provided"):
        await invalidate_cache_async()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_invalidate_cache_async_error_handling(initialized_redis_pool):
    """Test invalidate_cache_async() handles Redis errors gracefully."""
    initialized_redis_pool.delete.side_effect = Exception("Redis error")

    count = await invalidate_cache_async(key="test:error")

    # Should return 0 on error, not raise
    assert count == 0


@pytest.mark.unit
def test_invalidate_cache_sync_wrapper():
    """Test invalidate_cache() sync wrapper function."""
    with patch('backend.cache.decorator.invalidate_cache_async') as mock_async:
        # Mock the async function
        async def mock_invalidate(key=None, pattern=None):
            return 1

        mock_async.return_value = mock_invalidate(key="test:sync")

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = 1

            count = invalidate_cache(key="test:sync")

            # Sync wrapper should call async version
            mock_run.assert_called_once()


# ==================== Decorator Argument Validation ====================


@pytest.mark.unit
def test_cached_requires_key_or_key_builder():
    """Test @cached decorator raises error without key or key_builder."""
    with pytest.raises(ValueError, match="Either 'key' or 'key_builder' must be provided"):
        @cached(ttl=60)
        async def invalid_func():
            return {}


@pytest.mark.unit
def test_cached_rejects_both_key_and_key_builder():
    """Test @cached decorator raises error with both key and key_builder."""
    with pytest.raises(ValueError, match="Cannot provide both 'key' and 'key_builder'"):
        @cached(key="test", key_builder=lambda x: "test", ttl=60)
        async def invalid_func():
            return {}


# ==================== Integration-Style Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_multiple_calls_same_key(initialized_redis_pool):
    """Test multiple calls to cached function with same key."""
    call_count = 0

    @cached(key="test:multiple", ttl=60)
    async def get_data():
        nonlocal call_count
        call_count += 1
        return {"call": call_count}

    # First call - cache miss
    initialized_redis_pool.get.return_value = None
    result1 = await get_data()
    assert result1 == {"call": 1}
    assert call_count == 1

    # Second call - cache hit
    initialized_redis_pool.get.return_value = json.dumps({"call": 1})
    result2 = await get_data()
    assert result2 == {"call": 1}  # Returns cached value
    assert call_count == 1  # Function not called again


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_different_keys_different_values(initialized_redis_pool):
    """Test cached function with different keys returns different values."""
    @cached(
        key_builder=lambda user_id: f"user:{user_id}",
        ttl=60
    )
    async def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}

    initialized_redis_pool.get.return_value = None

    # Call with different user IDs
    result1 = await get_user("123")
    result2 = await get_user("456")

    assert result1 == {"user_id": "123", "name": "User 123"}
    assert result2 == {"user_id": "456", "name": "User 456"}

    # Verify different keys were used
    assert initialized_redis_pool.get.call_count == 2
    calls = [call[0][0] for call in initialized_redis_pool.get.call_args_list]
    assert "user:123" in calls
    assert "user:456" in calls


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_preserves_function_metadata(initialized_redis_pool):
    """Test @cached decorator preserves function name and docstring."""
    @cached(key="test:metadata", ttl=60)
    async def documented_function():
        """This function has a docstring."""
        return {"documented": True}

    assert documented_function.__name__ == "documented_function"
    assert "docstring" in documented_function.__doc__


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_complex_data_types(initialized_redis_pool):
    """Test @cached decorator with complex nested data structures."""
    @cached(key="test:complex", ttl=60)
    async def get_complex_data():
        return {
            "nested": {
                "list": [1, 2, 3],
                "dict": {"a": "b"}
            },
            "array": [{"x": 1}, {"x": 2}],
            "null": None,
            "bool": True
        }

    initialized_redis_pool.get.return_value = None

    result = await get_complex_data()

    # Verify complex structure is preserved
    assert result["nested"]["list"] == [1, 2, 3]
    assert result["nested"]["dict"] == {"a": "b"}
    assert result["array"] == [{"x": 1}, {"x": 2}]
    assert result["null"] is None
    assert result["bool"] is True


# ==================== Edge Cases ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_empty_result(initialized_redis_pool):
    """Test @cached decorator with empty result."""
    @cached(key="test:empty", ttl=60)
    async def get_empty_data():
        return {}

    initialized_redis_pool.get.return_value = None

    result = await get_empty_data()

    # Empty dict should still be cached
    assert result == {}
    initialized_redis_pool.setex.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_with_none_result(initialized_redis_pool):
    """Test @cached decorator with None result."""
    @cached(key="test:none", ttl=60)
    async def get_none_data():
        return None

    initialized_redis_pool.get.return_value = None

    result = await get_none_data()

    # None should be cached (as JSON null)
    assert result is None
    initialized_redis_pool.setex.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_cached_function_raises_exception(initialized_redis_pool):
    """Test @cached decorator propagates function exceptions."""
    @cached(key="test:exception", ttl=60)
    async def failing_function():
        raise ValueError("Function failed")

    initialized_redis_pool.get.return_value = None

    # Exception should be propagated
    with pytest.raises(ValueError, match="Function failed"):
        await failing_function()

    # Should not attempt to cache on error
    initialized_redis_pool.setex.assert_not_called()
