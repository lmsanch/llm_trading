"""Cache key builders for different data types.

This module provides functions to build consistent, namespaced cache keys
for different data types in the Redis cache layer.

Key Naming Convention:
    - Use colons (:) to separate namespaces
    - Format: {category}:{subcategory}:{identifier}
    - Examples:
        - research:report:abc123
        - market:metrics:2024-01-08
        - pitches:week:2024-W02

Benefits:
    - Easy pattern-based invalidation (e.g., "research:*")
    - Consistent naming across the codebase
    - Clear data type identification
    - Supports Redis keyspace notifications

Usage:
    from backend.cache.keys import research_report_key

    # Build a cache key
    key = research_report_key(report_id="abc123")
    # Returns: "research:report:abc123"

    # Use with Redis client
    redis = get_redis_client()
    cached = redis.get(key)
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Cache key prefixes for different data categories
PREFIX_RESEARCH = "research"
PREFIX_MARKET = "market"
PREFIX_PITCHES = "pitches"
PREFIX_GRAPHS = "graphs"
PREFIX_DATA_PACKAGE = "data_package"


# ============================================================================
# Research Report Keys
# ============================================================================


def research_report_key(report_id: str) -> str:
    """
    Build cache key for a specific research report by ID.

    Args:
        report_id: UUID of the research report

    Returns:
        Cache key in format: "research:report:{report_id}"

    Example:
        >>> research_report_key("550e8400-e29b-41d4-a716-446655440000")
        'research:report:550e8400-e29b-41d4-a716-446655440000'
    """
    if not report_id:
        raise ValueError("report_id is required")
    return f"{PREFIX_RESEARCH}:report:{report_id}"


def research_latest_key() -> str:
    """
    Build cache key for the latest research report.

    Returns:
        Cache key: "research:latest"

    Example:
        >>> research_latest_key()
        'research:latest'

    Note:
        This key should be invalidated whenever a new research report
        is saved to the database.
    """
    return f"{PREFIX_RESEARCH}:latest"


def research_week_key(week_id: str) -> str:
    """
    Build cache key for research reports by week identifier.

    Args:
        week_id: Week identifier (e.g., "2024-W02" or "2024-01-08")

    Returns:
        Cache key in format: "research:week:{week_id}"

    Example:
        >>> research_week_key("2024-W02")
        'research:week:2024-W02'
    """
    if not week_id:
        raise ValueError("week_id is required")
    return f"{PREFIX_RESEARCH}:week:{week_id}"


def research_history_key(days: int = 90) -> str:
    """
    Build cache key for research history.

    Args:
        days: Number of days to look back (default: 90)

    Returns:
        Cache key in format: "research:history:{days}"

    Example:
        >>> research_history_key(30)
        'research:history:30'
    """
    return f"{PREFIX_RESEARCH}:history:{days}"


# ============================================================================
# Market Data Keys
# ============================================================================


def market_metrics_key(date: Optional[str] = None) -> str:
    """
    Build cache key for market metrics (7-day returns and correlation matrix).

    Args:
        date: Optional date string (ISO format: "YYYY-MM-DD").
              If None, uses "latest" to cache the most recent metrics.

    Returns:
        Cache key in format:
            - "market:metrics:latest" (if date is None)
            - "market:metrics:{date}" (if date is provided)

    Examples:
        >>> market_metrics_key()
        'market:metrics:latest'

        >>> market_metrics_key("2024-01-08")
        'market:metrics:2024-01-08'

    Note:
        The "latest" key should be invalidated when new metrics are calculated.
        Dated keys can have longer TTL since historical data doesn't change.
    """
    if date:
        return f"{PREFIX_MARKET}:metrics:{date}"
    return f"{PREFIX_MARKET}:metrics:latest"


def market_prices_key(date: Optional[str] = None) -> str:
    """
    Build cache key for current prices (OHLCV data).

    Args:
        date: Optional date string (ISO format: "YYYY-MM-DD").
              If None, uses "latest" to cache the most recent prices.

    Returns:
        Cache key in format:
            - "market:prices:latest" (if date is None)
            - "market:prices:{date}" (if date is provided)

    Examples:
        >>> market_prices_key()
        'market:prices:latest'

        >>> market_prices_key("2024-01-08")
        'market:prices:2024-01-08'

    Note:
        Use shorter TTL for "latest" during market hours (5min),
        longer TTL after market close (1h).
    """
    if date:
        return f"{PREFIX_MARKET}:prices:{date}"
    return f"{PREFIX_MARKET}:prices:latest"


def market_snapshot_key() -> str:
    """
    Build cache key for market snapshot (30 bars × 10 instruments).

    Returns:
        Cache key: "market:snapshot:current"

    Example:
        >>> market_snapshot_key()
        'market:snapshot:current'

    Note:
        Market snapshot is expensive to compute (300 rows from DB).
        Cache with 15min TTL to balance freshness and performance.
    """
    return f"{PREFIX_MARKET}:snapshot:current"


def market_symbol_prices_key(symbol: str, date: Optional[str] = None) -> str:
    """
    Build cache key for a specific symbol's price data.

    Args:
        symbol: Trading symbol (e.g., "SPY", "QQQ")
        date: Optional date string (ISO format: "YYYY-MM-DD")

    Returns:
        Cache key in format:
            - "market:prices:symbol:{symbol}:latest" (if date is None)
            - "market:prices:symbol:{symbol}:{date}" (if date is provided)

    Examples:
        >>> market_symbol_prices_key("SPY")
        'market:prices:symbol:SPY:latest'

        >>> market_symbol_prices_key("SPY", "2024-01-08")
        'market:prices:symbol:SPY:2024-01-08'
    """
    if not symbol:
        raise ValueError("symbol is required")
    if date:
        return f"{PREFIX_MARKET}:prices:symbol:{symbol}:{date}"
    return f"{PREFIX_MARKET}:prices:symbol:{symbol}:latest"


# ============================================================================
# PM Pitches Keys
# ============================================================================


def pitches_week_key(week_id: str) -> str:
    """
    Build cache key for PM pitches by week identifier.

    Args:
        week_id: Week identifier (e.g., "2024-W02" or "2024-01-08")

    Returns:
        Cache key in format: "pitches:week:{week_id}"

    Example:
        >>> pitches_week_key("2024-W02")
        'pitches:week:2024-W02'
    """
    if not week_id:
        raise ValueError("week_id is required")
    return f"{PREFIX_PITCHES}:week:{week_id}"


def pitches_date_key(research_date: str) -> str:
    """
    Build cache key for PM pitches by research date.

    Args:
        research_date: ISO format date string (e.g., "2024-01-08")

    Returns:
        Cache key in format: "pitches:date:{research_date}"

    Example:
        >>> pitches_date_key("2024-01-08")
        'pitches:date:2024-01-08'

    Note:
        Research date is more specific than week_id and takes precedence
        when both are available.
    """
    if not research_date:
        raise ValueError("research_date is required")
    return f"{PREFIX_PITCHES}:date:{research_date}"


def pitches_latest_key() -> str:
    """
    Build cache key for the latest PM pitches.

    Returns:
        Cache key: "pitches:latest"

    Example:
        >>> pitches_latest_key()
        'pitches:latest'

    Note:
        This key should be invalidated whenever new pitches are saved.
    """
    return f"{PREFIX_PITCHES}:latest"


def pitches_model_key(model: str, week_id: Optional[str] = None) -> str:
    """
    Build cache key for pitches from a specific model.

    Args:
        model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")
        week_id: Optional week identifier

    Returns:
        Cache key in format:
            - "pitches:model:{model}:latest" (if week_id is None)
            - "pitches:model:{model}:{week_id}" (if week_id is provided)

    Examples:
        >>> pitches_model_key("gpt-4o")
        'pitches:model:gpt-4o:latest'

        >>> pitches_model_key("gpt-4o", "2024-W02")
        'pitches:model:gpt-4o:2024-W02'
    """
    if not model:
        raise ValueError("model is required")
    if week_id:
        return f"{PREFIX_PITCHES}:model:{model}:{week_id}"
    return f"{PREFIX_PITCHES}:model:{model}:latest"


# ============================================================================
# Knowledge Graphs Keys
# ============================================================================


def graphs_latest_key() -> str:
    """
    Build cache key for the latest knowledge graphs.

    Returns:
        Cache key: "graphs:latest"

    Example:
        >>> graphs_latest_key()
        'graphs:latest'

    Note:
        Knowledge graphs are extracted from research reports.
        Invalidate when new research is saved.
    """
    return f"{PREFIX_GRAPHS}:latest"


def graphs_week_key(week_id: str) -> str:
    """
    Build cache key for knowledge graphs by week identifier.

    Args:
        week_id: Week identifier (e.g., "2024-W02")

    Returns:
        Cache key in format: "graphs:week:{week_id}"

    Example:
        >>> graphs_week_key("2024-W02")
        'graphs:week:2024-W02'
    """
    if not week_id:
        raise ValueError("week_id is required")
    return f"{PREFIX_GRAPHS}:week:{week_id}"


# ============================================================================
# Data Package Keys
# ============================================================================


def data_package_key() -> str:
    """
    Build cache key for the complete data package.

    The data package combines:
        - Latest research report
        - Market metrics
        - Current prices

    Returns:
        Cache key: "data_package:latest"

    Example:
        >>> data_package_key()
        'data_package:latest'

    Note:
        This is a composite cache - invalidate when any component changes.
        Use short TTL (5min) since it aggregates multiple data sources.
    """
    return f"{PREFIX_DATA_PACKAGE}:latest"


def data_package_date_key(date: str) -> str:
    """
    Build cache key for data package on a specific date.

    Args:
        date: ISO format date string (e.g., "2024-01-08")

    Returns:
        Cache key in format: "data_package:date:{date}"

    Example:
        >>> data_package_date_key("2024-01-08")
        'data_package:date:2024-01-08'

    Note:
        Historical data packages can have longer TTL (24h+) since
        they don't change once created.
    """
    if not date:
        raise ValueError("date is required")
    return f"{PREFIX_DATA_PACKAGE}:date:{date}"


# ============================================================================
# Utility Functions
# ============================================================================


def get_all_research_keys_pattern() -> str:
    """
    Get pattern to match all research cache keys.

    Returns:
        Pattern: "research:*"

    Example:
        >>> get_all_research_keys_pattern()
        'research:*'

    Usage:
        # Invalidate all research caches
        redis.delete_pattern(get_all_research_keys_pattern())
    """
    return f"{PREFIX_RESEARCH}:*"


def get_all_market_keys_pattern() -> str:
    """
    Get pattern to match all market cache keys.

    Returns:
        Pattern: "market:*"

    Example:
        >>> get_all_market_keys_pattern()
        'market:*'
    """
    return f"{PREFIX_MARKET}:*"


def get_all_pitches_keys_pattern() -> str:
    """
    Get pattern to match all pitches cache keys.

    Returns:
        Pattern: "pitches:*"

    Example:
        >>> get_all_pitches_keys_pattern()
        'pitches:*'
    """
    return f"{PREFIX_PITCHES}:*"


def get_all_graphs_keys_pattern() -> str:
    """
    Get pattern to match all graphs cache keys.

    Returns:
        Pattern: "graphs:*"

    Example:
        >>> get_all_graphs_keys_pattern()
        'graphs:*'
    """
    return f"{PREFIX_GRAPHS}:*"


def get_all_data_package_keys_pattern() -> str:
    """
    Get pattern to match all data package cache keys.

    Returns:
        Pattern: "data_package:*"

    Example:
        >>> get_all_data_package_keys_pattern()
        'data_package:*'
    """
    return f"{PREFIX_DATA_PACKAGE}:*"


def parse_key(key: str) -> dict:
    """
    Parse a cache key into its components.

    Args:
        key: Cache key string

    Returns:
        Dict with parsed components:
            - category: Main category (e.g., "research", "market")
            - subcategory: Subcategory (e.g., "report", "metrics")
            - identifier: Optional identifier (e.g., report_id, date)

    Examples:
        >>> parse_key("research:report:abc123")
        {'category': 'research', 'subcategory': 'report', 'identifier': 'abc123'}

        >>> parse_key("market:metrics:latest")
        {'category': 'market', 'subcategory': 'metrics', 'identifier': 'latest'}

        >>> parse_key("pitches:latest")
        {'category': 'pitches', 'subcategory': 'latest', 'identifier': None}
    """
    parts = key.split(":")

    if len(parts) < 2:
        logger.warning(f"Invalid cache key format: {key}")
        return {
            "category": None,
            "subcategory": None,
            "identifier": None,
        }

    result = {
        "category": parts[0],
        "subcategory": parts[1] if len(parts) > 1 else None,
        "identifier": parts[2] if len(parts) > 2 else None,
    }

    # Handle keys with more than 3 parts (e.g., "market:prices:symbol:SPY:latest")
    if len(parts) > 3:
        result["identifier"] = ":".join(parts[2:])

    return result


def validate_key(key: str) -> bool:
    """
    Validate that a cache key follows the naming convention.

    Args:
        key: Cache key string

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_key("research:report:abc123")
        True

        >>> validate_key("invalid_key")
        False

        >>> validate_key("research:")
        False
    """
    if not key or not isinstance(key, str):
        return False

    parts = key.split(":")

    # Must have at least 2 parts (category:subcategory)
    if len(parts) < 2:
        return False

    # Category must be valid
    valid_categories = {
        PREFIX_RESEARCH,
        PREFIX_MARKET,
        PREFIX_PITCHES,
        PREFIX_GRAPHS,
        PREFIX_DATA_PACKAGE,
    }

    if parts[0] not in valid_categories:
        return False

    # All parts must be non-empty
    if any(not part for part in parts):
        return False

    return True
