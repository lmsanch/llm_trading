"""Test database save logic for peer reviews with correct pitch_id mappings."""

import pytest
import uuid
from datetime import datetime
from backend.db.council_db import save_peer_reviews
from backend.db_helpers import fetch_all, execute


@pytest.mark.asyncio
async def test_save_peer_reviews_with_correct_pitch_id_mappings(db_pool):
    """
    Test that save_peer_reviews stores all reviews with correct pitch_id mappings.

    Scenario: 4 PM pitches generate 12 peer reviews (each model reviews 3 others).
    Verify all 12 reviews are saved with correct pitch_id foreign keys via label_to_model.
    """
    # Setup test data
    week_id = "2025-01-15"
    research_date = "2025-01-15T08:00:00Z"

    # 4 PM models with unique pitches
    pm_models = [
        "openai/chatgpt-4o-latest",
        "google/gemini-pro-1.5",
        "anthropic/claude-3-5-sonnet-20241022",
        "xai/grok-2-1212"
    ]

    # Create 4 PM pitches (one per model)
    pm_pitches = []
    for i, model in enumerate(pm_models):
        pitch = {
            "model": model,
            "instrument": ["SPY", "TLT", "GLD", "QQQ"][i],
            "direction": "LONG",
            "conviction": 1.5 - (i * 0.1),
            "thesis_bullets": [f"Thesis for {model}"],
            "horizon": "1W",
        }
        pm_pitches.append(pitch)

    # Insert PM pitches into database first
    pitch_ids = {}
    for pitch in pm_pitches:
        result = await execute(
            """
            INSERT INTO pm_pitches
            (week_id, model, account, pitch_data, instrument, direction, conviction, research_date, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING id
            """,
            week_id,
            pitch["model"],
            f"account_{pitch['model'].split('/')[0]}",
            pitch,  # pitch_data as JSONB
            pitch["instrument"],
            pitch["direction"],
            pitch["conviction"],
            research_date
        )
        # Store pitch_id for verification
        pitch_ids[pitch["model"]] = result

    # Create label_to_model mapping (anonymization)
    labels = ["Pitch A", "Pitch B", "Pitch C", "Pitch D"]
    label_to_model = {labels[i]: model for i, model in enumerate(pm_models)}

    # Create 12 peer reviews (4 models × 3 reviews each = 12 total)
    # Each model reviews all other models' pitches (N-1 reviews)
    peer_reviews = []
    review_count = 0

    for reviewer_idx, reviewer_model in enumerate(pm_models):
        # Review all pitches except own
        for pitch_idx, pitch_label in enumerate(labels):
            if reviewer_idx != pitch_idx:  # Don't review own pitch
                review = {
                    "review_id": str(uuid.uuid4()),
                    "reviewer_model": reviewer_model,
                    "pitch_label": pitch_label,
                    "scores": {
                        "clarity": 8,
                        "edge_plausibility": 7,
                        "timing_catalyst": 6,
                        "risk_definition": 8,
                        "risk_management": 7,
                        "originality": 6,
                        "tradeability": 7
                    },
                    "best_argument_against": f"Review by {reviewer_model} for {pitch_label}",
                    "one_flip_condition": f"Flip condition for {pitch_label}",
                    "suggested_fix": "Add more detail",
                    "average_score": 7.0,
                    "timestamp": datetime.utcnow().isoformat()
                }
                peer_reviews.append(review)
                review_count += 1

    # Verify we created 12 reviews (4 models × 3 reviews each)
    assert len(peer_reviews) == 12, f"Expected 12 reviews, got {len(peer_reviews)}"

    # Save peer reviews to database
    await save_peer_reviews(
        week_id=week_id,
        peer_reviews=peer_reviews,
        research_date=research_date,
        pm_pitches=pm_pitches,
        label_to_model=label_to_model
    )

    # Verify all 12 reviews were saved
    saved_reviews = await fetch_all(
        "SELECT * FROM peer_reviews WHERE research_date = $1",
        research_date
    )

    assert len(saved_reviews) == 12, f"Expected 12 saved reviews, got {len(saved_reviews)}"

    # Verify each review has correct pitch_id mapping
    for saved_review in saved_reviews:
        pitch_label = saved_review["pitch_label"]
        reviewer_model = saved_review["reviewer_model"]
        pitch_id = saved_review["pitch_id"]

        # Verify pitch_label is in our label set
        assert pitch_label in labels, f"Invalid pitch_label: {pitch_label}"

        # Verify reviewer_model is in our model set
        assert reviewer_model in pm_models, f"Invalid reviewer_model: {reviewer_model}"

        # Verify pitch_id matches the model that created the pitch
        reviewed_model = label_to_model[pitch_label]
        expected_pitch_id = pitch_ids[reviewed_model]

        assert pitch_id == expected_pitch_id, (
            f"Pitch ID mismatch for {pitch_label} (reviewed by {reviewer_model}). "
            f"Expected {expected_pitch_id}, got {pitch_id}"
        )

        # Verify review_data is stored as JSONB
        assert saved_review["review_data"] is not None
        assert isinstance(saved_review["review_data"], dict)
        assert "scores" in saved_review["review_data"]
        assert "best_argument_against" in saved_review["review_data"]

    # Verify each model reviewed exactly 3 pitches (N-1 where N=4)
    reviewer_counts = {}
    for saved_review in saved_reviews:
        reviewer_model = saved_review["reviewer_model"]
        reviewer_counts[reviewer_model] = reviewer_counts.get(reviewer_model, 0) + 1

    for model in pm_models:
        assert reviewer_counts[model] == 3, (
            f"Model {model} should have reviewed 3 pitches, but reviewed {reviewer_counts[model]}"
        )

    # Verify each pitch was reviewed exactly 3 times (by all other models)
    pitch_review_counts = {}
    for saved_review in saved_reviews:
        pitch_id = saved_review["pitch_id"]
        pitch_review_counts[pitch_id] = pitch_review_counts.get(pitch_id, 0) + 1

    for model, pitch_id in pitch_ids.items():
        assert pitch_review_counts[pitch_id] == 3, (
            f"Pitch from {model} should have 3 reviews, but has {pitch_review_counts[pitch_id]}"
        )

    # Verify no model reviewed its own pitch
    for saved_review in saved_reviews:
        pitch_label = saved_review["pitch_label"]
        reviewer_model = saved_review["reviewer_model"]
        reviewed_model = label_to_model[pitch_label]

        assert reviewer_model != reviewed_model, (
            f"Model {reviewer_model} should not review its own pitch ({reviewed_model})"
        )

    # Clean up test data
    await execute("DELETE FROM peer_reviews WHERE research_date = $1", research_date)
    await execute("DELETE FROM pm_pitches WHERE research_date = $1", research_date)

    print("✅ Database save logic verified:")
    print(f"   - Saved all 12 reviews (4 models × 3 reviews each)")
    print(f"   - Each review has correct pitch_id mapping via label_to_model")
    print(f"   - Each model reviewed exactly 3 pitches (N-1)")
    print(f"   - Each pitch received exactly 3 reviews")
    print(f"   - No model reviewed its own pitch")


@pytest.mark.asyncio
async def test_save_peer_reviews_handles_idempotency(db_pool):
    """
    Test that save_peer_reviews deletes existing reviews before inserting new ones.

    This ensures idempotency - running the same save twice doesn't create duplicates.
    """
    week_id = "2025-01-16"
    research_date = "2025-01-16T08:00:00Z"

    # Create minimal test data
    pm_pitches = [
        {"model": "openai/chatgpt-4o-latest", "instrument": "SPY", "direction": "LONG", "conviction": 1.5},
        {"model": "google/gemini-pro-1.5", "instrument": "TLT", "direction": "SHORT", "conviction": 1.3}
    ]

    # Insert pitches
    pitch_ids = {}
    for pitch in pm_pitches:
        result = await execute(
            """
            INSERT INTO pm_pitches
            (week_id, model, account, pitch_data, instrument, direction, conviction, research_date, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING id
            """,
            week_id, pitch["model"], "test_account", pitch,
            pitch["instrument"], pitch["direction"], pitch["conviction"], research_date
        )
        pitch_ids[pitch["model"]] = result

    label_to_model = {
        "Pitch A": "openai/chatgpt-4o-latest",
        "Pitch B": "google/gemini-pro-1.5"
    }

    # Create 2 reviews (2 models × 1 review each = 2 total)
    peer_reviews = [
        {
            "review_id": str(uuid.uuid4()),
            "reviewer_model": "openai/chatgpt-4o-latest",
            "pitch_label": "Pitch B",
            "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                      "risk_definition": 8, "risk_management": 7, "originality": 6, "tradeability": 7},
            "best_argument_against": "Test",
            "one_flip_condition": "Test",
            "suggested_fix": "Test"
        },
        {
            "review_id": str(uuid.uuid4()),
            "reviewer_model": "google/gemini-pro-1.5",
            "pitch_label": "Pitch A",
            "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 5,
                      "risk_definition": 7, "risk_management": 6, "originality": 8, "tradeability": 6},
            "best_argument_against": "Test",
            "one_flip_condition": "Test",
            "suggested_fix": "Test"
        }
    ]

    # Save first time
    await save_peer_reviews(week_id, peer_reviews, research_date, pm_pitches, label_to_model)

    # Verify 2 reviews saved
    reviews = await fetch_all("SELECT * FROM peer_reviews WHERE research_date = $1", research_date)
    assert len(reviews) == 2, f"Expected 2 reviews after first save, got {len(reviews)}"

    # Save again (should delete and re-insert, not duplicate)
    await save_peer_reviews(week_id, peer_reviews, research_date, pm_pitches, label_to_model)

    # Verify still only 2 reviews (not 4)
    reviews = await fetch_all("SELECT * FROM peer_reviews WHERE research_date = $1", research_date)
    assert len(reviews) == 2, f"Expected 2 reviews after second save (idempotent), got {len(reviews)}"

    # Clean up
    await execute("DELETE FROM peer_reviews WHERE research_date = $1", research_date)
    await execute("DELETE FROM pm_pitches WHERE research_date = $1", research_date)

    print("✅ Idempotency verified: duplicate saves don't create duplicate reviews")


@pytest.mark.asyncio
async def test_save_peer_reviews_handles_missing_pitch(db_pool):
    """
    Test that save_peer_reviews logs warning when pitch_label doesn't map to a model.
    """
    week_id = "2025-01-17"
    research_date = "2025-01-17T08:00:00Z"

    # Create 1 pitch
    pm_pitches = [
        {"model": "openai/chatgpt-4o-latest", "instrument": "SPY", "direction": "LONG", "conviction": 1.5}
    ]

    # Insert pitch
    await execute(
        """
        INSERT INTO pm_pitches
        (week_id, model, account, pitch_data, instrument, direction, conviction, research_date, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
        RETURNING id
        """,
        week_id, pm_pitches[0]["model"], "test_account", pm_pitches[0],
        pm_pitches[0]["instrument"], pm_pitches[0]["direction"],
        pm_pitches[0]["conviction"], research_date
    )

    # label_to_model only has Pitch A, but review references Pitch B (missing)
    label_to_model = {"Pitch A": "openai/chatgpt-4o-latest"}

    # Create review for non-existent pitch
    peer_reviews = [
        {
            "review_id": str(uuid.uuid4()),
            "reviewer_model": "openai/chatgpt-4o-latest",
            "pitch_label": "Pitch B",  # This doesn't exist in label_to_model
            "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                      "risk_definition": 8, "risk_management": 7, "originality": 6, "tradeability": 7},
            "best_argument_against": "Test",
            "one_flip_condition": "Test",
            "suggested_fix": "Test"
        }
    ]

    # Save should succeed but log warning
    await save_peer_reviews(week_id, peer_reviews, research_date, pm_pitches, label_to_model)

    # Verify no reviews were saved (because Pitch B doesn't map to a model)
    reviews = await fetch_all("SELECT * FROM peer_reviews WHERE research_date = $1", research_date)
    assert len(reviews) == 0, f"Expected 0 reviews for unmapped pitch, got {len(reviews)}"

    # Clean up
    await execute("DELETE FROM pm_pitches WHERE research_date = $1", research_date)

    print("✅ Missing pitch handling verified: unmapped labels are logged and skipped")
