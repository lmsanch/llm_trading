"""Tests for peer review multiple reviews functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from backend.pipeline.stages.peer_review import PeerReviewStage


@pytest.mark.asyncio
async def test_generate_peer_reviews_returns_multiple():
    """Test that _generate_peer_reviews returns multiple reviews from multiple models."""
    stage = PeerReviewStage()

    # Mock 3 anonymized pitches with all required fields
    anonymized_pitches = [
        {
            "anonymized_label": "Pitch A",
            "instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "thesis_bullets": ["Bull thesis"],
            "conviction": 1.5,
            "risk_profile": "BASE",
            "entry_policy": {"stop_loss_pct": 2.0},
            "exit_policy": {"take_profit_pct": 5.0, "time_stop_days": 7},
            "risk_notes": "Standard risk",
        },
        {
            "anonymized_label": "Pitch B",
            "instrument": "TLT",
            "direction": "SHORT",
            "horizon": "1W",
            "thesis_bullets": ["Bear thesis"],
            "conviction": 1.2,
            "risk_profile": "BASE",
            "entry_policy": {"stop_loss_pct": 2.0},
            "exit_policy": {"take_profit_pct": 5.0, "time_stop_days": 7},
            "risk_notes": "Standard risk",
        },
        {
            "anonymized_label": "Pitch C",
            "instrument": "GLD",
            "direction": "LONG",
            "horizon": "1W",
            "thesis_bullets": ["Gold thesis"],
            "conviction": 1.0,
            "risk_profile": "BASE",
            "entry_policy": {"stop_loss_pct": 2.0},
            "exit_policy": {"take_profit_pct": 5.0, "time_stop_days": 7},
            "risk_notes": "Standard risk",
        },
    ]

    # Mock responses from 2 models, each reviewing the other 2 pitches
    mock_responses = {
        "chatgpt": {
            "content": """[
                {
                    "pitch_label": "Pitch B",
                    "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                              "risk_definition": 8, "risk_management": 7, "originality": 6,
                              "tradeability": 7},
                    "best_argument_against": "Rate cuts may be delayed",
                    "one_flip_condition": "If 10Y yield drops below 4%",
                    "suggested_fix": "Add more catalyst timing detail"
                },
                {
                    "pitch_label": "Pitch C",
                    "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 5,
                              "risk_definition": 7, "risk_management": 6, "originality": 8,
                              "tradeability": 6},
                    "best_argument_against": "Strong dollar pressure",
                    "one_flip_condition": "If DXY breaks 105",
                    "suggested_fix": "Strengthen dollar analysis"
                }
            ]"""
        },
        "gemini": {
            "content": """[
                {
                    "pitch_label": "Pitch A",
                    "scores": {"clarity": 9, "edge_plausibility": 8, "timing_catalyst": 7,
                              "risk_definition": 8, "risk_management": 8, "originality": 7,
                              "tradeability": 8},
                    "best_argument_against": "Momentum may fade",
                    "one_flip_condition": "If SPX breaks below 5500",
                    "suggested_fix": "Add momentum indicators"
                },
                {
                    "pitch_label": "Pitch C",
                    "scores": {"clarity": 6, "edge_plausibility": 5, "timing_catalyst": 6,
                              "risk_definition": 6, "risk_management": 5, "originality": 7,
                              "tradeability": 5},
                    "best_argument_against": "Inflation cooling",
                    "one_flip_condition": "If CPI drops below 2%",
                    "suggested_fix": "Improve risk management"
                }
            ]"""
        },
    }

    # Patch query_pm_models to return mock responses
    with patch('backend.pipeline.stages.peer_review.query_pm_models',
               new_callable=AsyncMock, return_value=mock_responses):

        # Execute the method
        reviews = await stage._generate_peer_reviews(anonymized_pitches)

        # Verify we got 4 reviews total (2 models × 2 reviews each)
        assert len(reviews) == 4, f"Expected 4 reviews, got {len(reviews)}"

        # Verify each review has required fields
        for review in reviews:
            assert "pitch_label" in review
            assert "scores" in review
            assert "reviewer_model" in review
            assert "best_argument_against" in review
            assert "one_flip_condition" in review

        # Verify we got reviews for different pitches
        pitch_labels = {r["pitch_label"] for r in reviews}
        assert len(pitch_labels) >= 2, "Should have reviews for multiple pitches"

        # Verify reviews from different models
        reviewer_models = {r["reviewer_model"] for r in reviews}
        assert len(reviewer_models) == 2, "Should have reviews from 2 models"

        print(f"✅ Successfully generated {len(reviews)} reviews from {len(reviewer_models)} models")
        print(f"   Pitches reviewed: {pitch_labels}")
        print(f"   Reviewers: {reviewer_models}")


@pytest.mark.asyncio
async def test_parse_peer_review_single_object():
    """Test that _parse_peer_review can handle a single review object."""
    stage = PeerReviewStage()

    content = """{
        "pitch_label": "Pitch A",
        "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6,
                  "tradeability": 7},
        "best_argument_against": "Test argument",
        "one_flip_condition": "Test condition"
    }"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 1, "Should contain one review"
    assert reviews[0]["pitch_label"] == "Pitch A"
    assert reviews[0]["reviewer_model"] == "test-model"


@pytest.mark.asyncio
async def test_parse_peer_review_array():
    """Test that _parse_peer_review can handle an array of reviews."""
    stage = PeerReviewStage()

    content = """[
        {
            "pitch_label": "Pitch A",
            "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                      "risk_definition": 8, "risk_management": 7, "originality": 6,
                      "tradeability": 7},
            "best_argument_against": "Argument 1",
            "one_flip_condition": "Condition 1"
        },
        {
            "pitch_label": "Pitch B",
            "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 5,
                      "risk_definition": 7, "risk_management": 6, "originality": 8,
                      "tradeability": 6},
            "best_argument_against": "Argument 2",
            "one_flip_condition": "Condition 2"
        }
    ]"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 2, "Should contain two reviews"
    assert reviews[0]["pitch_label"] == "Pitch A"
    assert reviews[1]["pitch_label"] == "Pitch B"
    assert all(r["reviewer_model"] == "test-model" for r in reviews)


@pytest.mark.asyncio
async def test_parse_peer_review_invalid_json():
    """Test that _parse_peer_review handles invalid JSON gracefully."""
    stage = PeerReviewStage()

    content = "This is not valid JSON at all"

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list even on error"
    assert len(reviews) == 0, "Should return empty list for invalid JSON"


@pytest.mark.asyncio
async def test_parse_peer_review_with_code_fences():
    """Test that _parse_peer_review can strip markdown code fences."""
    stage = PeerReviewStage()

    content = """```json
    {
        "pitch_label": "Pitch A",
        "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6,
                  "tradeability": 7},
        "best_argument_against": "Test argument",
        "one_flip_condition": "Test condition"
    }
    ```"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 1, "Should parse one review despite code fences"
    assert reviews[0]["pitch_label"] == "Pitch A"


@pytest.mark.asyncio
async def test_parse_peer_review_with_trailing_text():
    """Test that _parse_peer_review can handle JSON with trailing text using raw_decode."""
    stage = PeerReviewStage()

    # JSON at the start with trailing text - raw_decode should handle this
    content = """{
        "pitch_label": "Pitch A",
        "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6,
                  "tradeability": 7},
        "best_argument_against": "Test argument",
        "one_flip_condition": "Test condition"
    }
    This is some trailing text that should be ignored."""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 1, "Should extract JSON with trailing text"
    assert reviews[0]["pitch_label"] == "Pitch A"


@pytest.mark.asyncio
async def test_parse_peer_review_missing_required_field():
    """Test that _parse_peer_review rejects reviews missing required fields."""
    stage = PeerReviewStage()

    # Missing 'one_flip_condition'
    content = """{
        "pitch_label": "Pitch A",
        "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6,
                  "tradeability": 7},
        "best_argument_against": "Test argument"
    }"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 0, "Should reject review missing required field"


@pytest.mark.asyncio
async def test_parse_peer_review_missing_score_dimension():
    """Test that _parse_peer_review rejects reviews missing score dimensions."""
    stage = PeerReviewStage()

    # Missing 'tradeability' dimension
    content = """{
        "pitch_label": "Pitch A",
        "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6},
        "best_argument_against": "Test argument",
        "one_flip_condition": "Test condition"
    }"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 0, "Should reject review missing score dimension"


@pytest.mark.asyncio
async def test_parse_peer_review_invalid_score_range():
    """Test that _parse_peer_review rejects scores outside 1-10 range."""
    stage = PeerReviewStage()

    # Score of 15 is invalid (should be 1-10)
    content = """{
        "pitch_label": "Pitch A",
        "scores": {"clarity": 15, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6,
                  "tradeability": 7},
        "best_argument_against": "Test argument",
        "one_flip_condition": "Test condition"
    }"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 0, "Should reject review with invalid score range"


@pytest.mark.asyncio
async def test_parse_peer_review_empty_array():
    """Test that _parse_peer_review handles empty arrays."""
    stage = PeerReviewStage()

    content = "[]"

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 0, "Should return empty list for empty array"


@pytest.mark.asyncio
async def test_parse_peer_review_array_with_invalid_items():
    """Test that _parse_peer_review filters out invalid items from array."""
    stage = PeerReviewStage()

    # First review is valid, second is missing required field
    content = """[
        {
            "pitch_label": "Pitch A",
            "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                      "risk_definition": 8, "risk_management": 7, "originality": 6,
                      "tradeability": 7},
            "best_argument_against": "Argument 1",
            "one_flip_condition": "Condition 1"
        },
        {
            "pitch_label": "Pitch B",
            "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 5,
                      "risk_definition": 7, "risk_management": 6, "originality": 8,
                      "tradeability": 6},
            "best_argument_against": "Argument 2"
        }
    ]"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert isinstance(reviews, list), "Should return a list"
    assert len(reviews) == 1, "Should filter out invalid review and keep valid one"
    assert reviews[0]["pitch_label"] == "Pitch A"


@pytest.mark.asyncio
async def test_parse_peer_review_enrichment():
    """Test that _parse_peer_review enriches reviews with metadata."""
    stage = PeerReviewStage()

    content = """{
        "pitch_label": "Pitch A",
        "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                  "risk_definition": 8, "risk_management": 7, "originality": 6,
                  "tradeability": 7},
        "best_argument_against": "Test argument",
        "one_flip_condition": "Test condition"
    }"""

    reviews = stage._parse_peer_review(content, "test-model")

    assert len(reviews) == 1
    review = reviews[0]

    # Check enriched fields
    assert "review_id" in review, "Should add review_id"
    assert "reviewer_model" in review, "Should add reviewer_model"
    assert review["reviewer_model"] == "test-model"
    assert "average_score" in review, "Should calculate average_score"
    assert "timestamp" in review, "Should add timestamp"
    assert "suggested_fix" in review, "Should add suggested_fix"

    # Verify average score calculation (sum of all scores / 7)
    expected_avg = (8 + 7 + 6 + 8 + 7 + 6 + 7) / 7
    assert abs(review["average_score"] - expected_avg) < 0.01
