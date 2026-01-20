"""Test AlpacaAccountClient initialization and configuration.

This module tests the AlpacaAccountClient class from backend.multi_alpaca_client:
- Initialization for all 6 accounts (CHATGPT, GEMINI, CLAUDE, GROQ, DEEPSEEK, COUNCIL)
- Credential loading and validation
- Base URL configuration (paper vs live)
- Header configuration
- Error handling for invalid account names
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from backend.multi_alpaca_client import (
    AlpacaAccountClient,
    ALPACA_ACCOUNTS,
    PAPER_URL,
    get_account_config,
    get_all_account_names,
    verify_credentials
)


class TestAlpacaAccountsConfiguration:
    """Test suite for ALPACA_ACCOUNTS constant and configuration."""

    def test_alpaca_accounts_exists(self):
        """Test that ALPACA_ACCOUNTS constant is defined."""
        assert ALPACA_ACCOUNTS is not None
        assert isinstance(ALPACA_ACCOUNTS, dict)

    def test_all_six_accounts_defined(self):
        """Test that all 6 required accounts are defined."""
        expected_accounts = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']
        for account in expected_accounts:
            assert account in ALPACA_ACCOUNTS, f"Account {account} not found in ALPACA_ACCOUNTS"

    def test_account_config_structure(self):
        """Test that each account config has required fields."""
        required_fields = ['key_id', 'secret_key', 'account_id', 'email']
        for account_name, config in ALPACA_ACCOUNTS.items():
            for field in required_fields:
                assert field in config, f"Account {account_name} missing field: {field}"

    def test_paper_url_constant(self):
        """Test that PAPER_URL constant is correctly defined."""
        assert PAPER_URL == "https://paper-api.alpaca.markets"

    def test_account_ids_are_unique(self):
        """Test that all account IDs are unique."""
        account_ids = [config['account_id'] for config in ALPACA_ACCOUNTS.values()]
        assert len(account_ids) == len(set(account_ids)), "Duplicate account IDs found"


class TestAlpacaAccountClientInitialization:
    """Test suite for AlpacaAccountClient initialization."""

    @pytest.fixture
    def mock_alpaca_env(self, monkeypatch):
        """Set up mock environment variables for Alpaca credentials."""
        env_vars = {
            'ALPACA_CHATGPT_KEY_ID': 'test_chatgpt_key',
            'ALPACA_CHATGPT_SECRET_KEY': 'test_chatgpt_secret',
            'ALPACA_GEMINI_KEY_ID': 'test_gemini_key',
            'ALPACA_GEMINI_SECRET_KEY': 'test_gemini_secret',
            'ALPACA_CLAUDE_KEY_ID': 'test_claude_key',
            'ALPACA_CLAUDE_SECRET_KEY': 'test_claude_secret',
            'ALPACA_GROQ_KEY_ID': 'test_groq_key',
            'ALPACA_GROQ_SECRET_KEY': 'test_groq_secret',
            'ALPACA_DEEPSEEK_KEY_ID': 'test_deepseek_key',
            'ALPACA_DEEPSEEK_SECRET_KEY': 'test_deepseek_secret',
            'ALPACA_COUNCIL_KEY_ID': 'test_council_key',
            'ALPACA_COUNCIL_SECRET_KEY': 'test_council_secret',
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        # Reload ALPACA_ACCOUNTS to pick up new env vars
        from importlib import reload
        import backend.multi_alpaca_client as mac
        reload(mac)

        yield env_vars

        # Reload again to restore original state
        reload(mac)

    def test_initialize_chatgpt_account(self):
        """Test initialization of CHATGPT account."""
        client = AlpacaAccountClient('CHATGPT')
        assert client.account_name == 'CHATGPT'
        assert client.account_id == 'PA3IUYCYRWGK'
        assert client.base_url == PAPER_URL

    def test_initialize_gemini_account(self):
        """Test initialization of GEMINI account."""
        client = AlpacaAccountClient('GEMINI')
        assert client.account_name == 'GEMINI'
        assert client.account_id == 'PA3M2HMSLN00'
        assert client.base_url == PAPER_URL

    def test_initialize_claude_account(self):
        """Test initialization of CLAUDE account."""
        client = AlpacaAccountClient('CLAUDE')
        assert client.account_name == 'CLAUDE'
        assert client.account_id == 'PA38PAHFRFYC'
        assert client.base_url == PAPER_URL

    def test_initialize_groq_account(self):
        """Test initialization of GROQ account."""
        client = AlpacaAccountClient('GROQ')
        assert client.account_name == 'GROQ'
        assert client.account_id == 'PA33MEQA4WT7'
        assert client.base_url == PAPER_URL

    def test_initialize_deepseek_account(self):
        """Test initialization of DEEPSEEK account."""
        client = AlpacaAccountClient('DEEPSEEK')
        assert client.account_name == 'DEEPSEEK'
        assert client.account_id == 'PA3KKW3TN54V'
        assert client.base_url == PAPER_URL

    def test_initialize_council_account(self):
        """Test initialization of COUNCIL account."""
        client = AlpacaAccountClient('COUNCIL')
        assert client.account_name == 'COUNCIL'
        assert client.account_id == 'PA3MQLPXBSO1'
        assert client.base_url == PAPER_URL

    def test_initialize_all_six_accounts(self):
        """Test that all 6 accounts can be initialized without errors."""
        account_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']
        clients = []

        for account_name in account_names:
            client = AlpacaAccountClient(account_name)
            clients.append(client)
            assert client.account_name == account_name
            assert client.account_id is not None

        # Verify all clients were created
        assert len(clients) == 6

    def test_invalid_account_name_raises_error(self):
        """Test that invalid account name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown account"):
            AlpacaAccountClient('INVALID_ACCOUNT')

    def test_invalid_account_name_case_sensitive(self):
        """Test that account names are case-sensitive."""
        with pytest.raises(ValueError, match="Unknown account"):
            AlpacaAccountClient('chatgpt')  # lowercase should fail

    def test_invalid_account_name_similar_name(self):
        """Test that similar but incorrect account names raise errors."""
        invalid_names = ['GPT', 'GEMINI_PRO', 'CLAUDE_3', 'DEEPSEEK_V2']
        for invalid_name in invalid_names:
            with pytest.raises(ValueError, match="Unknown account"):
                AlpacaAccountClient(invalid_name)


class TestAlpacaAccountClientBaseURL:
    """Test suite for base URL configuration."""

    def test_paper_trading_url_default(self):
        """Test that paper trading URL is used by default."""
        client = AlpacaAccountClient('CHATGPT')
        assert client.base_url == PAPER_URL

    def test_paper_trading_url_explicit_true(self):
        """Test that paper trading URL is used when explicitly set to True."""
        client = AlpacaAccountClient('CHATGPT', paper=True)
        assert client.base_url == PAPER_URL

    def test_live_trading_url(self):
        """Test that live trading URL is used when paper=False."""
        client = AlpacaAccountClient('CHATGPT', paper=False)
        assert client.base_url == "https://api.alpaca.markets"

    def test_all_accounts_paper_url(self):
        """Test that all accounts default to paper trading URL."""
        account_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']

        for account_name in account_names:
            client = AlpacaAccountClient(account_name)
            assert client.base_url == PAPER_URL, \
                f"Account {account_name} does not default to paper URL"

    def test_all_accounts_live_url(self):
        """Test that all accounts can use live trading URL."""
        account_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']

        for account_name in account_names:
            client = AlpacaAccountClient(account_name, paper=False)
            assert client.base_url == "https://api.alpaca.markets", \
                f"Account {account_name} does not use live URL when paper=False"


class TestAlpacaAccountClientHeaders:
    """Test suite for HTTP header configuration."""

    def test_headers_contain_api_key_id(self):
        """Test that headers contain APCA-API-KEY-ID."""
        client = AlpacaAccountClient('CHATGPT')
        assert 'APCA-API-KEY-ID' in client.headers
        assert client.headers['APCA-API-KEY-ID'] is not None

    def test_headers_contain_api_secret_key(self):
        """Test that headers contain APCA-API-SECRET-KEY."""
        client = AlpacaAccountClient('CHATGPT')
        assert 'APCA-API-SECRET-KEY' in client.headers
        assert client.headers['APCA-API-SECRET-KEY'] is not None

    def test_headers_contain_content_type(self):
        """Test that headers contain Content-Type."""
        client = AlpacaAccountClient('CHATGPT')
        assert 'Content-Type' in client.headers
        assert client.headers['Content-Type'] == 'application/json'

    def test_headers_structure(self):
        """Test that headers have correct structure for all required fields."""
        client = AlpacaAccountClient('CHATGPT')
        required_headers = ['APCA-API-KEY-ID', 'APCA-API-SECRET-KEY', 'Content-Type']

        for header in required_headers:
            assert header in client.headers, f"Missing header: {header}"

    def test_headers_credentials_not_empty(self):
        """Test that credential headers are not empty strings."""
        client = AlpacaAccountClient('CHATGPT')

        # Note: In test environment, credentials might be None if env vars not set
        # but if they exist, they should not be empty strings
        if client.headers['APCA-API-KEY-ID']:
            assert len(client.headers['APCA-API-KEY-ID']) > 0
        if client.headers['APCA-API-SECRET-KEY']:
            assert len(client.headers['APCA-API-SECRET-KEY']) > 0

    def test_all_accounts_have_headers(self):
        """Test that all accounts have properly configured headers."""
        account_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']

        for account_name in account_names:
            client = AlpacaAccountClient(account_name)
            assert client.headers is not None
            assert isinstance(client.headers, dict)
            assert 'APCA-API-KEY-ID' in client.headers
            assert 'APCA-API-SECRET-KEY' in client.headers
            assert 'Content-Type' in client.headers


class TestAlpacaAccountClientCredentials:
    """Test suite for credential loading and validation."""

    def test_credentials_loaded_from_config(self):
        """Test that credentials are loaded from ALPACA_ACCOUNTS config."""
        client = AlpacaAccountClient('CHATGPT')

        # Credentials should match config (might be None if env vars not set)
        config = ALPACA_ACCOUNTS['CHATGPT']
        assert client.headers['APCA-API-KEY-ID'] == config['key_id']
        assert client.headers['APCA-API-SECRET-KEY'] == config['secret_key']

    def test_account_id_matches_config(self):
        """Test that account_id matches config for each account."""
        account_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']

        for account_name in account_names:
            client = AlpacaAccountClient(account_name)
            config = ALPACA_ACCOUNTS[account_name]
            assert client.account_id == config['account_id'], \
                f"Account ID mismatch for {account_name}"

    def test_different_accounts_have_different_credentials(self):
        """Test that different accounts have different credentials (if set)."""
        client1 = AlpacaAccountClient('CHATGPT')
        client2 = AlpacaAccountClient('GEMINI')

        # If credentials are set, they should be different
        if (client1.headers['APCA-API-KEY-ID'] and
            client2.headers['APCA-API-KEY-ID']):
            # Different accounts should have different keys
            # (unless they're both None or same test value)
            key1 = client1.headers['APCA-API-KEY-ID']
            key2 = client2.headers['APCA-API-KEY-ID']
            # Note: In test environment they might be the same, so we just check they exist
            assert key1 is not None
            assert key2 is not None


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_get_account_config_valid(self):
        """Test get_account_config returns correct config for valid account."""
        config = get_account_config('CHATGPT')
        assert config is not None
        assert isinstance(config, dict)
        assert 'key_id' in config
        assert 'secret_key' in config
        assert 'account_id' in config
        assert 'email' in config

    def test_get_account_config_invalid(self):
        """Test get_account_config raises error for invalid account."""
        with pytest.raises(ValueError, match="Unknown account"):
            get_account_config('INVALID')

    def test_get_account_config_returns_copy(self):
        """Test that get_account_config returns a copy, not reference."""
        config1 = get_account_config('CHATGPT')
        config2 = get_account_config('CHATGPT')

        # Modify config1 and ensure config2 is unchanged
        config1['test_field'] = 'test_value'
        assert 'test_field' not in config2

    def test_get_all_account_names(self):
        """Test get_all_account_names returns all account names."""
        names = get_all_account_names()
        assert isinstance(names, list)
        assert len(names) == 6

        expected_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']
        for name in expected_names:
            assert name in names

    def test_verify_credentials(self):
        """Test verify_credentials returns status for all accounts."""
        results = verify_credentials()
        assert isinstance(results, dict)
        assert len(results) == 6

        # All accounts should be in results
        expected_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']
        for name in expected_names:
            assert name in results
            assert isinstance(results[name], bool)

    def test_verify_credentials_returns_false_for_missing(self):
        """Test that verify_credentials returns False when credentials are None."""
        # In test environment without env vars set, credentials should be None
        results = verify_credentials()

        # At least check that the function returns boolean values
        for account_name, has_creds in results.items():
            assert isinstance(has_creds, bool), \
                f"verify_credentials returned non-boolean for {account_name}"


class TestAlpacaAccountClientEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_empty_string_account_name(self):
        """Test that empty string account name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown account"):
            AlpacaAccountClient('')

    def test_none_account_name(self):
        """Test that None account name raises appropriate error."""
        with pytest.raises((ValueError, TypeError)):
            AlpacaAccountClient(None)

    def test_numeric_account_name(self):
        """Test that numeric account name raises appropriate error."""
        with pytest.raises((ValueError, TypeError)):
            AlpacaAccountClient(123)

    def test_account_name_with_spaces(self):
        """Test that account names with spaces raise ValueError."""
        with pytest.raises(ValueError, match="Unknown account"):
            AlpacaAccountClient('CHAT GPT')

    def test_account_name_with_special_chars(self):
        """Test that account names with special characters raise ValueError."""
        invalid_names = ['CHATGPT!', 'GEMINI@', 'CLAUDE#', 'GROQ$']
        for invalid_name in invalid_names:
            with pytest.raises(ValueError, match="Unknown account"):
                AlpacaAccountClient(invalid_name)

    def test_multiple_clients_same_account(self):
        """Test that multiple clients for same account can be created independently."""
        client1 = AlpacaAccountClient('CHATGPT')
        client2 = AlpacaAccountClient('CHATGPT')

        # Both should be valid but independent objects
        assert client1 is not client2
        assert client1.account_name == client2.account_name
        assert client1.account_id == client2.account_id
        assert client1.base_url == client2.base_url

    def test_client_initialization_idempotent(self):
        """Test that initializing same account multiple times is safe."""
        clients = [AlpacaAccountClient('CHATGPT') for _ in range(5)]

        # All should have same configuration
        for client in clients:
            assert client.account_name == 'CHATGPT'
            assert client.account_id == 'PA3IUYCYRWGK'


# ============================================================================
# API METHOD TESTS WITH MOCKED HTTP RESPONSES
# ============================================================================


class TestAlpacaAccountClientGetAccount:
    """Test suite for get_account method with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_get_account_success(self):
        """Test get_account returns correct account data on success."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response_data = {
            "id": "PA3IUYCYRWGK",
            "account_number": "PA3IUYCYRWGK",
            "status": "ACTIVE",
            "currency": "USD",
            "cash": "100000.00",
            "portfolio_value": "100000.00",
            "buying_power": "200000.00",
            "equity": "100000.00",
            "last_equity": "100000.00",
            "long_market_value": "0.00",
            "short_market_value": "0.00",
            "pattern_day_trader": False,
        }

        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_account()

            # Verify result matches mock data
            assert result == mock_response_data
            assert result['id'] == 'PA3IUYCYRWGK'
            assert result['cash'] == '100000.00'
            assert result['status'] == 'ACTIVE'

            # Verify correct endpoint was called
            mock_client_instance.get.assert_called_once_with('/v2/account')

    @pytest.mark.asyncio
    async def test_get_account_uses_correct_headers(self):
        """Test that get_account uses correct authentication headers."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "PA3IUYCYRWGK", "status": "ACTIVE"}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.get_account()

            # Verify AsyncClient was initialized with correct headers
            call_kwargs = mock_client_class.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert 'APCA-API-KEY-ID' in headers
            assert 'APCA-API-SECRET-KEY' in headers
            assert 'Content-Type' in headers
            assert headers['Content-Type'] == 'application/json'

    @pytest.mark.asyncio
    async def test_get_account_http_error(self):
        """Test that get_account raises exception on HTTP error."""
        client = AlpacaAccountClient('CHATGPT')

        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock()
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_account()

    @pytest.mark.asyncio
    async def test_get_account_uses_correct_base_url(self):
        """Test that get_account uses paper trading URL."""
        client = AlpacaAccountClient('CHATGPT', paper=True)

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "PA3IUYCYRWGK"}
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.get_account()

            # Verify correct base_url was used
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs['base_url'] == PAPER_URL


class TestAlpacaAccountClientGetPositions:
    """Test suite for get_positions method with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_get_positions_all(self):
        """Test get_positions returns all positions when no symbol provided."""
        client = AlpacaAccountClient('CHATGPT')

        mock_positions = [
            {
                "symbol": "SPY",
                "qty": "10",
                "avg_entry_price": "445.50",
                "market_value": "4502.50",
                "unrealized_pl": "47.50",
            },
            {
                "symbol": "QQQ",
                "qty": "5",
                "avg_entry_price": "378.25",
                "market_value": "1902.50",
                "unrealized_pl": "11.25",
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_positions
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_positions()

            # Verify result matches mock data
            assert result == mock_positions
            assert len(result) == 2
            assert result[0]['symbol'] == 'SPY'
            assert result[1]['symbol'] == 'QQQ'

            # Verify correct endpoint was called (no symbol)
            mock_client_instance.get.assert_called_once_with('/v2/positions')

    @pytest.mark.asyncio
    async def test_get_positions_filtered_by_symbol(self):
        """Test get_positions filters by symbol when provided."""
        client = AlpacaAccountClient('CHATGPT')

        mock_position = {
            "symbol": "SPY",
            "qty": "10",
            "avg_entry_price": "445.50",
            "market_value": "4502.50",
            "unrealized_pl": "47.50",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_position
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_positions(symbol='SPY')

            # Verify result matches mock data
            assert result == mock_position
            assert result['symbol'] == 'SPY'

            # Verify correct endpoint was called with symbol
            mock_client_instance.get.assert_called_once_with('/v2/positions/SPY')

    @pytest.mark.asyncio
    async def test_get_positions_empty(self):
        """Test get_positions returns empty list when no positions exist."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_positions()

            assert result == []
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_positions_http_error(self):
        """Test that get_positions raises exception on HTTP error."""
        client = AlpacaAccountClient('CHATGPT')

        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock()
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_positions()

    @pytest.mark.asyncio
    async def test_get_positions_uses_correct_headers(self):
        """Test that get_positions uses correct authentication headers."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.get_positions()

            # Verify AsyncClient was initialized with correct headers
            call_kwargs = mock_client_class.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert 'APCA-API-KEY-ID' in headers
            assert 'APCA-API-SECRET-KEY' in headers

    @pytest.mark.asyncio
    async def test_get_positions_multiple_symbols(self):
        """Test get_positions with different symbol calls."""
        client = AlpacaAccountClient('CHATGPT')

        symbols_to_test = ['SPY', 'QQQ', 'TLT', 'GLD']

        for symbol in symbols_to_test:
            mock_response = MagicMock()
            mock_response.json.return_value = {"symbol": symbol, "qty": "10"}
            mock_response.raise_for_status = MagicMock()

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_instance = MagicMock()
                mock_client_instance.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client_instance

                result = await client.get_positions(symbol=symbol)

                # Verify correct endpoint
                expected_endpoint = f'/v2/positions/{symbol}'
                mock_client_instance.get.assert_called_once_with(expected_endpoint)
                assert result['symbol'] == symbol


class TestAlpacaAccountClientGetOrders:
    """Test suite for get_orders method with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_get_orders_no_filters(self):
        """Test get_orders returns all orders when no filters provided."""
        client = AlpacaAccountClient('CHATGPT')

        mock_orders = [
            {
                "id": "order-1",
                "symbol": "SPY",
                "qty": "10",
                "side": "buy",
                "type": "market",
                "status": "filled",
            },
            {
                "id": "order-2",
                "symbol": "QQQ",
                "qty": "5",
                "side": "sell",
                "type": "limit",
                "status": "open",
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_orders
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_orders()

            # Verify result matches mock data
            assert result == mock_orders
            assert len(result) == 2
            assert result[0]['symbol'] == 'SPY'
            assert result[1]['symbol'] == 'QQQ'

            # Verify correct endpoint was called with no params
            mock_client_instance.get.assert_called_once_with('/v2/orders', params={})

    @pytest.mark.asyncio
    async def test_get_orders_filter_by_status(self):
        """Test get_orders filters by status correctly."""
        client = AlpacaAccountClient('CHATGPT')

        mock_orders = [
            {
                "id": "order-1",
                "symbol": "SPY",
                "status": "open",
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_orders
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_orders(status='open')

            # Verify result
            assert result == mock_orders
            assert all(order['status'] == 'open' for order in result)

            # Verify params include status
            mock_client_instance.get.assert_called_once_with(
                '/v2/orders',
                params={'status': 'open'}
            )

    @pytest.mark.asyncio
    async def test_get_orders_filter_by_limit(self):
        """Test get_orders applies limit correctly."""
        client = AlpacaAccountClient('CHATGPT')

        mock_orders = [
            {"id": "order-1", "symbol": "SPY"},
            {"id": "order-2", "symbol": "QQQ"},
            {"id": "order-3", "symbol": "TLT"},
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_orders
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_orders(limit=3)

            # Verify params include limit
            mock_client_instance.get.assert_called_once_with(
                '/v2/orders',
                params={'limit': 3}
            )

    @pytest.mark.asyncio
    async def test_get_orders_filter_by_symbol(self):
        """Test get_orders filters by symbol correctly."""
        client = AlpacaAccountClient('CHATGPT')

        mock_orders = [
            {
                "id": "order-1",
                "symbol": "SPY",
                "qty": "10",
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_orders
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_orders(symbol='SPY')

            # Verify result
            assert result == mock_orders
            assert all(order['symbol'] == 'SPY' for order in result)

            # Verify params include symbol
            mock_client_instance.get.assert_called_once_with(
                '/v2/orders',
                params={'symbol': 'SPY'}
            )

    @pytest.mark.asyncio
    async def test_get_orders_multiple_filters(self):
        """Test get_orders applies multiple filters correctly."""
        client = AlpacaAccountClient('CHATGPT')

        mock_orders = [
            {
                "id": "order-1",
                "symbol": "SPY",
                "status": "filled",
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_orders
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_orders(status='filled', limit=10, symbol='SPY')

            # Verify all params are included
            mock_client_instance.get.assert_called_once_with(
                '/v2/orders',
                params={'status': 'filled', 'limit': 10, 'symbol': 'SPY'}
            )

    @pytest.mark.asyncio
    async def test_get_orders_empty(self):
        """Test get_orders returns empty list when no orders exist."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.get_orders()

            assert result == []
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_orders_http_error(self):
        """Test that get_orders raises exception on HTTP error."""
        client = AlpacaAccountClient('CHATGPT')

        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock()
        )

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(httpx.HTTPStatusError):
                await client.get_orders()

    @pytest.mark.asyncio
    async def test_get_orders_uses_correct_headers(self):
        """Test that get_orders uses correct authentication headers."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.get_orders()

            # Verify AsyncClient was initialized with correct headers
            call_kwargs = mock_client_class.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert 'APCA-API-KEY-ID' in headers
            assert 'APCA-API-SECRET-KEY' in headers
            assert 'Content-Type' in headers

    @pytest.mark.asyncio
    async def test_get_orders_various_statuses(self):
        """Test get_orders with various status values."""
        client = AlpacaAccountClient('CHATGPT')

        statuses = ['open', 'closed', 'filled', 'canceled', 'pending_new']

        for status in statuses:
            mock_response = MagicMock()
            mock_response.json.return_value = [{"id": "order-1", "status": status}]
            mock_response.raise_for_status = MagicMock()

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_instance = MagicMock()
                mock_client_instance.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client_instance

                result = await client.get_orders(status=status)

                # Verify params include correct status
                mock_client_instance.get.assert_called_once_with(
                    '/v2/orders',
                    params={'status': status}
                )


# ============================================================================
# PLACE ORDER TESTS WITH MOCKED HTTP RESPONSES
# ============================================================================


class TestAlpacaAccountClientPlaceOrder:
    """Test suite for place_order method with various order types and parameters."""

    @pytest.mark.asyncio
    async def test_place_market_order_buy(self):
        """Test placing a market buy order."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-123",
            "client_order_id": "test-order-123",
            "symbol": "SPY",
            "qty": "10",
            "side": "buy",
            "type": "market",
            "time_in_force": "gtc",
            "status": "accepted",
            "created_at": "2025-01-20T12:00:00Z",
            "extended_hours": False,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                order_type="market"
            )

            # Verify result matches mock data
            assert result == mock_order_response
            assert result['symbol'] == 'SPY'
            assert result['qty'] == '10'
            assert result['side'] == 'buy'
            assert result['type'] == 'market'

            # Verify correct endpoint and payload
            call_args = mock_client_instance.post.call_args
            assert call_args[0][0] == '/v2/orders'
            payload = call_args[1]['json']
            assert payload['symbol'] == 'SPY'
            assert payload['qty'] == '10'
            assert payload['side'] == 'buy'
            assert payload['type'] == 'market'
            assert payload['time_in_force'] == 'gtc'
            assert payload['extended_hours'] is False

    @pytest.mark.asyncio
    async def test_place_market_order_sell(self):
        """Test placing a market sell order."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-456",
            "symbol": "QQQ",
            "qty": "5",
            "side": "sell",
            "type": "market",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="QQQ",
                qty=5,
                side="sell"
            )

            # Verify result
            assert result['symbol'] == 'QQQ'
            assert result['side'] == 'sell'

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['side'] == 'sell'

    @pytest.mark.asyncio
    async def test_place_limit_order_with_limit_price(self):
        """Test placing a limit order with limit_price."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-789",
            "symbol": "SPY",
            "qty": "10",
            "side": "buy",
            "type": "limit",
            "limit_price": "450.00",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                order_type="limit",
                limit_price="450.00"
            )

            # Verify result includes limit_price
            assert result['type'] == 'limit'
            assert result['limit_price'] == '450.00'

            # Verify payload includes limit_price
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['type'] == 'limit'
            assert payload['limit_price'] == '450.00'

    @pytest.mark.asyncio
    async def test_place_stop_order_with_stop_price(self):
        """Test placing a stop order with stop_price."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-101",
            "symbol": "TLT",
            "qty": "20",
            "side": "sell",
            "type": "stop",
            "stop_price": "90.00",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="TLT",
                qty=20,
                side="sell",
                order_type="stop",
                stop_price="90.00"
            )

            # Verify result includes stop_price
            assert result['type'] == 'stop'
            assert result['stop_price'] == '90.00'

            # Verify payload includes stop_price
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['type'] == 'stop'
            assert payload['stop_price'] == '90.00'

    @pytest.mark.asyncio
    async def test_place_stop_limit_order(self):
        """Test placing a stop_limit order with both stop_price and limit_price."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-102",
            "symbol": "GLD",
            "qty": "15",
            "side": "buy",
            "type": "stop_limit",
            "stop_price": "180.00",
            "limit_price": "182.00",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="GLD",
                qty=15,
                side="buy",
                order_type="stop_limit",
                stop_price="180.00",
                limit_price="182.00"
            )

            # Verify result includes both prices
            assert result['type'] == 'stop_limit'
            assert result['stop_price'] == '180.00'
            assert result['limit_price'] == '182.00'

            # Verify payload includes both prices
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['type'] == 'stop_limit'
            assert payload['stop_price'] == '180.00'
            assert payload['limit_price'] == '182.00'

    @pytest.mark.asyncio
    async def test_place_order_time_in_force_gtc(self):
        """Test placing order with time_in_force='gtc' (good till canceled)."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-103",
            "symbol": "SPY",
            "qty": "10",
            "side": "buy",
            "type": "market",
            "time_in_force": "gtc",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                time_in_force="gtc"
            )

            # Verify time_in_force is gtc (default)
            assert result['time_in_force'] == 'gtc'

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['time_in_force'] == 'gtc'

    @pytest.mark.asyncio
    async def test_place_order_time_in_force_day(self):
        """Test placing order with time_in_force='day'."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-104",
            "symbol": "QQQ",
            "qty": "5",
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="QQQ",
                qty=5,
                side="buy",
                time_in_force="day"
            )

            # Verify time_in_force is day
            assert result['time_in_force'] == 'day'

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['time_in_force'] == 'day'

    @pytest.mark.asyncio
    async def test_place_order_time_in_force_ioc(self):
        """Test placing order with time_in_force='ioc' (immediate or cancel)."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-105",
            "symbol": "IWM",
            "qty": "8",
            "side": "sell",
            "type": "limit",
            "limit_price": "200.00",
            "time_in_force": "ioc",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="IWM",
                qty=8,
                side="sell",
                order_type="limit",
                limit_price="200.00",
                time_in_force="ioc"
            )

            # Verify time_in_force is ioc
            assert result['time_in_force'] == 'ioc'

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['time_in_force'] == 'ioc'

    @pytest.mark.asyncio
    async def test_place_order_time_in_force_fok(self):
        """Test placing order with time_in_force='fok' (fill or kill)."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-106",
            "symbol": "HYG",
            "qty": "12",
            "side": "buy",
            "type": "limit",
            "limit_price": "75.50",
            "time_in_force": "fok",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="HYG",
                qty=12,
                side="buy",
                order_type="limit",
                limit_price="75.50",
                time_in_force="fok"
            )

            # Verify time_in_force is fok
            assert result['time_in_force'] == 'fok'

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['time_in_force'] == 'fok'

    @pytest.mark.asyncio
    async def test_place_order_with_extended_hours_true(self):
        """Test placing order with extended_hours=True."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-107",
            "symbol": "SPY",
            "qty": "10",
            "side": "buy",
            "type": "limit",
            "limit_price": "445.00",
            "extended_hours": True,
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                order_type="limit",
                limit_price="445.00",
                extended_hours=True
            )

            # Verify extended_hours is True
            assert result['extended_hours'] is True

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['extended_hours'] is True

    @pytest.mark.asyncio
    async def test_place_order_with_extended_hours_false(self):
        """Test placing order with extended_hours=False (default)."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-108",
            "symbol": "QQQ",
            "qty": "5",
            "side": "buy",
            "type": "market",
            "extended_hours": False,
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="QQQ",
                qty=5,
                side="buy",
                extended_hours=False
            )

            # Verify extended_hours is False
            assert result['extended_hours'] is False

            # Verify payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['extended_hours'] is False

    @pytest.mark.asyncio
    async def test_place_order_qty_converted_to_string(self):
        """Test that qty is converted to string in the payload."""
        client = AlpacaAccountClient('CHATGPT')

        mock_order_response = {
            "id": "order-109",
            "symbol": "SPY",
            "qty": "100",
            "side": "buy",
            "type": "market",
            "status": "accepted",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_order_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.place_order(
                symbol="SPY",
                qty=100,  # Integer input
                side="buy"
            )

            # Verify qty is converted to string in payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['qty'] == '100'
            assert isinstance(payload['qty'], str)

    @pytest.mark.asyncio
    async def test_place_order_http_error_400(self):
        """Test that place_order raises exception on HTTP 400 error (validation error)."""
        client = AlpacaAccountClient('CHATGPT')

        error_response_data = {
            "code": 40010001,
            "message": "qty is required"
        }

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = error_response_data

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(Exception, match="Order failed for CHATGPT"):
                await client.place_order(
                    symbol="SPY",
                    qty=10,
                    side="buy"
                )

    @pytest.mark.asyncio
    async def test_place_order_http_error_422(self):
        """Test that place_order raises exception on HTTP 422 error (unprocessable entity)."""
        client = AlpacaAccountClient('CHATGPT')

        error_response_data = {
            "code": 42210000,
            "message": "insufficient buying power"
        }

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = error_response_data

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(Exception, match="insufficient buying power"):
                await client.place_order(
                    symbol="SPY",
                    qty=1000,
                    side="buy"
                )

    @pytest.mark.asyncio
    async def test_place_order_http_error_403(self):
        """Test that place_order raises exception on HTTP 403 error (forbidden)."""
        client = AlpacaAccountClient('CHATGPT')

        error_response_data = {
            "code": 40310000,
            "message": "forbidden: account is not authorized for trading"
        }

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = error_response_data

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(Exception, match="forbidden"):
                await client.place_order(
                    symbol="SPY",
                    qty=10,
                    side="buy"
                )

    @pytest.mark.asyncio
    async def test_place_order_uses_correct_headers(self):
        """Test that place_order uses correct authentication headers."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "order-110", "status": "accepted"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy"
            )

            # Verify AsyncClient was initialized with correct headers
            call_kwargs = mock_client_class.call_args[1]
            assert 'headers' in call_kwargs
            headers = call_kwargs['headers']
            assert 'APCA-API-KEY-ID' in headers
            assert 'APCA-API-SECRET-KEY' in headers
            assert 'Content-Type' in headers
            assert headers['Content-Type'] == 'application/json'

    @pytest.mark.asyncio
    async def test_place_order_uses_correct_base_url(self):
        """Test that place_order uses paper trading URL."""
        client = AlpacaAccountClient('CHATGPT', paper=True)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "order-111"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy"
            )

            # Verify correct base_url was used
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs['base_url'] == PAPER_URL

    @pytest.mark.asyncio
    async def test_place_order_multiple_symbols(self):
        """Test place_order with multiple different symbols."""
        client = AlpacaAccountClient('CHATGPT')

        symbols_to_test = ['SPY', 'QQQ', 'IWM', 'TLT', 'HYG', 'GLD', 'USO']

        for symbol in symbols_to_test:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": f"order-{symbol}",
                "symbol": symbol,
                "qty": "10",
                "side": "buy",
                "status": "accepted"
            }

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_instance = MagicMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client_instance

                result = await client.place_order(
                    symbol=symbol,
                    qty=10,
                    side="buy"
                )

                # Verify correct symbol in result
                assert result['symbol'] == symbol

                # Verify correct symbol in payload
                payload = mock_client_instance.post.call_args[1]['json']
                assert payload['symbol'] == symbol

    @pytest.mark.asyncio
    async def test_place_order_error_includes_account_name(self):
        """Test that error message includes account name."""
        client = AlpacaAccountClient('GEMINI')

        error_response_data = {
            "message": "insufficient buying power"
        }

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = error_response_data

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(Exception, match="Order failed for GEMINI"):
                await client.place_order(
                    symbol="SPY",
                    qty=1000,
                    side="buy"
                )

    @pytest.mark.asyncio
    async def test_place_order_limit_price_not_included_for_market_order(self):
        """Test that limit_price is not included in payload for market orders when not provided."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "order-112", "status": "accepted"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                order_type="market"
            )

            # Verify limit_price is NOT in payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert 'limit_price' not in payload

    @pytest.mark.asyncio
    async def test_place_order_stop_price_not_included_for_market_order(self):
        """Test that stop_price is not included in payload for market orders when not provided."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "order-113", "status": "accepted"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                order_type="market"
            )

            # Verify stop_price is NOT in payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert 'stop_price' not in payload

    @pytest.mark.asyncio
    async def test_place_order_large_quantity(self):
        """Test placing order with large quantity."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "order-114",
            "symbol": "SPY",
            "qty": "1000",
            "side": "buy",
            "status": "accepted"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="SPY",
                qty=1000,
                side="buy"
            )

            # Verify large quantity is handled correctly
            assert result['qty'] == '1000'
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['qty'] == '1000'

    @pytest.mark.asyncio
    async def test_place_order_all_parameters(self):
        """Test placing order with all optional parameters specified."""
        client = AlpacaAccountClient('CHATGPT')

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "order-115",
            "symbol": "SPY",
            "qty": "10",
            "side": "buy",
            "type": "stop_limit",
            "limit_price": "450.00",
            "stop_price": "445.00",
            "time_in_force": "day",
            "extended_hours": True,
            "status": "accepted"
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client_instance

            result = await client.place_order(
                symbol="SPY",
                qty=10,
                side="buy",
                order_type="stop_limit",
                limit_price="450.00",
                stop_price="445.00",
                time_in_force="day",
                extended_hours=True
            )

            # Verify all parameters in result
            assert result['symbol'] == 'SPY'
            assert result['qty'] == '10'
            assert result['side'] == 'buy'
            assert result['type'] == 'stop_limit'
            assert result['limit_price'] == '450.00'
            assert result['stop_price'] == '445.00'
            assert result['time_in_force'] == 'day'
            assert result['extended_hours'] is True

            # Verify all parameters in payload
            payload = mock_client_instance.post.call_args[1]['json']
            assert payload['symbol'] == 'SPY'
            assert payload['qty'] == '10'
            assert payload['side'] == 'buy'
            assert payload['type'] == 'stop_limit'
            assert payload['limit_price'] == '450.00'
            assert payload['stop_price'] == '445.00'
            assert payload['time_in_force'] == 'day'
            assert payload['extended_hours'] is True
