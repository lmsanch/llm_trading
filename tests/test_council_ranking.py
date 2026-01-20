"""Test council aggregate ranking calculation logic.

This module tests the calculate_aggregate_rankings function which aggregates
rankings from multiple models to determine consensus rankings.
"""

import pytest
from backend.council import calculate_aggregate_rankings


class TestCalculateAggregateRankings:
    """Test suite for calculate_aggregate_rankings function."""

    def test_unanimous_ranking(self):
        """Test when all models agree on the same ranking order."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 3
        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.0
        assert result[1]["model"] == "openai/gpt-4-turbo"
        assert result[1]["average_rank"] == 2.0
        assert result[2]["model"] == "google/gemini-pro"
        assert result[2]["average_rank"] == 3.0

    def test_divergent_rankings(self):
        """Test when models provide different ranking orders."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response B"""
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response B
2. Response C
3. Response A"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 3
        # All should have average rank of 2.0 (each appears in all positions)
        assert result[0]["average_rank"] == 2.0
        assert result[1]["average_rank"] == 2.0
        assert result[2]["average_rank"] == 2.0

    def test_four_models_ranking(self):
        """Test ranking with 4 models (all PM models)."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response D
2. Response A
3. Response C
4. Response B"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response A
2. Response C
3. Response D
4. Response B"""
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C
4. Response D"""
            },
            {
                "model": "model4",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response D
4. Response B"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
            "Response D": "meta-llama/llama-3-70b",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 4
        # Response A: positions [2, 1, 1, 2] = avg 1.5
        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.5
        # Response C: positions [3, 2, 3, 1] = avg 2.25
        assert result[1]["model"] == "google/gemini-pro"
        assert result[1]["average_rank"] == 2.25
        # Response D: positions [1, 3, 4, 3] = avg 2.75
        assert result[2]["model"] == "meta-llama/llama-3-70b"
        assert result[2]["average_rank"] == 2.75
        # Response B: positions [4, 4, 2, 4] = avg 3.5
        assert result[3]["model"] == "openai/gpt-4-turbo"
        assert result[3]["average_rank"] == 3.5

    def test_tie_in_average_ranks(self):
        """Test when multiple models have the same average rank."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response B
2. Response A"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 2
        # Both should have average rank 1.5
        assert result[0]["average_rank"] == 1.5
        assert result[1]["average_rank"] == 1.5
        # Order is preserved from sort (stable sort)
        models = {r["model"] for r in result}
        assert "anthropic/claude-3.5-sonnet" in models
        assert "openai/gpt-4-turbo" in models

    def test_partial_rankings_missing_responses(self):
        """Test when some models don't rank all responses (partial rankings)."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response A
2. Response C"""
                # Response B is missing
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response C"""
                # Response A and B are missing
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Response A: positions [1, 1] = avg 1.0 (2 rankings)
        # Response C: positions [3, 2, 1] = avg 2.0 (3 rankings)
        # Response B: positions [2] = avg 2.0 (1 ranking)
        assert len(result) == 3

        # Response A should be first with lowest average
        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.0
        assert result[0]["rankings_count"] == 2

        # Response C and B both have avg 2.0
        remaining_models = [result[1]["model"], result[2]["model"]]
        assert "google/gemini-pro" in remaining_models
        assert "openai/gpt-4-turbo" in remaining_models

    def test_single_ranking_only(self):
        """Test when only one model provides a ranking."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response B"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 3
        assert result[0]["model"] == "google/gemini-pro"
        assert result[0]["average_rank"] == 1.0
        assert result[0]["rankings_count"] == 1
        assert result[1]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[1]["average_rank"] == 2.0
        assert result[2]["model"] == "openai/gpt-4-turbo"
        assert result[2]["average_rank"] == 3.0

    def test_empty_rankings(self):
        """Test when no rankings are provided."""
        stage2_results = []
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert result == []

    def test_malformed_rankings_ignored(self):
        """Test that malformed rankings are gracefully handled."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """I think Response A is best, Response B is second."""
                # No FINAL RANKING section - will extract Response labels
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response B
2. Response A"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Should still aggregate the valid rankings
        assert len(result) == 2

    def test_unknown_labels_ignored(self):
        """Test that unknown response labels are ignored."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response X
3. Response B"""
                # Response X is not in label_to_model
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Only Response A and B should be included
        assert len(result) == 2
        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.0
        assert result[1]["model"] == "openai/gpt-4-turbo"
        assert result[1]["average_rank"] == 3.0  # Position 3 in original ranking

    def test_rankings_count_field(self):
        """Test that rankings_count field is correctly calculated."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B"""
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response B"""
                # Response A is missing
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Response A appears in 2 rankings
        response_a = [r for r in result if r["model"] == "anthropic/claude-3.5-sonnet"][0]
        assert response_a["rankings_count"] == 2

        # Response B appears in 3 rankings
        response_b = [r for r in result if r["model"] == "openai/gpt-4-turbo"][0]
        assert response_b["rankings_count"] == 3

    def test_average_rank_decimal_precision(self):
        """Test that average ranks are rounded to 2 decimal places."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response A
2. Response C
3. Response B"""
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response B
2. Response A
3. Response C"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Response A: [1, 1, 2] = avg 1.333... should be 1.33
        response_a = [r for r in result if r["model"] == "anthropic/claude-3.5-sonnet"][0]
        assert response_a["average_rank"] == 1.33

        # Response B: [2, 3, 1] = avg 2.0
        response_b = [r for r in result if r["model"] == "openai/gpt-4-turbo"][0]
        assert response_b["average_rank"] == 2.0

        # Response C: [3, 2, 3] = avg 2.666... should be 2.67
        response_c = [r for r in result if r["model"] == "google/gemini-pro"][0]
        assert response_c["average_rank"] == 2.67

    def test_sorting_order_ascending(self):
        """Test that results are sorted by average rank (ascending - lower is better)."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response C
2. Response B
3. Response A"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response B"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Response C: [1, 1] = avg 1.0 (best)
        # Response A: [3, 2] = avg 2.5
        # Response B: [2, 3] = avg 2.5
        assert result[0]["model"] == "google/gemini-pro"
        assert result[0]["average_rank"] == 1.0

        # The next two have the same avg rank (2.5)
        assert result[1]["average_rank"] == 2.5
        assert result[2]["average_rank"] == 2.5

    def test_realistic_council_scenario(self):
        """Test with realistic council ranking scenario matching fixtures."""
        stage2_results = [
            {
                "model": "anthropic/claude-3.5-sonnet",
                "ranking": """After evaluating all responses:

Response A provides comprehensive analysis with strong reasoning.
Response B offers good technical perspective.
Response C gives balanced view.
Response D has interesting points.

FINAL RANKING:
1. Response C
2. Response A
3. Response B
4. Response D"""
            },
            {
                "model": "openai/gpt-4-turbo",
                "ranking": """FINAL RANKING:
1. Response A
2. Response C
3. Response D
4. Response B"""
            },
            {
                "model": "google/gemini-pro",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C
4. Response D"""
            },
            {
                "model": "meta-llama/llama-3-70b",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response D
4. Response B"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
            "Response D": "meta-llama/llama-3-70b",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 4

        # Response A: [2, 1, 1, 2] = avg 1.5 (best)
        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.5
        assert result[0]["rankings_count"] == 4

        # Response C: [1, 2, 3, 1] = avg 1.75
        assert result[1]["model"] == "google/gemini-pro"
        assert result[1]["average_rank"] == 1.75
        assert result[1]["rankings_count"] == 4

        # Response B: [3, 4, 2, 4] = avg 3.25
        assert result[2]["model"] == "openai/gpt-4-turbo"
        assert result[2]["average_rank"] == 3.25

        # Response D: [4, 3, 4, 3] = avg 3.5
        assert result[3]["model"] == "meta-llama/llama-3-70b"
        assert result[3]["average_rank"] == 3.5


class TestCalculateAggregateRankingsEdgeCases:
    """Test edge cases and error conditions for calculate_aggregate_rankings."""

    def test_single_response(self):
        """Test with only one response to rank."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 1
        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.0
        assert result[0]["rankings_count"] == 1

    def test_no_valid_labels_in_rankings(self):
        """Test when rankings contain no valid labels."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. The first one
2. The second one"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert result == []

    def test_duplicate_labels_in_same_ranking(self):
        """Test handling of duplicate labels in a single ranking."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response A
3. Response B"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Response A appears twice: positions [1, 2] = avg 1.5
        response_a = [r for r in result if r["model"] == "anthropic/claude-3.5-sonnet"][0]
        assert response_a["average_rank"] == 1.5
        assert response_a["rankings_count"] == 2

        # Response B appears once: position [3]
        response_b = [r for r in result if r["model"] == "openai/gpt-4-turbo"][0]
        assert response_b["average_rank"] == 3.0
        assert response_b["rankings_count"] == 1

    def test_empty_label_to_model_mapping(self):
        """Test with empty label_to_model mapping."""
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B"""
            },
        ]
        label_to_model = {}

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert result == []

    def test_very_large_number_of_responses(self):
        """Test with a large number of responses (performance check)."""
        # Generate 20 responses (Response A through Response T)
        rankings_text = "\n".join([f"{i+1}. Response {chr(65+i)}" for i in range(20)])
        stage2_results = [
            {
                "model": "model1",
                "ranking": f"FINAL RANKING:\n{rankings_text}"
            },
        ]
        label_to_model = {
            f"Response {chr(65+i)}": f"model-{i}"
            for i in range(20)
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        assert len(result) == 20
        # Verify positions 1 through 20
        for i in range(20):
            assert result[i]["average_rank"] == float(i + 1)


class TestCalculateAggregateRankingsIntegration:
    """Integration tests for calculate_aggregate_rankings with real fixtures."""

    def test_with_mock_stage2_responses(self, mock_stage2_rankings, label_to_model_mapping):
        """Test with mock Stage 2 responses from fixtures."""
        # Convert fixture format (ranking_text) to expected format (ranking)
        stage2_results = [
            {
                "model": ranking["model"],
                "ranking": ranking["ranking_text"]  # Convert key name
            }
            for ranking in mock_stage2_rankings
        ]

        result = calculate_aggregate_rankings(stage2_results, label_to_model_mapping)

        # Should have 4 models in results
        assert len(result) == 4

        # All results should have required fields
        for ranking in result:
            assert "model" in ranking
            assert "average_rank" in ranking
            assert "rankings_count" in ranking
            assert ranking["rankings_count"] > 0
            assert ranking["average_rank"] > 0

        # Results should be sorted by average rank
        for i in range(len(result) - 1):
            assert result[i]["average_rank"] <= result[i+1]["average_rank"]

    def test_matches_expected_aggregate_rankings(self):
        """Test that aggregate rankings match expected values from documentation."""
        # This test uses the exact scenario from CLAUDE.md
        stage2_results = [
            {
                "model": "model1",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response B
4. Response D"""
            },
            {
                "model": "model2",
                "ranking": """FINAL RANKING:
1. Response A
2. Response C
3. Response D
4. Response B"""
            },
            {
                "model": "model3",
                "ranking": """FINAL RANKING:
1. Response A
2. Response B
3. Response C
4. Response D"""
            },
            {
                "model": "model4",
                "ranking": """FINAL RANKING:
1. Response C
2. Response A
3. Response D
4. Response B"""
            },
        ]
        label_to_model = {
            "Response A": "anthropic/claude-3.5-sonnet",
            "Response B": "openai/gpt-4-turbo",
            "Response C": "google/gemini-pro",
            "Response D": "meta-llama/llama-3-70b",
        }

        result = calculate_aggregate_rankings(stage2_results, label_to_model)

        # Expected from documentation:
        # Response A: avg 1.5 (positions: 2, 1, 1, 2)
        # Response C: avg 1.75 (positions: 1, 2, 3, 1)
        # Response D: avg 3.5 (positions: 4, 3, 4, 3)
        # Response B: avg 3.25 (positions: 3, 4, 2, 4)

        assert result[0]["model"] == "anthropic/claude-3.5-sonnet"
        assert result[0]["average_rank"] == 1.5

        assert result[1]["model"] == "google/gemini-pro"
        assert result[1]["average_rank"] == 1.75

        assert result[2]["model"] == "openai/gpt-4-turbo"
        assert result[2]["average_rank"] == 3.25

        assert result[3]["model"] == "meta-llama/llama-3-70b"
        assert result[3]["average_rank"] == 3.5
