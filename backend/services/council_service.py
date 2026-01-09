"""Council service for council synthesis logic."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from backend.db.council_db import (
    save_peer_reviews as db_save_peer_reviews,
    save_chairman_decision as db_save_chairman_decision,
)
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.peer_review import PeerReviewStage, PEER_REVIEWS
from backend.pipeline.stages.chairman import ChairmanStage, CHAIRMAN_DECISION
from backend.utils.formatters import _format_council_for_frontend

logger = logging.getLogger(__name__)


class CouncilService:
    """
    Service class for council synthesis operations.

    Provides business logic for council peer review and chairman decision synthesis
    including:
    - Peer review generation using PeerReviewStage
    - Chairman decision generation using ChairmanStage
    - Council data storage in database
    - Integration with PM pitches and market data

    This service acts as a bridge between API routes and database/pipeline operations,
    encapsulating business logic and data transformations for the council process.
    """

    def __init__(self):
        """Initialize the CouncilService."""
        pass

    async def synthesize_council(
        self,
        pm_pitches_raw: List[Dict[str, Any]],
        research_context: Optional[Dict[str, Any]] = None,
        pipeline_state: Any = None,
        week_id: Optional[str] = None,
        research_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize council decision through peer review and chairman stages.

        Executes the council pipeline stages to generate peer reviews from multiple
        PM models reviewing each other's pitches, then synthesizes a final chairman
        decision. Updates job status in pipeline_state throughout the process.

        Args:
            pm_pitches_raw: List of raw PM pitch dictionaries with full context.
                Each pitch should contain:
                - model: Model name
                - account: Account name
                - instrument: Trading instrument
                - direction: Trade direction
                - [other pitch fields]
            research_context: Optional research context containing:
                - research_packs: Research Pack A and B
                - market_snapshot: Current market conditions
            pipeline_state: Global pipeline state object for job tracking
            week_id: Week identifier for the council session (optional)
            research_date: ISO format research date (optional)

        Returns:
            Dict containing:
                - job_id: Unique identifier for this job
                - status: Job status ('running', 'complete', 'error')
                - started_at: ISO timestamp when job started
                - progress: Progress tracking dict with status, progress, message
                - results: Formatted council results (only when complete)
                - peer_reviews: Raw peer review data (only when complete)
                - chairman_decision: Raw chairman decision data (only when complete)
                - error: Error message (only on error)

        Raises:
            Exception: If council synthesis fails
        """
        job_id = str(uuid.uuid4())

        try:
            # Initialize job status
            job_status = {
                "job_id": job_id,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "progress": {
                    "status": "running",
                    "progress": 10,
                    "message": "Initializing council synthesis...",
                },
            }

            if pipeline_state:
                pipeline_state.jobs[job_id] = job_status
                pipeline_state.council_status = "synthesizing"

            logger.info(f"Starting council synthesis with {len(pm_pitches_raw)} pitches")

            # Validate input
            if not pm_pitches_raw:
                raise ValueError("No PM pitches provided for council synthesis")

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 20
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    "Preparing council context..."
                )

            # Create pipeline context with pitches and research data
            context = PipelineContext()

            # Set PM pitches in context
            from backend.pipeline.stages.pm_pitch import PM_PITCHES
            context.data[PM_PITCHES] = pm_pitches_raw

            # Set research context if provided
            if research_context:
                if research_context.get("research_packs"):
                    context.data["research_pack_a"] = research_context["research_packs"].get("packA")
                    context.data["research_pack_b"] = research_context["research_packs"].get("packB")
                context.data["market_snapshot"] = research_context.get("market_snapshot", {})

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 30
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    f"Conducting peer reviews among {len(pm_pitches_raw)} portfolio managers..."
                )

            # Stage 1: Peer Review
            logger.info("Executing PeerReviewStage...")
            peer_review_stage = PeerReviewStage()
            context = await peer_review_stage.execute(context)

            # Extract peer reviews
            peer_reviews = context.data.get(PEER_REVIEWS, [])
            logger.info(f"Generated {len(peer_reviews)} peer reviews")

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 60
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    "Chairman synthesizing final decision..."
                )

            # Stage 2: Chairman Decision
            logger.info("Executing ChairmanStage...")
            chairman_stage = ChairmanStage()
            context = await chairman_stage.execute(context)

            # Extract chairman decision
            chairman_decision = context.data.get(CHAIRMAN_DECISION, {})
            logger.info(f"Chairman decision generated: {chairman_decision.get('selected_pitch', 'unknown')}")

            # Update progress
            if pipeline_state:
                pipeline_state.jobs[job_id]["progress"]["progress"] = 80
                pipeline_state.jobs[job_id]["progress"]["message"] = (
                    "Saving council results to database..."
                )

            # Save to database if week_id and research_date provided
            if week_id and research_date:
                try:
                    # Extract label_to_model mapping from context
                    label_to_model = context.data.get("label_to_model", {})

                    # Save peer reviews
                    db_save_peer_reviews(
                        week_id=week_id,
                        peer_reviews=peer_reviews,
                        research_date=research_date,
                        pm_pitches=pm_pitches_raw,
                        label_to_model=label_to_model,
                    )
                    logger.info(f"Saved {len(peer_reviews)} peer reviews to database")

                    # Save chairman decision
                    db_save_chairman_decision(
                        week_id=week_id,
                        chairman_decision=chairman_decision,
                        research_date=research_date,
                    )
                    logger.info("Saved chairman decision to database")

                except Exception as e:
                    logger.error(f"Error saving council data to database: {e}", exc_info=True)
                    # Continue despite database error - we still have the results

            # Format council results for frontend
            formatted_council = _format_council_for_frontend(context)

            # Update pipeline state
            if pipeline_state:
                pipeline_state.peer_reviews = peer_reviews
                pipeline_state.council_decision = formatted_council
                pipeline_state.council_status = "complete"

                # Update job status
                pipeline_state.jobs[job_id]["status"] = "complete"
                pipeline_state.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                pipeline_state.jobs[job_id]["progress"] = {
                    "status": "complete",
                    "progress": 100,
                    "message": "Council synthesis completed successfully",
                }
                pipeline_state.jobs[job_id]["results"] = formatted_council
                pipeline_state.jobs[job_id]["peer_reviews"] = peer_reviews
                pipeline_state.jobs[job_id]["chairman_decision"] = chairman_decision

            return job_status

        except Exception as e:
            logger.error(f"Error in council synthesis: {e}", exc_info=True)

            if pipeline_state:
                pipeline_state.council_status = "error"
                pipeline_state.jobs[job_id]["status"] = "error"
                pipeline_state.jobs[job_id]["error"] = str(e)
                pipeline_state.jobs[job_id]["progress"] = {
                    "status": "error",
                    "progress": 0,
                    "message": f"Error: {str(e)}",
                }

            raise

    def get_council_decision(
        self,
        pipeline_state: Any = None
    ) -> Dict[str, Any]:
        """
        Get the current council decision from pipeline state.

        Retrieves the cached council decision from pipeline state. The decision
        includes chairman's final selection and peer reviews.

        Args:
            pipeline_state: Global pipeline state object

        Returns:
            Dict containing formatted council decision with:
                - selected_pitch: The pitch selected by the chairman
                - reasoning: Chairman's reasoning
                - peer_reviews: List of peer review summaries
            Returns empty dict if no decision available or error occurs.
        """
        try:
            if pipeline_state and hasattr(pipeline_state, 'council_decision'):
                decision = pipeline_state.council_decision
                if decision:
                    logger.info("Retrieved council decision from pipeline state")
                    return decision
                else:
                    logger.info("No council decision available in pipeline state")
                    return {}
            else:
                logger.warning("Pipeline state not available or has no council_decision attribute")
                return {}

        except Exception as e:
            logger.error(f"Error in get_council_decision: {e}", exc_info=True)
            return {}

    def get_peer_reviews(
        self,
        pipeline_state: Any = None
    ) -> List[Dict[str, Any]]:
        """
        Get the current peer reviews from pipeline state.

        Retrieves the cached peer reviews from pipeline state. These are the
        raw peer review objects before chairman synthesis.

        Args:
            pipeline_state: Global pipeline state object

        Returns:
            List of peer review dictionaries. Each dict contains:
                - reviewer_model: Name of the reviewing model
                - pitch_label: Label of the pitch being reviewed
                - [other review fields]: Review content and scores
            Returns empty list if no reviews available or error occurs.
        """
        try:
            if pipeline_state and hasattr(pipeline_state, 'peer_reviews'):
                reviews = pipeline_state.peer_reviews
                if reviews:
                    logger.info(f"Retrieved {len(reviews)} peer reviews from pipeline state")
                    return reviews
                else:
                    logger.info("No peer reviews available in pipeline state")
                    return []
            else:
                logger.warning("Pipeline state not available or has no peer_reviews attribute")
                return []

        except Exception as e:
            logger.error(f"Error in get_peer_reviews: {e}", exc_info=True)
            return []
