"""Unit tests for HTTP client pool (backend/http_pool.py).

This module tests:
- HttpClientConfig initialization with various configurations
- Configuration loading from environment variables
- Client initialization and lifecycle
- Health checks and error handling
- Connection reuse and pooling
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import the http_pool module
from backend import http_pool


@pytest.fixture(autouse=True)
async def cleanup_pool():
    """Cleanup HTTP clients after each test to ensure test isolation."""
    yield
    # Clean up after test
    if http_pool._alpaca_client is not None or http_pool._openrouter_client is not None:
        await http_pool.close_http_clients()
    # Reset global state
    http_pool._alpaca_client = None
    http_pool._openrouter_client = None
    http_pool._config = None


@pytest.fixture
def mock_http_env(monkeypatch):
    """Provide mock HTTP client environment variables."""
    monkeypatch.setenv("HTTP_MAX_CONNECTIONS", "50")
    monkeypatch.setenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "10")
    monkeypatch.setenv("HTTP_KEEPALIVE_EXPIRY", "3.0")
    monkeypatch.setenv("HTTP_CONNECT_TIMEOUT", "5.0")
    monkeypatch.setenv("HTTP_READ_TIMEOUT", "15.0")
    monkeypatch.setenv("HTTP_WRITE_TIMEOUT", "15.0")
    monkeypatch.setenv("HTTP_POOL_TIMEOUT", "5.0")
    monkeypatch.setenv("HTTP2_ENABLED", "true")
    monkeypatch.setenv("HTTP_MAX_RETRIES", "2")


@pytest.fixture
def mock_http_env_defaults(monkeypatch):
    """Clear HTTP environment variables to test defaults."""
    for var in [
        "HTTP_MAX_CONNECTIONS",
        "HTTP_MAX_KEEPALIVE_CONNECTIONS",
        "HTTP_KEEPALIVE_EXPIRY",
        "HTTP_CONNECT_TIMEOUT",
        "HTTP_READ_TIMEOUT",
        "HTTP_WRITE_TIMEOUT",
        "HTTP_POOL_TIMEOUT",
        "HTTP2_ENABLED",
        "HTTP_MAX_RETRIES",
    ]:
        monkeypatch.delenv(var, raising=False)


# ==================== HttpClientConfig Tests ====================


@pytest.mark.unit
def test_http_client_config(mock_http_env):
    """Test HttpClientConfig initialization from environment variables."""
    config = http_pool.HttpClientConfig()

    assert config.max_connections == 50
    assert config.max_keepalive_connections == 10
    assert config.keepalive_expiry == 3.0
    assert config.connect_timeout == 5.0
    assert config.read_timeout == 15.0
    assert config.write_timeout == 15.0
    assert config.pool_timeout == 5.0
    assert config.http2_enabled is True
    assert config.max_retries == 2


@pytest.mark.unit
def test_http_client_config_defaults(mock_http_env_defaults):
    """Test HttpClientConfig with default values."""
    config = http_pool.HttpClientConfig()

    assert config.max_connections == 100
    assert config.max_keepalive_connections == 20
    assert config.keepalive_expiry == 5.0
    assert config.connect_timeout == 10.0
    assert config.read_timeout == 30.0
    assert config.write_timeout == 30.0
    assert config.pool_timeout == 10.0
    assert config.http2_enabled is True
    assert config.max_retries == 3


@pytest.mark.unit
def test_http_client_config_get_limits(mock_http_env):
    """Test HttpClientConfig.get_limits() returns correct dict."""
    config = http_pool.HttpClientConfig()
    limits = config.get_limits()

    assert isinstance(limits, dict)
    assert limits["max_connections"] == 50
    assert limits["max_keepalive_connections"] == 10
    assert limits["keepalive_expiry"] == 3.0


@pytest.mark.unit
def test_http_client_config_get_timeout(mock_http_env):
    """Test HttpClientConfig.get_timeout() returns correct dict."""
    config = http_pool.HttpClientConfig()
    timeout = config.get_timeout()

    assert isinstance(timeout, dict)
    assert timeout["connect"] == 5.0
    assert timeout["read"] == 15.0
    assert timeout["write"] == 15.0
    assert timeout["pool"] == 5.0


@pytest.mark.unit
def test_http_client_config_http2_disabled(monkeypatch):
    """Test HttpClientConfig with HTTP/2 disabled."""
    monkeypatch.setenv("HTTP2_ENABLED", "false")
    config = http_pool.HttpClientConfig()

    assert config.http2_enabled is False


@pytest.mark.unit
def test_http_client_config_http2_case_insensitive(monkeypatch):
    """Test HttpClientConfig HTTP/2 setting is case-insensitive."""
    monkeypatch.setenv("HTTP2_ENABLED", "TRUE")
    config = http_pool.HttpClientConfig()
    assert config.http2_enabled is True

    monkeypatch.setenv("HTTP2_ENABLED", "False")
    config2 = http_pool.HttpClientConfig()
    assert config2.http2_enabled is False


@pytest.mark.unit
def test_http_client_config_repr(mock_http_env):
    """Test HttpClientConfig string representation."""
    config = http_pool.HttpClientConfig()
    repr_str = repr(config)

    assert "HttpClientConfig" in repr_str
    assert "max_connections=50" in repr_str
    assert "max_keepalive=10" in repr_str
    assert "connect_timeout=5.0s" in repr_str
    assert "read_timeout=15.0s" in repr_str
    assert "http2=True" in repr_str


# ==================== HTTP Client Initialization Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_http_clients_success(mock_http_env):
    """Test successful HTTP clients initialization."""
    # Mock httpx.AsyncClient
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        # Return different mock instances for each call
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        alpaca, openrouter = await http_pool.init_http_clients()

        # Verify clients were created
        assert alpaca is not None
        assert openrouter is not None
        assert http_pool._alpaca_client is not None
        assert http_pool._openrouter_client is not None
        assert http_pool._config is not None

        # Verify AsyncClient was called twice (once for each client)
        assert mock_async_client.call_count == 2

        # Verify correct parameters
        call_kwargs = mock_async_client.call_args_list[0].kwargs
        assert "limits" in call_kwargs
        assert "timeout" in call_kwargs
        assert call_kwargs["http2"] is True
        assert call_kwargs["follow_redirects"] is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_http_clients_idempotent(mock_http_env):
    """Test that init_http_clients is idempotent (safe to call multiple times)."""
    # Mock httpx.AsyncClient
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        # First call - should initialize
        alpaca1, openrouter1 = await http_pool.init_http_clients()
        first_call_count = mock_async_client.call_count

        # Second call - should return existing clients
        alpaca2, openrouter2 = await http_pool.init_http_clients()

        # Should return the same clients
        assert alpaca1 is alpaca2
        assert openrouter1 is openrouter2

        # Should not create new clients
        assert mock_async_client.call_count == first_call_count


@pytest.mark.asyncio
@pytest.mark.unit
async def test_init_http_clients_error_handling(mock_http_env):
    """Test error handling during HTTP clients initialization."""
    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        # Simulate initialization failure
        mock_async_client.side_effect = Exception("Connection failed")

        # Should raise exception
        with pytest.raises(Exception, match="Connection failed"):
            await http_pool.init_http_clients()

        # Global state should be reset
        assert http_pool._alpaca_client is None
        assert http_pool._openrouter_client is None
        assert http_pool._config is None


# ==================== HTTP Client Getter Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_alpaca_client_not_initialized():
    """Test get_alpaca_client raises error when clients not initialized."""
    # Ensure clients are not initialized
    http_pool._alpaca_client = None

    with pytest.raises(RuntimeError, match="HTTP clients not initialized"):
        http_pool.get_alpaca_client()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_openrouter_client_not_initialized():
    """Test get_openrouter_client raises error when clients not initialized."""
    # Ensure clients are not initialized
    http_pool._openrouter_client = None

    with pytest.raises(RuntimeError, match="HTTP clients not initialized"):
        http_pool.get_openrouter_client()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_alpaca_client_success(mock_http_env):
    """Test get_alpaca_client returns client after initialization."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        await http_pool.init_http_clients()

        # Should return the Alpaca client
        client = http_pool.get_alpaca_client()
        assert client is mock_alpaca_client


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_openrouter_client_success(mock_http_env):
    """Test get_openrouter_client returns client after initialization."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        await http_pool.init_http_clients()

        # Should return the OpenRouter client
        client = http_pool.get_openrouter_client()
        assert client is mock_openrouter_client


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_clients(mock_http_env):
    """Test get_alpaca_client() and get_openrouter_client() return correct clients."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        # Initialize clients
        await http_pool.init_http_clients()

        # Should return both clients correctly
        alpaca = http_pool.get_alpaca_client()
        openrouter = http_pool.get_openrouter_client()

        assert alpaca is mock_alpaca_client
        assert openrouter is mock_openrouter_client

        # Verify they are different instances
        assert alpaca is not openrouter


# ==================== HTTP Client Lifecycle Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_http_clients(mock_http_env):
    """Test closing HTTP clients."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_alpaca_client.aclose = AsyncMock()
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False
    mock_openrouter_client.aclose = AsyncMock()

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        # Initialize clients
        await http_pool.init_http_clients()

        # Close clients
        await http_pool.close_http_clients()

        # Verify aclose was called on both clients
        mock_alpaca_client.aclose.assert_called_once()
        mock_openrouter_client.aclose.assert_called_once()

        # Verify global state is reset
        assert http_pool._alpaca_client is None
        assert http_pool._openrouter_client is None
        assert http_pool._config is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_http_clients_idempotent():
    """Test that close_http_clients is idempotent (safe to call multiple times)."""
    # Close when clients are not initialized (should be no-op)
    await http_pool.close_http_clients()

    # Should not raise any errors
    assert http_pool._alpaca_client is None
    assert http_pool._openrouter_client is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_close_http_clients_error_handling(mock_http_env):
    """Test error handling during HTTP clients closure."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_alpaca_client.aclose = AsyncMock(side_effect=Exception("Close failed"))
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False
    mock_openrouter_client.aclose = AsyncMock()

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        # Initialize clients
        await http_pool.init_http_clients()

        # Close clients (should handle error gracefully)
        await http_pool.close_http_clients()

        # Global state should still be reset even if close failed
        assert http_pool._alpaca_client is None
        assert http_pool._openrouter_client is None
        assert http_pool._config is None


# ==================== HTTP Client Health Check Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_http_clients_health_not_initialized():
    """Test health check when clients are not initialized."""
    # Ensure clients are not initialized
    http_pool._alpaca_client = None
    http_pool._openrouter_client = None

    health = await http_pool.check_http_clients_health()

    assert health["status"] == "unavailable"
    assert "error" in health
    assert "not initialized" in health["error"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_http_clients_health_healthy(mock_http_env):
    """Test health check when clients are healthy."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        await http_pool.init_http_clients()

        health = await http_pool.check_http_clients_health()

        assert health["status"] == "healthy"
        assert health["alpaca_client"]["status"] == "open"
        assert health["openrouter_client"]["status"] == "open"
        assert health["alpaca_client"]["http2"] is True
        assert health["alpaca_client"]["max_connections"] == 50


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_http_clients_health_degraded(mock_http_env):
    """Test health check when one client is closed (degraded state)."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = True  # Closed
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False  # Open

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        await http_pool.init_http_clients()

        health = await http_pool.check_http_clients_health()

        assert health["status"] == "degraded"
        assert health["alpaca_client"]["status"] == "closed"
        assert health["openrouter_client"]["status"] == "open"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_check_http_clients_health_closed(mock_http_env):
    """Test health check when both clients are closed."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = True
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = True

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        await http_pool.init_http_clients()

        health = await http_pool.check_http_clients_health()

        assert health["status"] == "unavailable"
        assert health["alpaca_client"]["status"] == "closed"
        assert health["openrouter_client"]["status"] == "closed"


# ==================== HTTP Client Configuration Getter Tests ====================


@pytest.mark.unit
def test_get_config_not_initialized():
    """Test get_config returns None when clients not initialized."""
    http_pool._config = None

    config = http_pool.get_config()

    assert config is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_config_success(mock_http_env):
    """Test get_config returns config after initialization."""
    mock_alpaca_client = AsyncMock()
    mock_alpaca_client.is_closed = False
    mock_openrouter_client = AsyncMock()
    mock_openrouter_client.is_closed = False

    with patch("backend.http_pool.httpx.AsyncClient") as mock_async_client:
        mock_async_client.side_effect = [mock_alpaca_client, mock_openrouter_client]

        await http_pool.init_http_clients()

        config = http_pool.get_config()

        assert config is not None
        assert isinstance(config, http_pool.HttpClientConfig)
        assert config.max_connections == 50
        assert config.http2_enabled is True
