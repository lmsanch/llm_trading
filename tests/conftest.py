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

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session.

    This fixture ensures all async tests in a session share the same event loop,
    which is required for pytest-asyncio to work correctly.
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
