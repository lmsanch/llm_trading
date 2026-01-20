"""FastAPI backend for LLM Council and Trading Dashboard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.pipeline.stages.research import get_week_id
from backend.config import get_cors_origins
from backend.redis_client import get_redis_client, close_redis_client


class PipelineState:
    """In-memory state for the trading pipeline."""

    def __init__(self):
        self.current_week = get_week_id()
        self.research_status = "pending"
        self.pm_status = "pending"
        self.council_status = "pending"
        self.execution_status = "pending"
        self.research_packs = None
        self.pm_pitches = None
        self.pm_pitches_raw = None
        self.peer_reviews = None
        self.council_decision = None
        self.execution_results = None
        self.pending_trades = []
        self.executed_trades = []
        self.jobs = {}  # job_id -> status_dict


# Global state
pipeline_state = PipelineState()

# Application setup
app = FastAPI(title="LLM Council API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from backend.api.market import router as market_router
from backend.api.research import router as research_router, graphs_router, data_package_router
from backend.api.pitches import router as pitches_router
from backend.api.council import router as council_router
from backend.api.trades import router as trades_router
from backend.api.monitor import router as monitor_router
from backend.api.conversations import router as conversations_router

app.include_router(market_router)
app.include_router(research_router)
app.include_router(graphs_router)
app.include_router(data_package_router)
app.include_router(pitches_router)
app.include_router(council_router)
app.include_router(trades_router)
app.include_router(monitor_router)
app.include_router(conversations_router)


@app.on_event("startup")
async def startup_event():
    print("Startup: Listing all registered routes:")
    for route in app.routes:
        print(f" - {route.path} [{getattr(route, 'methods', [])}]")

    # Initialize Redis client
    try:
        redis_client = get_redis_client()
        if redis_client.ping():
            print("✓ Redis connected successfully")
        else:
            print("✗ Redis ping failed - caching will be disabled")
    except Exception as e:
        print(f"✗ Redis initialization failed: {e}")
        print("  Application will continue without caching")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    print("Shutting down...")
    close_redis_client()
    print("✓ Redis connection closed")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "LLM Council API",
        "week": pipeline_state.current_week,
        "research_status": pipeline_state.research_status,
        "pm_status": pipeline_state.pm_status,
        "council_status": pipeline_state.council_status,
        "execution_status": pipeline_state.execution_status,
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint that verifies Redis connectivity."""
    status = {
        "status": "ok",
        "service": "LLM Council API",
        "redis": "unknown"
    }

    try:
        redis_client = get_redis_client()
        if redis_client.ping():
            status["redis"] = "connected"
        else:
            status["redis"] = "disconnected"
            status["status"] = "degraded"
    except Exception as e:
        status["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status


if __name__ == "__main__":
    import uvicorn
    from backend.config import BACKEND_PORT

    print(f"🚀 Starting LLM Trading backend on http://0.0.0.0:{BACKEND_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=BACKEND_PORT)
