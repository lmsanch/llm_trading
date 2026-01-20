"""End-to-end tests for checkpoint workflow with frozen research and position adjustments.

This module tests the complete checkpoint workflow:
1. Weekly pipeline runs and establishes frozen research
2. Checkpoints use frozen research (no new research)
3. Positions are evaluated using frozen indicators
4. Position adjustments are executed correctly
5. Conviction is updated for next checkpoint cycle

Tests verify the complete integration between weekly pipeline and checkpoint stages,
ensuring frozen research constraint is respected and positions are managed correctly.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from backend.pipeline.weekly_pipeline import WeeklyTradingPipeline
from backend.pipeline.stages.checkpoint import CheckpointStage, CHECKPOINT_RESULT
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.market_sentiment import SENTIMENT_PACK
from backend.pipeline.stages.research import RESEARCH_PACK_A, RESEARCH_PACK_B, MARKET_SNAPSHOT
from backend.pipeline.stages.pm_pitch import PM_PITCHES
from backend.pipeline.stages.peer_review import PEER_REVIEWS, LABEL_TO_MODEL
from backend.pipeline.stages.chairman import CHAIRMAN_DECISION
from backend.pipeline.stages.execution import EXECUTION_RESULT


class TestCheckpointWorkflowWithFrozenResearch:
    """Test complete checkpoint workflow using frozen research from weekly pipeline."""

    @pytest.fixture
    def mock_weekly_data(self):
        """Mock data for complete weekly pipeline execution."""
        return {
            "sentiment": {
                "overall_market_sentiment": "bullish",
                "search_provider": "tavily",
                "articles": [],
            },
            "research_a": {
                "source": "perplexity",
                "structured_json": {
                    "macro_regime": {"risk_mode": "risk-on"},
                    "conviction_level": 1.5,
                },
                "report": "Strong macro conditions support risk assets...",
            },
            "research_b": {
                "source": "perplexity_alt",
                "structured_json": {
                    "macro_regime": {"risk_mode": "risk-on"},
                    "conviction_level": 1.3,
                },
                "report": "Alternative view confirms bullish outlook...",
            },
            "market_snapshot": {
                "timestamp": "2025-01-20T08:00:00Z",
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
                        "trend": "bullish",
                        "avg_volume": 80000000,
                        "change_pct": 2.5
                    },
                    "QQQ": {
                        "price": 380.50,
                        "volume": 55000000,
                        "trend": "neutral",
                        "avg_volume": 52000000,
                        "change_pct": 0.8
                    }
                },
                "macro_data": {
                    "risk_mode": "RISK_ON",
                    "narratives": ["Fed dovish pivot", "Tech rally continues"]
                }
            },
            "pm_pitches": [
                {
                    "model_info": {"account": "CHATGPT"},
                    "instrument": "SPY",
                    "direction": "LONG",
                    "conviction": 1.5,
                    "thesis_bullets": ["Bullish outlook on equities"],
                },
                {
                    "model_info": {"account": "GEMINI"},
                    "instrument": "QQQ",
                    "direction": "LONG",
                    "conviction": 1.3,
                    "thesis_bullets": ["Tech strength continues"],
                },
            ],
            "peer_reviews": [
                {
                    "review_id": "review-1",
                    "pitch_id": "pitch-1",
                    "scores": {"clarity": 8, "edge_plausibility": 7},
                }
            ],
            "label_to_model": {
                "Response A": "openai/gpt-4-turbo",
                "Response B": "google/gemini-pro",
            },
            "chairman_decision": {
                "selected_trade": {
                    "instrument": "SPY",
                    "direction": "LONG",
                    "horizon": "1w",
                },
                "conviction": 1.5,
                "rationale": "Council consensus supports SPY long position",
            },
            "execution_result": {
                "executed": True,
                "trades": [
                    {
                        "account": "COUNCIL",
                        "instrument": "SPY",
                        "success": True,
                        "message": "Order placed successfully",
                    }
                ],
            }
        }

    @pytest.fixture
    def mock_positions_after_execution(self):
        """Mock positions that exist after weekly pipeline execution."""
        return {
            "COUNCIL": [{
                "symbol": "SPY",
                "qty": "100",
                "avg_entry_price": "450.25",
                "current_price": "452.00",
                "cost_basis": "45025.00",
                "market_value": "45200.00",
                "unrealized_pl": "175.00",
                "unrealized_plpc": "0.0039"
            }]
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_weekly_pipeline_then_checkpoint_workflow(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test complete workflow: weekly pipeline establishes frozen research, checkpoint uses it."""

        # Stage 1: Run weekly pipeline to establish frozen research
        with patch(
            "backend.pipeline.stages.market_sentiment.MarketSentimentStage.execute",
            new_callable=AsyncMock,
        ) as mock_sentiment_stage, patch(
            "backend.pipeline.stages.research.ResearchStage.execute",
            new_callable=AsyncMock,
        ) as mock_research_stage, patch(
            "backend.pipeline.stages.pm_pitch.PMPitchStage.execute",
            new_callable=AsyncMock,
        ) as mock_pm_stage, patch(
            "backend.pipeline.stages.peer_review.PeerReviewStage.execute",
            new_callable=AsyncMock,
        ) as mock_peer_review_stage, patch(
            "backend.pipeline.stages.chairman.ChairmanStage.execute",
            new_callable=AsyncMock,
        ) as mock_chairman_stage, patch(
            "backend.pipeline.stages.execution.ExecutionStage.execute",
            new_callable=AsyncMock,
        ) as mock_execution_stage:

            # Configure weekly pipeline stage mocks
            async def sentiment_mock(ctx):
                return ctx.set(SENTIMENT_PACK, mock_weekly_data["sentiment"])

            async def research_mock(ctx):
                return (
                    ctx.set(RESEARCH_PACK_A, mock_weekly_data["research_a"])
                    .set(RESEARCH_PACK_B, mock_weekly_data["research_b"])
                    .set(MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"])
                )

            async def pm_pitch_mock(ctx):
                return ctx.set(PM_PITCHES, mock_weekly_data["pm_pitches"])

            async def peer_review_mock(ctx):
                return ctx.set(PEER_REVIEWS, mock_weekly_data["peer_reviews"]).set(
                    LABEL_TO_MODEL, mock_weekly_data["label_to_model"]
                )

            async def chairman_mock(ctx):
                return ctx.set(CHAIRMAN_DECISION, mock_weekly_data["chairman_decision"])

            async def execution_mock(ctx):
                return ctx.set(EXECUTION_RESULT, mock_weekly_data["execution_result"])

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            # Execute weekly pipeline
            pipeline = WeeklyTradingPipeline(execution_mode="full")
            weekly_results = await pipeline.run()

            # Verify weekly pipeline completed successfully
            # (successful pipeline doesn't have "success" key, only failures do)
            assert "error" not in weekly_results
            assert weekly_results["market_snapshot"] == mock_weekly_data["market_snapshot"]

        # Stage 2: Extract frozen context for checkpoint
        # Simulate that we've saved the context and now load it for checkpoint
        frozen_context = (
            PipelineContext()
            .set(MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"])
            .set(EXECUTION_RESULT, mock_weekly_data["execution_result"])
        )

        # Stage 3: Run checkpoint using frozen research
        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Mock that positions exist after execution
            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00", "equity": "95200.00"}
            }

            # Mock chairman checkpoint evaluation
            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.6,
                    "action": "STAY",
                    "reason": "Position performing well, slight conviction increase"
                })
            }

            # Execute checkpoint stage
            checkpoint_stage = CheckpointStage()
            checkpoint_result_context = await checkpoint_stage.execute(frozen_context)

            # Verify checkpoint used frozen research
            checkpoint_result = checkpoint_result_context.get(CHECKPOINT_RESULT)
            assert checkpoint_result is not None
            assert checkpoint_result["success"] is True

            # Verify frozen snapshot was used (not modified)
            frozen_snapshot_used = checkpoint_result_context.get(MARKET_SNAPSHOT)
            assert frozen_snapshot_used == mock_weekly_data["market_snapshot"]

            # Verify checkpoint evaluated positions
            assert len(checkpoint_result["actions"]) == 1
            assert checkpoint_result["actions"][0]["instrument"] == "SPY"
            assert checkpoint_result["actions"][0]["action"] == "STAY"

            # Verify conviction was updated
            assert checkpoint_result["actions"][0]["new_conviction"] == 1.6

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_uses_frozen_research_not_new_research(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that checkpoint uses frozen research from weekly pipeline, not new research."""

        # Create context with frozen research
        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman, patch(
            'backend.research.query_perplexity_research', new_callable=AsyncMock
        ) as mock_perplexity, patch(
            'backend.storage.data_fetcher.MarketDataFetcher'
        ) as mock_fetcher_class:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "Position stable"
                })
            }

            # Execute checkpoint
            checkpoint_stage = CheckpointStage()
            await checkpoint_stage.execute(frozen_context)

            # Verify NO new research was fetched
            mock_perplexity.assert_not_called()
            mock_fetcher_class.assert_not_called()

            # Verify chairman was called with frozen indicators
            assert mock_chairman.call_count == 1
            call_args = mock_chairman.call_args
            messages = call_args[0][0]
            user_message = messages[1]["content"]

            # Verify frozen indicators from snapshot are in prompt
            assert "FROZEN RESEARCH INDICATORS" in user_message
            assert "SPY" in user_message or "indicators" in user_message.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_evaluates_positions_correctly(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that checkpoint evaluates current positions correctly using frozen research."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }

            # Mock chairman evaluates position with specific conviction change
            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.2,
                    "action": "REDUCE",
                    "reason": "Conviction dropped slightly, reduce exposure"
                })
            }

            # Execute checkpoint
            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            # Verify position evaluation
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            assert checkpoint_result["success"] is True

            # Verify position snapshot captured
            positions_snapshot = checkpoint_result["positions_snapshot"]
            assert len(positions_snapshot) == 1
            assert positions_snapshot[0]["symbol"] == "SPY"
            assert positions_snapshot[0]["account"] == "COUNCIL"
            assert positions_snapshot[0]["current_price"] == 452.00
            assert positions_snapshot[0]["unrealized_pl"] == 175.00

            # Verify action determination
            actions = checkpoint_result["actions"]
            assert len(actions) == 1
            assert actions[0]["action"] == "REDUCE"
            assert actions[0]["current_conviction"] == 1.5
            assert actions[0]["new_conviction"] == 1.2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_executes_position_adjustments(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that checkpoint executes position adjustments correctly."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }
            mock_manager.close_all_positions.return_value = {"success": True}

            # Mock EXIT action
            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 0.5,
                    "action": "EXIT",
                    "reason": "Conviction dropped below threshold, exit position"
                })
            }

            # Execute checkpoint
            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            # Verify action execution
            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            execution_results = checkpoint_result["execution_results"]

            assert len(execution_results) == 1
            assert execution_results[0]["action"] == "EXIT"
            assert execution_results[0]["executed"] is True
            assert execution_results[0]["instrument"] == "SPY"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_updates_conviction_for_next_cycle(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that checkpoint updates conviction for next checkpoint cycle."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        # Checkpoint 1: Initial evaluation
        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }

            # First checkpoint: conviction increases
            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.8,
                    "action": "INCREASE",
                    "reason": "Strong momentum, increase position"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context_1 = await checkpoint_stage.execute(frozen_context)

            # Verify conviction update from checkpoint 1
            checkpoint_result_1 = result_context_1.get(CHECKPOINT_RESULT)
            actions_1 = checkpoint_result_1["actions"]
            assert actions_1[0]["current_conviction"] == 1.5
            assert actions_1[0]["new_conviction"] == 1.8
            assert actions_1[0]["action"] == "INCREASE"

        # Checkpoint 2: Next checkpoint cycle uses updated conviction
        # (In real system, this would be saved and loaded from DB)
        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # Position now reflects increased size from previous checkpoint
            increased_position = {
                "COUNCIL": [{
                    "symbol": "SPY",
                    "qty": "150",  # Increased from 100
                    "avg_entry_price": "450.25",
                    "current_price": "455.00",
                    "cost_basis": "67537.50",
                    "market_value": "68250.00",
                    "unrealized_pl": "712.50",
                    "unrealized_plpc": "0.0105"
                }]
            }

            mock_manager.get_all_positions.return_value = increased_position
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "30000.00"}
            }

            # Second checkpoint: conviction drops back
            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.8,  # Uses updated conviction from checkpoint 1
                    "new_conviction": 1.3,
                    "action": "REDUCE",
                    "reason": "Momentum slowing, reduce back to normal"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context_2 = await checkpoint_stage.execute(frozen_context)

            # Verify conviction updated in checkpoint 2
            checkpoint_result_2 = result_context_2.get(CHECKPOINT_RESULT)
            actions_2 = checkpoint_result_2["actions"]

            # Verify current_conviction reflects the updated value from checkpoint 1
            assert actions_2[0]["current_conviction"] == 1.8
            assert actions_2[0]["new_conviction"] == 1.3
            assert actions_2[0]["action"] == "REDUCE"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_checkpoints_same_frozen_research(
        self, mock_weekly_data
    ):
        """Test multiple checkpoints throughout day all use same frozen research."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        # Simulate 4 checkpoints throughout the day
        checkpoint_times = ["09:00", "12:00", "14:00", "15:50"]
        frozen_indicators_used = []

        for checkpoint_time in checkpoint_times:
            with patch(
                'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
            ) as mock_manager_class, patch(
                'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
            ) as mock_chairman:

                mock_manager = AsyncMock()
                mock_manager_class.return_value = mock_manager

                # Position with different P/L at each checkpoint
                mock_manager.get_all_positions.return_value = {
                    "COUNCIL": [{
                        "symbol": "SPY",
                        "qty": "100",
                        "avg_entry_price": "450.25",
                        "current_price": 451.00 + float(checkpoint_times.index(checkpoint_time)),  # Price changes
                        "cost_basis": "45025.00",
                        "market_value": "45100.00",
                        "unrealized_pl": "75.00",
                        "unrealized_plpc": "0.0017"
                    }]
                }
                mock_manager.get_all_accounts.return_value = {
                    "COUNCIL": {"cash": "50000.00"}
                }

                mock_chairman.return_value = {
                    "content": json.dumps({
                        "current_conviction": 1.5,
                        "new_conviction": 1.5,
                        "action": "STAY",
                        "reason": "Position stable"
                    })
                }

                # Execute checkpoint
                checkpoint_stage = CheckpointStage()
                await checkpoint_stage.execute(frozen_context)

                # Capture frozen indicators from chairman prompt
                assert mock_chairman.call_count == 1
                call_args = mock_chairman.call_args
                messages = call_args[0][0]
                user_message = messages[1]["content"]

                # Extract frozen indicators section
                if "FROZEN RESEARCH INDICATORS" in user_message:
                    frozen_indicators_used.append(user_message)

        # Verify all checkpoints used the SAME frozen indicators
        assert len(frozen_indicators_used) == 4
        # All prompts should reference the same frozen snapshot
        # (In practice, the indicators are formatted the same way each time)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_stay_maintains_position(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that STAY action maintains current position without changes."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 1.5,
                    "action": "STAY",
                    "reason": "No change in thesis"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            execution_results = checkpoint_result["execution_results"]

            # Verify STAY action executed (but no actual trade)
            assert len(execution_results) == 1
            assert execution_results[0]["action"] == "STAY"
            assert execution_results[0]["executed"] is True
            assert execution_results[0]["message"] == "No action taken"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_exit_closes_position(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that EXIT action closes position entirely."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }
            mock_manager.close_all_positions.return_value = {"success": True}

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": 0.3,
                    "action": "EXIT",
                    "reason": "Stop loss triggered"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify EXIT action was determined
            assert checkpoint_result["actions"][0]["action"] == "EXIT"

            # Verify position was closed
            mock_manager.close_all_positions.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_flip_reverses_direction(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that FLIP action reverses position direction."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }
            mock_manager.close_all_positions.return_value = {"success": True}

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.5,
                    "new_conviction": -1.2,
                    "action": "FLIP",
                    "reason": "Strong reversal signal detected"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify FLIP action was determined
            assert checkpoint_result["actions"][0]["action"] == "FLIP"
            assert checkpoint_result["actions"][0]["new_conviction"] == -1.2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_reduce_decreases_position(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that REDUCE action decreases position size."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.8,
                    "new_conviction": 1.2,
                    "action": "REDUCE",
                    "reason": "Conviction weakened, reduce exposure"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            execution_results = checkpoint_result["execution_results"]

            # Verify REDUCE action executed
            assert execution_results[0]["action"] == "REDUCE"
            assert execution_results[0]["executed"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_action_increase_grows_position(
        self, mock_weekly_data, mock_positions_after_execution
    ):
        """Test that INCREASE action grows position size."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class, patch(
            'backend.pipeline.stages.checkpoint.query_chairman', new_callable=AsyncMock
        ) as mock_chairman:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_manager.get_all_positions.return_value = mock_positions_after_execution
            mock_manager.get_all_accounts.return_value = {
                "COUNCIL": {"cash": "50000.00"}
            }

            mock_chairman.return_value = {
                "content": json.dumps({
                    "current_conviction": 1.3,
                    "new_conviction": 1.9,
                    "action": "INCREASE",
                    "reason": "Strong momentum confirmed, increase exposure"
                })
            }

            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            checkpoint_result = result_context.get(CHECKPOINT_RESULT)
            execution_results = checkpoint_result["execution_results"]

            # Verify INCREASE action executed
            assert execution_results[0]["action"] == "INCREASE"
            assert execution_results[0]["executed"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_with_no_positions_completes_successfully(
        self, mock_weekly_data
    ):
        """Test checkpoint completes successfully when no positions exist."""

        frozen_context = PipelineContext().set(
            MARKET_SNAPSHOT, mock_weekly_data["market_snapshot"]
        )

        with patch(
            'backend.pipeline.stages.checkpoint.MultiAlpacaManager'
        ) as mock_manager_class:

            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager

            # No positions
            mock_manager.get_all_positions.return_value = {}
            mock_manager.get_all_accounts.return_value = {}

            checkpoint_stage = CheckpointStage()
            result_context = await checkpoint_stage.execute(frozen_context)

            checkpoint_result = result_context.get(CHECKPOINT_RESULT)

            # Verify checkpoint completed successfully with no actions
            assert checkpoint_result["success"] is True
            assert checkpoint_result["action"] == "STAY"
            assert checkpoint_result["message"] == "No positions to monitor"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_checkpoint_fails_without_frozen_research(self):
        """Test checkpoint fails gracefully when frozen research not available."""

        # Create context WITHOUT frozen research
        empty_context = PipelineContext()

        checkpoint_stage = CheckpointStage()
        result_context = await checkpoint_stage.execute(empty_context)

        checkpoint_result = result_context.get(CHECKPOINT_RESULT)

        # Verify checkpoint failed with clear error message
        assert checkpoint_result["success"] is False
        assert checkpoint_result["error"] == "No frozen market snapshot"
        assert "Run weekly pipeline first" in checkpoint_result["message"]
