"""Cache decorator for automatic Redis caching.

This module provides a @cached decorator that automatically caches function
results in Redis. It supports both synchronous and asynchronous functions,
custom key builders, TTL configuration, and multiple serialization formats.

Features:
    - Automatic cache-through pattern (try cache, fallback to function)
    - Support for both sync and async functions
    - Custom cache key builders
    - Configurable TTL (time-to-live)
    - Multiple serialization formats (JSON, msgpack)
    - Automatic compression for large payloads
    - Graceful error handling (fallback to function if Redis fails)
    - Detailed logging for cache hits/misses

Usage:
    from backend.cache.decorator import cached
    from backend.cache.keys import research_report_key

    # Simple usage with string key
    @cached(key="data:simple", ttl=3600)
    def get_simple_data():
        return {"value": 42}

    # Custom key builder function
    @cached(key_builder=lambda report_id: research_report_key(report_id), ttl=86400)
    def get_research_report(report_id: str):
        # Expensive database query
        return fetch_from_database(report_id)

    # Async function support
    @cached(key="data:async", ttl=300)
    async def get_async_data():
        # Async operation
        return await fetch_data()

    # With compression for large data
    @cached(key="data:large", ttl=600, compress=True)
    def get_large_dataset():
        return {"bars": [...]}  # Large dataset

Example:
    # Define a cached function
    @cached(
        key_builder=lambda symbol: f"market:price:{symbol}",
        ttl=300,  # 5 minutes
        format="msgpack",
        compress=True
    )
    def get_stock_price(symbol: str):
        # This will only be called on cache miss
        return fetch_price_from_api(symbol)

    # First call - cache miss, fetches from API
    price = get_stock_price("SPY")

    # Second call - cache hit, returns from Redis
    price = get_stock_price("SPY")
"""

import functools
import inspect
import logging
import base64
from typing import Any, Callable, Optional, Union
import asyncio

from backend.redis_client import get_redis_client, get_redis_pool
from backend.cache.serializer import serialize, deserialize

logger = logging.getLogger(__name__)


def cached(
    key: Optional[str] = None,
    key_builder: Optional[Callable[..., str]] = None,
    ttl: Optional[int] = None,
    format: str = "json",
    compress: bool = False,
    compression_threshold: int = 1024,
):
    """
    Decorator for automatic Redis caching of function results.

    This decorator implements a cache-through pattern: it first checks Redis
    for a cached result, and if not found, calls the original function and
    caches the result.

    Args:
        key: Static cache key (use for functions with no arguments)
        key_builder: Function that builds cache key from function arguments.
                    Should accept the same arguments as the decorated function.
                    Example: lambda report_id: f"research:report:{report_id}"
        ttl: Time-to-live in seconds. None = no expiration
        format: Serialization format ("json" or "msgpack")
        compress: Whether to compress cached data
        compression_threshold: Compress if size exceeds this (bytes)

    Returns:
        Decorated function that uses caching

    Raises:
        ValueError: If neither key nor key_builder is provided, or both are provided

    Examples:
        # Static key (for functions with no args)
        @cached(key="data:latest", ttl=3600)
        def get_latest_data():
            return fetch_data()

        # Dynamic key builder
        @cached(
            key_builder=lambda report_id: f"research:report:{report_id}",
            ttl=86400
        )
        def get_report(report_id: str):
            return fetch_report(report_id)

        # With multiple arguments
        @cached(
            key_builder=lambda symbol, date: f"market:price:{symbol}:{date}",
            ttl=3600
        )
        def get_price(symbol: str, date: str):
            return fetch_price(symbol, date)

        # Async function
        @cached(key="data:async", ttl=300)
        async def get_async_data():
            return await fetch_async()

        # With compression
        @cached(
            key_builder=lambda week_id: f"research:week:{week_id}",
            ttl=3600,
            format="msgpack",
            compress=True
        )
        def get_large_report(week_id: str):
            return fetch_large_data(week_id)

    Notes:
        - If Redis is unavailable, the decorator falls back to calling the function
        - Cache errors are logged but don't break the application
        - Both sync and async functions are supported automatically
        - The decorator preserves function signatures and docstrings
    """
    # Validate arguments
    if key is None and key_builder is None:
        raise ValueError("Either 'key' or 'key_builder' must be provided")
    if key is not None and key_builder is not None:
        raise ValueError("Cannot provide both 'key' and 'key_builder'")

    def decorator(func: Callable) -> Callable:
        """Inner decorator that wraps the function."""

        # Check if function is async
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                """Async wrapper with caching logic."""
                return await _cached_call(
                    func=func,
                    args=args,
                    kwargs=kwargs,
                    key=key,
                    key_builder=key_builder,
                    ttl=ttl,
                    format=format,
                    compress=compress,
                    compression_threshold=compression_threshold,
                    is_async=True,
                )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                """Sync wrapper with caching logic."""
                return _cached_call_sync(
                    func=func,
                    args=args,
                    kwargs=kwargs,
                    key=key,
                    key_builder=key_builder,
                    ttl=ttl,
                    format=format,
                    compress=compress,
                    compression_threshold=compression_threshold,
                )
            return sync_wrapper

    return decorator


def _cached_call_sync(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key: Optional[str],
    key_builder: Optional[Callable],
    ttl: Optional[int],
    format: str,
    compress: bool,
    compression_threshold: int,
) -> Any:
    """
    Internal function that implements the caching logic for sync functions.

    This is the synchronous version of _cached_call.

    Args:
        func: The original function to cache
        args: Positional arguments passed to the function
        kwargs: Keyword arguments passed to the function
        key: Static cache key
        key_builder: Dynamic key builder function
        ttl: Time-to-live in seconds
        format: Serialization format
        compress: Whether to compress
        compression_threshold: Compression threshold

    Returns:
        The function result (from cache or freshly computed)
    """
    # Build cache key
    try:
        if key is not None:
            cache_key = key
        else:
            # Call key_builder with function arguments
            cache_key = key_builder(*args, **kwargs)
    except Exception as e:
        logger.error(f"Failed to build cache key for {func.__name__}: {e}")
        # Fall back to calling function without caching
        return func(*args, **kwargs)

    # Try to get from cache
    try:
        redis_client = get_redis_client()
        cached_value = redis_client.get(cache_key)

        if cached_value is not None:
            # Cache hit - deserialize and return
            try:
                # If format is msgpack or compressed, decode from base64
                if format == "msgpack" or compress:
                    cached_value = base64.b64decode(cached_value)

                result = deserialize(
                    cached_value,
                    format=format,
                    compressed=compress
                )
                logger.info(f"Cache HIT: {cache_key} (func={func.__name__})")
                return result
            except Exception as e:
                logger.error(
                    f"Failed to deserialize cached value for {cache_key}: {e}. "
                    "Falling back to function call."
                )
                # Fall through to cache miss logic

    except Exception as e:
        logger.warning(
            f"Redis error for {cache_key}: {e}. "
            "Falling back to function call without caching."
        )
        # Fall through to cache miss logic

    # Cache miss - call the original function
    logger.info(f"Cache MISS: {cache_key} (func={func.__name__})")

    try:
        result = func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Function {func.__name__} failed: {e}")
        raise

    # Cache the result
    try:
        redis_client = get_redis_client()

        # Serialize the result
        serialized = serialize(
            result,
            format=format,
            compress=compress,
            compression_threshold=compression_threshold
        )

        # Store in Redis (convert bytes to base64 string for storage)
        if isinstance(serialized, bytes):
            # For msgpack or compressed data, encode to base64
            serialized = base64.b64encode(serialized).decode("ascii")

        success = redis_client.set(cache_key, serialized, ttl=ttl)

        if success:
            logger.info(
                f"Cache SET: {cache_key} (func={func.__name__}, ttl={ttl})"
            )
        else:
            logger.warning(f"Failed to cache result for {cache_key}")

    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to cache result for {cache_key}: {e}")

    return result


async def _cached_call(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key: Optional[str],
    key_builder: Optional[Callable],
    ttl: Optional[int],
    format: str,
    compress: bool,
    compression_threshold: int,
    is_async: bool,
) -> Any:
    """
    Internal function that implements the caching logic.

    This function is called by both sync and async wrappers to avoid
    code duplication.

    Args:
        func: The original function to cache
        args: Positional arguments passed to the function
        kwargs: Keyword arguments passed to the function
        key: Static cache key
        key_builder: Dynamic key builder function
        ttl: Time-to-live in seconds
        format: Serialization format
        compress: Whether to compress
        compression_threshold: Compression threshold
        is_async: Whether the function is async

    Returns:
        The function result (from cache or freshly computed)
    """
    # Build cache key
    try:
        if key is not None:
            cache_key = key
        else:
            # Call key_builder with function arguments
            cache_key = key_builder(*args, **kwargs)
    except Exception as e:
        logger.error(f"Failed to build cache key for {func.__name__}: {e}")
        # Fall back to calling function without caching
        if is_async:
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    # Try to get from cache
    try:
        redis_pool = get_redis_pool()
        cached_value = await redis_pool.get(cache_key)

        if cached_value is not None:
            # Cache hit - deserialize and return
            try:
                # If format is msgpack or compressed, decode from base64
                if format == "msgpack" or compress:
                    cached_value = base64.b64decode(cached_value)

                result = deserialize(
                    cached_value,
                    format=format,
                    compressed=compress
                )
                logger.info(f"Cache HIT: {cache_key} (func={func.__name__})")
                return result
            except Exception as e:
                logger.error(
                    f"Failed to deserialize cached value for {cache_key}: {e}. "
                    "Falling back to function call."
                )
                # Fall through to cache miss logic

    except Exception as e:
        logger.warning(
            f"Redis error for {cache_key}: {e}. "
            "Falling back to function call without caching."
        )
        # Fall through to cache miss logic

    # Cache miss - call the original function
    logger.info(f"Cache MISS: {cache_key} (func={func.__name__})")

    try:
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Function {func.__name__} failed: {e}")
        raise

    # Cache the result
    try:
        redis_pool = get_redis_pool()

        # Serialize the result
        serialized = serialize(
            result,
            format=format,
            compress=compress,
            compression_threshold=compression_threshold
        )

        # Store in Redis (convert bytes to base64 string for storage)
        if isinstance(serialized, bytes):
            # For msgpack or compressed data, encode to base64
            serialized = base64.b64encode(serialized).decode("ascii")

        if ttl:
            success = await redis_pool.setex(cache_key, ttl, serialized)
        else:
            success = await redis_pool.set(cache_key, serialized)

        if success:
            logger.info(
                f"Cache SET: {cache_key} (func={func.__name__}, ttl={ttl})"
            )
        else:
            logger.warning(f"Failed to cache result for {cache_key}")

    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to cache result for {cache_key}: {e}")

    return result


def cache_key_from_args(*arg_names: str) -> Callable:
    """
    Helper function to build cache key from function arguments.

    This is a convenience function for creating key_builder functions
    that combine multiple function arguments into a cache key.

    Args:
        *arg_names: Names of function arguments to include in the key

    Returns:
        A key_builder function that can be passed to @cached

    Examples:
        # Cache by report_id
        @cached(
            key_builder=cache_key_from_args("report_id"),
            ttl=3600
        )
        def get_report(report_id: str):
            return fetch_report(report_id)

        # Cache by symbol and date
        @cached(
            key_builder=cache_key_from_args("symbol", "date"),
            ttl=3600
        )
        def get_price(symbol: str, date: str):
            return fetch_price(symbol, date)

    Notes:
        The key format is: "func:{func_name}:{arg1}:{arg2}:..."
    """
    def builder(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # Extract argument values
            arg_values = []
            for arg_name in arg_names:
                if arg_name in bound.arguments:
                    arg_values.append(str(bound.arguments[arg_name]))
                else:
                    logger.warning(
                        f"Argument '{arg_name}' not found in function signature. "
                        f"Available: {list(bound.arguments.keys())}"
                    )

            # Build key
            key_parts = ["func", func.__name__] + arg_values
            return ":".join(key_parts)

        return wrapper

    return builder


async def invalidate_cache_async(
    key: Optional[str] = None,
    pattern: Optional[str] = None
) -> int:
    """
    Manually invalidate cache entries (async version).

    This function allows manual cache invalidation by either:
    - Deleting a specific key
    - Deleting all keys matching a pattern

    Args:
        key: Specific cache key to delete
        pattern: Pattern to match (e.g., "research:*", "market:prices:*")

    Returns:
        Number of keys deleted

    Examples:
        # Delete specific key
        await invalidate_cache_async(key="research:report:abc123")

        # Delete all research caches
        await invalidate_cache_async(pattern="research:*")

        # Delete all price caches
        await invalidate_cache_async(pattern="market:prices:*")

    Raises:
        ValueError: If neither key nor pattern is provided

    Notes:
        - Use pattern with caution - it can delete many keys at once
        - Returns 0 if Redis is unavailable or if no keys match
        - Use this in async contexts (FastAPI routes, async functions)
    """
    if key is None and pattern is None:
        raise ValueError("Either 'key' or 'pattern' must be provided")

    try:
        redis_pool = get_redis_pool()

        if key is not None:
            count = await redis_pool.delete(key)
            logger.info(f"Cache invalidated: {key} (deleted={count})")
            return count
        else:
            # For pattern deletion, we need to get keys first, then delete
            keys = await redis_pool.keys(pattern)
            if keys:
                count = await redis_pool.delete(*keys)
                logger.info(
                    f"Cache invalidated by pattern: {pattern} (deleted={count})"
                )
                return count
            else:
                logger.info(f"No keys matched pattern: {pattern}")
                return 0

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        return 0


def invalidate_cache(
    key: Optional[str] = None,
    pattern: Optional[str] = None
) -> int:
    """
    Manually invalidate cache entries (sync version).

    This function allows manual cache invalidation by either:
    - Deleting a specific key
    - Deleting all keys matching a pattern

    Args:
        key: Specific cache key to delete
        pattern: Pattern to match (e.g., "research:*", "market:prices:*")

    Returns:
        Number of keys deleted

    Examples:
        # Delete specific key
        invalidate_cache(key="research:report:abc123")

        # Delete all research caches
        invalidate_cache(pattern="research:*")

        # Delete all price caches
        invalidate_cache(pattern="market:prices:*")

    Raises:
        ValueError: If neither key nor pattern is provided

    Notes:
        - Use pattern with caution - it can delete many keys at once
        - Returns 0 if Redis is unavailable or if no keys match
        - Use this in sync contexts (scripts, sync functions)
        - For async contexts, use invalidate_cache_async() instead
    """
    if key is None and pattern is None:
        raise ValueError("Either 'key' or 'pattern' must be provided")

    try:
        redis_client = get_redis_client()

        if key is not None:
            count = redis_client.delete(key)
            logger.info(f"Cache invalidated: {key} (deleted={count})")
            return count
        else:
            count = redis_client.delete_pattern(pattern)
            logger.info(
                f"Cache invalidated by pattern: {pattern} (deleted={count})"
            )
            return count

    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        return 0
