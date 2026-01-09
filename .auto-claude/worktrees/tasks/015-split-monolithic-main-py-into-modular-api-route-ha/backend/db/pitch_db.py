"""PM pitch database operations."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from backend.db.database import DatabaseConnection

logger = logging.getLogger(__name__)


def save_pitches(
    week_id: str,
    pitches_raw: List[Dict[str, Any]],
    research_date: Optional[str] = None
) -> None:
    """
    Save raw PM pitches to database.

    Saves a list of PM pitch dictionaries to the pm_pitches table. If a pitch
    already exists for the same model and research_date (or week_id), it will
    be deleted and replaced with the new pitch data.

    Args:
        week_id: Week identifier for the pitches
        pitches_raw: List of pitch dictionaries containing:
            - model: Model name (required)
            - model_info: Dict with account info (optional)
            - selected_instrument or instrument: Trading instrument
            - direction: Trade direction
            - conviction: Conviction score
            - timestamp: ISO format timestamp (auto-added if missing)
            - [other pitch fields]
        research_date: ISO format research date (optional, uses week_id if not provided)

    Database Tables:
        - pm_pitches: Stores PM pitch data with columns:
            week_id, model, account, pitch_data, instrument, direction,
            conviction, research_date, created_at

    Returns:
        None

    Raises:
        Exception: If database operation fails (logged but not raised)
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                logger.info(
                    f"Saving {len(pitches_raw)} pitches to DB for week {week_id}"
                )

                for pitch in pitches_raw:
                    model = pitch.get("model", "unknown")
                    account = pitch.get("model_info", {}).get("account", "UNKNOWN")

                    # Ensure timestamp exists
                    if "timestamp" not in pitch:
                        pitch["timestamp"] = datetime.utcnow().isoformat()

                    # Delete existing pitch for this model/research_date to allow re-runs
                    # Match by research_date and model to avoid deleting pitches from other research dates
                    if research_date:
                        cur.execute(
                            "DELETE FROM pm_pitches WHERE research_date = %s AND model = %s",
                            (research_date, model),
                        )
                    else:
                        # Fallback to week_id if research_date not provided
                        cur.execute(
                            "DELETE FROM pm_pitches WHERE week_id = %s AND model = %s",
                            (week_id, model),
                        )

                    # Insert new pitch
                    cur.execute(
                        """
                        INSERT INTO pm_pitches
                        (week_id, model, account, pitch_data, instrument, direction, conviction, research_date, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            week_id,
                            model,
                            account,
                            json.dumps(pitch),
                            pitch.get("selected_instrument") or pitch.get("instrument"),
                            pitch.get("direction"),
                            float(pitch.get("conviction", 0)),
                            research_date,
                        ),
                    )

                logger.info("Pitches saved to DB successfully")

    except Exception as e:
        logger.error(f"Error saving pitches to DB: {e}", exc_info=True)
        raise


def load_pitches(
    week_id: Optional[str] = None,
    research_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load PM pitches from database.

    Retrieves pitches based on week_id or research_date. If neither is provided,
    returns the latest pitches (preferring research_date over week_id).

    Args:
        week_id: Week identifier to filter by (optional)
        research_date: Research date to filter by (optional, takes precedence over week_id)

    Returns:
        List of pitch dictionaries. Each dict contains:
            - All fields from pitch_data JSON column
            - created_at: Timestamp when pitch was saved
            - research_date: Research date associated with pitch
        Returns empty list if no pitches found or error occurs.

    Database Tables:
        - pm_pitches: Contains PM pitch data

    Query Logic:
        - If research_date provided: Match exact date and time (date, hour, minute)
        - If week_id provided: Match by week_id
        - If neither provided: Get latest by research_date, fall back to week_id
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                if research_date:
                    # Search by exact date and time match (YYYY-MM-DD HH:MM)
                    # Match both date and time components
                    query = """
                        SELECT pitch_data, created_at, research_date
                        FROM pm_pitches
                        WHERE research_date::date = %s::date
                          AND DATE_PART('hour', research_date) = DATE_PART('hour', %s::timestamptz)
                          AND DATE_PART('minute', research_date) = DATE_PART('minute', %s::timestamptz)
                        ORDER BY model
                    """
                    params = (research_date, research_date, research_date)
                elif week_id:
                    query = "SELECT pitch_data, created_at, research_date FROM pm_pitches WHERE week_id = %s ORDER BY model"
                    params = (week_id,)
                else:
                    # Get latest by research_date if available, else by week_id
                    # Prefer using research_date as it's more valid
                    cur.execute(
                        "SELECT MAX(research_date) FROM pm_pitches WHERE research_date IS NOT NULL"
                    )
                    latest_date = cur.fetchone()[0]

                    if latest_date:
                        query = """
                            SELECT pitch_data, created_at, research_date
                            FROM pm_pitches
                            WHERE research_date = %s
                            ORDER BY model
                        """
                        params = (latest_date,)
                    else:
                        # Fallback to week_id
                        cur.execute("SELECT MAX(week_id) FROM pm_pitches")
                        latest_week = cur.fetchone()[0]
                        if not latest_week:
                            return []
                        query = "SELECT pitch_data, created_at, research_date FROM pm_pitches WHERE week_id = %s ORDER BY model"
                        params = (latest_week,)

                cur.execute(query, params)
                rows = cur.fetchall()

                if not rows:
                    return []

                # Extract pitch data (first column is pitch_data JSON)
                pitches = [row[0] for row in rows]

                logger.info(f"Loaded {len(pitches)} pitches from DB")
                return pitches

    except Exception as e:
        logger.error(f"Error loading pitches from DB: {e}", exc_info=True)
        return []


def find_pitch_by_id(pitch_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve PM pitch from database by ID.

    Fetches a specific pitch by its database primary key ID and returns
    all pitch data including parsed JSON fields.

    Args:
        pitch_id: Primary key ID of the pitch in pm_pitches table

    Returns:
        Dict containing all pitch columns:
            - id: Database ID
            - week_id: Week identifier
            - model: Model name
            - account: Account name
            - pitch_data: Full pitch data as JSON
            - instrument: Trading instrument
            - direction: Trade direction
            - conviction: Conviction score
            - research_date: Research date
            - created_at: Creation timestamp
            - entry_policy: Entry policy JSON (parsed if present)
            - exit_policy: Exit policy JSON (parsed if present)
        Returns None if pitch not found or error occurs.

    Database Tables:
        - pm_pitches: Contains PM pitch data
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM pm_pitches WHERE id = %s",
                    (pitch_id,)
                )
                result = cur.fetchone()

                if not result:
                    return None

                # Convert to dict
                columns = [desc[0] for desc in cur.description]
                pitch_dict = dict(zip(columns, result))

                # Parse JSON fields if they exist
                if pitch_dict.get('entry_policy'):
                    try:
                        pitch_dict['entry_policy'] = json.loads(pitch_dict['entry_policy'])
                    except (json.JSONDecodeError, TypeError):
                        pass

                if pitch_dict.get('exit_policy'):
                    try:
                        pitch_dict['exit_policy'] = json.loads(pitch_dict['exit_policy'])
                    except (json.JSONDecodeError, TypeError):
                        pass

                logger.info(f"Found pitch {pitch_id} in database")
                return pitch_dict

    except Exception as e:
        logger.error(f"Error fetching pitch {pitch_id}: {e}", exc_info=True)
        return None
