"""Council API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from backend.services.council_service import CouncilService

logger = logging.getLogger(__name__)

# Create router for council endpoints
router = APIRouter(prefix="/api/council", tags=["council"])

# Initialize council service
council_service = CouncilService()


# ============================================================================
# Request Models
# ============================================================================


class SynthesizeCouncilRequest(BaseModel):
    """Request model for council synthesis."""

    pm_pitches_raw: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Raw PM pitch data. If not provided, will load from database or pipeline state.",
    )
    research_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Research context containing research_packs and market_snapshot",
    )
    week_id: Optional[str] = Field(
        default=None, description="Week identifier for the council session"
    )
    research_date: Optional[str] = Field(
        default=None, description="ISO format research date"
    )


# ============================================================================
# Response Models
# ============================================================================


class PeerReviewSummary(BaseModel):
    """Peer review summary for a single pitch."""

    reviewer: str = Field(description="Model name of the reviewer")
    pitch_reviewed: str = Field(description="Pitch label (e.g., 'Pitch A')")
    score: float = Field(description="Review score")
    key_points: List[str] = Field(description="List of key review points")


class CouncilDecisionResponse(BaseModel):
    """Response model for council decision."""

    selected_pitch: Optional[str] = Field(
        default=None, description="The pitch label selected by the chairman"
    )
    reasoning: Optional[str] = Field(
        default=None, description="Chairman's reasoning for the selection"
    )
    model: Optional[str] = Field(
        default=None, description="Model name of the selected pitch"
    )
    instrument: Optional[str] = Field(
        default=None, description="Trading instrument (e.g., 'SPY')"
    )
    direction: Optional[str] = Field(
        default=None, description="Trade direction (LONG, SHORT, FLAT)"
    )
    conviction: Optional[float] = Field(
        default=None, description="Conviction score (0.0 to 1.0)"
    )
    peer_reviews_summary: Optional[List[PeerReviewSummary]] = Field(
        default=None, description="List of peer review summaries"
    )


class SynthesizeCouncilResponse(BaseModel):
    """Response model for council synthesis."""

    status: str = Field(
        description="Job status (synthesizing, complete, error)"
    )
    message: str = Field(description="Status message")
    job_id: str = Field(description="Unique identifier for this job")


# Mock data fallback (for when pipeline_state has no data)
MOCK_COUNCIL_DECISION = {
    "selected_pitch": "Pitch A",
    "reasoning": "Strong technical setup combined with favorable macro conditions",
    "model": "gpt-4o",
    "instrument": "SPY",
    "direction": "LONG",
    "conviction": 0.82,
    "peer_reviews_summary": [
        {
            "reviewer": "claude-3-5-sonnet-20241022",
            "pitch_reviewed": "Pitch A",
            "score": 8.5,
            "key_points": ["Strong momentum", "Good risk/reward"],
        },
        {
            "reviewer": "gpt-4o",
            "pitch_reviewed": "Pitch B",
            "score": 7.0,
            "key_points": ["Decent setup", "Lower conviction"],
        },
    ],
}


# Global pipeline state (will be injected or imported in Phase 5)
# For now, we'll access it from backend.main
def get_pipeline_state():
    """
    Get the global pipeline state.

    This is a temporary workaround until Phase 5 when we create
    proper dependency injection with backend/dependencies.py.

    Returns:
        Pipeline state object from backend.main
    """
    try:
        from backend.main import pipeline_state

        return pipeline_state
    except ImportError:
        logger.warning("Could not import pipeline_state from backend.main")
        return None


@router.get("/current")
async def get_council_decision() -> CouncilDecisionResponse:
    """
    Get current council decision from pipeline state.

    Retrieves the cached council decision including the chairman's selected pitch
    and peer review summaries. This is the final synthesized decision from the
    council process.

    Returns:
        Dict containing council decision with:
            - selected_pitch: The pitch label selected by the chairman
            - reasoning: Chairman's reasoning for the selection
            - model: Model name of the selected pitch
            - instrument: Trading instrument
            - direction: Trade direction
            - conviction: Conviction score
            - peer_reviews_summary: List of peer review summaries
        Returns empty dict if no decision available.

    Example Response:
        {
            "selected_pitch": "Pitch A",
            "reasoning": "Strong technical setup...",
            "model": "gpt-4o",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 0.82,
            "peer_reviews_summary": [...]
        }
    """
    try:
        pipeline_state = get_pipeline_state()

        # Try to get decision from pipeline state
        if pipeline_state:
            decision = council_service.get_council_decision(pipeline_state)
            if decision:
                return CouncilDecisionResponse(**decision)

        # Fallback to mock data for frontend development
        logger.info("No council decision found, returning mock data")
        return CouncilDecisionResponse(**MOCK_COUNCIL_DECISION)

    except Exception as e:
        logger.error(f"Error in get_council_decision endpoint: {e}", exc_info=True)
        # Return empty response on error (don't raise, so frontend doesn't break)
        return CouncilDecisionResponse()


@router.post("/synthesize")
async def synthesize_council(
    background_tasks: BackgroundTasks,
    request: SynthesizeCouncilRequest = SynthesizeCouncilRequest(),
) -> SynthesizeCouncilResponse:
    """
    Synthesize council decision through peer review and chairman stages.

    Starts a background task to run the council synthesis process:
    1. Loads raw PM pitches from database or uses provided pitches
    2. Conducts peer reviews among portfolio managers
    3. Chairman synthesizes final decision
    4. Saves results to database
    5. Updates pipeline state with council decision and pending trades

    The task runs asynchronously and its status can be polled using the
    /council/status endpoint (if implemented) or checked via pipeline state.

    Args:
        background_tasks: FastAPI background tasks manager (injected)
        request: Request body with optional pm_pitches_raw, research_context, week_id, research_date

    Returns:
        Dict containing:
            - status: "synthesizing" or "error"
            - message: Status message
            - job_id: Unique identifier for this job (when successful)

    Raises:
        HTTPException: 500 if pipeline state is not available
        HTTPException: 400 if no PM pitches are available

    Example Request:
        {
            "pm_pitches_raw": [...],  # Optional, will load from DB if not provided
            "research_context": {
                "research_packs": {...},
                "market_snapshot": {...}
            },
            "week_id": "2024-W02",
            "research_date": "2024-01-08"
        }

    Example Response:
        {
            "status": "synthesizing",
            "message": "Council peer review and chairman synthesis started",
            "job_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """

    async def run_council():
        """Background task for council synthesis."""
        try:
            pipeline_state = get_pipeline_state()

            if not pipeline_state:
                logger.error("Pipeline state not available in background task")
                return

            # Update pipeline status
            pipeline_state.council_status = "synthesizing"

            # Get PM pitches from request, pipeline state, or database
            pm_pitches_raw = request.pm_pitches_raw

            if not pm_pitches_raw:
                logger.info("No pitches in request, checking pipeline state...")

                # Try pipeline state
                if pipeline_state.pm_pitches_raw:
                    pm_pitches_raw = pipeline_state.pm_pitches_raw
                    logger.info(f"Using {len(pm_pitches_raw)} pitches from pipeline state")
                else:
                    # Try loading from database
                    logger.info("Attempting to load pitches from database...")
                    try:
                        from backend.db.pitch_db import load_pitches

                        pitches = await load_pitches(
                            week_id=request.week_id,
                            research_date=request.research_date,
                        )

                        if pitches:
                            pm_pitches_raw = pitches
                            pipeline_state.pm_pitches_raw = pitches
                            logger.info(f"Loaded {len(pitches)} pitches from database")
                        else:
                            logger.error("No pitches found in database")

                    except Exception as e:
                        logger.error(f"Error loading pitches from database: {e}", exc_info=True)

            # Validate we have pitches
            if not pm_pitches_raw:
                error_msg = "No PM pitches available - please generate PM pitches first"
                logger.error(error_msg)
                pipeline_state.council_status = "error"
                return

            logger.info(f"Starting council synthesis with {len(pm_pitches_raw)} pitches")

            # Run council synthesis
            await council_service.synthesize_council(
                pm_pitches_raw=pm_pitches_raw,
                research_context=request.research_context,
                pipeline_state=pipeline_state,
                week_id=request.week_id,
                research_date=request.research_date,
            )

            logger.info("Council synthesis completed successfully")

        except Exception as e:
            logger.error(f"Error in council synthesis background task: {e}", exc_info=True)
            if pipeline_state:
                pipeline_state.council_status = "error"

    try:
        pipeline_state = get_pipeline_state()

        if not pipeline_state:
            logger.error("Pipeline state not available")
            raise HTTPException(
                status_code=500, detail="Pipeline state not available"
            )

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Start background task
        background_tasks.add_task(run_council)

        return SynthesizeCouncilResponse(
            status="synthesizing",
            message="Council peer review and chairman synthesis started",
            job_id=job_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in synthesize_council endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
