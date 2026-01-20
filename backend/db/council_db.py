"""Council database operations for peer reviews and chairman decisions."""

import json
import logging
from typing import Dict, List, Any

from backend.db_helpers import fetch_one, execute

logger = logging.getLogger(__name__)


async def save_peer_reviews(
    week_id: str,
    peer_reviews: List[Dict[str, Any]],
    research_date: str,
    pm_pitches: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> None:
    """
    Save peer reviews to database with pitch ID mapping.

    Saves a list of peer review dictionaries to the peer_reviews table. Creates
    mapping from model names to pitch IDs by looking up the latest pitch for each
    model in the database. Maps pitch labels (e.g., "Pitch A") back to models
    using the provided label_to_model mapping. Deletes existing reviews for the
    research_date before inserting new ones.

    Args:
        week_id: Week identifier for the reviews
        peer_reviews: List of peer review dictionaries containing:
            - reviewer_model: Name of the model providing the review
            - pitch_label: Label of the pitch being reviewed (e.g., "Pitch A")
            - [other review fields]: Additional review data
        research_date: ISO format research date to associate reviews with
        pm_pitches: List of PM pitch dictionaries used to map models to pitch IDs.
            Each should contain a "model" field.
        label_to_model: Mapping from pitch labels (e.g., "Pitch A") to model names.
            Used to identify which pitch each review is about.

    Database Tables:
        - peer_reviews: Stores peer review data with columns:
            week_id, pitch_id, reviewer_model, pitch_label, review_data,
            research_date, created_at
        - pm_pitches: Referenced to get pitch IDs by model and research_date

    Returns:
        None

    Raises:
        Exception: If database operation fails (logged and raised)
    """
    try:
        logger.info(
            f"Saving {len(peer_reviews)} peer reviews to DB for research_date {research_date}"
        )

        # Create mapping from model to pitch_id (look up pitch IDs from DB)
        model_to_pitch_id = {}
        for pitch in pm_pitches:
            model = pitch.get("model")
            if model:
                row = await fetch_one(
                    """
                    SELECT id FROM pm_pitches
                    WHERE model = $1 AND research_date = $2
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    model, research_date
                )
                if row:
                    model_to_pitch_id[model] = row["id"]

        # Delete existing peer reviews for this research_date
        await execute(
            "DELETE FROM peer_reviews WHERE research_date = $1",
            research_date
        )

        # Insert peer reviews
        for review in peer_reviews:
            reviewer_model = review.get("reviewer_model", "unknown")
            pitch_label = review.get("pitch_label", "")

            # Map label (e.g., "Pitch A") back to model using label_to_model
            reviewed_model = label_to_model.get(pitch_label)
            if reviewed_model and reviewed_model in model_to_pitch_id:
                pitch_id = model_to_pitch_id[reviewed_model]

                logger.debug(
                    f"Inserting peer review: week_id='{week_id}', "
                    f"pitch_label='{pitch_label}', reviewer_model='{reviewer_model}'"
                )

                await execute(
                    """
                    INSERT INTO peer_reviews
                    (week_id, pitch_id, reviewer_model, pitch_label, review_data, research_date, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """,
                    week_id,
                    pitch_id,
                    reviewer_model,
                    pitch_label,
                    json.dumps(review),
                    research_date
                )
            else:
                logger.warning(
                    f"Could not map pitch_label '{pitch_label}' to model for review"
                )

        logger.info("Peer reviews saved to DB successfully")

    except Exception as e:
        logger.error(f"Error saving peer reviews to DB: {e}", exc_info=True)
        raise


async def save_chairman_decision(
    week_id: str,
    chairman_decision: Dict[str, Any],
    research_date: str
) -> None:
    """
    Save chairman decision to database.

    Saves the chairman's final decision to the chairman_decisions table. Deletes
    any existing decision for the same research_date before inserting the new one.

    Args:
        week_id: Week identifier for the decision
        chairman_decision: Dictionary containing the chairman's decision data:
            - selected_pitch: The pitch selected by the chairman
            - reasoning: Explanation for the selection
            - [other decision fields]: Additional decision data
        research_date: ISO format research date to associate decision with

    Database Tables:
        - chairman_decisions: Stores chairman decision data with columns:
            week_id, decision_data, research_date, created_at

    Returns:
        None

    Raises:
        Exception: If database operation fails (logged and raised)
    """
    try:
        logger.info(
            f"Saving chairman decision to DB for research_date {research_date}"
        )

        # Delete existing decision for this research_date
        await execute(
            "DELETE FROM chairman_decisions WHERE research_date = $1",
            research_date
        )

        # Insert new decision
        await execute(
            """
            INSERT INTO chairman_decisions
            (week_id, decision_data, research_date, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            week_id, json.dumps(chairman_decision), research_date
        )

        logger.info("Chairman decision saved to DB successfully")

    except Exception as e:
        logger.error(f"Error saving chairman decision to DB: {e}", exc_info=True)
        raise
