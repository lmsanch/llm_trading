"""Test MultiAlpacaManager parallel operations across accounts.

This module tests the MultiAlpacaManager class from backend.multi_alpaca_client:
- Initialization of all 6 account clients
- Parallel account info retrieval (get_all_accounts)
- Parallel positions retrieval (get_all_positions)
- Single account order placement (place_order_for_account)
- Parallel order placement (place_orders_parallel)
- Position closing operations (close_all_positions)
- Partial failure handling (some accounts succeed, some fail)
- Result aggregation and mapping to account names
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from backend.multi_alpaca_client import (
    MultiAlpacaManager,
    AlpacaAccountClient,
    ALPACA_ACCOUNTS,
    get_all_account_names
)


class TestMultiAlpacaManagerInitialization:
    """Test suite for MultiAlpacaManager initialization."""

    def test_manager_initialization(self):
        """Test that MultiAlpacaManager initializes all 6 clients."""
        manager = MultiAlpacaManager()

        assert manager.clients is not None
        assert isinstance(manager.clients, dict)
        assert len(manager.clients) == 6

    def test_all_accounts_have_clients(self):
        """Test that all 6 accounts have initialized clients."""
        manager = MultiAlpacaManager()
        expected_accounts = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']

        for account_name in expected_accounts:
            assert account_name in manager.clients, f"Account {account_name} not initialized"
            assert isinstance(manager.clients[account_name], AlpacaAccountClient)

    def test_client_account_names_match(self):
        """Test that each client has the correct account_name."""
        manager = MultiAlpacaManager()

        for account_name, client in manager.clients.items():
            assert client.account_name == account_name

    def test_get_client_valid_account(self):
        """Test get_client returns correct client for valid account."""
        manager = MultiAlpacaManager()

        client = manager.get_client('CHATGPT')
        assert client is not None
        assert isinstance(client, AlpacaAccountClient)
        assert client.account_name == 'CHATGPT'

    def test_get_client_all_accounts(self):
        """Test get_client works for all 6 accounts."""
        manager = MultiAlpacaManager()
        account_names = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL']

        for account_name in account_names:
            client = manager.get_client(account_name)
            assert client.account_name == account_name

    def test_get_client_invalid_account(self):
        """Test get_client raises ValueError for invalid account."""
        manager = MultiAlpacaManager()

        with pytest.raises(ValueError, match="Unknown account"):
            manager.get_client('INVALID_ACCOUNT')

    def test_get_client_empty_string(self):
        """Test get_client raises ValueError for empty string."""
        manager = MultiAlpacaManager()

        with pytest.raises(ValueError):
            manager.get_client('')

    def test_get_client_none(self):
        """Test get_client raises error for None."""
        manager = MultiAlpacaManager()

        with pytest.raises((ValueError, TypeError)):
            manager.get_client(None)


class TestGetAllAccounts:
    """Test suite for get_all_accounts parallel operations."""

    @pytest.mark.asyncio
    async def test_get_all_accounts_success(self):
        """Test get_all_accounts retrieves info for all 6 accounts in parallel."""
        manager = MultiAlpacaManager()

        # Mock get_account for each client
        mock_account_data = {
            'CHATGPT': {'id': 'PA3IUYCYRWGK', 'cash': '100000.00', 'buying_power': '100000.00'},
            'GEMINI': {'id': 'PA3M2HMSLN00', 'cash': '95000.00', 'buying_power': '95000.00'},
            'CLAUDE': {'id': 'PA38PAHFRFYC', 'cash': '98000.00', 'buying_power': '98000.00'},
            'GROQ': {'id': 'PA33MEQA4WT7', 'cash': '102000.00', 'buying_power': '102000.00'},
            'DEEPSEEK': {'id': 'PA3KKW3TN54V', 'cash': '99000.00', 'buying_power': '99000.00'},
            'COUNCIL': {'id': 'PA3MQLPXBSO1', 'cash': '101000.00', 'buying_power': '101000.00'},
        }

        for account_name, client in manager.clients.items():
            client.get_account = AsyncMock(return_value=mock_account_data[account_name])

        results = await manager.get_all_accounts()

        # Verify results structure
        assert isinstance(results, dict)
        assert len(results) == 6

        # Verify all accounts present
        for account_name in mock_account_data.keys():
            assert account_name in results
            assert results[account_name] == mock_account_data[account_name]

    @pytest.mark.asyncio
    async def test_get_all_accounts_calls_made_in_parallel(self):
        """Test that get_all_accounts makes parallel calls to asyncio.gather."""
        manager = MultiAlpacaManager()

        # Mock get_account for each client
        for client in manager.clients.values():
            client.get_account = AsyncMock(return_value={'cash': '100000.00'})

        # Patch asyncio.gather to verify it's called
        with patch('backend.multi_alpaca_client.asyncio.gather', new_callable=AsyncMock) as mock_gather:
            mock_gather.return_value = [{'cash': '100000.00'}] * 6

            await manager.get_all_accounts()

            # Verify asyncio.gather was called with all 6 tasks
            assert mock_gather.called
            assert mock_gather.call_count == 1

    @pytest.mark.asyncio
    async def test_get_all_accounts_different_data(self):
        """Test get_all_accounts with different data for each account."""
        manager = MultiAlpacaManager()

        # Create different mock data for each account
        for i, (account_name, client) in enumerate(manager.clients.items()):
            mock_data = {
                'id': f'PA{i}',
                'cash': f'{100000 + i * 1000}.00',
                'portfolio_value': f'{105000 + i * 1500}.00'
            }
            client.get_account = AsyncMock(return_value=mock_data)

        results = await manager.get_all_accounts()

        # Verify each account has different data
        account_names = list(results.keys())
        for i in range(len(account_names)):
            for j in range(i + 1, len(account_names)):
                assert results[account_names[i]] != results[account_names[j]]

    @pytest.mark.asyncio
    async def test_get_all_accounts_preserves_account_names(self):
        """Test that get_all_accounts preserves account name mapping."""
        manager = MultiAlpacaManager()

        # Mock with account-specific data
        for account_name, client in manager.clients.items():
            client.get_account = AsyncMock(return_value={'account': account_name})

        results = await manager.get_all_accounts()

        # Verify mapping is correct
        for account_name in results.keys():
            assert results[account_name]['account'] == account_name


class TestGetAllPositions:
    """Test suite for get_all_positions parallel operations."""

    @pytest.mark.asyncio
    async def test_get_all_positions_success(self):
        """Test get_all_positions retrieves positions for all 6 accounts in parallel."""
        manager = MultiAlpacaManager()

        # Mock positions for each client
        mock_positions = {
            'CHATGPT': [{'symbol': 'SPY', 'qty': '10', 'avg_entry_price': '450.00'}],
            'GEMINI': [{'symbol': 'QQQ', 'qty': '5', 'avg_entry_price': '380.00'}],
            'CLAUDE': [],
            'GROQ': [{'symbol': 'SPY', 'qty': '15', 'avg_entry_price': '448.00'}],
            'DEEPSEEK': [{'symbol': 'GLD', 'qty': '20', 'avg_entry_price': '180.00'}],
            'COUNCIL': [{'symbol': 'TLT', 'qty': '8', 'avg_entry_price': '95.00'}],
        }

        for account_name, client in manager.clients.items():
            client.get_positions = AsyncMock(return_value=mock_positions[account_name])

        results = await manager.get_all_positions()

        # Verify results structure
        assert isinstance(results, dict)
        assert len(results) == 6

        # Verify all accounts present
        for account_name in mock_positions.keys():
            assert account_name in results
            assert results[account_name] == mock_positions[account_name]

    @pytest.mark.asyncio
    async def test_get_all_positions_empty_positions(self):
        """Test get_all_positions when all accounts have no positions."""
        manager = MultiAlpacaManager()

        # Mock empty positions for all clients
        for client in manager.clients.values():
            client.get_positions = AsyncMock(return_value=[])

        results = await manager.get_all_positions()

        # Verify all accounts have empty lists
        assert len(results) == 6
        for positions in results.values():
            assert positions == []

    @pytest.mark.asyncio
    async def test_get_all_positions_mixed_empty_and_filled(self):
        """Test get_all_positions with mix of empty and filled positions."""
        manager = MultiAlpacaManager()

        # Some accounts have positions, some don't
        mock_positions = {
            'CHATGPT': [{'symbol': 'SPY', 'qty': '10'}],
            'GEMINI': [],
            'CLAUDE': [{'symbol': 'QQQ', 'qty': '5'}],
            'GROQ': [],
            'DEEPSEEK': [],
            'COUNCIL': [{'symbol': 'GLD', 'qty': '20'}],
        }

        for account_name, client in manager.clients.items():
            client.get_positions = AsyncMock(return_value=mock_positions[account_name])

        results = await manager.get_all_positions()

        # Verify correct accounts have positions
        assert len(results['CHATGPT']) == 1
        assert len(results['GEMINI']) == 0
        assert len(results['CLAUDE']) == 1
        assert len(results['GROQ']) == 0
        assert len(results['DEEPSEEK']) == 0
        assert len(results['COUNCIL']) == 1

    @pytest.mark.asyncio
    async def test_get_all_positions_multiple_positions_per_account(self):
        """Test get_all_positions with multiple positions per account."""
        manager = MultiAlpacaManager()

        # Multiple positions for some accounts
        mock_positions = [
            {'symbol': 'SPY', 'qty': '10'},
            {'symbol': 'QQQ', 'qty': '5'},
            {'symbol': 'GLD', 'qty': '20'}
        ]

        for client in manager.clients.values():
            client.get_positions = AsyncMock(return_value=mock_positions)

        results = await manager.get_all_positions()

        # Verify all accounts have all 3 positions
        for positions in results.values():
            assert len(positions) == 3
            assert positions == mock_positions


class TestPlaceOrderForAccount:
    """Test suite for place_order_for_account operations."""

    @pytest.mark.asyncio
    async def test_place_order_for_account_success(self):
        """Test placing order for specific account."""
        manager = MultiAlpacaManager()

        # Mock place_order for CHATGPT client
        mock_order = {
            'id': 'order123',
            'symbol': 'SPY',
            'qty': '10',
            'side': 'buy',
            'status': 'accepted'
        }
        manager.clients['CHATGPT'].place_order = AsyncMock(return_value=mock_order)

        result = await manager.place_order_for_account(
            account_name='CHATGPT',
            symbol='SPY',
            qty=10,
            side='buy'
        )

        assert result == mock_order
        manager.clients['CHATGPT'].place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_for_account_with_limit_price(self):
        """Test placing limit order for specific account."""
        manager = MultiAlpacaManager()

        mock_order = {'id': 'order456', 'type': 'limit'}
        manager.clients['GEMINI'].place_order = AsyncMock(return_value=mock_order)

        result = await manager.place_order_for_account(
            account_name='GEMINI',
            symbol='QQQ',
            qty=5,
            side='sell',
            order_type='limit',
            limit_price='380.50'
        )

        assert result == mock_order
        manager.clients['GEMINI'].place_order.assert_called_once_with(
            symbol='QQQ',
            qty=5,
            side='sell',
            order_type='limit',
            limit_price='380.50',
            stop_price=None
        )

    @pytest.mark.asyncio
    async def test_place_order_for_account_invalid_account(self):
        """Test placing order for invalid account raises error."""
        manager = MultiAlpacaManager()

        with pytest.raises(ValueError, match="Unknown account"):
            await manager.place_order_for_account(
                account_name='INVALID',
                symbol='SPY',
                qty=10,
                side='buy'
            )

    @pytest.mark.asyncio
    async def test_place_order_for_account_all_accounts(self):
        """Test placing orders for each of the 6 accounts."""
        manager = MultiAlpacaManager()

        # Mock place_order for all clients
        for account_name, client in manager.clients.items():
            client.place_order = AsyncMock(return_value={'id': f'order_{account_name}'})

        # Place order for each account
        for account_name in manager.clients.keys():
            result = await manager.place_order_for_account(
                account_name=account_name,
                symbol='SPY',
                qty=10,
                side='buy'
            )
            assert result['id'] == f'order_{account_name}'


class TestPlaceOrdersParallel:
    """Test suite for place_orders_parallel operations."""

    @pytest.mark.asyncio
    async def test_place_orders_parallel_success(self):
        """Test placing orders for multiple accounts in parallel."""
        manager = MultiAlpacaManager()

        # Mock place_order for all clients
        for account_name, client in manager.clients.items():
            client.place_order = AsyncMock(
                return_value={'id': f'order_{account_name}', 'status': 'accepted'}
            )

        orders = [
            {'account_name': 'CHATGPT', 'symbol': 'SPY', 'qty': 10, 'side': 'buy'},
            {'account_name': 'GEMINI', 'symbol': 'QQQ', 'qty': 5, 'side': 'buy'},
            {'account_name': 'CLAUDE', 'symbol': 'GLD', 'qty': 20, 'side': 'sell'},
        ]

        results = await manager.place_orders_parallel(orders)

        # Verify results structure
        assert isinstance(results, dict)
        assert len(results) == 3
        assert 'CHATGPT' in results
        assert 'GEMINI' in results
        assert 'CLAUDE' in results

        # Verify correct order IDs
        assert results['CHATGPT']['id'] == 'order_CHATGPT'
        assert results['GEMINI']['id'] == 'order_GEMINI'
        assert results['CLAUDE']['id'] == 'order_CLAUDE'

    @pytest.mark.asyncio
    async def test_place_orders_parallel_all_accounts(self):
        """Test placing orders for all 6 accounts in parallel."""
        manager = MultiAlpacaManager()

        # Mock place_order for all clients
        for account_name, client in manager.clients.items():
            client.place_order = AsyncMock(
                return_value={'id': f'order_{account_name}', 'account': account_name}
            )

        orders = [
            {'account_name': name, 'symbol': 'SPY', 'qty': 10, 'side': 'buy'}
            for name in manager.clients.keys()
        ]

        results = await manager.place_orders_parallel(orders)

        # Verify all 6 accounts
        assert len(results) == 6
        for account_name in manager.clients.keys():
            assert account_name in results
            assert results[account_name]['account'] == account_name

    @pytest.mark.asyncio
    async def test_place_orders_parallel_with_limit_prices(self):
        """Test placing parallel limit orders with different prices."""
        manager = MultiAlpacaManager()

        # Mock place_order for clients
        for account_name in ['CHATGPT', 'GEMINI']:
            manager.clients[account_name].place_order = AsyncMock(
                return_value={'id': f'order_{account_name}', 'type': 'limit'}
            )

        orders = [
            {
                'account_name': 'CHATGPT',
                'symbol': 'SPY',
                'qty': 10,
                'side': 'buy',
                'order_type': 'limit',
                'limit_price': '450.00'
            },
            {
                'account_name': 'GEMINI',
                'symbol': 'QQQ',
                'qty': 5,
                'side': 'sell',
                'order_type': 'limit',
                'limit_price': '380.50'
            },
        ]

        results = await manager.place_orders_parallel(orders)

        assert len(results) == 2
        assert results['CHATGPT']['type'] == 'limit'
        assert results['GEMINI']['type'] == 'limit'

    @pytest.mark.asyncio
    async def test_place_orders_parallel_empty_list(self):
        """Test placing parallel orders with empty list."""
        manager = MultiAlpacaManager()

        results = await manager.place_orders_parallel([])

        assert results == {}

    @pytest.mark.asyncio
    async def test_place_orders_parallel_single_order(self):
        """Test placing parallel orders with single order."""
        manager = MultiAlpacaManager()

        manager.clients['CHATGPT'].place_order = AsyncMock(
            return_value={'id': 'order123'}
        )

        orders = [{'account_name': 'CHATGPT', 'symbol': 'SPY', 'qty': 10, 'side': 'buy'}]

        results = await manager.place_orders_parallel(orders)

        assert len(results) == 1
        assert results['CHATGPT']['id'] == 'order123'


class TestCloseAllPositions:
    """Test suite for close_all_positions operations."""

    @pytest.mark.asyncio
    async def test_close_all_positions_single_account(self):
        """Test closing all positions for single account."""
        manager = MultiAlpacaManager()

        # Mock get_positions and close_position
        mock_positions = [
            {'symbol': 'SPY', 'qty': '10'},
            {'symbol': 'QQQ', 'qty': '5'}
        ]
        manager.clients['CHATGPT'].get_positions = AsyncMock(return_value=mock_positions)
        manager.clients['CHATGPT'].close_position = AsyncMock(
            return_value={'id': 'close_order', 'status': 'filled'}
        )

        results = await manager.close_all_positions(account_name='CHATGPT')

        # Verify structure
        assert 'CHATGPT' in results
        assert 'SPY' in results['CHATGPT']
        assert 'QQQ' in results['CHATGPT']

        # Verify close_position called for each symbol
        assert manager.clients['CHATGPT'].close_position.call_count == 2

    @pytest.mark.asyncio
    async def test_close_all_positions_all_accounts(self):
        """Test closing all positions for all accounts."""
        manager = MultiAlpacaManager()

        # Mock positions for all accounts
        for account_name, client in manager.clients.items():
            mock_positions = [{'symbol': 'SPY', 'qty': '10'}]
            client.get_positions = AsyncMock(return_value=mock_positions)
            client.close_position = AsyncMock(
                return_value={'id': f'close_{account_name}', 'status': 'filled'}
            )

        results = await manager.close_all_positions(account_name=None)

        # Verify all 6 accounts
        assert len(results) == 6
        for account_name in manager.clients.keys():
            assert account_name in results
            assert 'SPY' in results[account_name]

    @pytest.mark.asyncio
    async def test_close_all_positions_no_positions(self):
        """Test closing positions when account has no positions."""
        manager = MultiAlpacaManager()

        # Mock empty positions
        manager.clients['CHATGPT'].get_positions = AsyncMock(return_value=[])

        results = await manager.close_all_positions(account_name='CHATGPT')

        # Should return empty dict for account
        assert 'CHATGPT' in results
        assert results['CHATGPT'] == {}

    @pytest.mark.asyncio
    async def test_close_all_positions_multiple_positions(self):
        """Test closing multiple positions for single account."""
        manager = MultiAlpacaManager()

        # Mock multiple positions
        mock_positions = [
            {'symbol': 'SPY', 'qty': '10'},
            {'symbol': 'QQQ', 'qty': '5'},
            {'symbol': 'GLD', 'qty': '20'}
        ]
        manager.clients['COUNCIL'].get_positions = AsyncMock(return_value=mock_positions)

        close_results = {
            'SPY': {'id': 'close_spy', 'status': 'filled'},
            'QQQ': {'id': 'close_qqq', 'status': 'filled'},
            'GLD': {'id': 'close_gld', 'status': 'filled'}
        }

        async def mock_close(symbol):
            return close_results[symbol]

        manager.clients['COUNCIL'].close_position = AsyncMock(side_effect=mock_close)

        results = await manager.close_all_positions(account_name='COUNCIL')

        # Verify all 3 positions closed
        assert len(results['COUNCIL']) == 3
        assert 'SPY' in results['COUNCIL']
        assert 'QQQ' in results['COUNCIL']
        assert 'GLD' in results['COUNCIL']

    @pytest.mark.asyncio
    async def test_close_all_positions_mixed_accounts(self):
        """Test closing positions when some accounts have positions and some don't."""
        manager = MultiAlpacaManager()

        # Set up mixed positions
        manager.clients['CHATGPT'].get_positions = AsyncMock(
            return_value=[{'symbol': 'SPY', 'qty': '10'}]
        )
        manager.clients['GEMINI'].get_positions = AsyncMock(return_value=[])
        manager.clients['CLAUDE'].get_positions = AsyncMock(
            return_value=[{'symbol': 'QQQ', 'qty': '5'}]
        )
        manager.clients['GROQ'].get_positions = AsyncMock(return_value=[])
        manager.clients['DEEPSEEK'].get_positions = AsyncMock(return_value=[])
        manager.clients['COUNCIL'].get_positions = AsyncMock(
            return_value=[{'symbol': 'GLD', 'qty': '20'}]
        )

        for client in manager.clients.values():
            client.close_position = AsyncMock(
                return_value={'id': 'close_order', 'status': 'filled'}
            )

        results = await manager.close_all_positions(account_name=None)

        # Verify accounts with positions have close orders
        assert len(results['CHATGPT']) == 1
        assert len(results['GEMINI']) == 0
        assert len(results['CLAUDE']) == 1
        assert len(results['GROQ']) == 0
        assert len(results['DEEPSEEK']) == 0
        assert len(results['COUNCIL']) == 1


class TestPartialFailures:
    """Test suite for handling partial failures in parallel operations."""

    @pytest.mark.asyncio
    async def test_get_all_accounts_partial_failure(self):
        """Test get_all_accounts when some accounts fail."""
        manager = MultiAlpacaManager()

        # Mock successful and failed calls
        manager.clients['CHATGPT'].get_account = AsyncMock(
            return_value={'cash': '100000.00'}
        )
        manager.clients['GEMINI'].get_account = AsyncMock(
            side_effect=Exception("API Error")
        )
        manager.clients['CLAUDE'].get_account = AsyncMock(
            return_value={'cash': '98000.00'}
        )

        # Since asyncio.gather will raise if any task fails,
        # we need to test with return_exceptions=True behavior or catch
        with pytest.raises(Exception):
            await manager.get_all_accounts()

    @pytest.mark.asyncio
    async def test_place_orders_parallel_partial_failure(self):
        """Test place_orders_parallel when some orders fail."""
        manager = MultiAlpacaManager()

        # Mock successful and failed orders
        manager.clients['CHATGPT'].place_order = AsyncMock(
            return_value={'id': 'order123', 'status': 'accepted'}
        )
        manager.clients['GEMINI'].place_order = AsyncMock(
            side_effect=Exception("Insufficient funds")
        )
        manager.clients['CLAUDE'].place_order = AsyncMock(
            return_value={'id': 'order789', 'status': 'accepted'}
        )

        orders = [
            {'account_name': 'CHATGPT', 'symbol': 'SPY', 'qty': 10, 'side': 'buy'},
            {'account_name': 'GEMINI', 'symbol': 'QQQ', 'qty': 5, 'side': 'buy'},
            {'account_name': 'CLAUDE', 'symbol': 'GLD', 'qty': 20, 'side': 'sell'},
        ]

        # Since asyncio.gather will raise if any task fails
        with pytest.raises(Exception):
            await manager.place_orders_parallel(orders)


class TestResultAggregation:
    """Test suite for result aggregation and mapping to account names."""

    @pytest.mark.asyncio
    async def test_results_mapped_to_correct_accounts(self):
        """Test that results are correctly mapped to account names."""
        manager = MultiAlpacaManager()

        # Mock different data for ALL 6 accounts
        account_data = {
            'CHATGPT': {'cash': '100000.00', 'account': 'CHATGPT'},
            'GEMINI': {'cash': '95000.00', 'account': 'GEMINI'},
            'CLAUDE': {'cash': '98000.00', 'account': 'CLAUDE'},
            'GROQ': {'cash': '102000.00', 'account': 'GROQ'},
            'DEEPSEEK': {'cash': '99000.00', 'account': 'DEEPSEEK'},
            'COUNCIL': {'cash': '101000.00', 'account': 'COUNCIL'},
        }

        for account_name, data in account_data.items():
            manager.clients[account_name].get_account = AsyncMock(return_value=data)

        results = await manager.get_all_accounts()

        # Verify each account gets its own data
        for account_name, expected_data in account_data.items():
            assert results[account_name] == expected_data

    @pytest.mark.asyncio
    async def test_parallel_orders_preserve_account_mapping(self):
        """Test that parallel orders preserve account mapping in results."""
        manager = MultiAlpacaManager()

        # Mock place_order with account-specific responses
        for account_name, client in manager.clients.items():
            client.place_order = AsyncMock(
                return_value={
                    'id': f'order_{account_name}',
                    'account': account_name,
                    'symbol': 'SPY'
                }
            )

        orders = [
            {'account_name': name, 'symbol': 'SPY', 'qty': 10, 'side': 'buy'}
            for name in ['CHATGPT', 'GEMINI', 'CLAUDE']
        ]

        results = await manager.place_orders_parallel(orders)

        # Verify mapping is correct
        for account_name in ['CHATGPT', 'GEMINI', 'CLAUDE']:
            assert results[account_name]['account'] == account_name
            assert results[account_name]['id'] == f'order_{account_name}'

    @pytest.mark.asyncio
    async def test_positions_aggregation_structure(self):
        """Test that get_all_positions aggregates results with correct structure."""
        manager = MultiAlpacaManager()

        # Mock positions with different symbols per account
        positions_map = {
            'CHATGPT': [{'symbol': 'SPY', 'qty': '10'}],
            'GEMINI': [{'symbol': 'QQQ', 'qty': '5'}],
            'CLAUDE': [],
            'GROQ': [{'symbol': 'GLD', 'qty': '20'}],
            'DEEPSEEK': [{'symbol': 'TLT', 'qty': '8'}],
            'COUNCIL': [{'symbol': 'SPY', 'qty': '15'}],
        }

        for account_name, positions in positions_map.items():
            manager.clients[account_name].get_positions = AsyncMock(return_value=positions)

        results = await manager.get_all_positions()

        # Verify structure
        assert isinstance(results, dict)
        assert len(results) == 6

        # Verify each account has correct positions
        for account_name, expected_positions in positions_map.items():
            assert results[account_name] == expected_positions
