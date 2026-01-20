"""Integration tests for run_full_council.

This module tests the complete 3-stage council workflow with all stages
orchestrated together. Tests ensure proper data flow between stages and
correct handling of various scenarios.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.council import run_full_council


class TestRunFullCouncil:
    """Integration test suite for run_full_council function."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_successful_full_workflow_all_stages(
        self, mock_stage1_responses, mock_stage2_rankings, mock_chairman_response
    ):
        """Test successful execution of all 3 stages in sequence."""
        user_query = "What is the best trading strategy for next week?"

        # Mock Stage 1 responses
        mock_stage1_data = mock_stage1_responses

        # Mock Stage 2 responses - convert from fixture format
        mock_stage2_data = [
            {
                "model": r["model"],
                "ranking": r["ranking_text"],
                "parsed_ranking": ["Response A", "Response B", "Response C", "Response D"]
            }
            for r in mock_stage2_rankings
        ]

        # Mock label_to_model mapping
        mock_label_mapping = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
            "Response D": "meta-llama/llama-3-70b",
        }

        # Mock Stage 3 response
        mock_stage3_data = {
            "model": "anthropic/claude-opus-4",
            "response": mock_chairman_response
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            # Execute full council
            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(user_query)

            # Verify all stages were called
            mock_s1.assert_called_once_with(user_query)
            mock_s2.assert_called_once_with(user_query, mock_stage1_data)
            mock_s3.assert_called_once_with(user_query, mock_stage1_data, mock_stage2_data)

            # Verify return structure
            assert isinstance(stage1_results, list)
            assert isinstance(stage2_results, list)
            assert isinstance(stage3_result, dict)
            assert isinstance(metadata, dict)

            # Verify stage1 results
            assert len(stage1_results) == 4
            assert stage1_results == mock_stage1_data

            # Verify stage2 results
            assert len(stage2_results) == 4
            assert stage2_results == mock_stage2_data

            # Verify stage3 result
            assert stage3_result["model"] == "anthropic/claude-opus-4"
            assert stage3_result["response"] == mock_chairman_response

            # Verify metadata
            assert "label_to_model" in metadata
            assert "aggregate_rankings" in metadata
            assert metadata["label_to_model"] == mock_label_mapping
            assert isinstance(metadata["aggregate_rankings"], list)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stage1_failure_no_responses(self):
        """Test handling when Stage 1 returns no responses (all models failed)."""
        user_query = "Test query with all models failing"

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1:
            # Simulate all models failing
            mock_s1.return_value = []

            # Execute full council
            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(user_query)

            # Verify stage1 was called
            mock_s1.assert_called_once_with(user_query)

            # Verify error response structure
            assert stage1_results == []
            assert stage2_results == []
            assert isinstance(stage3_result, dict)
            assert stage3_result["model"] == "error"
            assert "failed to respond" in stage3_result["response"].lower()
            assert metadata == {}

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stage1_single_response_only(self):
        """Test handling when only one model responds successfully."""
        user_query = "Test query with single response"

        # Mock single Stage 1 response
        mock_stage1_data = [
            {
                "model": "openai/gpt-5.1",
                "response": "Single model response"
            }
        ]

        # Mock Stage 2 response
        mock_stage2_data = [
            {
                "model": "openai/gpt-5.1",
                "ranking": "FINAL RANKING:\n1. Response A\n",
                "parsed_ranking": ["Response A"]
            }
        ]

        mock_label_mapping = {
            "Response A": "openai/gpt-5.1"
        }

        # Mock Stage 3 response
        mock_stage3_data = {
            "model": "anthropic/claude-opus-4",
            "response": "Chairman synthesis with single input"
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            # Execute full council
            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(user_query)

            # Verify all stages were called even with single response
            mock_s1.assert_called_once()
            mock_s2.assert_called_once()
            mock_s3.assert_called_once()

            # Verify results
            assert len(stage1_results) == 1
            assert len(stage2_results) == 1
            assert stage3_result["response"] == "Chairman synthesis with single input"
            assert metadata["label_to_model"] == mock_label_mapping

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metadata_contains_aggregate_rankings(
        self, mock_stage1_responses, mock_stage2_rankings
    ):
        """Test that metadata includes correctly calculated aggregate rankings."""
        user_query = "Test aggregate rankings calculation"

        mock_stage1_data = mock_stage1_responses

        # Create Stage 2 data with known rankings
        mock_stage2_data = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n",
                "parsed_ranking": ["Response A", "Response B", "Response C"]
            },
            {
                "model": "model2",
                "ranking": "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B\n",
                "parsed_ranking": ["Response C", "Response A", "Response B"]
            }
        ]

        mock_label_mapping = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        mock_stage3_data = {
            "model": "anthropic/claude-opus-4",
            "response": "Synthesis"
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            # Execute full council
            _, _, _, metadata = await run_full_council(user_query)

            # Verify aggregate rankings in metadata
            assert "aggregate_rankings" in metadata
            aggregate = metadata["aggregate_rankings"]

            assert isinstance(aggregate, list)
            assert len(aggregate) > 0

            # Verify structure of aggregate rankings
            for ranking in aggregate:
                assert "model" in ranking
                assert "average_rank" in ranking
                assert "rankings_count" in ranking
                assert isinstance(ranking["average_rank"], (int, float))
                assert isinstance(ranking["rankings_count"], int)

            # Verify rankings are sorted (best to worst)
            if len(aggregate) > 1:
                for i in range(len(aggregate) - 1):
                    assert aggregate[i]["average_rank"] <= aggregate[i + 1]["average_rank"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_flow_between_stages(self):
        """Test that data flows correctly from Stage 1 -> Stage 2 -> Stage 3."""
        user_query = "Test data flow"

        stage1_data = [
            {"model": "model1", "response": "Response 1"},
            {"model": "model2", "response": "Response 2"}
        ]

        stage2_data = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n",
                "parsed_ranking": ["Response A", "Response B"]
            }
        ]

        label_mapping = {
            "Response A": "model1",
            "Response B": "model2"
        }

        stage3_data = {
            "model": "chairman",
            "response": "Final synthesis"
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = stage1_data
            mock_s2.return_value = (stage2_data, label_mapping)
            mock_s3.return_value = stage3_data

            await run_full_council(user_query)

            # Verify Stage 2 receives Stage 1 data
            mock_s2.assert_called_once()
            s2_call_args = mock_s2.call_args
            assert s2_call_args[0][0] == user_query
            assert s2_call_args[0][1] == stage1_data

            # Verify Stage 3 receives both Stage 1 and Stage 2 data
            mock_s3.assert_called_once()
            s3_call_args = mock_s3.call_args
            assert s3_call_args[0][0] == user_query
            assert s3_call_args[0][1] == stage1_data
            assert s3_call_args[0][2] == stage2_data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_special_characters_in_query(self):
        """Test handling of special characters in user query."""
        user_query = "What about $SPY > $500? (Long term) & {Q1 2025}"

        mock_stage1_data = [
            {"model": "model1", "response": "Response with special chars"}
        ]

        mock_stage2_data = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n",
                "parsed_ranking": ["Response A"]
            }
        ]

        mock_label_mapping = {"Response A": "model1"}

        mock_stage3_data = {
            "model": "chairman",
            "response": "Synthesis"
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            # Should handle special characters without error
            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(user_query)

            # Verify query was passed correctly to all stages
            mock_s1.assert_called_once_with(user_query)
            mock_s2.assert_called_once_with(user_query, mock_stage1_data)
            mock_s3.assert_called_once_with(user_query, mock_stage1_data, mock_stage2_data)

            # Verify results returned successfully
            assert isinstance(stage1_results, list)
            assert isinstance(stage3_result, dict)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unicode_in_responses(self):
        """Test handling of unicode characters in responses."""
        user_query = "Test unicode handling"

        mock_stage1_data = [
            {"model": "model1", "response": "Response with 日本 and €UR"},
            {"model": "model2", "response": "Unicode symbols: ← → ★"}
        ]

        mock_stage2_data = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n",
                "parsed_ranking": ["Response A", "Response B"]
            }
        ]

        mock_label_mapping = {
            "Response A": "model1",
            "Response B": "model2"
        }

        mock_stage3_data = {
            "model": "chairman",
            "response": "Synthesis with unicode 日本"
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            # Should handle unicode without error
            stage1_results, _, stage3_result, _ = await run_full_council(user_query)

            # Verify unicode is preserved
            assert "日本" in stage1_results[0]["response"]
            assert "€UR" in stage1_results[0]["response"]
            assert "日本" in stage3_result["response"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_return_tuple_structure(self):
        """Test that return value is a properly structured tuple."""
        user_query = "Test return structure"

        mock_stage1_data = [{"model": "model1", "response": "R1"}]
        mock_stage2_data = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n",
                "parsed_ranking": ["Response A"]
            }
        ]
        mock_label_mapping = {"Response A": "model1"}
        mock_stage3_data = {"model": "chairman", "response": "Synthesis"}

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            result = await run_full_council(user_query)

            # Verify it's a tuple with 4 elements
            assert isinstance(result, tuple)
            assert len(result) == 4

            # Verify each element type
            stage1_results, stage2_results, stage3_result, metadata = result
            assert isinstance(stage1_results, list)
            assert isinstance(stage2_results, list)
            assert isinstance(stage3_result, dict)
            assert isinstance(metadata, dict)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_empty_stage2_rankings_handled(self):
        """Test handling when Stage 2 returns empty rankings (all ranking models failed)."""
        user_query = "Test with stage2 failure"

        mock_stage1_data = [
            {"model": "model1", "response": "Response 1"},
            {"model": "model2", "response": "Response 2"}
        ]

        # Empty stage2 results
        mock_stage2_data = []
        mock_label_mapping = {
            "Response A": "model1",
            "Response B": "model2"
        }

        mock_stage3_data = {
            "model": "chairman",
            "response": "Synthesis despite no rankings"
        }

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            # Should still complete workflow
            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(user_query)

            # Verify all stages still called
            mock_s1.assert_called_once()
            mock_s2.assert_called_once()
            mock_s3.assert_called_once()

            # Verify results
            assert len(stage1_results) == 2
            assert len(stage2_results) == 0
            assert stage3_result["response"] == "Synthesis despite no rankings"
            assert "aggregate_rankings" in metadata

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_stage3_receives_correct_parameters(self):
        """Test that Stage 3 receives all required parameters correctly."""
        user_query = "Test stage3 parameters"

        mock_stage1_data = [{"model": "m1", "response": "R1"}]
        mock_stage2_data = [
            {
                "model": "m1",
                "ranking": "FINAL RANKING:\n1. Response A\n",
                "parsed_ranking": ["Response A"]
            }
        ]
        mock_label_mapping = {"Response A": "m1"}
        mock_stage3_data = {"model": "chairman", "response": "S"}

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            await run_full_council(user_query)

            # Verify Stage 3 received correct parameters
            mock_s3.assert_called_once()
            call_args = mock_s3.call_args[0]

            # First parameter: user query
            assert call_args[0] == user_query

            # Second parameter: stage1 results
            assert call_args[1] == mock_stage1_data

            # Third parameter: stage2 results
            assert call_args[2] == mock_stage2_data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_response_structure_on_stage1_failure(self):
        """Test the exact structure of error response when Stage 1 fails."""
        user_query = "Test error structure"

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1:
            mock_s1.return_value = []

            stage1_results, stage2_results, stage3_result, metadata = await run_full_council(user_query)

            # Verify exact error structure
            assert stage1_results == []
            assert stage2_results == []
            assert stage3_result == {
                "model": "error",
                "response": "All models failed to respond. Please try again."
            }
            assert metadata == {}

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_aggregate_rankings_sorted_by_average_rank(self):
        """Test that aggregate rankings are sorted correctly (best to worst)."""
        user_query = "Test ranking sort order"

        mock_stage1_data = [
            {"model": "m1", "response": "R1"},
            {"model": "m2", "response": "R2"},
            {"model": "m3", "response": "R3"}
        ]

        # Create rankings where Response B is best, A is middle, C is worst
        mock_stage2_data = [
            {
                "model": "m1",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C\n",
                "parsed_ranking": ["Response B", "Response A", "Response C"]
            },
            {
                "model": "m2",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C\n",
                "parsed_ranking": ["Response B", "Response A", "Response C"]
            }
        ]

        mock_label_mapping = {
            "Response A": "m1",
            "Response B": "m2",
            "Response C": "m3"
        }

        mock_stage3_data = {"model": "chairman", "response": "S"}

        with patch('backend.council.stage1_collect_responses', new_callable=AsyncMock) as mock_s1, \
             patch('backend.council.stage2_collect_rankings', new_callable=AsyncMock) as mock_s2, \
             patch('backend.council.stage3_synthesize_final', new_callable=AsyncMock) as mock_s3:

            mock_s1.return_value = mock_stage1_data
            mock_s2.return_value = (mock_stage2_data, mock_label_mapping)
            mock_s3.return_value = mock_stage3_data

            _, _, _, metadata = await run_full_council(user_query)

            aggregate = metadata["aggregate_rankings"]

            # Verify sorting: best (lowest average_rank) should be first
            if len(aggregate) > 0:
                assert aggregate[0]["model"] == "m2"  # Response B was ranked 1st twice
                assert aggregate[0]["average_rank"] == 1.0
