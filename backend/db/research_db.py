"""Research database operations."""

import logging
from typing import Dict, List, Optional, Any

from backend.db_helpers import fetch_one, fetch_all
from backend.cache.decorator import cached
from backend.cache.keys import research_history_key

logger = logging.getLogger(__name__)


async def get_latest_research() -> Optional[Dict[str, Any]]:
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
        # Get latest complete research report
        row = await fetch_one("""
            SELECT
                id, week_id, provider, model,
                natural_language, structured_json,
                status, error_message, created_at
            FROM research_reports
            WHERE status = 'complete'
            ORDER BY created_at DESC
            LIMIT 1
        """)

        if not row:
            return {}

        return {
            "id": str(row["id"]),
            "week_id": row["week_id"],
            "provider": row["provider"],
            "model": row["model"],
            "natural_language": row["natural_language"],
            "structured_json": row["structured_json"],
            "status": row["status"],
            "error_message": row["error_message"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    except Exception as e:
        logger.error(f"Error fetching latest research: {e}")
        return {}


async def get_research_by_id(report_id: str) -> Optional[Dict[str, Any]]:
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
        row = await fetch_one(
            """
            SELECT
                id, week_id, provider, model,
                natural_language, structured_json,
                status, error_message, created_at
            FROM research_reports
            WHERE id = $1
        """,
            report_id,
        )

        if not row:
            return None

        return {
            "id": str(row["id"]),
            "week_id": row["week_id"],
            "provider": row["provider"],
            "model": row["model"],
            "natural_language": row["natural_language"],
            "structured_json": row["structured_json"],
            "status": row["status"],
            "error_message": row["error_message"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    except Exception as e:
        logger.error(f"Error fetching research report {report_id}: {e}")
        return None


@cached(
    key_builder=lambda days=90: research_history_key(days),
    ttl=300  # 5 minutes - research is generated at most once per day
)
async def get_research_history(days: int = 90) -> Dict[str, Any]:
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
        # Get research grouped by date
        # Note: PostgreSQL INTERVAL doesn't support parameter substitution directly,
        # so we use NOW() - make_interval(days => $1) instead
        rows = await fetch_all(
            """
            SELECT
                DATE(created_at) as research_date,
                provider,
                COUNT(*) as count,
                array_agg(id ORDER BY created_at DESC) as report_ids,
                array_agg(status ORDER BY created_at DESC) as statuses
            FROM research_reports
            WHERE created_at >= NOW() - make_interval(days => $1)
            GROUP BY DATE(created_at), provider
            ORDER BY research_date DESC, provider
        """,
            days,
        )

        # Format for frontend
        history = {}
        for row in rows:
            date_str = row["research_date"].strftime("%Y-%m-%d")
            provider = row["provider"]
            count = row["count"]
            report_ids = row["report_ids"]
            statuses = row["statuses"]

            # asyncpg returns PostgreSQL arrays as Python lists directly
            # Convert UUIDs to strings
            report_ids_list = [str(id) for id in report_ids] if report_ids else []
            statuses_list = list(statuses) if statuses else []

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
