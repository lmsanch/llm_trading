"""Research service for research business logic."""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import uuid

from backend.db.research_db import (
    get_latest_research as db_get_latest_research,
    get_research_by_id as db_get_research_by_id,
    get_research_history as db_get_research_history,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.research import ResearchStage
from backend.utils.formatters import _format_research_for_frontend

logger = logging.getLogger(__name__)


class ResearchService:
    """
    Service class for research operations.

    Provides business logic for research generation and retrieval including:
    - Research prompt management
    - Research generation using ResearchStage
    - Latest research retrieval from database
    - Research history for calendar widget
    - Research verification
    - Data package aggregation

    This service acts as a bridge between API routes and database/pipeline operations,
    encapsulating business logic and data transformations.
    """

    def __init__(self):
        """Initialize the ResearchService."""
        pass

    def get_research_prompt(self) -> Dict[str, Any]:
        """
        Get the current research prompt for review.

        Reads the research prompt from the markdown file and returns it with metadata.

        Returns:
            Dict containing:
                - prompt: The prompt content as a string
                - version: Prompt version
                - last_updated: ISO timestamp of last modification
                - instruments: List of tracked instruments
                - horizon: Trading horizon (7 DAYS ONLY)

        Raises:
            FileNotFoundError: If the prompt file does not exist
        """
        try:
            prompt_path = Path("config/prompts/research_prompt.md")

            if not prompt_path.exists():
                logger.error(f"Prompt file not found at {prompt_path}")
                raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

            with open(prompt_path, "r") as f:
                content = f.read()

            return {
                "prompt": content,
                "version": "1.1",
                "last_updated": datetime.fromtimestamp(
                    prompt_path.stat().st_mtime
                ).isoformat(),
                "instruments": [
                    "SPY",
                    "QQQ",
                    "IWM",
                    "TLT",
                    "HYG",
                    "UUP",
                    "GLD",
                    "USO",
                    "VIXY",
                    "SH",
                ],
                "horizon": "7 DAYS ONLY",
            }
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error reading research prompt: {e}")
            raise

    def get_latest_research(self) -> Dict[str, Any]:
        """
        Get the latest complete research report from database.

        Retrieves the most recent research report with status='complete'.

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
            return db_get_latest_research()
        except Exception as e:
            logger.error(f"Error in get_latest_research: {e}")
            return {}

    def get_research_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific research report by ID.

        Args:
            report_id: UUID of the research report

        Returns:
            Dict containing research report data, or None if not found.

        Database Tables:
            - research_reports: Contains research report data
        """
        try:
            return db_get_research_by_id(report_id)
        except Exception as e:
            logger.error(f"Error in get_research_by_id for {report_id}: {e}")
            return None

    def get_research_history(self, days: int = 90) -> Dict[str, Any]:
        """
        Get research history grouped by date and provider.

        Retrieves research reports from the last N days, grouped by creation date
        and provider. Useful for displaying research history in a calendar widget.

        Args:
            days: Number of days to look back (default: 90)

        Returns:
            Dict containing:
                - history: Dict keyed by date string (YYYY-MM-DD) with provider data
                - days: Number of days queried
                - error: Error message if query failed (optional)

        Database Tables:
            - research_reports: Contains research report data
        """
        try:
            return db_get_research_history(days)
        except Exception as e:
            logger.error(f"Error in get_research_history: {e}")
            return {"history": {}, "days": days, "error": str(e)}

    async def generate_research(
        self,
        models: List[str],
        prompt_override: Optional[str] = None,
        pipeline_state: Any = None,
    ) -> Dict[str, Any]:
        """
        Generate new research using the ResearchStage.

        Executes the research pipeline stage to generate market research using
        the specified models (e.g., perplexity, gemini). Updates job status in
        pipeline_state throughout the process.

        Args:
            models: List of model names to use for research (e.g., ['perplexity'])
            prompt_override: Optional custom prompt to override the default
            pipeline_state: Global pipeline state object for job tracking

        Returns:
            Dict containing:
                - job_id: Unique identifier for this job
                - status: Job status ('running', 'complete', 'error')
                - started_at: ISO timestamp when job started
                - models: List of models being used
                - perplexity: Progress tracking dict with status, progress, message
                - results: Research results (only when complete)
                - error: Error message (only on error)

        Raises:
            Exception: If research generation fails
        """
        job_id = str(uuid.uuid4())

        try:
            # Initialize job status
            job_status = {
                "job_id": job_id,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "models": models,
                "perplexity": {
                    "status": "running",
                    "progress": 10,
                    "message": "Initializing...",
                },
            }

            if pipeline_state:
                pipeline_state.jobs[job_id] = job_status
                pipeline_state.research_status = "generating"

            # Simulate progress for better UI experience
            if pipeline_state:
                pipeline_state.jobs[job_id]["perplexity"]["progress"] = 30
                pipeline_state.jobs[job_id]["perplexity"]["message"] = (
                    "Fetching market data..."
                )

            # Run research stage
            context = PipelineContext()

            # Configure stage with selection and override
            stage = ResearchStage(
                selected_models=models, prompt_override=prompt_override
            )

            # Update progress further
            if pipeline_state:
                pipeline_state.jobs[job_id]["perplexity"]["progress"] = 60
                pipeline_state.jobs[job_id]["perplexity"]["message"] = (
                    "Consulting Perplexity..."
                )

            result_context = await stage.execute(context)

            # Store results
            results = _format_research_for_frontend(result_context)

            if pipeline_state:
                pipeline_state.research_packs = results  # Update global state with latest
                pipeline_state.research_status = "complete"

                # Update job status
                pipeline_state.jobs[job_id]["status"] = "complete"
                pipeline_state.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                pipeline_state.jobs[job_id]["perplexity"] = {
                    "status": "complete",
                    "progress": 100,
                    "message": "Finished",
                }
                pipeline_state.jobs[job_id]["results"] = results

            return job_status

        except Exception as e:
            logger.error(f"Error generating research: {e}", exc_info=True)

            if pipeline_state:
                pipeline_state.research_status = "error"
                pipeline_state.jobs[job_id]["status"] = "error"
                pipeline_state.jobs[job_id]["error"] = str(e)

            raise

    def verify_research(self, research_id: str, pipeline_state: Any = None) -> Dict[str, Any]:
        """
        Mark research as verified by human.

        Updates the pipeline state to mark research as verified, indicating
        that a human has reviewed and approved the research output.

        Args:
            research_id: ID of the research to verify (or "current" for latest)
            pipeline_state: Global pipeline state object

        Returns:
            Dict containing:
                - status: "success"
                - message: Confirmation message
        """
        try:
            if pipeline_state:
                pipeline_state.research_status = "verified"

            logger.info(f"Research {research_id} marked as verified")
            return {
                "status": "success",
                "message": f"Research {research_id} verified"
            }
        except Exception as e:
            logger.error(f"Error verifying research {research_id}: {e}")
            raise

    def get_latest_graphs(self) -> Dict[str, Any]:
        """
        Get the latest knowledge graphs from database.

        Retrieves the weekly graph from the latest research report's structured JSON.

        Returns:
            Dict containing:
                - date: Creation timestamp of the research
                - weekly_graph: Weekly knowledge graph from structured_json
            Returns empty dict if no research or no graph available.

        Database Tables:
            - research_reports: Contains research report data with structured_json
        """
        try:
            report = self.get_latest_research()

            if report and report.get("structured_json"):
                return {
                    "date": report.get("created_at"),
                    "weekly_graph": report.get("structured_json", {}).get("weekly_graph"),
                }

            return {}
        except Exception as e:
            logger.error(f"Error getting latest graphs: {e}")
            return {}

    async def get_latest_data_package(self) -> Dict[str, Any]:
        """
        Get the latest complete data package with research and market data.

        Combines latest research, market metrics, and current prices into a single
        comprehensive data package. Useful for endpoints that need all market context.

        Returns:
            Dict containing:
                - date: Most recent data date (ISO format)
                - research: Latest complete research report
                - market_metrics: Latest 7-day returns and correlation matrix
                - current_prices: Latest OHLCV data for tracked symbols
        """
        try:
            # Import here to avoid circular dependencies
            from backend.services.market_service import MarketService

            market_service = MarketService()

            research = self.get_latest_research()
            metrics = await market_service.get_market_metrics()
            prices = await market_service.get_current_prices()

            return {
                "date": research.get("created_at") if research else None,
                "research": research,
                "market_metrics": metrics,
                "current_prices": prices,
            }
        except Exception as e:
            logger.error(f"Error getting latest data package: {e}")
            return {
                "date": None,
                "research": {},
                "market_metrics": None,
                "current_prices": None,
            }
