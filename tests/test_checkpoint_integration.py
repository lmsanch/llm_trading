"""Integration tests for CheckpointStage execution workflow.

This module tests the complete checkpoint stage workflow with mocked market
data, positions, and API calls. Tests cover:
- Position snapshotting from Alpaca
- Conviction evaluation with chairman queries
- Action determination based on conviction changes
- Position adjustment execution
- Frozen research constraint enforcement
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from backend.pipeline.stages.checkpoint import CheckpointStage, CheckpointAction, CHECKPOINT_RESULT
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.research import MARKET_SNAPSHOT


class TestCheckpointStageExecution:
    """Integration tests for full CheckpointStage execution workflow."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    @pytest.fixture
    def sample_market_snapshot(self):
        """Sample frozen market snapshot for testing."""
        return {
            "timestamp": "2025-01-20T09:00:00Z",
            "week_id": "2025-01-20",
            "prices": {
                "SPY": 450.25,
                "QQQ": 380.50,
                "TLT": 95.30,
            },
            "indicators": {
                "SPY": {
                    "price": 450.25,
                    "volume": 85000000,
                    "trend": "bullish"
                },
                "QQQ": {
                    "price": 380.50,
                    "volume": 55000000,
                    "trend": "neutral"
                }
            }
        }

    @pytest.fixture
    def sample_positions_raw(self):
        """Sample raw positions from Alpaca API for testing."""
        return [
            {
                "symbol": "SPY",
                "qty": "100",
                "avg_entry_price": "440.00",
                "current_price": "450.25",
                "cost_basis": "44000.00",
                "market_value": "45025.00",
                "unrealized_pl": "1025.00",
                "unrealized_plpc": "0.0233"
            },
            {
                "symbol": "QQQ",
                "qty": "50",
                "avg_entry_price": "370.00",
                "current_price": "380.50",
                "cost_basis": "18500.00",
                "market_value": "19025.00",
                "unrealized_pl": "525.00",
                "unrealized_plpc": "0.0284"
            }
        ]

    @pytest.fixture
    def sample_accounts(self):
        """Sample account data from Alpaca."""
        return {
            "Council": {
                "account_number": "COUNCIL123",
                "cash": "50000.00",
                "portfolio_value": "95025.00",
                "equity": "95025.00"
            },
            "GPT-5.1": {
                "account_number": "GPT123",
                "cash": "80000.00",
                "portfolio_value": "99025.00",
                "equity": "99025.00"
            }
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_successful_checkpoint_execution_with_positions(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test successful checkpoint execution with open positions."""
        # Create context with frozen market snapshot
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        # Mock chairman responses for each position
        mock_chairman_responses = [
            # Council SPY position - STAY
            {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "Position performing well, no change needed"
                })
            },
            # GPT-5.1 QQQ position - REDUCE
            {
                "content": json.dumps({
                    "current_conviction": 1.8,
                    "new_conviction": 1.2,
                    "action": "REDUCE",
                    "reason": "Conviction weakened, reducing exposure"
                })
            }
        ]

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            # Mock MultiAlpacaManager methods
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Mock get_all_positions - return raw Alpaca format
            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]],
                "GPT-5.1": [sample_positions_raw[1]]
            }

            # Mock get_all_accounts
            mock_manager.get_all_accounts.return_value = sample_accounts

            # Mock close_all_positions
            mock_manager.close_all_positions.return_value = {"success": True}

            # Mock chairman responses
            mock_chairman.side_effect = mock_chairman_responses

            # Execute checkpoint stage
            result_context = await checkpoint_stage.execute(context)

            # Verify checkpoint result exists
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            assert checkpoint_result is not None
            assert checkpoint_result["success"] is True

            # Verify result structure
            assert "week_id" in checkpoint_result
            assert "timestamp" in checkpoint_result
            assert "checkpoint_time" in checkpoint_result
            assert "positions_snapshot" in checkpoint_result
            assert "actions" in checkpoint_result
            assert "execution_results" in checkpoint_result

            # Verify positions were snapshotted
            assert len(checkpoint_result["positions_snapshot"]) == 2

            # Verify actions were determined
            actions = checkpoint_result["actions"]
            assert len(actions) == 2

            # Verify first action (STAY)
            assert actions[0]["action"] == "STAY"
            assert actions[0]["account"] == "Council"
            assert actions[0]["instrument"] == "SPY"

            # Verify second action (REDUCE)
            assert actions[1]["action"] == "REDUCE"
            assert actions[1]["account"] == "GPT-5.1"
            assert actions[1]["instrument"] == "QQQ"

            # Verify chairman was called for each position
            assert mock_chairman.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_with_no_positions(self, checkpoint_stage, sample_market_snapshot):
        """Test checkpoint execution when there are no open positions."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class:
            # Mock MultiAlpacaManager with no positions
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_all_positions.return_value = {}
            mock_manager.get_all_accounts.return_value = {}

            # Execute checkpoint stage
            result_context = await checkpoint_stage.execute(context)

            # Verify checkpoint result
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            assert checkpoint_result is not None
            assert checkpoint_result["success"] is True
            assert checkpoint_result["action"] == "STAY"
            assert checkpoint_result["message"] == "No positions to monitor"

            # Verify no accounts/positions were called beyond initial check
            mock_manager.get_all_positions.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_without_frozen_snapshot(self, checkpoint_stage):
        """Test checkpoint fails gracefully when no frozen market snapshot exists."""
        # Create context WITHOUT market snapshot
        context = PipelineContext()

        # Execute checkpoint stage
        result_context = await checkpoint_stage.execute(context)

        # Verify checkpoint result indicates failure
        checkpoint_result = result_context.get(CHECKPOINT_RESULT)
        assert checkpoint_result is not None
        assert checkpoint_result["success"] is False
        assert "error" in checkpoint_result
        assert checkpoint_result["error"] == "No frozen market snapshot"
        assert "Run weekly pipeline first" in checkpoint_result["message"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_execution_exit(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint executes EXIT action correctly."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        # Mock chairman response for EXIT action
        mock_chairman_response = {
            "content": json.dumps({
                "current_conviction": 1.5,
                "new_conviction": 0.5,
                "action": "EXIT",
                "reason": "Conviction dropped below threshold"
            })
        }

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Return only one position
            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}
            mock_manager.close_all_positions.return_value = {"success": True, "message": "Position closed"}

            mock_chairman.return_value = mock_chairman_response

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify EXIT action was determined
            actions = checkpoint_result["actions"]
            assert len(actions) == 1
            assert actions[0]["action"] == "EXIT"

            # Verify execution results show EXIT was executed
            execution_results = checkpoint_result["execution_results"]
            assert len(execution_results) == 1
            assert execution_results[0]["action"] == "EXIT"
            assert execution_results[0]["executed"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_execution_flip(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint executes FLIP action correctly."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        # Mock chairman response for FLIP action
        mock_chairman_response = {
            "content": json.dumps({
                "current_conviction": 1.5,
                "new_conviction": -1.0,
                "action": "FLIP",
                "reason": "Strong reversal signal detected"
            })
        }

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}
            mock_manager.close_all_positions.return_value = {"success": True}

            mock_chairman.return_value = mock_chairman_response

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify FLIP action was determined
            actions = checkpoint_result["actions"]
            assert len(actions) == 1
            assert actions[0]["action"] == "FLIP"

            # Verify execution results show FLIP was executed
            execution_results = checkpoint_result["execution_results"]
            assert len(execution_results) == 1
            assert execution_results[0]["action"] == "FLIP"
            assert execution_results[0]["executed"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_multiple_accounts_different_actions(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint handles multiple accounts with different actions."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        # Create 3 positions with different actions
        positions = [
            sample_positions_raw[0],  # Council - STAY
            sample_positions_raw[1],  # GPT-5.1 - REDUCE
            {
                "symbol": "TLT",
                "qty": "30",
                "avg_entry_price": "100.00",
                "current_price": "95.30",
                "cost_basis": "3000.00",
                "market_value": "2859.00",
                "unrealized_pl": "-141.00",
                "unrealized_plpc": "-0.047"
            }  # Gemini - EXIT
        ]

        mock_chairman_responses = [
            {"content": json.dumps({
                "current_conviction": 1.5,
                "new_conviction": 1.5,
                "action": "STAY",
                "reason": "Position good"
            })},
            {"content": json.dumps({
                "current_conviction": 1.8,
                "new_conviction": 1.2,
                "action": "REDUCE",
                "reason": "Reducing exposure"
            })},
            {"content": json.dumps({
                "current_conviction": 1.0,
                "new_conviction": 0.3,
                "action": "EXIT",
                "reason": "Stop loss triggered"
            })}
        ]

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [positions[0]],
                "GPT-5.1": [positions[1]],
                "Gemini": [positions[2]]
            }
            mock_manager.get_all_accounts.return_value = sample_accounts
            mock_manager.close_all_positions.return_value = {"success": True}

            mock_chairman.side_effect = mock_chairman_responses

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify all 3 actions were determined
            actions = checkpoint_result["actions"]
            assert len(actions) == 3

            # Verify action types
            action_types = [a["action"] for a in actions]
            assert "STAY" in action_types
            assert "REDUCE" in action_types
            assert "EXIT" in action_types

            # Verify execution results
            execution_results = checkpoint_result["execution_results"]
            assert len(execution_results) == 3

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_chairman_query_uses_frozen_indicators(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test that checkpoint uses frozen indicators in chairman query."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "Good"
                })
            }

            # Execute checkpoint
            await checkpoint_stage.execute(context)

            # Verify chairman was called
            assert mock_chairman.call_count == 1

            # Verify chairman query includes frozen indicators
            call_args = mock_chairman.call_args
            messages = call_args[0][0]

            # Check user message contains frozen indicators reference
            user_message = messages[1]["content"]
            assert "FROZEN RESEARCH INDICATORS" in user_message
            assert "SPY" in user_message or "indicators" in user_message.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_position_snapshot_correctness(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test that checkpoint correctly snapshots position data."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]],
                "GPT-5.1": [sample_positions_raw[1]]
            }
            mock_manager.get_all_accounts.return_value = sample_accounts

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "Good"
                })
            }

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify positions_snapshot has correct structure
            positions_snapshot = checkpoint_result["positions_snapshot"]
            assert len(positions_snapshot) == 2

            # Verify first position data
            pos1 = positions_snapshot[0]
            assert pos1["account"] == "Council"
            assert pos1["symbol"] == "SPY"
            assert pos1["qty"] == "100"
            assert pos1["side"] == "long"
            assert pos1["current_price"] == 450.25
            assert pos1["unrealized_pl"] == 1025.00

            # Verify second position data
            pos2 = positions_snapshot[1]
            assert pos2["account"] == "GPT-5.1"
            assert pos2["symbol"] == "QQQ"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_conviction_calculation_from_chairman(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test conviction change calculation from chairman response."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        # Chairman response with explicit conviction values
        mock_chairman_response = {
            "content": json.dumps({
                "current_conviction": 1.8,
                "new_conviction": 1.1,
                "action": "REDUCE",
                "reason": "Conviction dropped by 0.7"
            })
        }

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}

            mock_chairman.return_value = mock_chairman_response

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify conviction values are correct
            actions = checkpoint_result["actions"]
            assert len(actions) == 1
            assert actions[0]["current_conviction"] == 1.8
            assert actions[0]["new_conviction"] == 1.1

            # Verify conviction drop triggered REDUCE
            conviction_drop = actions[0]["current_conviction"] - actions[0]["new_conviction"]
            assert conviction_drop == 0.7
            assert conviction_drop >= CheckpointStage.CONVICTION_THRESHOLDS["reduce"]
            assert actions[0]["action"] == "REDUCE"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_handles_chairman_api_failure(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint handles chairman API failure gracefully."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}

            # Chairman returns None (API failure)
            mock_chairman.return_value = None

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify checkpoint still succeeds with default action
            assert checkpoint_result["success"] is True

            # Verify default STAY action was used
            actions = checkpoint_result["actions"]
            assert len(actions) == 1
            assert actions[0]["action"] == "STAY"
            assert "No chairman response" in actions[0]["reason"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_execution_result_structure(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint execution results have correct structure."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        mock_chairman_response = {
            "content": json.dumps({
                "current_conviction": 1.5,
                "new_conviction": 1.5,
                "action": "STAY",
                "reason": "Position good"
            })
        }

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}

            mock_chairman.return_value = mock_chairman_response

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify execution results structure
            execution_results = checkpoint_result["execution_results"]
            assert isinstance(execution_results, list)
            assert len(execution_results) == 1

            result = execution_results[0]
            assert "account" in result
            assert "instrument" in result
            assert "action" in result
            assert "executed" in result
            assert "message" in result

            # Verify values
            assert result["account"] == "Council"
            assert result["instrument"] == "SPY"
            assert result["action"] == "STAY"
            assert result["executed"] is True
            assert result["message"] == "No action taken"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_timestamp_and_metadata(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint result includes proper timestamp and metadata."""
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "Good"
                })
            }

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify timestamp fields exist
            assert "timestamp" in checkpoint_result
            assert "checkpoint_time" in checkpoint_result
            assert "week_id" in checkpoint_result

            # Verify timestamp is valid ISO format
            timestamp = checkpoint_result["timestamp"]
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            # Verify checkpoint_time is in HH:MM format
            checkpoint_time = checkpoint_result["checkpoint_time"]
            assert ":" in checkpoint_time
            parts = checkpoint_time.split(":")
            assert len(parts) == 2
            assert len(parts[0]) == 2  # HH
            assert len(parts[1]) == 2  # MM

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_uses_week_id_from_frozen_snapshot(
        self, checkpoint_stage, sample_market_snapshot, sample_positions_raw, sample_accounts
    ):
        """Test checkpoint uses week_id from frozen market snapshot."""
        # Set specific week_id in snapshot
        sample_market_snapshot["week_id"] = "2025-01-13"
        context = PipelineContext().set(MARKET_SNAPSHOT, sample_market_snapshot)

        with patch('backend.pipeline.stages.checkpoint.MultiAlpacaManager') as mock_manager_class, \
             patch('backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock) as mock_chairman, \
             patch('backend.pipeline.stages.checkpoint.get_week_id') as mock_get_week_id:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = {
                "Council": [sample_positions_raw[0]]
            }
            mock_manager.get_all_accounts.return_value = {"Council": sample_accounts["Council"]}

            # Mock get_week_id to return current week
            mock_get_week_id.return_value = "2025-01-13"

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "Good"
                })
            }

            # Execute checkpoint
            result_context = await checkpoint_stage.execute(context)
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify week_id matches
            assert checkpoint_result["week_id"] == "2025-01-13"
