"""Test Stage 2 of council orchestration (collect rankings).

This module tests stage2_collect_rankings which creates anonymized responses,
prompts models to rank them, and returns rankings with label_to_model mapping.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.council import stage2_collect_rankings


class TestStage2CollectRankings:
    """Test suite for stage2_collect_rankings function."""

    @pytest.mark.asyncio
    async def test_successful_ranking_collection(self, mock_stage1_responses):
        """Test successful ranking collection from all models."""
        user_query = "What is the market outlook?"

        # Mock query_models_parallel to return ranking responses
        mock_responses = {
            "openai/gpt-5.1": {
                "content": """Response A provides comprehensive analysis.
Response B offers good technical perspective.
Response C gives balanced view.
Response D has interesting points.

FINAL RANKING:
1. Response A
2. Response C
3. Response B
4. Response D
""",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": """All responses evaluated.

FINAL RANKING:
1. Response C
2. Response A
3. Response D
4. Response B
""",
                "model": "google/gemini-3-pro-preview"
            },
            "anthropic/claude-sonnet-4.5": {
                "content": """FINAL RANKING:
1. Response A
2. Response B
3. Response C
4. Response D
""",
                "model": "anthropic/claude-sonnet-4.5"
            },
            "x-ai/grok-4": {
                "content": """FINAL RANKING:
1. Response C
2. Response B
3. Response A
4. Response D
""",
                "model": "x-ai/grok-4"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Verify query was called
            mock_query.assert_called_once()

            # Verify stage2_results structure
            assert len(stage2_results) == 4
            assert all(isinstance(item, dict) for item in stage2_results)
            assert all("model" in item and "ranking" in item and "parsed_ranking" in item
                      for item in stage2_results)

            # Verify label_to_model mapping
            assert len(label_to_model) == len(mock_stage1_responses)
            assert "Response A" in label_to_model
            assert "Response B" in label_to_model
            assert "Response C" in label_to_model
            assert "Response D" in label_to_model

            # Verify mapping correctness
            assert label_to_model["Response A"] == mock_stage1_responses[0]["model"]
            assert label_to_model["Response B"] == mock_stage1_responses[1]["model"]
            assert label_to_model["Response C"] == mock_stage1_responses[2]["model"]
            assert label_to_model["Response D"] == mock_stage1_responses[3]["model"]

    @pytest.mark.asyncio
    async def test_anonymization_in_prompt(self, mock_stage1_responses):
        """Test that responses are properly anonymized in the ranking prompt."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            await stage2_collect_rankings(user_query, mock_stage1_responses)

            # Verify the prompt was called
            mock_query.assert_called_once()
            call_args = mock_query.call_args

            # Get the messages argument
            messages = call_args[0][1]
            prompt_content = messages[0]["content"]

            # Verify anonymization - model names should NOT appear in prompt
            for response in mock_stage1_responses:
                # Model names should not be in the prompt (they're anonymized)
                assert response["model"] not in prompt_content

            # Verify labels ARE in the prompt
            assert "Response A" in prompt_content
            assert "Response B" in prompt_content
            assert "Response C" in prompt_content
            assert "Response D" in prompt_content

            # Verify actual response content is in the prompt
            for response in mock_stage1_responses:
                assert response["response"] in prompt_content

    @pytest.mark.asyncio
    async def test_label_creation_order(self):
        """Test that labels are created in correct alphabetical order."""
        stage1_results = [
            {"model": "model1", "response": "Response 1"},
            {"model": "model2", "response": "Response 2"},
            {"model": "model3", "response": "Response 3"},
        ]

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            _, label_to_model = await stage2_collect_rankings("test", stage1_results)

            # Verify labels are alphabetical
            assert "Response A" in label_to_model
            assert "Response B" in label_to_model
            assert "Response C" in label_to_model

            # Verify order matches stage1_results order
            assert label_to_model["Response A"] == "model1"
            assert label_to_model["Response B"] == "model2"
            assert label_to_model["Response C"] == "model3"

    @pytest.mark.asyncio
    async def test_handles_single_response(self):
        """Test handling when only one Stage 1 response exists."""
        stage1_results = [
            {"model": "openai/gpt-5.1", "response": "Single response"}
        ]

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                "test", stage1_results
            )

            # Should still work with single response
            assert len(label_to_model) == 1
            assert "Response A" in label_to_model
            assert label_to_model["Response A"] == "openai/gpt-5.1"

    @pytest.mark.asyncio
    async def test_parsed_ranking_extraction(self, mock_stage1_responses):
        """Test that rankings are correctly parsed from model responses."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": """Some analysis here.

FINAL RANKING:
1. Response C
2. Response A
3. Response B
4. Response D
""",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, _ = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Verify parsed ranking
            assert len(stage2_results) == 1
            parsed = stage2_results[0]["parsed_ranking"]

            assert len(parsed) == 4
            assert parsed[0] == "Response C"
            assert parsed[1] == "Response A"
            assert parsed[2] == "Response B"
            assert parsed[3] == "Response D"

    @pytest.mark.asyncio
    async def test_handles_malformed_ranking(self, mock_stage1_responses):
        """Test handling of malformed ranking responses (missing FINAL RANKING)."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": """I think Response A is best, followed by Response C.
Response B is okay and Response D is weakest.
My ranking would be: A, C, B, D""",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": "FINAL RANKING:\n1. Response B\n2. Response A\n3. Response C\n4. Response D\n",
                "model": "google/gemini-3-pro-preview"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, _ = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Both should be included
            assert len(stage2_results) == 2

            # Find the malformed one
            malformed = [r for r in stage2_results if r["model"] == "openai/gpt-5.1"][0]

            # Should still parse what it can (fallback parsing)
            # The fallback should extract "Response X" patterns even without FINAL RANKING
            assert "parsed_ranking" in malformed
            # Fallback should find Response A, C, B, D in order of appearance
            parsed = malformed["parsed_ranking"]
            assert "Response A" in parsed
            assert "Response C" in parsed

    @pytest.mark.asyncio
    async def test_handles_empty_ranking_response(self, mock_stage1_responses):
        """Test handling of empty ranking responses."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "",  # Empty response
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "model": "google/gemini-3-pro-preview"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, _ = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Both should be included
            assert len(stage2_results) == 2

            # Empty response should have empty parsed_ranking
            empty_result = [r for r in stage2_results if r["model"] == "openai/gpt-5.1"][0]
            assert empty_result["ranking"] == ""
            assert empty_result["parsed_ranking"] == []

    @pytest.mark.asyncio
    async def test_handles_partial_model_failure(self, mock_stage1_responses):
        """Test handling when some models fail to respond."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "model": "openai/gpt-5.1"
            },
            "google/gemini-3-pro-preview": None,  # Failed
            "anthropic/claude-sonnet-4.5": {
                "content": "FINAL RANKING:\n1. Response C\n2. Response A\n3. Response B\n4. Response D\n",
                "model": "anthropic/claude-sonnet-4.5"
            },
            "x-ai/grok-4": None,  # Failed
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, _ = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Only successful responses should be included
            assert len(stage2_results) == 2
            models = [r["model"] for r in stage2_results]
            assert "openai/gpt-5.1" in models
            assert "anthropic/claude-sonnet-4.5" in models
            assert "google/gemini-3-pro-preview" not in models
            assert "x-ai/grok-4" not in models

    @pytest.mark.asyncio
    async def test_all_models_fail(self, mock_stage1_responses):
        """Test handling when all ranking models fail."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": None,
            "google/gemini-3-pro-preview": None,
            "anthropic/claude-sonnet-4.5": None,
            "x-ai/grok-4": None,
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Should return empty results but valid label_to_model mapping
            assert stage2_results == []
            assert len(label_to_model) == len(mock_stage1_responses)

    @pytest.mark.asyncio
    async def test_prompt_format_structure(self, mock_stage1_responses):
        """Test that the ranking prompt has correct structure and instructions."""
        user_query = "What should I invest in?"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            await stage2_collect_rankings(user_query, mock_stage1_responses)

            # Verify prompt structure
            messages = mock_query.call_args[0][1]
            prompt = messages[0]["content"]

            # Should include original question
            assert user_query in prompt

            # Should include FINAL RANKING instructions
            assert "FINAL RANKING:" in prompt
            assert "evaluate each response" in prompt.lower()

            # Should include format instructions
            assert "numbered list" in prompt.lower() or "1." in prompt

    @pytest.mark.asyncio
    async def test_data_structure_format(self, mock_stage1_responses):
        """Test that stage2_results have correct data structure."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Verify structure
            assert len(stage2_results) == 1
            result = stage2_results[0]

            # Must have exactly these keys
            assert set(result.keys()) == {"model", "ranking", "parsed_ranking"}

            # Verify types
            assert isinstance(result["model"], str)
            assert isinstance(result["ranking"], str)
            assert isinstance(result["parsed_ranking"], list)

            # Verify label_to_model is dict
            assert isinstance(label_to_model, dict)
            assert all(isinstance(k, str) and isinstance(v, str)
                      for k, v in label_to_model.items())

    @pytest.mark.asyncio
    async def test_handles_many_responses(self):
        """Test handling of many Stage 1 responses (beyond D)."""
        # Create 10 responses (up to Response J)
        stage1_results = [
            {"model": f"model{i}", "response": f"Response content {i}"}
            for i in range(10)
        ]

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n" + "\n".join([
                    f"{i+1}. Response {chr(65+i)}" for i in range(10)
                ]),
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            _, label_to_model = await stage2_collect_rankings("test", stage1_results)

            # Verify all 10 labels created
            assert len(label_to_model) == 10
            assert "Response A" in label_to_model
            assert "Response J" in label_to_model

            # Verify correct mapping
            assert label_to_model["Response A"] == "model0"
            assert label_to_model["Response J"] == "model9"

    @pytest.mark.asyncio
    async def test_special_characters_in_responses(self):
        """Test handling of special characters in Stage 1 responses."""
        stage1_results = [
            {"model": "model1", "response": "Response with $SPY & {special} chars!"},
            {"model": "model2", "response": "Unicode: 日本 €UR"},
        ]

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                "test", stage1_results
            )

            # Verify the prompt was called with special characters preserved
            messages = mock_query.call_args[0][1]
            prompt = messages[0]["content"]

            assert "$SPY" in prompt
            assert "{special}" in prompt
            assert "日本" in prompt

            # Verify results are valid
            assert len(stage2_results) == 1
            assert len(label_to_model) == 2

    @pytest.mark.asyncio
    async def test_ranking_with_reasoning_details(self, mock_stage1_responses):
        """Test handling of ranking responses that include reasoning_details."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "reasoning_details": "Extended reasoning for this ranking...",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, _ = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Verify only content is used, not reasoning_details
            assert len(stage2_results) == 1
            result = stage2_results[0]

            # Should not include reasoning_details in result
            assert "reasoning_details" not in result
            assert "ranking" in result
            assert "parsed_ranking" in result

    @pytest.mark.asyncio
    async def test_integration_with_mock_fixtures(self, mock_stage1_responses, mock_stage2_rankings):
        """Test integration with mock stage2 ranking fixtures."""
        user_query = "Test query"

        # Convert fixture format to API response format
        mock_api_responses = {}
        for ranking in mock_stage2_rankings:
            mock_api_responses[ranking["model"]] = {
                "content": ranking["ranking_text"],
                "model": ranking["model"]
            }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_api_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query, mock_stage1_responses
            )

            # Verify result matches fixture expectations
            assert len(stage2_results) == len(mock_stage2_rankings)

            # Verify label_to_model created correctly
            assert len(label_to_model) == len(mock_stage1_responses)

    @pytest.mark.asyncio
    async def test_return_tuple_structure(self, mock_stage1_responses):
        """Test that function returns correct tuple structure."""
        user_query = "Test query"

        mock_responses = {
            "openai/gpt-5.1": {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B\n3. Response C\n4. Response D\n",
                "model": "openai/gpt-5.1"
            }
        }

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            result = await stage2_collect_rankings(user_query, mock_stage1_responses)

            # Verify it's a tuple with 2 elements
            assert isinstance(result, tuple)
            assert len(result) == 2

            stage2_results, label_to_model = result

            # Verify types
            assert isinstance(stage2_results, list)
            assert isinstance(label_to_model, dict)

    @pytest.mark.asyncio
    async def test_empty_stage1_results(self):
        """Test handling of empty Stage 1 results."""
        stage1_results = []
        user_query = "Test query"

        mock_responses = {}

        with patch('backend.council.query_models_parallel', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = mock_responses

            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query, stage1_results
            )

            # Should handle empty input gracefully
            assert isinstance(stage2_results, list)
            assert isinstance(label_to_model, dict)
            assert len(label_to_model) == 0
