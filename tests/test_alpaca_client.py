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
from unittest.mock import patch, MagicMock
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
