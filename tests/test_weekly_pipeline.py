"""Integration tests for complete weekly trading pipeline.

This module tests the end-to-end weekly pipeline workflow:
1. Market Sentiment Stage (news search + sentiment analysis)
2. Research Stage (market data + macro analysis)
3. PM Pitch Stage (5 PM models generate pitches)
4. Peer Review Stage (anonymized evaluation)
5. Chairman Stage (synthesis of final decision)
6. Execution Stage (place approved trades via Alpaca)

Tests ensure proper data flow between stages and correct handling of
various scenarios including failures and partial successes.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from backend.pipeline.weekly_pipeline import WeeklyTradingPipeline, run_weekly_pipeline
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.market_sentiment import SENTIMENT_PACK
from backend.pipeline.stages.research import RESEARCH_PACK_A, RESEARCH_PACK_B, MARKET_SNAPSHOT
from backend.pipeline.stages.pm_pitch import PM_PITCHES
from backend.pipeline.stages.peer_review import PEER_REVIEWS, LABEL_TO_MODEL
from backend.pipeline.stages.chairman import CHAIRMAN_DECISION
from backend.pipeline.stages.execution import EXECUTION_RESULT


class TestWeeklyPipelineOrchestration:
    """Test suite for weekly pipeline orchestration and data flow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_weekly_pipeline_all_stages_success(self):
        """Test successful execution of complete weekly pipeline with all stages."""
        # Mock data for each stage
        mock_sentiment = {
            "overall_market_sentiment": "bullish",
            "search_provider": "tavily",
            "articles": [],
        }

        mock_research_a = {
            "source": "perplexity",
            "structured_json": {
                "macro_regime": {"risk_mode": "risk-on"},
                "conviction_level": 1.5,
            },
            "report": "Strong macro conditions support risk assets...",
        }

        mock_research_b = {
            "source": "perplexity_alt",
            "structured_json": {
                "macro_regime": {"risk_mode": "risk-on"},
                "conviction_level": 1.3,
            },
            "report": "Alternative view confirms bullish outlook...",
        }

        mock_market_snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "prices": {"SPY": 450.25, "QQQ": 380.50, "TLT": 95.30},
        }

        mock_pm_pitches = [
            {
                "model_info": {"account": "CHATGPT"},
                "instrument": "SPY",
                "direction": "LONG",
                "conviction": 1.5,
                "thesis_bullets": ["Bullish outlook"],
            },
            {
                "model_info": {"account": "GEMINI"},
                "instrument": "QQQ",
                "direction": "LONG",
                "conviction": 1.3,
                "thesis_bullets": ["Tech strength"],
            },
        ]

        mock_peer_reviews = [
            {
                "review_id": "review-1",
                "pitch_id": "pitch-1",
                "scores": {"clarity": 8, "edge_plausibility": 7},
            }
        ]

        mock_label_to_model = {
            "Response A": "openai/gpt-4-turbo",
            "Response B": "google/gemini-pro",
        }

        mock_chairman_decision = {
            "selected_trade": {
                "instrument": "SPY",
                "direction": "LONG",
                "horizon": "1w",
            },
            "conviction": 1.5,
            "rationale": "Council consensus supports SPY long position",
        }

        mock_execution_result = {
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

        # Patch all stage execute methods
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

            # Configure stage mocks to return contexts with appropriate data
            async def sentiment_mock(ctx):
                return ctx.set(SENTIMENT_PACK, mock_sentiment)

            async def research_mock(ctx):
                return (
                    ctx.set(RESEARCH_PACK_A, mock_research_a)
                    .set(RESEARCH_PACK_B, mock_research_b)
                    .set(MARKET_SNAPSHOT, mock_market_snapshot)
                )

            async def pm_pitch_mock(ctx):
                return ctx.set(PM_PITCHES, mock_pm_pitches)

            async def peer_review_mock(ctx):
                return ctx.set(PEER_REVIEWS, mock_peer_reviews).set(
                    LABEL_TO_MODEL, mock_label_to_model
                )

            async def chairman_mock(ctx):
                return ctx.set(CHAIRMAN_DECISION, mock_chairman_decision)

            async def execution_mock(ctx):
                return ctx.set(EXECUTION_RESULT, mock_execution_result)

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            # Execute pipeline
            pipeline = WeeklyTradingPipeline(execution_mode="full")
            results = await pipeline.run()

            # Verify all stages were called
            mock_sentiment_stage.assert_called_once()
            mock_research_stage.assert_called_once()
            mock_pm_stage.assert_called_once()
            mock_peer_review_stage.assert_called_once()
            mock_chairman_stage.assert_called_once()
            mock_execution_stage.assert_called_once()

            # Verify results contain all stage outputs
            assert results["sentiment_pack"] == mock_sentiment
            assert results["research_pack_a"] == mock_research_a
            assert results["research_pack_b"] == mock_research_b
            assert results["market_snapshot"] == mock_market_snapshot
            assert results["pm_pitches"] == mock_pm_pitches
            assert results["peer_reviews"] == mock_peer_reviews
            assert results["label_to_model"] == mock_label_to_model
            assert results["chairman_decision"] == mock_chairman_decision
            assert results["execution_result"] == mock_execution_result

            # Verify metadata
            assert "week_id" in results
            assert "timestamp" in results
            assert results["execution_mode"] == "full"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_context_data_flow_between_stages(self):
        """Test that context data flows correctly from one stage to the next."""
        # This test verifies that each stage receives the data from previous stages

        stages_called = []

        async def sentiment_mock(ctx):
            stages_called.append("sentiment")
            # Verify initial context is empty
            assert ctx.get(SENTIMENT_PACK) is None
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            stages_called.append("research")
            # Verify sentiment data is available
            assert ctx.get(SENTIMENT_PACK) == {"test": "sentiment"}
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            stages_called.append("pm_pitch")
            # Verify both sentiment and research data are available
            assert ctx.get(SENTIMENT_PACK) == {"test": "sentiment"}
            assert ctx.get(RESEARCH_PACK_A) == {"test": "research"}
            assert ctx.get(MARKET_SNAPSHOT) == {"test": "snapshot"}
            return ctx.set(PM_PITCHES, [{"test": "pitch"}])

        async def peer_review_mock(ctx):
            stages_called.append("peer_review")
            # Verify all previous stage data is available
            assert ctx.get(SENTIMENT_PACK) == {"test": "sentiment"}
            assert ctx.get(RESEARCH_PACK_A) == {"test": "research"}
            assert ctx.get(PM_PITCHES) == [{"test": "pitch"}]
            return ctx.set(PEER_REVIEWS, [{"test": "review"}])

        async def chairman_mock(ctx):
            stages_called.append("chairman")
            # Verify all previous stage data is available
            assert ctx.get(PM_PITCHES) == [{"test": "pitch"}]
            assert ctx.get(PEER_REVIEWS) == [{"test": "review"}]
            return ctx.set(CHAIRMAN_DECISION, {"test": "decision"})

        async def execution_mock(ctx):
            stages_called.append("execution")
            # Verify chairman decision is available
            assert ctx.get(CHAIRMAN_DECISION) == {"test": "decision"}
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            pipeline = WeeklyTradingPipeline(execution_mode="full")
            await pipeline.run()

            # Verify all stages were called in correct order
            assert stages_called == [
                "sentiment",
                "research",
                "pm_pitch",
                "peer_review",
                "chairman",
                "execution",
            ]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_handles_research_stage_failure(self):
        """Test pipeline error handling when research stage fails."""

        async def sentiment_mock(ctx):
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            raise Exception("Research API unavailable")

        with patch(
            "backend.pipeline.stages.market_sentiment.MarketSentimentStage.execute",
            new_callable=AsyncMock,
        ) as mock_sentiment_stage, patch(
            "backend.pipeline.stages.research.ResearchStage.execute",
            new_callable=AsyncMock,
        ) as mock_research_stage:

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock

            pipeline = WeeklyTradingPipeline(execution_mode="full")
            results = await pipeline.run()

            # Verify failure is captured
            assert results["success"] is False
            assert "error" in results
            assert "Research API unavailable" in results["error"]
            assert "timestamp" in results

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_handles_pm_pitch_stage_failure(self):
        """Test pipeline error handling when PM pitch stage fails."""

        async def sentiment_mock(ctx):
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            raise Exception("PM models unavailable")

        with patch(
            "backend.pipeline.stages.market_sentiment.MarketSentimentStage.execute",
            new_callable=AsyncMock,
        ) as mock_sentiment_stage, patch(
            "backend.pipeline.stages.research.ResearchStage.execute",
            new_callable=AsyncMock,
        ) as mock_research_stage, patch(
            "backend.pipeline.stages.pm_pitch.PMPitchStage.execute",
            new_callable=AsyncMock,
        ) as mock_pm_stage:

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock

            pipeline = WeeklyTradingPipeline(execution_mode="full")
            results = await pipeline.run()

            # Verify failure is captured
            assert results["success"] is False
            assert "error" in results
            assert "PM models unavailable" in results["error"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_handles_execution_stage_failure(self):
        """Test pipeline error handling when execution stage fails."""
        # Even if execution fails, we should get error info

        mock_sentiment = {"test": "sentiment"}
        mock_research_a = {"test": "research"}
        mock_market_snapshot = {"test": "snapshot"}
        mock_pm_pitches = [{"test": "pitch"}]
        mock_peer_reviews = [{"test": "review"}]
        mock_chairman_decision = {"test": "decision"}

        async def sentiment_mock(ctx):
            return ctx.set(SENTIMENT_PACK, mock_sentiment)

        async def research_mock(ctx):
            return ctx.set(RESEARCH_PACK_A, mock_research_a).set(
                MARKET_SNAPSHOT, mock_market_snapshot
            )

        async def pm_pitch_mock(ctx):
            return ctx.set(PM_PITCHES, mock_pm_pitches)

        async def peer_review_mock(ctx):
            return ctx.set(PEER_REVIEWS, mock_peer_reviews)

        async def chairman_mock(ctx):
            return ctx.set(CHAIRMAN_DECISION, mock_chairman_decision)

        async def execution_mock(ctx):
            raise Exception("Alpaca API error")

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

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            pipeline = WeeklyTradingPipeline(execution_mode="full")
            results = await pipeline.run()

            # Verify failure is captured
            assert results["success"] is False
            assert "error" in results
            assert "Alpaca API error" in results["error"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_execution_stage_receives_correct_chairman_decision(self):
        """Test that execution stage receives chairman decision correctly."""

        chairman_decision_received = {}

        mock_chairman_decision = {
            "selected_trade": {
                "instrument": "SPY",
                "direction": "LONG",
                "horizon": "1w",
            },
            "conviction": 1.8,
            "rationale": "Strong consensus for SPY long",
        }

        async def sentiment_mock(ctx):
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            return ctx.set(PM_PITCHES, [{"test": "pitch"}])

        async def peer_review_mock(ctx):
            return ctx.set(PEER_REVIEWS, [{"test": "review"}])

        async def chairman_mock(ctx):
            return ctx.set(CHAIRMAN_DECISION, mock_chairman_decision)

        async def execution_mock(ctx):
            # Capture what execution stage receives
            chairman_decision_received["decision"] = ctx.get(CHAIRMAN_DECISION)
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            pipeline = WeeklyTradingPipeline(execution_mode="full")
            await pipeline.run()

            # Verify execution stage received correct chairman decision
            assert chairman_decision_received["decision"] == mock_chairman_decision
            assert (
                chairman_decision_received["decision"]["selected_trade"]["instrument"]
                == "SPY"
            )
            assert (
                chairman_decision_received["decision"]["selected_trade"]["direction"]
                == "LONG"
            )
            assert chairman_decision_received["decision"]["conviction"] == 1.8

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_different_execution_modes(self):
        """Test pipeline with different execution modes (chat_only, ranking, full)."""

        # Test chat_only mode - only PM pitches, no peer review or chairman
        async def sentiment_mock(ctx):
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            return ctx.set(PM_PITCHES, [{"test": "pitch"}])

        async def execution_mock(ctx):
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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
            "backend.pipeline.stages.execution.ExecutionStage.execute",
            new_callable=AsyncMock,
        ) as mock_execution_stage:

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_execution_stage.side_effect = execution_mock

            pipeline = WeeklyTradingPipeline(execution_mode="chat_only")
            results = await pipeline.run()

            # Verify correct stages were called
            mock_sentiment_stage.assert_called_once()
            mock_research_stage.assert_called_once()
            mock_pm_stage.assert_called_once()
            mock_execution_stage.assert_called_once()

            # Verify execution mode in results
            assert results["execution_mode"] == "chat_only"
            assert results["pm_pitches"] == [{"test": "pitch"}]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_with_user_query(self):
        """Test pipeline execution with custom user query."""

        user_query_received = {}

        async def sentiment_mock(ctx):
            from backend.pipeline.context import USER_QUERY

            user_query_received["query"] = ctx.get(USER_QUERY)
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            return ctx.set(PM_PITCHES, [{"test": "pitch"}])

        async def execution_mock(ctx):
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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
            "backend.pipeline.stages.execution.ExecutionStage.execute",
            new_callable=AsyncMock,
        ) as mock_execution_stage:

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_execution_stage.side_effect = execution_mock

            custom_query = "What is the outlook for tech stocks this week?"
            pipeline = WeeklyTradingPipeline(execution_mode="chat_only")
            await pipeline.run(user_query=custom_query)

            # Verify user query was passed to stages
            assert user_query_received["query"] == custom_query

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_run_weekly_pipeline_convenience_function(self):
        """Test the convenience function run_weekly_pipeline()."""

        async def sentiment_mock(ctx):
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            return ctx.set(PM_PITCHES, [{"test": "pitch"}])

        async def peer_review_mock(ctx):
            return ctx.set(PEER_REVIEWS, [{"test": "review"}])

        async def chairman_mock(ctx):
            return ctx.set(CHAIRMAN_DECISION, {"test": "decision"})

        async def execution_mock(ctx):
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            # Test convenience function
            results = await run_weekly_pipeline()

            # Verify pipeline executed
            assert "week_id" in results
            assert "timestamp" in results
            assert results["sentiment_pack"] == {"test": "sentiment"}
            assert results["pm_pitches"] == [{"test": "pitch"}]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_stage_order_is_correct(self):
        """Test that pipeline stages execute in the correct order."""

        execution_order = []

        async def sentiment_mock(ctx):
            execution_order.append(1)
            return ctx.set(SENTIMENT_PACK, {"test": "sentiment"})

        async def research_mock(ctx):
            execution_order.append(2)
            return ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )

        async def pm_pitch_mock(ctx):
            execution_order.append(3)
            return ctx.set(PM_PITCHES, [{"test": "pitch"}])

        async def peer_review_mock(ctx):
            execution_order.append(4)
            return ctx.set(PEER_REVIEWS, [{"test": "review"}])

        async def chairman_mock(ctx):
            execution_order.append(5)
            return ctx.set(CHAIRMAN_DECISION, {"test": "decision"})

        async def execution_mock(ctx):
            execution_order.append(6)
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_peer_review_stage.side_effect = peer_review_mock
            mock_chairman_stage.side_effect = chairman_mock
            mock_execution_stage.side_effect = execution_mock

            pipeline = WeeklyTradingPipeline(execution_mode="full")
            await pipeline.run()

            # Verify correct execution order
            assert execution_order == [1, 2, 3, 4, 5, 6]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pipeline_context_immutability(self):
        """Test that pipeline context remains immutable through stages."""

        original_context_id = None
        context_ids = []

        async def sentiment_mock(ctx):
            nonlocal original_context_id
            original_context_id = id(ctx)
            context_ids.append(id(ctx))
            new_ctx = ctx.set(SENTIMENT_PACK, {"test": "sentiment"})
            # Verify new context is different object
            assert id(new_ctx) != id(ctx)
            return new_ctx

        async def research_mock(ctx):
            context_ids.append(id(ctx))
            # Verify context changed from original
            assert id(ctx) != original_context_id
            new_ctx = ctx.set(RESEARCH_PACK_A, {"test": "research"}).set(
                MARKET_SNAPSHOT, {"test": "snapshot"}
            )
            assert id(new_ctx) != id(ctx)
            return new_ctx

        async def pm_pitch_mock(ctx):
            context_ids.append(id(ctx))
            new_ctx = ctx.set(PM_PITCHES, [{"test": "pitch"}])
            assert id(new_ctx) != id(ctx)
            return new_ctx

        async def execution_mock(ctx):
            context_ids.append(id(ctx))
            return ctx.set(EXECUTION_RESULT, {"executed": True})

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
            "backend.pipeline.stages.execution.ExecutionStage.execute",
            new_callable=AsyncMock,
        ) as mock_execution_stage:

            mock_sentiment_stage.side_effect = sentiment_mock
            mock_research_stage.side_effect = research_mock
            mock_pm_stage.side_effect = pm_pitch_mock
            mock_execution_stage.side_effect = execution_mock

            pipeline = WeeklyTradingPipeline(execution_mode="chat_only")
            await pipeline.run()

            # Verify each stage received a different context object
            assert len(set(context_ids)) == len(context_ids)
