"""Pytest configuration and shared fixtures for LLM Trading tests.

This module provides:
- Basic pytest configuration
- Common fixtures for testing (mock API clients, test data, etc.)
- Setup/teardown for test isolation
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

import pytest

# Add project root to Python path to allow imports from backend, council, etc.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== Pytest Configuration ====================

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (automatically handled by pytest-asyncio)"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (slower, multiple components)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (may take several seconds)"
    )


# ==================== Async Test Support ====================

@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for each test function.

    This fixture creates a new event loop for each async test,
    which is required for pytest-asyncio 0.21+ to work correctly.
    Using function scope prevents "Event loop is closed" errors.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Environment Fixtures ====================

@pytest.fixture(scope="function", autouse=True)
def isolate_environment(monkeypatch):
    """Isolate each test by preventing environment variable pollution.

    This fixture automatically applies to all tests and ensures that
    environment variables don't leak between tests.
    """
    # Store original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment after test
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_env_vars(monkeypatch) -> Dict[str, str]:
    """Provide mock environment variables for testing.

    Returns:
        Dict of environment variables that can be modified per test
    """
    env_vars = {
        "OPENROUTER_API_KEY": "test-openrouter-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "PERPLEXITY_API_KEY": "test-perplexity-key",
        "APCA_API_KEY_ID": "test-alpaca-key",
        "APCA_API_SECRET_KEY": "test-alpaca-secret",
        "DATABASE_PATH": ":memory:",  # Use in-memory SQLite for tests
        "LOG_LEVEL": "ERROR",  # Suppress logs during tests
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# ==================== Mock Data Fixtures ====================

@pytest.fixture
def sample_model_names() -> list[str]:
    """Provide sample model names for testing council logic."""
    return [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4-turbo",
        "google/gemini-pro",
        "meta-llama/llama-3-70b",
    ]


@pytest.fixture
def sample_instruments() -> list[str]:
    """Provide sample tradable instruments."""
    return ["SPY", "QQQ", "IWM", "TLT", "GLD", "UUP"]


# ==================== Test Data Directory ====================

@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Create a temporary data directory for test isolation.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path to temporary data directory
    """
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def temp_storage_dir(tmp_path) -> Path:
    """Create a temporary storage directory for conversation tests.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path to temporary storage directory
    """
    storage_dir = tmp_path / "conversations"
    storage_dir.mkdir(exist_ok=True)
    return storage_dir


# ==================== Async Mock Fixtures ====================

@pytest.fixture
def mock_query_model():
    """Provide a mock query_model function for testing.

    Returns:
        Mock function that can be configured per test

    Example:
        mock_query_model.side_effect = async_return({"content": "Test response"})
    """
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def mock_query_models_parallel():
    """Provide a mock query_models_parallel function for testing.

    Returns:
        Mock function that can be configured per test

    Example:
        mock_query_models_parallel.return_value = {
            "model1": {"content": "Response 1"},
            "model2": {"content": "Response 2"},
        }
    """
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def mock_alpaca_client():
    """Provide a mock Alpaca client for testing.

    Returns:
        Mock AlpacaAccountClient instance

    Example:
        mock_alpaca_client.get_account.return_value = {"cash": "100000.00"}
    """
    from tests.fixtures.test_helpers import MockAlpacaClient
    return MockAlpacaClient()


# ==================== PM Pitch Fixtures ====================

@pytest.fixture
def valid_long_pitch():
    """Provide a valid LONG pitch for testing.

    Returns:
        Valid PM pitch dictionary
    """
    from tests.fixtures.sample_pitches import get_valid_long_pitch
    return get_valid_long_pitch()


@pytest.fixture
def valid_short_pitch():
    """Provide a valid SHORT pitch for testing.

    Returns:
        Valid PM pitch dictionary
    """
    from tests.fixtures.sample_pitches import get_valid_short_pitch
    return get_valid_short_pitch()


@pytest.fixture
def valid_flat_pitch():
    """Provide a valid FLAT pitch for testing.

    Returns:
        Valid FLAT pitch dictionary
    """
    from tests.fixtures.sample_pitches import get_valid_flat_pitch
    return get_valid_flat_pitch()


@pytest.fixture
def all_pm_pitches():
    """Provide pitches from all 5 PM models for testing.

    Returns:
        List of 5 PM pitches
    """
    from tests.fixtures.sample_pitches import get_all_pm_pitches
    return get_all_pm_pitches()


@pytest.fixture
def conflicting_pitches():
    """Provide conflicting pitches for chairman decision testing.

    Returns:
        List of conflicting pitches
    """
    from tests.fixtures.sample_pitches import get_conflicting_pitches
    return get_conflicting_pitches()


# ==================== Council Response Fixtures ====================

@pytest.fixture
def mock_stage1_responses():
    """Provide mock Stage 1 council responses.

    Returns:
        List of mock Stage 1 responses
    """
    from tests.fixtures.mock_council_responses import get_mock_stage1_responses
    return get_mock_stage1_responses()


@pytest.fixture
def mock_stage2_rankings():
    """Provide mock Stage 2 ranking responses.

    Returns:
        List of mock ranking responses
    """
    from tests.fixtures.mock_council_responses import get_mock_stage2_responses
    return get_mock_stage2_responses()


@pytest.fixture
def mock_chairman_response():
    """Provide mock chairman synthesis response.

    Returns:
        Mock chairman response text
    """
    from tests.fixtures.mock_council_responses import get_mock_chairman_response
    return get_mock_chairman_response()


@pytest.fixture
def label_to_model_mapping():
    """Provide label_to_model mapping for testing.

    Returns:
        Dict mapping response labels to model names
    """
    from tests.fixtures.mock_council_responses import get_label_to_model_mapping
    return get_label_to_model_mapping()


# ==================== Market Data Fixtures ====================

@pytest.fixture
def market_snapshot():
    """Provide a mock market data snapshot.

    Returns:
        MockMarketSnapshot instance
    """
    from tests.fixtures.test_helpers import MockMarketSnapshot
    return MockMarketSnapshot()


@pytest.fixture
def sample_prices() -> Dict[str, float]:
    """Provide sample market prices for testing.

    Returns:
        Dict of instrument -> price
    """
    return {
        "SPY": 450.25,
        "QQQ": 380.50,
        "IWM": 195.75,
        "TLT": 95.30,
        "GLD": 180.40,
        "UUP": 28.15,
    }


# ==================== Test Helper Fixtures ====================

@pytest.fixture
def async_return():
    """Provide async_return helper for creating async mock returns.

    Returns:
        async_return function from test_helpers
    """
    from tests.fixtures.test_helpers import async_return
    return async_return


@pytest.fixture
def async_raise():
    """Provide async_raise helper for creating async mock exceptions.

    Returns:
        async_raise function from test_helpers
    """
    from tests.fixtures.test_helpers import async_raise
    return async_raise


# ==================== Database Pool Fixtures ====================

@pytest.fixture(scope="function")
async def db_pool():
    """Initialize database connection pool for testing.

    This fixture initializes the database pool before each test and closes
    it after the test completes. Ensures proper cleanup of connections.

    Yields:
        None (pool is accessible via get_pool() after initialization)
    """
    from backend.db.pool import init_pool, close_pool

    # Initialize the pool
    await init_pool()

    yield

    # Close the pool after test
    await close_pool()
