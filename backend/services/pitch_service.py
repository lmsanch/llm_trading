"""Pitch service for PM pitch business logic."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from backend.db.pitch_db import (
    save_pitches as db_save_pitches,
    load_pitches as db_load_pitches,
    find_pitch_by_id as db_find_pitch_by_id,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.pm_pitch import PMPitchStage, PM_PITCHES
from backend.utils.formatters import _format_pitches_for_frontend

logger = logging.getLogger(__name__)


class PitchService:
    """
    Service class for PM pitch operations.

    Provides business logic for PM pitch generation and management including:
    - Pitch generation using PMPitchStage
    - Current pitches retrieval from database
    - Pitch approval workflow
    - Integration with market data and research

    This service acts as a bridge between API routes and database/pipeline operations,
    encapsulating business logic and data transformations.
    """

    def __init__(self):
        """Initialize the PitchService."""
        pass

    async def get_current_pitches(
        self,
        week_id: Optional[str] = None,
        research_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get current PM pitches from database.

        Retrieves pitches based on week_id or research_date. If neither is provided,
        returns the latest pitches.

        Args:
            week_id: Week identifier to filter by (optional)
            research_date: Research date to filter by (optional, takes precedence)

        Returns:
            List of pitch dictionaries. Each dict contains all pitch data including:
                - model: Model name
                - account: Account name
                - instrument: Trading instrument
                - direction: Trade direction
                - conviction: Conviction score
                - [other pitch fields from pitch_data]
            Returns empty list if no pitches found or error occurs.

        Database Tables:
            - pm_pitches: Contains PM pitch data
        """
        try:
            pitches = await db_load_pitches(week_id=week_id, research_date=research_date)
            logger.info(f"Retrieved {len(pitches)} pitches from database")
            return pitches
        except Exception as e:
            logger.error(f"Error in get_current_pitches: {e}")
            return []

    async def generate_pitches(
        self,
        models: List[str],
        research_context: Dict[str, Any],
        pipeline_state: Any = None,
        week_id: Optional[str] = None,
        research_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate PM pitches using the PMPitchStage.

        Executes the PM pitch pipeline stage to generate investment pitches from
        multiple portfolio manager models. Updates job status in pipeline_state
        throughout the process.

        Args:
            models: List of PM model names to generate pitches (e.g., ['gpt-4o', 'claude-3-5-sonnet-20241022'])
            research_context: Research context containing:
                - research_packs: Research Pack A and B
                - market_snapshot: Current market conditions
            pipeline_state: Global pipeline state object for job tracking
            week_id: Week identifier for the pitches (optional)
            research_date: ISO format research date (optional)

        Returns:
            Dict containing:
                - job_id: Unique identifier for this job
                - status: Job status ('running', 'complete', 'error')
                - started_at: ISO timestamp when job started
                - models: List of models being used
                - progress: Progress tracking dict with status, progress, message
                - results: Formatted pitch results (only when complete)
                - raw_pitches: Raw pitch data with full context (only when complete)
                - error: Error message (only on error)

        Raises:
            Exception: If pitch generation fails
        """
        job_id = str(uuid.uuid4())

        try:
            # Initialize job status
            job_status = {
                "job_id": job_id,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "models": models,
                "progress": {
                    "status": "running",
                    "progress": 10,
                    "message": "Initializing PM pitch generation...",
                },
            }

            if pipeline_state:
                pipeline_state.jobs[job_id] = job_status
                pipeline_state.pm_status = "generating"

            # Get market context
            logger.info(f"Generating pitches with models: {models}")

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 30
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    "Fetching market data..."
                )

            # Import market service here to avoid circular dependencies
            from backend.services.market_service import MarketService

            market_service = MarketService()

            # Get market metrics and current prices
            market_metrics = await market_service.get_market_metrics()
            current_prices = await market_service.get_current_prices()

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 50
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    f"Consulting {len(models)} portfolio managers..."
                )

            # Create pipeline context with research and market data
            context = PipelineContext()

            # Set research packs from research context
            if research_context and research_context.get("research_packs"):
                context.data["research_pack_a"] = research_context["research_packs"].get("packA")
                context.data["research_pack_b"] = research_context["research_packs"].get("packB")
                context.data["market_snapshot"] = research_context.get("market_snapshot", {})

            # Set market data
            context.data["market_metrics"] = market_metrics
            context.data["current_prices"] = current_prices

            # Configure and run PMPitchStage
            stage = PMPitchStage(selected_models=models)

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 70
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    "Generating pitches..."
                )

            result_context = await stage.execute(context)

            # Extract raw pitches from context
            raw_pitches = result_context.data.get(PM_PITCHES, [])

            # Format pitches for frontend
            formatted_pitches = _format_pitches_for_frontend(result_context)

            # Save pitches to database
            if raw_pitches and week_id:
                try:
                    await db_save_pitches(
                        week_id=week_id,
                        pitches_raw=raw_pitches,
                        research_date=research_date
                    )
                    logger.info(f"Saved {len(raw_pitches)} pitches to database")
                except Exception as e:
                    logger.error(f"Error saving pitches to database: {e}")

            # Update pipeline state
            if pipeline_state:
                pipeline_state.pm_pitches = formatted_pitches
                pipeline_state.pm_pitches_raw = raw_pitches
                pipeline_state.pm_status = "complete"

                # Update job status
                pipeline_state.jobs[job_id]["status"] = "complete"
                pipeline_state.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                pipeline_state.jobs[job_id]["progress"] = {
                    "status": "complete",
                    "progress": 100,
                    "message": "Pitches generated successfully",
                }
                pipeline_state.jobs[job_id]["results"] = formatted_pitches
                pipeline_state.jobs[job_id]["raw_pitches"] = raw_pitches

            return job_status

        except Exception as e:
            logger.error(f"Error generating pitches: {e}", exc_info=True)

            if pipeline_state:
                pipeline_state.pm_status = "error"
                pipeline_state.jobs[job_id]["status"] = "error"
                pipeline_state.jobs[job_id]["error"] = str(e)
                pipeline_state.jobs[job_id]["progress"] = {
                    "status": "error",
                    "progress": 0,
                    "message": f"Error: {str(e)}",
                }

            raise

    async def approve_pitch(
        self,
        pitch_id: int,
        pipeline_state: Any = None
    ) -> Dict[str, Any]:
        """
        Approve a specific PM pitch.

        Marks a pitch as approved for trading. This typically happens before
        council synthesis and trade execution.

        Args:
            pitch_id: Database ID of the pitch to approve
            pipeline_state: Global pipeline state object (optional)

        Returns:
            Dict containing:
                - status: "success" or "error"
                - message: Confirmation or error message
                - pitch: The approved pitch data (if found)

        Raises:
            HTTPException: If pitch not found or approval fails
        """
        try:
            # Retrieve pitch from database
            pitch = await db_find_pitch_by_id(pitch_id)

            if not pitch:
                logger.warning(f"Pitch {pitch_id} not found for approval")
                return {
                    "status": "error",
                    "message": f"Pitch {pitch_id} not found"
                }

            # Mark pitch as approved (in a real system, this would update a status field)
            # For now, we just log the approval
            logger.info(f"Pitch {pitch_id} approved for model {pitch.get('model')}")

            # Update pipeline state if provided
            if pipeline_state and hasattr(pipeline_state, 'approved_pitches'):
                if not pipeline_state.approved_pitches:
                    pipeline_state.approved_pitches = []
                pipeline_state.approved_pitches.append(pitch_id)

            return {
                "status": "success",
                "message": f"Pitch {pitch_id} approved successfully",
                "pitch": pitch
            }

        except Exception as e:
            logger.error(f"Error approving pitch {pitch_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error approving pitch: {str(e)}"
            }

    async def get_pitch_by_id(self, pitch_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific pitch by its database ID.

        Args:
            pitch_id: Database primary key ID of the pitch

        Returns:
            Dict containing all pitch data, or None if not found.

        Database Tables:
            - pm_pitches: Contains PM pitch data
        """
        try:
            pitch = await db_find_pitch_by_id(pitch_id)
            if pitch:
                logger.info(f"Retrieved pitch {pitch_id} from database")
            else:
                logger.warning(f"Pitch {pitch_id} not found")
            return pitch
        except Exception as e:
            logger.error(f"Error in get_pitch_by_id for {pitch_id}: {e}")
            return None
