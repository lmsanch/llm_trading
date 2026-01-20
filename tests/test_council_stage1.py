"""Test Stage 1 of council orchestration (collect responses).

This module tests stage1_collect_responses which queries all council models
in parallel and collects their individual responses.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.council import stage1_collect_responses


class TestStage1CollectResponses:
    """Test suite for stage1_collect_responses function."""

    @pytest.mark.asyncio
    async def test_successful_collection_all_models(self):
        """Test successful response collection from all council models."""
        # Mock query_models_parallel to return responses for all models
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Based on market analysis, I recommend focusing on defensive sectors.",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": "The technical setup suggests consolidation with bullish bias.",
                "model": "google/gemini-3-pro-preview"
            },
            "anthropic/claude-sonnet-4.5": {
                "content": "Risk-reward favors selective long positions in quality names.",
                "model": "anthropic/claude-sonnet-4.5"
            },
            "x-ai/grok-4": {
                "content": "Market breadth is improving, supporting continuation of trend.",
                "model": "x-ai/grok-4"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("What is the market outlook?")

            # Verify function was called correctly
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            assert call_args[0][1][0]["role"] == "user"
            assert call_args[0][1][0]["content"] == "What is the market outlook?"

            # Verify result structure
            assert len(result) == 4
            assert all(isinstance(item, dict) for item in result)
            assert all("model" in item and "response" in item for item in result)

            # Verify all models are present
            models = [item["model"] for item in result]
            assert "openai/gpt-5.1" in models
            assert "google/gemini-3-pro-preview" in models
            assert "anthropic/claude-sonnet-4.5" in models
            assert "x-ai/grok-4" in models

            # Verify responses are extracted correctly
            for item in result:
                assert len(item["response"]) > 0
                assert isinstance(item["response"], str)

    @pytest.mark.asyncio
    async def test_partial_failure_filters_none_responses(self):
        """Test that None responses from failed models are filtered out."""
        # Mock query_models_parallel with one model returning None
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Market outlook is cautiously optimistic.",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": None,  # This model failed
            "anthropic/claude-sonnet-4.5": {
                "content": "Technical indicators suggest continued strength.",
                "model": "anthropic/claude-sonnet-4.5"
            },
            "x-ai/grok-4": {
                "content": "Momentum remains positive across major sectors.",
                "model": "x-ai/grok-4"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("What is the trend?")

            # Verify only successful responses are included
            assert len(result) == 3
            models = [item["model"] for item in result]
            assert "openai/gpt-5.1" in models
            assert "anthropic/claude-sonnet-4.5" in models
            assert "x-ai/grok-4" in models
            assert "google/gemini-3-pro-preview" not in models

    @pytest.mark.asyncio
    async def test_complete_failure_all_models(self):
        """Test when all models fail to respond."""
        # Mock query_models_parallel with all models returning None
        mock_responses = {
            "openai/gpt-5.1": None,
            "google/gemini-3-pro-preview": None,
            "anthropic/claude-sonnet-4.5": None,
            "x-ai/grok-4": None,
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Verify empty list is returned
            assert result == []
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_single_model_success(self):
        """Test when only one model succeeds."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Single successful response.",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": None,
            "anthropic/claude-sonnet-4.5": None,
            "x-ai/grok-4": None,
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            assert len(result) == 1
            assert result[0]["model"] == "openai/gpt-5.1"
            assert result[0]["response"] == "Single successful response."

    @pytest.mark.asyncio
    async def test_response_with_reasoning_details(self):
        """Test that responses with reasoning_details are handled correctly."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Main response content",
                "reasoning_details": "Extended reasoning process...",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": "Another response",
                "model": "google/gemini-3-pro-preview"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Verify that only 'content' is extracted, not reasoning_details
            assert len(result) == 2
            for item in result:
                assert "response" in item
                assert "reasoning_details" not in item
                # Verify response contains the content, not reasoning
                assert "Main response content" in str(result) or "Another response" in str(result)

    @pytest.mark.asyncio
    async def test_empty_content_response(self):
        """Test handling of responses with empty content."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "",  # Empty content
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": "Valid response",
                "model": "google/gemini-3-pro-preview"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Both should be included (empty content is still a valid response)
            assert len(result) == 2

            # Find the empty response
            empty_response = [item for item in result if item["model"] == "openai/gpt-5.1"][0]
            assert empty_response["response"] == ""

    @pytest.mark.asyncio
    async def test_missing_content_key(self):
        """Test handling of responses missing the 'content' key."""
        mock_responses = {
            "openai/gpt-5.1": {
                "model": "openai/gpt-5.1"
                # Missing 'content' key
            },
            "google/gemini-3-pro-preview": {
                "content": "Valid response",
                "model": "google/gemini-3-pro-preview"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Both should be included
            assert len(result) == 2

            # Find the response with missing content key
            missing_content = [item for item in result if item["model"] == "openai/gpt-5.1"][0]
            assert missing_content["response"] == ""  # Should default to empty string

    @pytest.mark.asyncio
    async def test_response_data_structure(self):
        """Test that the response data structure matches expected format."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Test content",
                "model": "openai/gpt-5.1"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Verify exact structure
            assert len(result) == 1
            item = result[0]

            # Must have exactly these keys
            assert set(item.keys()) == {"model", "response"}

            # Values must be strings
            assert isinstance(item["model"], str)
            assert isinstance(item["response"], str)

    @pytest.mark.asyncio
    async def test_query_with_special_characters(self):
        """Test handling of user queries with special characters."""
        special_query = "What about SPY > $500? (Long term) & {Q1 2025}"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Response to special query",
                "model": "openai/gpt-5.1"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses(special_query)

            # Verify the query was passed through correctly
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            assert call_args[0][1][0]["content"] == special_query

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_with_unicode(self):
        """Test handling of user queries with unicode characters."""
        unicode_query = "Market outlook for 日本 and €UR?"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Unicode response: 日本 €",
                "model": "openai/gpt-5.1"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses(unicode_query)

            assert len(result) == 1
            assert "日本" in result[0]["response"] or "€" in result[0]["response"]

    @pytest.mark.asyncio
    async def test_long_response_content(self):
        """Test handling of very long response content."""
        long_content = "A" * 10000  # 10k character response

        mock_responses = {
            "openai/gpt-5.1": {
                "content": long_content,
                "model": "openai/gpt-5.1"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            assert len(result) == 1
            assert len(result[0]["response"]) == 10000

    @pytest.mark.asyncio
    async def test_response_order_preserved(self):
        """Test that the order of responses is consistent."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Response 1",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": "Response 2",
                "model": "google/gemini-3-pro-preview"
            },
            "anthropic/claude-sonnet-4.5": {
                "content": "Response 3",
                "model": "anthropic/claude-sonnet-4.5"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("Test query")

            # Verify all responses are present
            assert len(result) == 3
            models = [item["model"] for item in result]
            assert len(set(models)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_integration_with_mock_fixtures(self, mock_stage1_responses):
        """Test integration with mock stage1 response fixtures."""
        # Convert fixture format to API response format
        mock_api_responses = {}
        for response in mock_stage1_responses:
            mock_api_responses[response["model"]] = {
                "content": response["response"],
                "model": response["model"]
            }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_api_responses

            result = await stage1_collect_responses("Test query")

            # Verify result matches fixture expectations
            assert len(result) == len(mock_stage1_responses)

            # Verify each fixture response is present
            result_models = {item["model"] for item in result}
            fixture_models = {item["model"] for item in mock_stage1_responses}
            assert result_models == fixture_models

    @pytest.mark.asyncio
    async def test_empty_query_string(self):
        """Test handling of empty query string."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Response to empty query",
                "model": "openai/gpt-5.1"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage1_collect_responses("")

            # Should still work with empty query
            mock_query.assert_called_once()
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_messages_format(self):
        """Test that messages are formatted correctly for the API."""
        mock_responses = {
            "openai/gpt-5.1": {
                "content": "Test response",
                "model": "openai/gpt-5.1"
            },
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            user_query = "Test query for message format"
            await stage1_collect_responses(user_query)

            # Verify messages parameter structure
            mock_query.assert_called_once()
            _, kwargs = mock_query.call_args

            # Get the messages argument (second positional arg)
            messages = mock_query.call_args[0][1]

            assert isinstance(messages, list)
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == user_query
