"""Cache layer utilities for Redis caching.

This package provides utilities for caching research reports, market data,
and PM pitches in Redis. It includes key builders, serialization utilities,
decorators, and invalidation helpers.

Key Modules:
    - keys: Cache key builders for different data types
    - serializer: JSON/msgpack serialization utilities
    - decorator: @cached decorator for automatic caching
    - invalidation: Cache invalidation helpers

Example:
    from backend.cache.keys import research_report_key
    from backend.cache.decorator import cached
    from backend.redis_client import get_redis_client

    # Use decorator for automatic caching
    @cached(
        key_builder=lambda report_id: research_report_key(report_id),
        ttl=3600
    )
    def get_report(report_id: str):
        return fetch_from_db(report_id)

    # Or use Redis client directly
    redis = get_redis_client()
    redis.set(key, json.dumps(data), ttl=3600)
"""

__version__ = "1.0.0"

# Re-export key builders for convenience
from .keys import (
    research_report_key,
    research_latest_key,
    research_week_key,
    market_metrics_key,
    market_prices_key,
    market_snapshot_key,
    pitches_week_key,
    pitches_date_key,
    pitches_latest_key,
    graphs_latest_key,
    data_package_key,
)

# Re-export decorator functions
from .decorator import (
    cached,
    cache_key_from_args,
    invalidate_cache,
)

__all__ = [
    # Key builders
    "research_report_key",
    "research_latest_key",
    "research_week_key",
    "market_metrics_key",
    "market_prices_key",
    "market_snapshot_key",
    "pitches_week_key",
    "pitches_date_key",
    "pitches_latest_key",
    "graphs_latest_key",
    "data_package_key",
    # Decorator functions
    "cached",
    "cache_key_from_args",
    "invalidate_cache",
]
