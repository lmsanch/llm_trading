"""Test Stage 3 of council orchestration (synthesize final).

This module tests stage3_synthesize_final which queries the chairman model
to synthesize a final response based on all Stage 1 and Stage 2 data.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.council import stage3_synthesize_final


class TestStage3SynthesizeFinal:
    """Test suite for stage3_synthesize_final function."""

    def _convert_stage2_format(self, stage2_data):
        """Convert fixture format (ranking_text) to expected format (ranking).

        Args:
            stage2_data: List of stage2 data from fixture

        Returns:
            List with correct format for stage3_synthesize_final
        """
        return [
            {"model": r["model"], "ranking": r["ranking_text"], "parsed_ranking": []}
            for r in stage2_data
        ]

    @pytest.mark.asyncio
    async def test_successful_synthesis(self, mock_stage1_responses, mock_stage2_rankings):
        """Test successful chairman synthesis with all stage data."""
        from backend.config import CHAIRMAN_MODEL

        user_query = "What is the market outlook?"

        # Convert fixture format to expected format
        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        # Mock chairman response
        mock_chairman_response = {
            "content": "Based on the council's analysis, the market outlook is cautiously optimistic. "
                      "The consensus from multiple models indicates that while there are near-term "
                      "headwinds, the underlying technical and fundamental conditions support "
                      "selective positioning in defensive sectors with quality names.",
            "model": CHAIRMAN_MODEL
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify query was called once
            mock_query.assert_called_once()

            # Verify result structure
            assert isinstance(result, dict)
            assert "model" in result
            assert "response" in result

            # Verify content
            assert result["model"] == CHAIRMAN_MODEL
            assert len(result["response"]) > 0
            assert "cautiously optimistic" in result["response"]

    @pytest.mark.asyncio
    async def test_chairman_prompt_construction(self, mock_stage1_responses, mock_stage2_rankings):
        """Test that chairman prompt is correctly built from stage1 and stage2 data."""
        user_query = "Should I invest in tech stocks?"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Final synthesis here",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Get the messages argument
            call_args = mock_query.call_args
            messages = call_args[0][1]
            prompt = messages[0]["content"]

            # Verify prompt contains original query
            assert user_query in prompt

            # Verify prompt contains stage 1 data
            assert "STAGE 1" in prompt or "Stage 1" in prompt or "Individual Responses" in prompt
            for response in mock_stage1_responses:
                assert response["model"] in prompt
                assert response["response"] in prompt

            # Verify prompt contains stage 2 data
            assert "STAGE 2" in prompt or "Stage 2" in prompt or "Peer Rankings" in prompt
            for ranking in stage2_formatted:
                assert ranking["model"] in prompt

            # Verify prompt has chairman instructions
            assert "Chairman" in prompt
            assert "synthesize" in prompt.lower() or "synthesis" in prompt.lower()

    @pytest.mark.asyncio
    async def test_chairman_api_failure_returns_fallback(self, mock_stage1_responses, mock_stage2_rankings):
        """Test that chairman API failure returns appropriate fallback response."""
        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = None  # Simulate API failure

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify fallback response structure
            assert isinstance(result, dict)
            assert "model" in result
            assert "response" in result

            # Verify fallback content
            assert "Error" in result["response"] or "error" in result["response"]
            assert "Unable" in result["response"] or "unable" in result["response"]

    @pytest.mark.asyncio
    async def test_correct_chairman_model_called(self, mock_stage1_responses, mock_stage2_rankings):
        """Test that the correct chairman model is called."""
        from backend.config import CHAIRMAN_MODEL

        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Test response",
            "model": CHAIRMAN_MODEL
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify correct model was called
            call_args = mock_query.call_args
            model_arg = call_args[0][0]
            assert model_arg == CHAIRMAN_MODEL

    @pytest.mark.asyncio
    async def test_return_data_structure(self, mock_stage1_responses, mock_stage2_rankings):
        """Test that return value has correct data structure."""
        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Final answer",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify structure has exactly these keys
            assert set(result.keys()) == {"model", "response"}

            # Verify types
            assert isinstance(result["model"], str)
            assert isinstance(result["response"], str)

    @pytest.mark.asyncio
    async def test_handles_empty_stage1_results(self, mock_stage2_rankings):
        """Test handling when stage1_results is empty."""
        user_query = "Test query"
        empty_stage1 = []

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Synthesis based on limited data",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, empty_stage1, stage2_formatted
            )

            # Should still return valid result
            assert isinstance(result, dict)
            assert "model" in result
            assert "response" in result

    @pytest.mark.asyncio
    async def test_handles_empty_stage2_results(self, mock_stage1_responses):
        """Test handling when stage2_results is empty."""
        user_query = "Test query"
        empty_stage2 = []

        mock_chairman_response = {
            "content": "Synthesis based on Stage 1 only",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, empty_stage2
            )

            # Should still return valid result
            assert isinstance(result, dict)
            assert "model" in result
            assert "response" in result

    @pytest.mark.asyncio
    async def test_handles_empty_content_in_chairman_response(self, mock_stage1_responses, mock_stage2_rankings):
        """Test handling when chairman returns empty content."""
        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "",  # Empty content
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Should handle empty content gracefully
            assert isinstance(result, dict)
            assert result["response"] == ""

    @pytest.mark.asyncio
    async def test_handles_missing_content_key_in_chairman_response(self, mock_stage1_responses, mock_stage2_rankings):
        """Test handling when chairman response is missing 'content' key."""
        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "model": "anthropic/claude-opus-4"
            # Missing 'content' key
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Should default to empty string
            assert isinstance(result, dict)
            assert result["response"] == ""

    @pytest.mark.asyncio
    async def test_chairman_with_reasoning_details(self, mock_stage1_responses, mock_stage2_rankings):
        """Test handling chairman response with reasoning_details."""
        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Main synthesis response",
            "reasoning_details": "Extended reasoning process...",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Should only extract content, not reasoning_details
            assert result["response"] == "Main synthesis response"
            assert "reasoning_details" not in result

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, mock_stage1_responses, mock_stage2_rankings):
        """Test handling of special characters in user query."""
        special_query = "What about $SPY > $500? (Long term) & {Q1 2025}"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Analysis of special query",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                special_query, mock_stage1_responses, stage2_formatted
            )

            # Verify query was passed correctly
            messages = mock_query.call_args[0][1]
            prompt = messages[0]["content"]
            assert special_query in prompt

            assert isinstance(result, dict)
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_unicode_in_responses(self, mock_stage2_rankings):
        """Test handling of unicode characters in stage responses."""
        user_query = "Test query"

        stage1_with_unicode = [
            {"model": "model1", "response": "Response with 日本 and €UR"},
            {"model": "model2", "response": "Unicode symbols: ← → ★"},
        ]

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Synthesis with unicode support 日本",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, stage1_with_unicode, stage2_formatted
            )

            # Verify unicode is preserved
            messages = mock_query.call_args[0][1]
            prompt = messages[0]["content"]
            assert "日本" in prompt
            assert "€UR" in prompt

            assert "日本" in result["response"]

    @pytest.mark.asyncio
    async def test_long_stage_data(self, mock_stage2_rankings):
        """Test handling of very long stage1 and stage2 data."""
        user_query = "Test query"

        # Create long responses
        long_stage1 = [
            {"model": f"model{i}", "response": "A" * 1000}
            for i in range(5)
        ]

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Synthesis of long data",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, long_stage1, stage2_formatted
            )

            # Should handle long data without error
            assert isinstance(result, dict)
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_single_stage1_response(self, mock_stage2_rankings):
        """Test handling when only one Stage 1 response exists."""
        user_query = "Test query"

        single_stage1 = [
            {"model": "openai/gpt-5.1", "response": "Single response"}
        ]

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Synthesis based on single response",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, single_stage1, stage2_formatted
            )

            # Should work with single response
            assert isinstance(result, dict)
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_single_stage2_ranking(self, mock_stage1_responses):
        """Test handling when only one Stage 2 ranking exists."""
        user_query = "Test query"

        single_stage2 = [
            {
                "model": "openai/gpt-5.1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B\n",
                "parsed_ranking": ["Response A", "Response B"]
            }
        ]

        mock_chairman_response = {
            "content": "Synthesis based on single ranking",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, single_stage2
            )

            # Should work with single ranking
            assert isinstance(result, dict)
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_messages_format(self, mock_stage1_responses, mock_stage2_rankings):
        """Test that messages are formatted correctly for the chairman API."""
        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Test response",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify messages parameter structure
            call_args = mock_query.call_args
            messages = call_args[0][1]

            assert isinstance(messages, list)
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert isinstance(messages[0]["content"], str)
            assert len(messages[0]["content"]) > 0

    @pytest.mark.asyncio
    async def test_integration_with_mock_fixtures(
        self, mock_stage1_responses, mock_stage2_rankings, mock_chairman_response
    ):
        """Test integration with all council mock fixtures."""
        user_query = "What is the best strategy?"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        # Convert fixture to API response format
        mock_api_response = {
            "content": mock_chairman_response,
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_api_response

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify result uses fixture data
            assert isinstance(result, dict)
            assert result["response"] == mock_chairman_response

    @pytest.mark.asyncio
    async def test_fallback_includes_chairman_model(self, mock_stage1_responses, mock_stage2_rankings):
        """Test that fallback response includes the chairman model name."""
        from backend.config import CHAIRMAN_MODEL

        user_query = "Test query"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = None  # Simulate failure

            result = await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            # Verify fallback includes model name
            assert result["model"] == CHAIRMAN_MODEL
            assert "Error" in result["response"] or "error" in result["response"]

    @pytest.mark.asyncio
    async def test_stage1_and_stage2_both_included_in_prompt(
        self, mock_stage1_responses, mock_stage2_rankings
    ):
        """Test that both Stage 1 and Stage 2 data are included in chairman prompt."""
        user_query = "Test comprehensive prompt"

        stage2_formatted = self._convert_stage2_format(mock_stage2_rankings)

        mock_chairman_response = {
            "content": "Comprehensive synthesis",
            "model": "anthropic/claude-opus-4"
        }

        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_chairman_response

            await stage3_synthesize_final(
                user_query, mock_stage1_responses, stage2_formatted
            )

            messages = mock_query.call_args[0][1]
            prompt = messages[0]["content"]

            # Verify all Stage 1 models and responses are in prompt
            for response in mock_stage1_responses:
                assert response["model"] in prompt
                assert response["response"] in prompt

            # Verify all Stage 2 models are in prompt
            for ranking in stage2_formatted:
                assert ranking["model"] in prompt

            # Verify both stage sections exist
            assert "STAGE 1" in prompt or "Stage 1" in prompt
            assert "STAGE 2" in prompt or "Stage 2" in prompt
