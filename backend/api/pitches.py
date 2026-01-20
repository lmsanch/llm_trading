"""PM Pitch API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from backend.services.pitch_service import PitchService

logger = logging.getLogger(__name__)

# Create router for pitch endpoints
router = APIRouter(prefix="/api/pitches", tags=["pitches"])

# Initialize pitch service
pitch_service = PitchService()


class GeneratePitchesRequest(BaseModel):
    """Request model for pitch generation."""

    models: list[str] = Field(
        default=["gpt-4o", "claude-3-5-sonnet-20241022"],
        description="List of PM models to use for pitch generation",
    )
    research_context: Dict[str, Any] = Field(
        default={},
        description="Research context containing research_packs and market_snapshot",
    )
    week_id: Optional[str] = Field(
        default=None, description="Week identifier for the pitches"
    )
    research_date: Optional[str] = Field(
        default=None, description="ISO format research date"
    )


class ApprovePitchRequest(BaseModel):
    """Request model for pitch approval."""

    pitch_id: int = Field(..., description="Database ID of the pitch to approve")


# Mock data fallback (for when pipeline_state has no data)
MOCK_PM_PITCHES = [
    {
        "model": "gpt-4o",
        "account": "paper",
        "instrument": "SPY",
        "direction": "LONG",
        "conviction": 0.75,
        "rationale": "Strong momentum in broad market with Fed pivot imminent",
        "entry_price": 471.20,
        "target_price": 485.00,
        "stop_price": 465.00,
        "position_size": 0.15,
    },
    {
        "model": "claude-3-5-sonnet-20241022",
        "account": "paper",
        "instrument": "TLT",
        "direction": "LONG",
        "conviction": 0.68,
        "rationale": "Yields likely to fall further with disinflation trend",
        "entry_price": 92.50,
        "target_price": 96.00,
        "stop_price": 90.00,
        "position_size": 0.12,
    },
]


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
async def get_current_pitches(
    week_id: Optional[str] = None,
    research_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get current PM pitches from database or pipeline state.

    Retrieves PM pitches based on week_id or research_date. If neither is provided,
    returns the latest pitches. Falls back to mock data if no pitches are available.

    Args:
        week_id: Week identifier to filter by (optional)
        research_date: Research date to filter by (optional, takes precedence)

    Returns:
        List of pitch dictionaries. Each dict contains:
            - model: Model name (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')
            - account: Account name (e.g., 'paper')
            - instrument: Trading instrument (e.g., 'SPY', 'TLT')
            - direction: Trade direction ('LONG', 'SHORT', 'FLAT')
            - conviction: Conviction score (0.0 to 1.0)
            - rationale: Pitch rationale/reasoning
            - entry_price: Proposed entry price
            - target_price: Target price for take profit
            - stop_price: Stop loss price
            - position_size: Position size as fraction of portfolio
        Returns empty list if no pitches found.

    Database Tables:
        - pm_pitches: Contains PM pitch data

    Example Response:
        [
            {
                "model": "gpt-4o",
                "account": "paper",
                "instrument": "SPY",
                "direction": "LONG",
                "conviction": 0.75,
                "rationale": "Strong momentum...",
                "entry_price": 471.20,
                "target_price": 485.00,
                "stop_price": 465.00,
                "position_size": 0.15
            }
        ]
    """
    try:
        # Try to get pitches from database first
        pitches = await pitch_service.get_current_pitches(
            week_id=week_id,
            research_date=research_date
        )

        if pitches:
            return pitches

        # Fallback to pipeline state
        pipeline_state = get_pipeline_state()
        if pipeline_state and pipeline_state.pm_pitches:
            return pipeline_state.pm_pitches

        # Fallback to mock data for frontend development
        logger.info("No pitches found, returning mock data")
        return MOCK_PM_PITCHES

    except Exception as e:
        logger.error(f"Error in get_current_pitches endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_pitches(
    background_tasks: BackgroundTasks,
    request: GeneratePitchesRequest = GeneratePitchesRequest(),
) -> Dict[str, Any]:
    """
    Generate new PM pitches using AI models.

    Starts a background task to generate portfolio manager pitches using the specified
    models (e.g., GPT-4o, Claude). The task runs asynchronously and its status can be
    polled using the /pitches/status endpoint.

    Args:
        background_tasks: FastAPI background tasks manager (injected)
        request: Request body with models, research context, week_id, research_date

    Returns:
        Dict containing:
            - job_id: Unique identifier for this job
            - status: Job status ('running', 'complete', 'error')
            - started_at: ISO timestamp when job started
            - models: List of PM models being used
            - progress: Progress tracking dict with status, progress (0-100), message

    Raises:
        HTTPException: 500 if there's an error starting the pitch generation

    Example Request:
        {
            "models": ["gpt-4o", "claude-3-5-sonnet-20241022"],
            "research_context": {
                "research_packs": {...},
                "market_snapshot": {...}
            },
            "week_id": "2024-W02",
            "research_date": "2024-01-08"
        }

    Example Response:
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "running",
            "started_at": "2024-01-08T12:00:00",
            "models": ["gpt-4o", "claude-3-5-sonnet-20241022"],
            "progress": {
                "status": "running",
                "progress": 10,
                "message": "Initializing PM pitch generation..."
            }
        }
    """
    try:
        pipeline_state = get_pipeline_state()

        if not pipeline_state:
            logger.error("Pipeline state not available")
            raise HTTPException(
                status_code=500, detail="Pipeline state not available"
            )

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Initialize job status in pipeline_state before starting background task
        job_status = {
            "job_id": job_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "models": request.models,
            "progress": {
                "status": "running",
                "progress": 10,
                "message": "Initializing PM pitch generation...",
            },
        }

        if pipeline_state:
            pipeline_state.jobs[job_id] = job_status

        # Start background task for pitch generation
        background_tasks.add_task(
            lambda: pitch_service.generate_pitches(
                models=request.models,
                research_context=request.research_context,
                pipeline_state=pipeline_state,
                week_id=request.week_id,
                research_date=request.research_date,
            )
        )

        return job_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_pitches endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_pitches_status(job_id: str) -> Dict[str, Any]:
    """
    Poll status of a pitch generation job.

    Returns the current status and progress of a pitch generation job. Used for polling
    the status of asynchronous pitch generation started by /pitches/generate.

    Args:
        job_id: The unique job identifier returned from /pitches/generate

    Returns:
        Dict containing job status with:
            - job_id: The job identifier
            - status: Current status ('running', 'complete', 'error')
            - started_at: When the job started (ISO format)
            - completed_at: When the job completed (ISO format, if complete)
            - models: List of PM models being used
            - progress: Progress dict with status, progress (0-100), message
            - results: Formatted pitch results (only when status='complete')
            - raw_pitches: Raw pitch data (only when status='complete')
            - error: Error message (only when status='error')

    Raises:
        HTTPException: 404 if job_id is not found
        HTTPException: 500 if pipeline state is not available

    Example Response:
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "complete",
            "started_at": "2024-01-08T12:00:00",
            "completed_at": "2024-01-08T12:05:00",
            "models": ["gpt-4o", "claude-3-5-sonnet-20241022"],
            "progress": {
                "status": "complete",
                "progress": 100,
                "message": "Pitches generated successfully"
            },
            "results": [...],
            "raw_pitches": [...]
        }
    """
    try:
        pipeline_state = get_pipeline_state()

        if not pipeline_state:
            logger.error("Pipeline state not available")
            raise HTTPException(
                status_code=500, detail="Pipeline state not available"
            )

        if job_id not in pipeline_state.jobs:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        return pipeline_state.jobs[job_id]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_pitches_status endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id}/approve")
async def approve_pitch(id: int) -> Dict[str, Any]:
    """
    Approve a specific PM pitch for trading.

    Marks a pitch as approved, indicating that it has been reviewed and is ready for
    council synthesis and trade execution. This is a manual approval step in the workflow.

    Args:
        id: Database ID of the pitch to approve

    Returns:
        Dict containing:
            - status: "success" or "error"
            - message: Confirmation or error message
            - pitch: The approved pitch data (if found)

    Raises:
        HTTPException: 404 if pitch is not found
        HTTPException: 500 if there's an error approving the pitch

    Database Tables:
        - pm_pitches: Contains PM pitch data

    Example Response:
        {
            "status": "success",
            "message": "Pitch 42 approved successfully",
            "pitch": {
                "model": "gpt-4o",
                "instrument": "SPY",
                "direction": "LONG",
                ...
            }
        }
    """
    try:
        pipeline_state = get_pipeline_state()

        result = await pitch_service.approve_pitch(
            pitch_id=id,
            pipeline_state=pipeline_state
        )

        if result["status"] == "error":
            if "not found" in result["message"].lower():
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=500, detail=result["message"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in approve_pitch endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
