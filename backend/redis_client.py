"""Redis client wrapper with connection pooling and error handling.

This module provides a Redis client with automatic connection pooling,
retry logic, and health checks for caching research reports and market data.
"""

import os
import logging
from typing import Optional, Any, Union
from contextlib import contextmanager
import time

import redis
from redis.connection import ConnectionPool
from redis.exceptions import (
    RedisError,
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client with connection pooling and automatic retry logic.

    This client provides a robust interface to Redis with:
    - Connection pooling for efficient resource usage
    - Automatic retry logic for transient failures
    - Health checks to verify connectivity
    - Graceful error handling and logging

    Environment Variables:
        REDIS_HOST: Redis server host (default: localhost)
        REDIS_PORT: Redis server port (default: 6379)
        REDIS_DB: Redis database number (default: 0)
        REDIS_PASSWORD: Redis password (default: None)
        REDIS_MAX_CONNECTIONS: Max connections in pool (default: 10)
        REDIS_SOCKET_TIMEOUT: Socket timeout in seconds (default: 5)
        REDIS_SOCKET_CONNECT_TIMEOUT: Connection timeout in seconds (default: 5)
        REDIS_RETRY_ON_TIMEOUT: Retry on timeout (default: True)
        REDIS_MAX_RETRIES: Max retry attempts (default: 3)

    Example:
        # Initialize client (usually at startup)
        redis_client = RedisClient()

        # Check health
        if redis_client.ping():
            print("Redis is connected")

        # Set/get values
        redis_client.set("key", "value", ttl=3600)
        value = redis_client.get("key")

        # Use context manager for operations
        with redis_client.pipeline() as pipe:
            pipe.set("key1", "value1")
            pipe.set("key2", "value2")
            pipe.execute()
    """

    def __init__(self):
        """Initialize Redis client with connection pool."""
        # Read configuration from environment
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        self.socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        self.socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
        self.retry_on_timeout = os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        self.max_retries = int(os.getenv("REDIS_MAX_RETRIES", "3"))

        # Create connection pool
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self._initialized = False

        # Initialize connection
        self._initialize()

    def _initialize(self):
        """
        Initialize Redis connection pool and client.

        Creates a connection pool and Redis client instance.
        Logs connection details for debugging.
        """
        try:
            # Create connection pool
            self.pool = ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=True,  # Return strings instead of bytes
            )

            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)

            self._initialized = True
            logger.info(
                f"Redis client initialized: {self.host}:{self.port} db={self.db} "
                f"max_connections={self.max_connections}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}", exc_info=True)
            self._initialized = False
            raise

    def _ensure_connection(self):
        """
        Ensure Redis connection is initialized.

        Raises:
            RuntimeError: If Redis client is not initialized
        """
        if not self._initialized or self.client is None:
            raise RuntimeError("Redis client is not initialized")

    def _retry_operation(self, operation, *args, **kwargs) -> Any:
        """
        Execute a Redis operation with retry logic.

        Args:
            operation: The Redis operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            RedisError: If operation fails after all retries
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)

            except (RedisConnectionError, RedisTimeoutError) as e:
                last_error = e
                logger.warning(
                    f"Redis operation failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                # Wait before retry (exponential backoff)
                if attempt < self.max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # 0.1s, 0.2s, 0.4s
                    time.sleep(wait_time)

            except RedisError as e:
                # Non-retryable Redis error
                logger.error(f"Redis operation failed with non-retryable error: {e}")
                raise

        # All retries exhausted
        logger.error(f"Redis operation failed after {self.max_retries} attempts")
        raise last_error

    def ping(self) -> bool:
        """
        Check if Redis server is reachable.

        Returns:
            True if server responds to ping, False otherwise

        Example:
            if not redis_client.ping():
                logger.error("Redis is not available")
        """
        try:
            self._ensure_connection()
            result = self._retry_operation(self.client.ping)
            logger.debug("Redis ping successful")
            return result

        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.

        Args:
            key: Cache key

        Returns:
            Value if found, None otherwise

        Example:
            value = redis_client.get("market:prices:SPY")
        """
        try:
            self._ensure_connection()
            value = self._retry_operation(self.client.get, key)

            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")

            return value

        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            return None

    def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis with optional TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise

        Example:
            # Cache for 1 hour
            redis_client.set("market:prices:SPY", json.dumps(data), ttl=3600)
        """
        try:
            self._ensure_connection()

            if ttl is not None:
                result = self._retry_operation(self.client.setex, key, ttl, value)
            else:
                result = self._retry_operation(self.client.set, key, value)

            logger.debug(f"Cache SET: {key} (ttl={ttl})")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted

        Example:
            redis_client.delete("key1", "key2", "key3")
        """
        try:
            self._ensure_connection()
            count = self._retry_operation(self.client.delete, *keys)
            logger.debug(f"Cache DELETE: {keys} (count={count})")
            return count

        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """
        Check if keys exist in Redis.

        Args:
            *keys: Keys to check

        Returns:
            Number of keys that exist

        Example:
            if redis_client.exists("market:prices:SPY"):
                print("Cache exists")
        """
        try:
            self._ensure_connection()
            count = self._retry_operation(self.client.exists, *keys)
            return count

        except Exception as e:
            logger.error(f"Failed to check existence of keys {keys}: {e}")
            return 0

    def keys(self, pattern: str = "*") -> list[str]:
        """
        Find keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "market:*")

        Returns:
            List of matching keys

        Example:
            # Find all market-related keys
            keys = redis_client.keys("market:*")

        Warning:
            Use with caution in production - can be slow with many keys.
            Consider using SCAN instead for large datasets.
        """
        try:
            self._ensure_connection()
            keys = self._retry_operation(self.client.keys, pattern)
            return keys if keys else []

        except Exception as e:
            logger.error(f"Failed to get keys matching '{pattern}': {e}")
            return []

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "market:prices:*")

        Returns:
            Number of keys deleted

        Example:
            # Clear all price caches
            redis_client.delete_pattern("market:prices:*")

        Warning:
            Use with caution - this can delete many keys at once.
        """
        try:
            keys = self.keys(pattern)
            if keys:
                return self.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Failed to delete keys matching '{pattern}': {e}")
            return 0

    def ttl(self, key: str) -> int:
        """
        Get time-to-live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist

        Example:
            ttl = redis_client.ttl("market:prices:SPY")
            if ttl > 0:
                print(f"Cache expires in {ttl} seconds")
        """
        try:
            self._ensure_connection()
            return self._retry_operation(self.client.ttl, key)

        except Exception as e:
            logger.error(f"Failed to get TTL for key '{key}': {e}")
            return -2

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise

        Example:
            # Extend cache expiration
            redis_client.expire("market:prices:SPY", 3600)
        """
        try:
            self._ensure_connection()
            result = self._retry_operation(self.client.expire, key, ttl)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set expiration for key '{key}': {e}")
            return False

    @contextmanager
    def pipeline(self, transaction: bool = True):
        """
        Create a Redis pipeline for batch operations.

        Args:
            transaction: Whether to use MULTI/EXEC transaction

        Yields:
            Redis pipeline object

        Example:
            with redis_client.pipeline() as pipe:
                pipe.set("key1", "value1")
                pipe.set("key2", "value2")
                pipe.set("key3", "value3")
                results = pipe.execute()
        """
        self._ensure_connection()
        pipe = self.client.pipeline(transaction=transaction)
        try:
            yield pipe
        finally:
            pipe.reset()

    def info(self, section: Optional[str] = None) -> dict:
        """
        Get Redis server information.

        Args:
            section: Specific section to get (e.g., "memory", "stats")

        Returns:
            Dictionary with server information

        Example:
            info = redis_client.info("memory")
            print(f"Used memory: {info['used_memory_human']}")
        """
        try:
            self._ensure_connection()
            return self._retry_operation(self.client.info, section)

        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}

    def dbsize(self) -> int:
        """
        Get the number of keys in the current database.

        Returns:
            Number of keys

        Example:
            num_keys = redis_client.dbsize()
            print(f"Redis has {num_keys} keys")
        """
        try:
            self._ensure_connection()
            return self._retry_operation(self.client.dbsize)

        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0

    def flushdb(self) -> bool:
        """
        Delete all keys in the current database.

        Returns:
            True if successful, False otherwise

        Warning:
            This will delete ALL keys in the current database.
            Use with extreme caution!

        Example:
            # Clear all cached data
            redis_client.flushdb()
        """
        try:
            self._ensure_connection()
            result = self._retry_operation(self.client.flushdb)
            logger.warning("Redis database flushed - all keys deleted")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False

    def close(self):
        """
        Close Redis connection pool.

        Should be called on application shutdown.

        Example:
            # On shutdown
            redis_client.close()
        """
        if self.pool is not None:
            try:
                self.pool.disconnect()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")
            finally:
                self._initialized = False
                self.client = None
                self.pool = None


# Global Redis client instance (initialized on first import)
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get the global Redis client instance.

    This function provides a singleton Redis client that is shared
    across the application. The client is initialized on first access.

    Returns:
        RedisClient instance

    Raises:
        RuntimeError: If Redis client initialization fails

    Example:
        # In FastAPI dependency
        def get_redis():
            return get_redis_client()

        @app.get("/api/data")
        async def get_data(redis = Depends(get_redis)):
            cached = redis.get("data")
            if cached:
                return json.loads(cached)
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = RedisClient()
            logger.info("Global Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize global Redis client: {e}")
            raise RuntimeError(f"Redis client initialization failed: {e}")

    return _redis_client


def close_redis_client():
    """
    Close the global Redis client connection.

    Should be called on application shutdown.

    Example:
        @app.on_event("shutdown")
        async def shutdown_event():
            close_redis_client()
    """
    global _redis_client

    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
        logger.info("Global Redis client closed")
