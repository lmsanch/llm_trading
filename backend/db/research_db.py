"""Research database operations."""

import logging
from typing import Dict, List, Optional, Any

from backend.db.database import DatabaseConnection

logger = logging.getLogger(__name__)


def get_latest_research() -> Optional[Dict[str, Any]]:
    """
    Get the latest complete research report from database.

    Retrieves the most recent research report with status='complete',
    ordered by creation date descending.

    Returns:
        Dict containing:
            - id: Research report UUID
            - week_id: Week identifier
            - provider: Research provider (e.g., 'perplexity', 'gemini')
            - model: Model used for research
            - natural_language: Natural language summary
            - structured_json: Structured JSON data
            - status: Report status
            - error_message: Error message if any
            - created_at: Creation timestamp (ISO format)
        Returns empty dict if no research found or error occurs.

    Database Tables:
        - research_reports: Contains research report data
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                # Get latest complete research report
                cur.execute("""
                    SELECT
                        id, week_id, provider, model,
                        natural_language, structured_json,
                        status, error_message, created_at
                    FROM research_reports
                    WHERE status = 'complete'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)

                row = cur.fetchone()

                if not row:
                    return {}

                return {
                    "id": str(row[0]),
                    "week_id": row[1],
                    "provider": row[2],
                    "model": row[3],
                    "natural_language": row[4],
                    "structured_json": row[5],
                    "status": row[6],
                    "error_message": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                }

    except Exception as e:
        logger.error(f"Error fetching latest research: {e}")
        return {}


def get_research_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific research report by ID.

    Retrieves a research report by its unique ID.

    Args:
        report_id: UUID of the research report

    Returns:
        Dict containing:
            - id: Research report UUID
            - week_id: Week identifier
            - provider: Research provider (e.g., 'perplexity', 'gemini')
            - model: Model used for research
            - natural_language: Natural language summary
            - structured_json: Structured JSON data
            - status: Report status
            - error_message: Error message if any
            - created_at: Creation timestamp (ISO format)
        Returns None if report not found or error occurs.

    Database Tables:
        - research_reports: Contains research report data
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id, week_id, provider, model,
                        natural_language, structured_json,
                        status, error_message, created_at
                    FROM research_reports
                    WHERE id = %s
                """,
                    (report_id,),
                )

                row = cur.fetchone()

                if not row:
                    return None

                return {
                    "id": str(row[0]),
                    "week_id": row[1],
                    "provider": row[2],
                    "model": row[3],
                    "natural_language": row[4],
                    "structured_json": row[5],
                    "status": row[6],
                    "error_message": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                }

    except Exception as e:
        logger.error(f"Error fetching research report {report_id}: {e}")
        return None


def get_research_history(days: int = 90) -> Dict[str, Any]:
    """
    Get research history grouped by date and provider.

    Retrieves research reports from the last N days, grouped by creation date
    and provider. Useful for displaying research history in a calendar widget.

    Args:
        days: Number of days to look back (default: 90)

    Returns:
        Dict containing:
            - history: Dict keyed by date string (YYYY-MM-DD) with values:
                - providers: List of provider dicts with:
                    - name: Provider name
                    - count: Number of reports
                    - report_ids: List of report UUIDs
                    - statuses: List of report statuses
                - total: Total count for this date
            - days: Number of days queried
            - error: Error message if query failed (optional)
        Returns empty history dict if error occurs.

    Database Tables:
        - research_reports: Contains research report data
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                # Get research grouped by date
                cur.execute(
                    """
                    SELECT
                        DATE(created_at) as research_date,
                        provider,
                        COUNT(*) as count,
                        array_agg(id ORDER BY created_at DESC) as report_ids,
                        array_agg(status ORDER BY created_at DESC) as statuses
                    FROM research_reports
                    WHERE created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(created_at), provider
                    ORDER BY research_date DESC, provider
                """
                    % days
                )

                rows = cur.fetchall()

                # Format for frontend
                history = {}
                for row in rows:
                    date_str = row[0].strftime("%Y-%m-%d")
                    provider = row[1]
                    count = row[2]
                    report_ids = row[3]
                    statuses = row[4]

                    # Convert PostgreSQL arrays to Python lists
                    # psycopg2 may return arrays as strings like "{uuid1,uuid2}" or as Python lists
                    if isinstance(report_ids, list):
                        report_ids_list = [str(id) for id in report_ids]
                    elif isinstance(report_ids, str):
                        # Parse PostgreSQL array string format: "{uuid1,uuid2}"
                        report_ids_list = (
                            report_ids.strip("{}").split(",")
                            if report_ids and report_ids != "{}"
                            else []
                        )
                    else:
                        report_ids_list = []

                    if isinstance(statuses, list):
                        statuses_list = list(statuses)
                    elif isinstance(statuses, str):
                        statuses_list = (
                            statuses.strip("{}").split(",")
                            if statuses and statuses != "{}"
                            else []
                        )
                    else:
                        statuses_list = []

                    if date_str not in history:
                        history[date_str] = {"providers": [], "total": 0}

                    history[date_str]["providers"].append(
                        {
                            "name": provider,
                            "count": count,
                            "report_ids": report_ids_list,
                            "statuses": statuses_list,
                        }
                    )
                    history[date_str]["total"] += count

                return {"history": history, "days": days}

    except Exception as e:
        logger.error(f"Error fetching research history: {e}")
        return {"history": {}, "days": days, "error": str(e)}
