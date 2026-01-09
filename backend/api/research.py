"""Research API endpoints."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from backend.services.research_service import ResearchService

logger = logging.getLogger(__name__)

# Create router for research endpoints
router = APIRouter(prefix="/api/research", tags=["research"])

# Initialize research service
research_service = ResearchService()


class GenerateResearchRequest(BaseModel):
    """Request model for research generation."""

    query: Optional[str] = Field(default="", description="Optional query string")
    models: list[str] = Field(
        default=["perplexity"],
        description="List of models to use for research generation",
    )
    prompt_override: Optional[str] = Field(
        default=None, description="Optional custom prompt to override the default"
    )


# Mock data fallback (for when pipeline_state has no data)
MOCK_RESEARCH_PACKS = {
    "perplexity": {
        "source": "perplexity",
        "model": "perplexity-sonar-deep-research",
        "macro_regime": {
            "risk_mode": "RISK_ON",
            "description": "Markets are pricing in a soft landing with Fed rate cuts expected in Q1. Inflation data is cooperating, leading to a rotation from defensive into cyclical sectors.",
        },
        "top_narratives": [
            "Fed Pivot Imminent: 90% chance of cut in March",
            "AI Capex Cycle: Cloud providers increasing spend",
            "China Stimulus: New fiscal measures announced",
        ],
        "tradable_candidates": [
            {"ticker": "NVDA", "rationale": "Key beneficiary of AI spending"},
            {"ticker": "IWM", "rationale": "Small caps benefit from lower rates"},
            {"ticker": "TLT", "rationale": "Yields likely to fall further"},
        ],
        "event_calendar": [
            {"date": "2025-01-08", "event": "CPI Data Release", "impact": "HIGH"},
            {"date": "2025-01-15", "event": "Fed FOMC Meeting", "impact": "CRITICAL"},
        ],
    },
    "gemini": {
        "source": "gemini",
        "model": "gemini-2.0-flash-thinking-exp",
        "macro_regime": {
            "risk_mode": "NEUTRAL",
            "description": "While disinflation is tracking, growth signals are mixed. Labor market cooling faster than expected suggests caution. Prefer quality over pure momentum.",
        },
        "top_narratives": [
            "Consumer Weakness: Credit card delinquencies rising",
            "Tech Valuation concerns: Multiples at historic highs",
            "Energy Sector rotation: Oil supply constraints",
        ],
        "tradable_candidates": [
            {"ticker": "MSFT", "rationale": "Defensive growth play"},
            {"ticker": "XLE", "rationale": "Energy hedge against geopolitics"},
            {"ticker": "GLD", "rationale": "Safe haven demand"},
        ],
        "event_calendar": [
            {"date": "2025-01-10", "event": "Bank Earnings Start", "impact": "MEDIUM"},
            {"date": "2025-01-20", "event": "Inauguration Day", "impact": "MEDIUM"},
        ],
    },
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


@router.get("/prompt")
async def get_research_prompt() -> Dict[str, Any]:
    """
    Get the current research prompt for review.

    Reads the research prompt from the markdown file and returns it with metadata
    including version, last updated timestamp, tracked instruments, and trading horizon.

    Returns:
        Dict containing:
            - prompt: The prompt content as a string
            - version: Prompt version (e.g., "1.1")
            - last_updated: ISO timestamp of last modification
            - instruments: List of tracked instruments (10 ETFs)
            - horizon: Trading horizon (7 DAYS ONLY)

    Raises:
        HTTPException: 404 if the prompt file does not exist

    Example Response:
        {
            "prompt": "# Research Prompt\\n...",
            "version": "1.1",
            "last_updated": "2024-01-08T12:00:00",
            "instruments": ["SPY", "QQQ", "IWM", ...],
            "horizon": "7 DAYS ONLY"
        }
    """
    try:
        result = research_service.get_research_prompt()
        return result
    except FileNotFoundError as e:
        logger.error(f"Prompt file not found: {e}")
        raise HTTPException(status_code=404, detail="Prompt file not found")
    except Exception as e:
        logger.error(f"Error in get_research_prompt endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_research() -> Dict[str, Any]:
    """
    Get current research packs from pipeline state.

    Returns the research packs currently stored in pipeline state. If no research
    has been generated yet, returns mock data for frontend development/testing.

    Returns:
        Dict containing research packs with keys:
            - perplexity: Research pack from Perplexity model
            - gemini: Research pack from Gemini model (if available)
        Each pack contains: source, model, macro_regime, top_narratives,
        tradable_candidates, event_calendar

    Example Response:
        {
            "perplexity": {
                "source": "perplexity",
                "model": "perplexity-sonar-deep-research",
                "macro_regime": {...},
                "top_narratives": [...],
                "tradable_candidates": [...],
                "event_calendar": [...]
            }
        }
    """
    try:
        pipeline_state = get_pipeline_state()

        if pipeline_state and pipeline_state.research_packs:
            return pipeline_state.research_packs

        # Fallback to mock data
        return MOCK_RESEARCH_PACKS
    except Exception as e:
        logger.error(f"Error in get_current_research endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_research() -> Dict[str, Any]:
    """
    Get the latest complete research report from database.

    Retrieves the most recent research report with status='complete' from the
    research_reports table. Returns empty dict if no research is available.

    Returns:
        Dict containing:
            - id: Research report UUID
            - week_id: Week identifier (e.g., "2024-W02")
            - provider: Research provider (e.g., 'perplexity', 'gemini')
            - model: Model used for research
            - natural_language: Natural language summary
            - structured_json: Structured JSON data with graphs and analysis
            - status: Report status ('complete', 'error', etc.)
            - error_message: Error message if any
            - created_at: Creation timestamp (ISO format)
        Returns empty dict if no research found or error occurs.

    Database Tables:
        - research_reports: Contains research report data

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "week_id": "2024-W02",
            "provider": "perplexity",
            "model": "perplexity-sonar-deep-research",
            "natural_language": "Market analysis...",
            "structured_json": {...},
            "status": "complete",
            "error_message": null,
            "created_at": "2024-01-08T12:00:00"
        }
    """
    try:
        result = research_service.get_latest_research()
        return result
    except Exception as e:
        logger.error(f"Error in get_latest_research endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_research(
    background_tasks: BackgroundTasks,
    request: GenerateResearchRequest = GenerateResearchRequest(),
) -> Dict[str, Any]:
    """
    Generate new research packs using AI models.

    Starts a background task to generate market research using the specified models
    (e.g., Perplexity, Gemini). The task runs asynchronously and its status can be
    polled using the /research/status endpoint.

    Args:
        background_tasks: FastAPI background tasks manager (injected)
        request: Request body with models and optional prompt override

    Returns:
        Dict containing:
            - job_id: Unique identifier for this job
            - status: Job status ('running', 'complete', 'error')
            - started_at: ISO timestamp when job started
            - models: List of models being used
            - perplexity: Progress tracking dict with status, progress, message

    Raises:
        HTTPException: 500 if there's an error starting the research generation

    Example Request:
        {
            "models": ["perplexity"],
            "prompt_override": "Focus on tech stocks"
        }

    Example Response:
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "running",
            "started_at": "2024-01-08T12:00:00",
            "models": ["perplexity"],
            "perplexity": {
                "status": "running",
                "progress": 10,
                "message": "Initializing..."
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

        # Start research generation in background
        async def run_research_task():
            """Background task to run research generation."""
            try:
                await research_service.generate_research(
                    models=request.models,
                    prompt_override=request.prompt_override,
                    pipeline_state=pipeline_state,
                )
            except Exception as e:
                logger.error(f"Error in background research task: {e}", exc_info=True)

        # Get the job status that was created by generate_research
        # We need to call it synchronously first to get the job_id
        import uuid

        job_id = str(uuid.uuid4())

        # Initialize job status in pipeline_state before starting background task
        job_status = {
            "job_id": job_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "models": request.models,
            "perplexity": {
                "status": "running",
                "progress": 10,
                "message": "Initializing...",
            },
        }

        if pipeline_state:
            pipeline_state.jobs[job_id] = job_status

        # Start background task
        background_tasks.add_task(
            lambda: research_service.generate_research(
                models=request.models,
                prompt_override=request.prompt_override,
                pipeline_state=pipeline_state,
            )
        )

        return job_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_research endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_research_status(job_id: str) -> Dict[str, Any]:
    """
    Poll status of a research generation job.

    Returns the current status and progress of a research job. Used for polling
    the status of asynchronous research generation started by /research/generate.

    Args:
        job_id: The unique job identifier returned from /research/generate

    Returns:
        Dict containing job status with:
            - job_id: The job identifier
            - status: Current status ('running', 'complete', 'error')
            - started_at: When the job started (ISO format)
            - completed_at: When the job completed (ISO format, if complete)
            - models: List of models being used
            - perplexity: Progress dict with status, progress (0-100), message
            - results: Research results (only when status='complete')
            - error: Error message (only when status='error')

    Raises:
        HTTPException: 404 if job_id is not found

    Example Response:
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "complete",
            "started_at": "2024-01-08T12:00:00",
            "completed_at": "2024-01-08T12:05:00",
            "models": ["perplexity"],
            "perplexity": {
                "status": "complete",
                "progress": 100,
                "message": "Finished"
            },
            "results": {...}
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
        logger.error(f"Error in get_research_status endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_research_history(days: int = 90) -> Dict[str, Any]:
    """
    Get research history for calendar widget.

    Retrieves research reports from the last N days, grouped by creation date
    and provider. Useful for displaying research history in a calendar view.

    Args:
        days: Number of days to look back (default: 90)

    Returns:
        Dict containing:
            - history: Dict keyed by date string (YYYY-MM-DD) with provider data
            - days: Number of days queried
            - error: Error message if query failed (optional)

    Database Tables:
        - research_reports: Contains research report data

    Example Response:
        {
            "history": {
                "2024-01-08": {
                    "providers": [
                        {
                            "name": "perplexity",
                            "count": 2,
                            "report_ids": ["uuid1", "uuid2"],
                            "statuses": ["complete", "complete"]
                        }
                    ],
                    "total": 2
                }
            },
            "days": 90
        }
    """
    try:
        result = research_service.get_research_history(days=days)
        return result
    except Exception as e:
        logger.error(f"Error in get_research_history endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_research_results(job_id: str) -> Dict[str, Any]:
    """
    Get final results of a completed research job.

    Retrieves the final research results for a completed job. The job must be
    in 'complete' status, otherwise an error is returned.

    Args:
        job_id: The unique job identifier

    Returns:
        Dict containing the research results with research packs

    Raises:
        HTTPException: 404 if job_id is not found
        HTTPException: 400 if job is not complete

    Example Response:
        {
            "perplexity": {
                "source": "perplexity",
                "macro_regime": {...},
                "top_narratives": [...],
                ...
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

        if job_id not in pipeline_state.jobs:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")

        job = pipeline_state.jobs[job_id]

        if job["status"] != "complete":
            logger.warning(
                f"Job {job_id} is not complete, status: {job['status']}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Job is not complete (status: {job['status']})",
            )

        return job["results"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_research_results endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
async def verify_research(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mark research as verified by human.

    Updates the pipeline state to mark research as verified, indicating that
    a human has reviewed and approved the research output. This is used in
    the workflow to track which research has been manually reviewed.

    Args:
        data: Request body containing 'id' field (or "current" for latest)

    Returns:
        Dict containing:
            - status: "success"
            - message: Confirmation message

    Example Request:
        {
            "id": "current"
        }

    Example Response:
        {
            "status": "success",
            "message": "Research current verified"
        }
    """
    try:
        pipeline_state = get_pipeline_state()

        if not pipeline_state:
            logger.error("Pipeline state not available")
            raise HTTPException(
                status_code=500, detail="Pipeline state not available"
            )

        research_id = data.get("id", "current")
        result = research_service.verify_research(
            research_id=research_id, pipeline_state=pipeline_state
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify_research endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{report_id}")
async def get_research_report(report_id: str) -> Dict[str, Any]:
    """
    Get a specific research report by ID.

    Retrieves a research report from the database by its UUID. Returns full
    report data including natural language summary and structured JSON.

    Args:
        report_id: UUID of the research report

    Returns:
        Dict containing:
            - id: Research report UUID
            - week_id: Week identifier
            - provider: Research provider
            - model: Model used
            - natural_language: Natural language summary
            - structured_json: Structured data
            - status: Report status
            - error_message: Error message if any
            - created_at: Creation timestamp

    Raises:
        HTTPException: 404 if report is not found

    Database Tables:
        - research_reports: Contains research report data

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "week_id": "2024-W02",
            "provider": "perplexity",
            ...
        }
    """
    try:
        result = research_service.get_research_by_id(report_id)

        if not result:
            logger.warning(f"Research report not found: {report_id}")
            raise HTTPException(status_code=404, detail="Report not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_research_report endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Create separate router for graphs endpoints (under /api/graphs prefix)
graphs_router = APIRouter(prefix="/api/graphs", tags=["graphs"])


@graphs_router.get("/latest")
async def get_latest_graphs() -> Dict[str, Any]:
    """
    Get the latest knowledge graphs from database.

    Retrieves the weekly knowledge graph from the latest research report's
    structured JSON. The graph contains entities, relationships, and market
    structure information.

    Returns:
        Dict containing:
            - date: Creation timestamp of the research
            - weekly_graph: Weekly knowledge graph from structured_json
        Returns empty dict if no research or no graph available.

    Database Tables:
        - research_reports: Contains research report data with structured_json

    Example Response:
        {
            "date": "2024-01-08T12:00:00",
            "weekly_graph": {
                "entities": [...],
                "relationships": [...],
                ...
            }
        }
    """
    try:
        result = research_service.get_latest_graphs()
        return result
    except Exception as e:
        logger.error(f"Error in get_latest_graphs endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Create separate router for data-package endpoints
data_package_router = APIRouter(prefix="/api/data-package", tags=["data-package"])


@data_package_router.get("/latest")
async def get_latest_data_package() -> Dict[str, Any]:
    """
    Get the latest complete data package.

    Combines latest research, market metrics, and current prices into a single
    comprehensive data package. Useful for endpoints that need all market context.

    Returns:
        Dict containing:
            - date: Most recent data date (ISO format)
            - research: Latest complete research report
            - market_metrics: Latest 7-day returns and correlation matrix
            - current_prices: Latest OHLCV data for tracked symbols

    Database Tables:
        - research_reports: Research data
        - rolling_7day_log_returns: Market metrics
        - correlation_matrix: Correlation data
        - daily_bars: Price data

    Example Response:
        {
            "date": "2024-01-08T12:00:00",
            "research": {...},
            "market_metrics": {...},
            "current_prices": {...}
        }
    """
    try:
        result = await research_service.get_latest_data_package()
        return result
    except Exception as e:
        logger.error(f"Error in get_latest_data_package endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
