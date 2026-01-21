"""Test trade execution with event logging and retry logic.

This module tests the TradeService and ExecutionStage classes focusing on:
- Event logging for order_placed, order_failed, baseline_account_skipped events
- Retry logic for failed orders with exponential backoff
- Baseline account (DEEPSEEK) skip logic
- Account mapping validation
- FLAT position handling
- Integration with MultiAlpacaManager and execution_db
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from backend.services.trade_service import TradeService
from backend.pipeline.stages.execution import ExecutionStage


class TestTradeServiceEventLogging:
    """Test suite for event logging in TradeService.execute_trades()."""

    @pytest.fixture
    def trade_service(self):
        """Create a TradeService instance for testing."""
        return TradeService()

    @pytest.fixture
    def mock_pitch(self):
        """Create a mock pitch dict."""
        return {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "CHATGPT",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
            "entry_policy": {"limit_price": 500.0},
            "exit_policy": {
                "take_profit_pct": 5.0,
                "stop_loss_pct": 2.0
            }
        }

    @pytest.fixture
    def mock_order_result(self):
        """Create a mock order result."""
        return {
            "order_id": "order_123",
            "symbol": "SPY",
            "side": "buy",
            "qty": 10,
            "limit_price": 500.0,
            "take_profit_price": 525.0,
            "stop_loss_price": 490.0,
        }

    @pytest.mark.asyncio
    async def test_event_logged_on_successful_order(
        self, trade_service, mock_pitch, mock_order_result
    ):
        """Test that order_placed event is logged on successful order."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            mock_create_order.return_value = mock_order_result

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify event was logged
            assert mock_log_event.called
            event_call = mock_log_event.call_args
            assert event_call[1]["event_type"] == "order_placed"
            assert event_call[1]["account"] == "CHATGPT"
            assert event_call[1]["week_id"] == "2025-01-20"
            assert event_call[1]["event_data"]["trade_id"] == 123
            assert event_call[1]["event_data"]["symbol"] == "SPY"
            assert event_call[1]["event_data"]["side"] == "buy"
            assert event_call[1]["event_data"]["order_id"] == "order_123"

    @pytest.mark.asyncio
    async def test_event_logged_on_failed_order(
        self, trade_service, mock_pitch
    ):
        """Test that order_failed event is logged on order failure."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            mock_create_order.side_effect = Exception("Insufficient buying power")

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify order_failed event was logged
            event_calls = [call for call in mock_log_event.call_args_list if call[1]["event_type"] == "order_failed"]
            assert len(event_calls) > 0
            event_call = event_calls[0]
            assert event_call[1]["event_type"] == "order_failed"
            assert event_call[1]["account"] == "CHATGPT"
            assert "Insufficient buying power" in event_call[1]["event_data"]["error"]

    @pytest.mark.asyncio
    async def test_event_logged_on_baseline_account_skip(
        self, trade_service
    ):
        """Test that baseline_account_skipped event is logged when DEEPSEEK is skipped."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "DEEPSEEK",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify baseline_account_skipped event was logged
            assert mock_log_event.called
            event_call = mock_log_event.call_args
            assert event_call[1]["event_type"] == "baseline_account_skipped"
            assert event_call[1]["account"] == "DEEPSEEK"
            assert event_call[1]["event_data"]["trade_id"] == 123
            assert "baseline" in event_call[1]["event_data"]["reason"].lower()

    @pytest.mark.asyncio
    async def test_all_event_data_fields_present(
        self, trade_service, mock_pitch, mock_order_result
    ):
        """Test that all required event_data fields are present."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            mock_create_order.return_value = mock_order_result

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify all required fields are present
            event_call = mock_log_event.call_args
            event_data = event_call[1]["event_data"]

            required_fields = ["trade_id", "symbol", "side", "qty", "order_id"]
            for field in required_fields:
                assert field in event_data, f"Missing required field: {field}"


class TestTradeServiceRetryLogic:
    """Test suite for retry logic in TradeService.execute_trades()."""

    @pytest.fixture
    def trade_service(self):
        """Create a TradeService instance for testing."""
        return TradeService()

    @pytest.fixture
    def mock_pitch(self):
        """Create a mock pitch dict."""
        return {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "CHATGPT",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
            "symbol": "SPY",
            "entry_policy": {"limit_price": 500.0},
            "exit_policy": {
                "take_profit_pct": 5.0,
                "stop_loss_pct": 2.0
            }
        }

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(
        self, trade_service, mock_pitch
    ):
        """Test that transient errors trigger retry."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            # First attempt fails with transient error, second succeeds
            mock_create_order.side_effect = [
                Exception("Network timeout"),
                {
                    "order_id": "order_123",
                    "symbol": "SPY",
                    "side": "buy",
                    "qty": 10,
                    "limit_price": 500.0,
                    "take_profit_price": 525.0,
                    "stop_loss_price": 490.0,
                }
            ]

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify retry was attempted
            assert mock_create_order.call_count == 2
            # Verify 5-second delay
            mock_sleep.assert_called_once_with(5)
            # Verify order_retried event was logged
            retry_events = [call for call in mock_log_event.call_args_list if call[1]["event_type"] == "order_retried"]
            assert len(retry_events) == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(
        self, trade_service, mock_pitch
    ):
        """Test that non-retryable errors skip retry."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            # Fail with non-retryable error
            mock_create_order.side_effect = Exception("Insufficient buying power")

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify NO retry was attempted
            assert mock_create_order.call_count == 1
            # Verify NO sleep was called
            mock_sleep.assert_not_called()
            # Verify order_failed event was logged immediately
            failed_events = [call for call in mock_log_event.call_args_list if call[1]["event_type"] == "order_failed"]
            assert len(failed_events) == 1

    @pytest.mark.asyncio
    async def test_retry_delay_is_5_seconds(
        self, trade_service, mock_pitch
    ):
        """Test that retry delay is exactly 5 seconds."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock), \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            mock_create_order.side_effect = [
                Exception("Timeout"),
                Exception("Timeout again")
            ]

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify 5-second delay
            mock_sleep.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_max_two_attempts(
        self, trade_service, mock_pitch
    ):
        """Test that orders are retried at most once (2 total attempts)."""
        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock), \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class, \
             patch("asyncio.sleep", new_callable=AsyncMock):

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            # Fail all attempts
            mock_create_order.side_effect = [
                Exception("Timeout 1"),
                Exception("Timeout 2"),
                Exception("Timeout 3"),  # Should NOT be called
            ]

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify exactly 2 attempts (1 original + 1 retry)
            assert mock_create_order.call_count == 2

    def test_is_retryable_error_non_retryable_patterns(self, trade_service):
        """Test that non-retryable error patterns are correctly identified."""
        non_retryable_errors = [
            Exception("Insufficient buying power"),
            Exception("Insufficient funds for order"),
            Exception("Invalid symbol ABC"),
            Exception("Symbol not found"),
            Exception("Symbol is not tradable"),
            Exception("Account suspended"),
            Exception("Forbidden access"),
            Exception("Unauthorized request"),
        ]

        for error in non_retryable_errors:
            assert not trade_service._is_retryable_error(error), \
                f"Error should NOT be retryable: {error}"

    def test_is_retryable_error_retryable_patterns(self, trade_service):
        """Test that retryable error patterns are correctly identified."""
        retryable_errors = [
            Exception("Network timeout"),
            Exception("Connection reset by peer"),
            Exception("Temporary server error"),
            Exception("Rate limit exceeded"),
            Exception("Service unavailable"),
        ]

        for error in retryable_errors:
            assert trade_service._is_retryable_error(error), \
                f"Error should be retryable: {error}"


class TestTradeServiceBaselineAccountSkip:
    """Test suite for baseline account (DEEPSEEK) skip logic."""

    @pytest.fixture
    def trade_service(self):
        """Create a TradeService instance for testing."""
        return TradeService()

    @pytest.mark.asyncio
    async def test_deepseek_account_always_skipped(self, trade_service):
        """Test that DEEPSEEK account is always skipped."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "DEEPSEEK",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event:

            mock_find_pitch.return_value = mock_pitch

            result = await trade_service.execute_trades([123])

            # Verify trade was skipped
            assert result["results"][0]["status"] == "skipped"
            assert result["results"][0]["account"] == "DEEPSEEK"
            assert "baseline" in result["results"][0]["message"].lower()

    @pytest.mark.asyncio
    async def test_deepseek_skip_logged_to_database(self, trade_service):
        """Test that DEEPSEEK skip is logged to execution_events table."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "DEEPSEEK",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event:

            mock_find_pitch.return_value = mock_pitch

            result = await trade_service.execute_trades([123])

            # Verify event was logged
            assert mock_log_event.called
            event_call = mock_log_event.call_args
            assert event_call[1]["event_type"] == "baseline_account_skipped"
            assert event_call[1]["account"] == "DEEPSEEK"

    @pytest.mark.asyncio
    async def test_other_accounts_not_skipped(self, trade_service):
        """Test that non-DEEPSEEK accounts are not skipped."""
        accounts = ["CHATGPT", "GEMINI", "CLAUDE", "GROQ", "COUNCIL"]

        for account in accounts:
            mock_pitch = {
                "id": 123,
                "week_id": "2025-01-20",
                "account": account,
                "instrument": "SPY",
                "direction": "LONG",
                "conviction": 1.0,
                "entry_policy": {"limit_price": 500.0},
                "exit_policy": {
                    "take_profit_pct": 5.0,
                    "stop_loss_pct": 2.0
                }
            }

            with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
                 patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock), \
                 patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
                 patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class:

                mock_find_pitch.return_value = mock_pitch
                mock_create_order.return_value = {
                    "order_id": "order_123",
                    "symbol": "SPY",
                    "side": "buy",
                    "qty": 10,
                    "limit_price": 500.0,
                    "take_profit_price": 525.0,
                    "stop_loss_price": 490.0,
                }

                # Mock MultiAlpacaManager
                mock_manager = MagicMock()
                mock_alpaca_client = MagicMock()
                mock_manager.clients = {account: mock_alpaca_client}
                mock_manager_class.return_value = mock_manager

                result = await trade_service.execute_trades([123])

                # Verify trade was NOT skipped
                assert result["results"][0]["status"] != "skipped", \
                    f"Account {account} should not be skipped"


class TestTradeServiceAccountValidation:
    """Test suite for account mapping validation."""

    @pytest.fixture
    def trade_service(self):
        """Create a TradeService instance for testing."""
        return TradeService()

    @pytest.mark.asyncio
    async def test_invalid_account_name_rejected(self, trade_service):
        """Test that invalid account names are rejected."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "INVALID_ACCOUNT",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event:

            mock_find_pitch.return_value = mock_pitch

            result = await trade_service.execute_trades([123])

            # Verify trade was rejected
            assert result["results"][0]["status"] == "error"
            assert "Invalid account name" in result["results"][0]["message"]

    @pytest.mark.asyncio
    async def test_invalid_account_logged_to_database(self, trade_service):
        """Test that invalid account attempts are logged."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "INVALID_ACCOUNT",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event:

            mock_find_pitch.return_value = mock_pitch

            result = await trade_service.execute_trades([123])

            # Verify event was logged
            assert mock_log_event.called
            event_call = mock_log_event.call_args
            assert event_call[1]["event_type"] == "account_validation_error"
            assert event_call[1]["account"] == "INVALID_ACCOUNT"

    @pytest.mark.asyncio
    async def test_valid_accounts_pass_validation(self, trade_service):
        """Test that all valid account names pass validation."""
        valid_accounts = ["CHATGPT", "GEMINI", "CLAUDE", "GROQ", "DEEPSEEK", "COUNCIL"]

        for account in valid_accounts:
            mock_pitch = {
                "id": 123,
                "week_id": "2025-01-20",
                "account": account,
                "instrument": "SPY",
                "direction": "LONG" if account != "DEEPSEEK" else "FLAT",
                "conviction": 1.0 if account != "DEEPSEEK" else 0.0,
            }

            with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
                 patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock):
                mock_find_pitch.return_value = mock_pitch

                result = await trade_service.execute_trades([123])

                # Verify account name was accepted (not rejected with validation error)
                assert result["results"][0]["status"] != "error" or \
                       "Invalid account name" not in result["results"][0]["message"], \
                       f"Valid account {account} should pass validation"


class TestTradeServiceFlatPositionHandling:
    """Test suite for FLAT position handling."""

    @pytest.fixture
    def trade_service(self):
        """Create a TradeService instance for testing."""
        return TradeService()

    @pytest.mark.asyncio
    async def test_flat_positions_skipped(self, trade_service):
        """Test that FLAT positions are skipped."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "CHATGPT",
            "instrument": "SPY",
            "direction": "FLAT",
            "conviction": 0.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch:
            mock_find_pitch.return_value = mock_pitch

            result = await trade_service.execute_trades([123])

            # Verify trade was skipped
            assert result["results"][0]["status"] == "skipped"
            assert "FLAT" in result["results"][0]["message"]

    @pytest.mark.asyncio
    async def test_flat_positions_not_sent_to_alpaca(self, trade_service):
        """Test that FLAT positions are not sent to Alpaca."""
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "CHATGPT",
            "instrument": "SPY",
            "direction": "FLAT",
            "conviction": 0.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order:

            mock_find_pitch.return_value = mock_pitch

            result = await trade_service.execute_trades([123])

            # Verify create_bracket_order was NOT called
            mock_create_order.assert_not_called()


class TestExecutionStageBaselineAccountSkip:
    """Test suite for ExecutionStage baseline account skip logic."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_trade_skips_deepseek(self, execution_stage):
        """Test that _prepare_trade() returns None for DEEPSEEK account."""
        decision = {
            "account": "DEEPSEEK",
            "model": "deepseek-chat",
            "alpaca_id": "PA3KKW3TN54V",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "deepseek-chat")

        # Verify None was returned (trade not prepared)
        assert trade is None

    def test_prepare_trade_accepts_other_accounts(self, execution_stage):
        """Test that _prepare_trade() accepts non-DEEPSEEK accounts."""
        accounts = ["CHATGPT", "GEMINI", "CLAUDE", "GROQ", "COUNCIL"]

        for account in accounts:
            decision = {
                "account": account,
                "model": "test-model",
                "alpaca_id": "PA123456789",
                "instrument": "SPY",
                "direction": "LONG",
                "conviction": 1.0,
            }

            trade = execution_stage._prepare_trade(decision, "test-model")

            # Verify trade was prepared (not None)
            assert trade is not None, f"Account {account} should be accepted"
            assert trade["account"] == account

    @pytest.mark.asyncio
    async def test_place_orders_parallel_filters_deepseek(self, execution_stage):
        """Test that _place_orders_parallel() filters out DEEPSEEK trades."""
        trades = [
            {
                "trade_id": "trade_1",
                "account": "CHATGPT",
                "alpaca_id": "PA3IUYCYRWGK",
                "model": "openai/gpt-4",
                "instrument": "SPY",
                "direction": "LONG",
                "side": "buy",
                "qty": 10,
                "position_size": 0.5,
                "conviction": 1.0,
                "source": "chatgpt",
            },
            {
                "trade_id": "trade_2",
                "account": "DEEPSEEK",
                "alpaca_id": "PA3KKW3TN54V",
                "model": "deepseek/deepseek-chat",
                "instrument": "QQQ",
                "direction": "LONG",
                "side": "buy",
                "qty": 10,
                "position_size": 0.5,
                "conviction": 1.0,
                "source": "deepseek",
            },
        ]

        with patch("backend.pipeline.stages.execution.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.pipeline.stages.execution.MultiAlpacaManager") as mock_manager_class, \
             patch("backend.pipeline.stages.execution.get_week_id", return_value="2025-01-20"):

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_manager.place_orders_parallel = AsyncMock(return_value={
                "CHATGPT": {"order_id": "order_123", "id": "order_123", "message": "Order placed"}
            })
            mock_manager_class.return_value = mock_manager

            # Execute
            results = await execution_stage._place_orders_parallel(trades)

            # Verify DEEPSEEK was filtered out
            assert len(results) == 1
            assert results[0]["account"] == "CHATGPT"

            # Verify baseline_account_skipped event was logged
            baseline_events = [
                call for call in mock_log_event.call_args_list
                if call[1]["event_type"] == "baseline_account_skipped"
            ]
            assert len(baseline_events) == 1
            assert baseline_events[0][1]["account"] == "DEEPSEEK"


class TestExecutionStageEventLogging:
    """Test suite for ExecutionStage event logging."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    @pytest.mark.asyncio
    async def test_order_placed_event_logged(self, execution_stage):
        """Test that order_placed event is logged on successful order."""
        trades = [
            {
                "trade_id": "trade_1",
                "account": "CHATGPT",
                "alpaca_id": "PA3IUYCYRWGK",
                "model": "openai/gpt-4",
                "instrument": "SPY",
                "direction": "LONG",
                "side": "buy",
                "qty": 10,
                "position_size": 0.5,
                "conviction": 1.0,
                "source": "chatgpt",
            }
        ]

        with patch("backend.pipeline.stages.execution.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.pipeline.stages.execution.MultiAlpacaManager") as mock_manager_class, \
             patch("backend.pipeline.stages.execution.get_week_id", return_value="2025-01-20"):

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_manager.place_orders_parallel = AsyncMock(return_value={
                "CHATGPT": {"order_id": "order_123", "id": "order_123", "message": "Order placed"}
            })
            mock_manager_class.return_value = mock_manager

            # Execute
            results = await execution_stage._place_orders_parallel(trades)

            # Verify order_placed event was logged
            placed_events = [
                call for call in mock_log_event.call_args_list
                if call[1]["event_type"] == "order_placed"
            ]
            assert len(placed_events) == 1
            assert placed_events[0][1]["account"] == "CHATGPT"

    @pytest.mark.asyncio
    async def test_order_failed_event_logged(self, execution_stage):
        """Test that order_failed event is logged on order failure."""
        trades = [
            {
                "trade_id": "trade_1",
                "account": "CHATGPT",
                "alpaca_id": "PA3IUYCYRWGK",
                "model": "openai/gpt-4",
                "instrument": "SPY",
                "direction": "LONG",
                "side": "buy",
                "qty": 10,
                "position_size": 0.5,
                "conviction": 1.0,
                "source": "chatgpt",
            }
        ]

        with patch("backend.pipeline.stages.execution.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.pipeline.stages.execution.MultiAlpacaManager") as mock_manager_class, \
             patch("backend.pipeline.stages.execution.get_week_id", return_value="2025-01-20"):

            # Mock MultiAlpacaManager - order fails
            mock_manager = MagicMock()
            mock_manager.place_orders_parallel = AsyncMock(return_value={
                "CHATGPT": {"error": "Insufficient buying power"}
            })
            mock_manager_class.return_value = mock_manager

            # Execute
            results = await execution_stage._place_orders_parallel(trades)

            # Verify order_failed event was logged
            failed_events = [
                call for call in mock_log_event.call_args_list
                if call[1]["event_type"] == "order_failed"
            ]
            assert len(failed_events) == 1
            assert failed_events[0][1]["account"] == "CHATGPT"


class TestIntegrationEndToEndExecution:
    """Integration test for end-to-end trade execution flow."""

    @pytest.fixture
    def trade_service(self):
        """Create a TradeService instance for testing."""
        return TradeService()

    @pytest.mark.asyncio
    async def test_end_to_end_execution(self, trade_service):
        """
        Integration test: create mock decision → execute trades → verify events logged → verify orders placed.

        This test simulates the complete execution flow:
        1. Pitch data is retrieved from database
        2. Trade is validated and executed
        3. Events are logged to execution_events table
        4. Orders are placed via Alpaca (mocked)
        5. Results are returned with success status
        """
        mock_pitch = {
            "id": 123,
            "week_id": "2025-01-20",
            "account": "CHATGPT",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
            "symbol": "SPY",
            "entry_policy": {"limit_price": 500.0},
            "exit_policy": {
                "take_profit_pct": 5.0,
                "stop_loss_pct": 2.0
            }
        }

        mock_order_result = {
            "order_id": "order_123",
            "symbol": "SPY",
            "side": "buy",
            "qty": 10,
            "limit_price": 500.0,
            "take_profit_price": 525.0,
            "stop_loss_price": 490.0,
        }

        with patch("backend.services.trade_service.find_pitch_by_id", new_callable=AsyncMock) as mock_find_pitch, \
             patch("backend.services.trade_service.log_execution_event", new_callable=AsyncMock) as mock_log_event, \
             patch("backend.services.trade_service.create_bracket_order_from_pitch") as mock_create_order, \
             patch("backend.services.trade_service.MultiAlpacaManager") as mock_manager_class:

            # Setup mocks
            mock_find_pitch.return_value = mock_pitch
            mock_create_order.return_value = mock_order_result

            # Mock MultiAlpacaManager
            mock_manager = MagicMock()
            mock_alpaca_client = MagicMock()
            mock_manager.clients = {"CHATGPT": mock_alpaca_client}
            mock_manager_class.return_value = mock_manager

            # Execute trade
            result = await trade_service.execute_trades([123])

            # Verify overall success
            assert result["status"] == "success"
            assert len(result["results"]) == 1

            # Verify trade was submitted
            trade_result = result["results"][0]
            assert trade_result["status"] == "submitted"
            assert trade_result["order_id"] == "order_123"
            assert trade_result["symbol"] == "SPY"
            assert trade_result["side"] == "buy"

            # Verify event was logged
            assert mock_log_event.called
            event_call = mock_log_event.call_args
            assert event_call[1]["event_type"] == "order_placed"
            assert event_call[1]["account"] == "CHATGPT"
            assert event_call[1]["event_data"]["order_id"] == "order_123"

            # Verify order was placed via Alpaca
            assert mock_create_order.called
            assert mock_create_order.call_args[0][1] == mock_pitch
