"""Test helper utilities for LLM Trading tests.

This module provides:
- Async test helpers
- Mock API response generators
- Assertion helpers
- Common test patterns
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
import json


# ==================== Async Test Helpers ====================

def async_return(value: Any):
    """Create an async function that returns a value.

    Args:
        value: Value to return

    Returns:
        Async function that returns the value

    Example:
        mock_func = Mock(side_effect=async_return({"result": "success"}))
    """
    async def _async_return():
        return value
    return _async_return()


def async_raise(exception: Exception):
    """Create an async function that raises an exception.

    Args:
        exception: Exception to raise

    Returns:
        Async function that raises the exception

    Example:
        mock_func = Mock(side_effect=async_raise(ValueError("Test error")))
    """
    async def _async_raise():
        raise exception
    return _async_raise()


async def run_async_test(coro):
    """Run an async test coroutine.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine

    Note:
        This is typically not needed with pytest-asyncio,
        but can be useful for manual async testing.
    """
    return await coro


# ==================== Mock API Helpers ====================

class MockOpenRouterResponse:
    """Mock OpenRouter API response."""

    def __init__(
        self,
        content: str,
        model: str = "openai/gpt-4-turbo",
        reasoning: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.content = content
        self.model = model
        self.reasoning = reasoning
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format matching OpenRouter API."""
        response = {
            "model": self.model,
            "content": self.content,
        }
        if self.reasoning:
            response["reasoning_details"] = self.reasoning
        if self.error:
            response["error"] = self.error
        return response


class MockAlpacaClient:
    """Mock Alpaca API client for testing."""

    def __init__(
        self,
        account_info: Optional[Dict[str, Any]] = None,
        positions: Optional[List[Dict[str, Any]]] = None,
        orders: Optional[List[Dict[str, Any]]] = None
    ):
        self.account_info = account_info or self._default_account_info()
        self.positions = positions or []
        self.orders = orders or []
        self.placed_orders = []  # Track orders placed during test

    def _default_account_info(self) -> Dict[str, Any]:
        """Get default account info."""
        return {
            "account_number": "TEST123456",
            "status": "ACTIVE",
            "currency": "USD",
            "cash": "100000.00",
            "portfolio_value": "100000.00",
            "equity": "100000.00",
        }

    async def get_account(self) -> Dict[str, Any]:
        """Mock get_account method."""
        return self.account_info

    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock get_positions method."""
        if symbol:
            return [p for p in self.positions if p["symbol"] == symbol]
        return self.positions

    async def get_orders(self, **filters) -> List[Dict[str, Any]]:
        """Mock get_orders method."""
        # Simple filter implementation for testing
        filtered = self.orders
        if "status" in filters:
            filtered = [o for o in filtered if o["status"] == filters["status"]]
        if "symbol" in filters:
            filtered = [o for o in filtered if o["symbol"] == filters["symbol"]]
        return filtered

    async def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        **kwargs
    ) -> Dict[str, Any]:
        """Mock place_order method."""
        order = {
            "id": f"test-order-{len(self.placed_orders) + 1}",
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "status": "accepted",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        self.placed_orders.append(order)
        return order


class MockMarketSnapshot:
    """Mock market data snapshot for testing."""

    def __init__(
        self,
        prices: Optional[Dict[str, float]] = None,
        indicators: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        self.prices = prices or self._default_prices()
        self.indicators = indicators or {}
        self.timestamp = datetime.now(timezone.utc)

    def _default_prices(self) -> Dict[str, float]:
        """Get default price data."""
        return {
            "SPY": 450.25,
            "QQQ": 380.50,
            "IWM": 195.75,
            "TLT": 95.30,
            "GLD": 180.40,
            "UUP": 28.15,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "prices": self.prices,
            "indicators": self.indicators,
        }


# ==================== Assertion Helpers ====================

def assert_valid_pitch(pitch: Dict[str, Any]) -> None:
    """Assert that a pitch has all required fields.

    Args:
        pitch: Pitch dictionary to validate

    Raises:
        AssertionError: If pitch is invalid
    """
    required_fields = [
        "idea_id",
        "week_id",
        "model",
        "instrument",
        "direction",
        "horizon",
        "thesis_bullets",
        "conviction",
        "timestamp",
    ]

    for field in required_fields:
        assert field in pitch, f"Missing required field: {field}"

    # Validate types
    assert isinstance(pitch["thesis_bullets"], list), "thesis_bullets must be a list"
    assert isinstance(pitch["conviction"], (int, float)), "conviction must be numeric"
    assert pitch["direction"] in ["LONG", "SHORT", "FLAT"], "Invalid direction"


def assert_conviction_in_range(conviction: float, min_val: float = -2.0, max_val: float = 2.0) -> None:
    """Assert that conviction is within valid range.

    Args:
        conviction: Conviction value to check
        min_val: Minimum valid conviction
        max_val: Maximum valid conviction

    Raises:
        AssertionError: If conviction is out of range
    """
    assert min_val <= conviction <= max_val, \
        f"Conviction {conviction} outside valid range [{min_val}, {max_val}]"


def assert_valid_instrument(instrument: str, valid_instruments: List[str]) -> None:
    """Assert that instrument is in valid list.

    Args:
        instrument: Instrument to check
        valid_instruments: List of valid instruments

    Raises:
        AssertionError: If instrument is invalid
    """
    assert instrument in valid_instruments or instrument == "NONE", \
        f"Invalid instrument: {instrument}"


def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """Assert that actual dict contains all keys/values from expected dict.

    Args:
        actual: Actual dictionary
        expected: Expected key-value pairs (subset)

    Raises:
        AssertionError: If expected keys/values not found in actual
    """
    for key, value in expected.items():
        assert key in actual, f"Missing key: {key}"
        assert actual[key] == value, f"Value mismatch for {key}: {actual[key]} != {value}"


def assert_timestamp_recent(timestamp_str: str, max_age_seconds: int = 300) -> None:
    """Assert that timestamp is recent (within max_age_seconds).

    Args:
        timestamp_str: ISO format timestamp string
        max_age_seconds: Maximum age in seconds

    Raises:
        AssertionError: If timestamp is too old
    """
    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age = (now - timestamp).total_seconds()
    assert age < max_age_seconds, f"Timestamp too old: {age}s > {max_age_seconds}s"


# ==================== Data Generation Helpers ====================

def generate_week_id(weeks_ago: int = 0) -> str:
    """Generate week ID (Monday date) for testing.

    Args:
        weeks_ago: Number of weeks in the past (0 = current week)

    Returns:
        Week ID in YYYY-MM-DD format
    """
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday(), weeks=weeks_ago)
    return monday.strftime("%Y-%m-%d")


def generate_timestamp(hours_ago: int = 0) -> str:
    """Generate ISO timestamp for testing.

    Args:
        hours_ago: Number of hours in the past

    Returns:
        ISO format timestamp string
    """
    timestamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return timestamp.isoformat()


def generate_uuid() -> str:
    """Generate a test UUID.

    Returns:
        UUID string
    """
    import uuid
    return str(uuid.uuid4())


# ==================== Mock Factory Helpers ====================

def create_mock_query_model(responses: Dict[str, Any]) -> Mock:
    """Create a mock query_model function.

    Args:
        responses: Dict mapping model names to response content

    Returns:
        Mock function that returns appropriate response based on model

    Example:
        mock = create_mock_query_model({
            "openai/gpt-4": {"content": "Response A"},
            "anthropic/claude": {"content": "Response B"},
        })
    """
    async def _mock_query(model: str, messages: List[Dict], **kwargs):
        return responses.get(model, {"content": "Default response"})

    return Mock(side_effect=_mock_query)


def create_mock_query_models_parallel(responses: Dict[str, Any]) -> Mock:
    """Create a mock query_models_parallel function.

    Args:
        responses: Dict mapping model names to response content

    Returns:
        Mock function that returns all responses in parallel

    Example:
        mock = create_mock_query_models_parallel({
            "openai/gpt-4": {"content": "Response A"},
            "anthropic/claude": {"content": "Response B"},
        })
    """
    async def _mock_query_parallel(models: List[str], messages: List[Dict], **kwargs):
        return {model: responses.get(model) for model in models}

    return Mock(side_effect=_mock_query_parallel)


# ==================== Test Data Comparison ====================

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for comparison.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    return " ".join(text.split())


def json_equal(obj1: Any, obj2: Any, ignore_keys: Optional[List[str]] = None) -> bool:
    """Compare two objects as JSON, optionally ignoring certain keys.

    Args:
        obj1: First object
        obj2: Second object
        ignore_keys: Keys to ignore in comparison

    Returns:
        True if objects are equal (ignoring specified keys)
    """
    def remove_keys(obj, keys):
        if isinstance(obj, dict):
            return {k: remove_keys(v, keys) for k, v in obj.items() if k not in (keys or [])}
        elif isinstance(obj, list):
            return [remove_keys(item, keys) for item in obj]
        return obj

    obj1_clean = remove_keys(obj1, ignore_keys)
    obj2_clean = remove_keys(obj2, ignore_keys)

    return json.dumps(obj1_clean, sort_keys=True) == json.dumps(obj2_clean, sort_keys=True)


# ==================== Test Timing Helpers ====================

async def wait_for_condition(
    condition: Callable[[], bool],
    timeout_seconds: float = 5.0,
    check_interval: float = 0.1
) -> bool:
    """Wait for a condition to become true.

    Args:
        condition: Callable that returns bool
        timeout_seconds: Maximum time to wait
        check_interval: How often to check condition

    Returns:
        True if condition became true, False if timeout

    Example:
        success = await wait_for_condition(
            lambda: mock_client.placed_orders > 0,
            timeout_seconds=2.0
        )
    """
    elapsed = 0.0
    while elapsed < timeout_seconds:
        if condition():
            return True
        await asyncio.sleep(check_interval)
        elapsed += check_interval
    return False
