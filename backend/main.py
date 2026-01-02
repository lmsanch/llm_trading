"""FastAPI backend for LLM Council and Trading Dashboard."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
from datetime import datetime
import os
from pathlib import Path

# Legacy imports
from . import storage
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings
)

# Pipeline imports
from .pipeline.context import PipelineContext
from .pipeline.base import Pipeline
from .pipeline.stages.research import ResearchStage, get_week_id, RESEARCH_PACK_A, RESEARCH_PACK_B, MARKET_SNAPSHOT
from .pipeline.stages.pm_pitch import PMPitchStage, PM_PITCHES
from .pipeline.stages.peer_review import PeerReviewStage, PEER_REVIEWS
from .pipeline.stages.chairman import ChairmanStage, CHAIRMAN_DECISION
from .pipeline.stages.execution import ExecutionStage, EXECUTION_RESULT
from .multi_alpaca_client import MultiAlpacaManager

app = FastAPI(title="LLM Council API")

# Enable CORS for local development and Tailscale VPN
from backend.config import get_cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class PipelineState:
    """In-memory state for the trading pipeline."""

    def __init__(self):
        self.current_week = get_week_id()
        self.research_status = "pending"  # pending, generating, complete, verified
        self.pm_status = "pending"  # pending, generating, complete
        self.council_status = "pending"  # pending, synthesizing, complete
        self.execution_status = "pending"  # pending, executing, complete

        # Cached results
        self.research_packs = None
        self.pm_pitches = None
        self.peer_reviews = None
        self.council_decision = None
        self.execution_results = None

        # Pending trades
        self.pending_trades = []
        self.executed_trades = []
        
        # Async Job Tracking
        self.jobs = {} # job_id -> status_dict

# Global state
pipeline_state = PipelineState()

# ============================================================================
# MODELS
# ============================================================================

class GenerateResearchRequest(BaseModel):
    query: Optional[str] = ""
    models: List[str] = ["perplexity", "gemini"]
    prompt_override: Optional[str] = None

class ExecuteTradesRequest(BaseModel):
    trade_ids: Optional[List[int]] = None

# ============================================================================
# MOCK DATA FALLBACK
# ============================================================================

MOCK_RESEARCH_PACKS = {
  "perplexity": {
    "source": "perplexity",
    "model": "perplexity-sonar-deep-research",
    "macro_regime": {
      "risk_mode": "RISK_ON",
      "description": "Markets are pricing in a soft landing with Fed rate cuts expected in Q1. Inflation data is cooperating, leading to a rotation from defensive into cyclical sectors."
    },
    "top_narratives": [
      "Fed Pivot Imminent: 90% chance of cut in March",
      "AI Capex Cycle: Cloud providers increasing spend",
      "China Stimulus: New fiscal measures announced"
    ],
    "tradable_candidates": [
      { "ticker": "NVDA", "rationale": "Key beneficiary of AI spending" },
      { "ticker": "IWM", "rationale": "Small caps benefit from lower rates" },
      { "ticker": "TLT", "rationale": "Yields likely to fall further" }
    ],
    "event_calendar": [
      { "date": "2025-01-08", "event": "CPI Data Release", "impact": "HIGH" },
      { "date": "2025-01-15", "event": "Fed FOMC Meeting", "impact": "CRITICAL" }
    ]
  },
  "gemini": {
    "source": "gemini",
    "model": "gemini-2.0-flash-thinking-exp",
    "macro_regime": {
      "risk_mode": "NEUTRAL",
      "description": "While disinflation is tracking, growth signals are mixed. Labor market cooling faster than expected suggests caution. Prefer quality over pure momentum."
    },
    "top_narratives": [
      "Consumer Weakness: Credit card delinquencies rising",
      "Tech Valuation concerns: Multiples at historic highs",
      "Energy Sector rotation: Oil supply constraints"
    ],
    "tradable_candidates": [
      { "ticker": "MSFT", "rationale": "Defensive growth play" },
      { "ticker": "XLE", "rationale": "Energy hedge against geopolitics" },
      { "ticker": "GLD", "rationale": "Safe haven demand" }
    ],
    "event_calendar": [
      { "date": "2025-01-10", "event": "Bank Earnings Start", "impact": "MEDIUM" },
      { "date": "2025-01-20", "event": "Inauguration Day", "impact": "MEDIUM" }
    ]
  }
}

MOCK_POSITIONS = [
  { "account": "COUNCIL", "symbol": "SPY", "qty": 50, "avg_price": 475.20, "current_price": 482.30, "pl": 355 },
  { "account": "CHATGPT", "symbol": "SPY", "qty": 40, "avg_price": 475.20, "current_price": 482.30, "pl": 284 },
  { "account": "GEMINI", "symbol": "TLT", "qty": -30, "avg_price": 98.50, "current_price": 97.20, "pl": 39 },
  { "account": "CLAUDE", "symbol": "-", "qty": 0, "avg_price": 0, "current_price": 0, "pl": 0 },
  { "account": "GROQ", "symbol": "SPY", "qty": 35, "avg_price": 475.20, "current_price": 482.30, "pl": 249 },
  { "account": "DEEPSEEK", "symbol": "GLD", "qty": 25, "avg_price": 185.40, "current_price": 186.10, "pl": 18 },
]

MOCK_ACCOUNTS = [
  { "name": "COUNCIL", "equity": 100355, "cash": 75920, "pl": 355 },
  { "name": "CHATGPT", "equity": 100284, "cash": 80984, "pl": 284 },
  { "name": "GEMINI", "equity": 99961, "cash": 70089, "pl": 39 },
  { "name": "CLAUDE", "equity": 100000, "cash": 100000, "pl": 0 },
  { "name": "GROQ", "equity": 100249, "cash": 83589, "pl": 249 },
  { "name": "DEEPSEEK", "equity": 100018, "cash": 95328, "pl": 18 },
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    print("Startup: Listing all registered routes:")
    for route in app.routes:
        print(f" - {route.path} [{route.methods}]")

def _format_research_for_frontend(context: PipelineContext) -> Dict[str, Any]:
    """Format research results for frontend consumption."""
    research_a = context.get(RESEARCH_PACK_A)
    research_b = context.get(RESEARCH_PACK_B)
    market_snapshot = context.get(MARKET_SNAPSHOT)

    result = {}

    if market_snapshot:
        result["market_snapshot"] = market_snapshot

    if research_a:
        # Extract from new dual-format response (natural_language + structured_json)
        structured = research_a.get("structured_json", {})
        result["perplexity"] = {
            "source": research_a.get("source", "perplexity"),
            "model": research_a.get("model", "perplexity-sonar-pro"),
            "natural_language": research_a.get("natural_language", ""),
            "macro_regime": structured.get("macro_regime", {}),
            "top_narratives": structured.get("top_narratives", []),
            # Support both old (tradable_candidates) and new (asset_setups) formats
            "tradable_candidates": structured.get("tradable_candidates") or structured.get("asset_setups", []),
            "asset_setups": structured.get("asset_setups") or structured.get("tradable_candidates", []),
            "event_calendar": structured.get("event_calendar") or structured.get("event_calendar_next_7d", []),
            "confidence_notes": structured.get("confidence_notes", {}),
            "status": "complete" if not research_a.get("error") else "error",
            "generated_at": research_a.get("generated_at", "")
        }

    if research_b:
        # Extract from new dual-format response (natural_language + structured_json)
        structured = research_b.get("structured_json", {})
        result["gemini"] = {
            "source": research_b.get("source", "gemini"),
            "model": research_b.get("model", "gemini-2.0-flash-thinking"),
            "natural_language": research_b.get("natural_language", ""),
            "macro_regime": structured.get("macro_regime", {}),
            "top_narratives": structured.get("top_narratives", []),
            # Support both old (tradable_candidates) and new (asset_setups) formats
            "tradable_candidates": structured.get("tradable_candidates") or structured.get("asset_setups", []),
            "asset_setups": structured.get("asset_setups") or structured.get("tradable_candidates", []),
            "event_calendar": structured.get("event_calendar") or structured.get("event_calendar_next_7d", []),
            "confidence_notes": structured.get("confidence_notes", {}),
            "status": "complete" if not research_b.get("error") else "error",
            "generated_at": research_b.get("generated_at", "")
        }

    return result

def _format_pitches_for_frontend(context: PipelineContext) -> List[Dict[str, Any]]:
    """Format PM pitches for frontend consumption."""
    pitches = context.get(PM_PITCHES, [])

    formatted = []
    for i, pitch in enumerate(pitches):
        model_info = pitch.get("model_info", {})
        formatted.append({
            "id": i + 1,
            "model": pitch.get("model", "unknown"),
            "account": model_info.get("account", "Unknown"),
            "instrument": pitch.get("instrument", "N/A"),
            "direction": pitch.get("direction", "FLAT"),
            "horizon": pitch.get("horizon", "N/A"),
            "conviction": pitch.get("conviction", 0),
            "thesis_bullets": pitch.get("thesis_bullets", []),
            "indicators": pitch.get("indicators", []),
            "invalidation": pitch.get("invalidation", "N/A"),
            "status": "complete"
        })

    return formatted

def _format_council_for_frontend(context: PipelineContext) -> Dict[str, Any]:
    """Format council decision for frontend consumption."""
    decision = context.get(CHAIRMAN_DECISION)

    if not decision:
        return {}

    selected_trade = decision.get("selected_trade", {})

    return {
        "selected_trade": {
            "instrument": selected_trade.get("instrument", "N/A"),
            "direction": selected_trade.get("direction", "FLAT"),
            "conviction": decision.get("conviction", 0),
            "position_size": selected_trade.get("position_size", "0%")
        },
        "rationale": decision.get("rationale", ""),
        "dissent_summary": decision.get("dissent_summary", []),
        "monitoring_plan": {
            "key_levels": decision.get("monitoring_plan", {}).get("key_levels", []),
            "event_risks": decision.get("monitoring_plan", {}).get("event_risks", [])
        },
        "peer_review_scores": decision.get("peer_review_scores", {})
    }

def _format_trades_for_frontend(context: PipelineContext) -> List[Dict[str, Any]]:
    """Format trades for frontend consumption."""
    execution_result = context.get(EXECUTION_RESULT)

    if not execution_result or not execution_result.get("executed"):
        # Generate pending trades from council decision
        decision = context.get(CHAIRMAN_DECISION)
        if not decision:
            return []

        selected_trade = decision.get("selected_trade", {})
        conviction = decision.get("conviction", 0)

        # Create pending trades for all accounts
        from .requesty_client import REQUESTY_MODELS

        trades = []
        for model_key, config in REQUESTY_MODELS.items():
            account = config["account"]
            if account == "COUNCIL":
                # Council trade from chairman decision
                trades.append({
                    "id": len(trades) + 101,
                    "account": account,
                    "symbol": selected_trade.get("instrument", "SPY"),
                    "direction": "BUY" if selected_trade.get("direction") == "LONG" else "SELL",
                    "qty": 50,  # Would calculate from conviction
                    "status": "pending",
                    "conviction": conviction
                })

        return trades

    # Return executed trades
    return execution_result.get("trades", [])

# ============================================================================
# TRADING DASHBOARD ENDPOINTS
# ============================================================================

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
        "execution_status": pipeline_state.execution_status
    }


# --- RESEARCH ENDPOINTS ---

@app.get("/api/research/prompt")
async def get_research_prompt():
    """Get the current research prompt for review."""
    prompt_path = Path("config/prompts/research_prompt.md")
    if not prompt_path.exists():
        raise HTTPException(status_code=404, detail="Prompt file not found")
    
    with open(prompt_path, "r") as f:
        content = f.read()
    
    return {
        "prompt": content,
        "version": "1.1",
        "last_updated": datetime.fromtimestamp(prompt_path.stat().st_mtime).isoformat(),
        "instruments": ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"],
        "horizon": "7 DAYS ONLY"
    }

@app.get("/api/research/current")
async def get_current_research():
    """Get current research packs."""
    if pipeline_state.research_packs:
        return pipeline_state.research_packs
    return MOCK_RESEARCH_PACKS

@app.get("/api/market/snapshot")
async def get_market_snapshot():
    """Get current market snapshot for research context."""
    try:
        from .storage.data_fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        snapshot = fetcher.get_market_snapshot_for_research()
        return snapshot
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/research/generate")
async def generate_research(background_tasks: BackgroundTasks, request: GenerateResearchRequest = GenerateResearchRequest()):
    """Generate new research packs."""
    job_id = str(uuid.uuid4())
    
    # Initialize job status based on selected models
    job_status = {
        "job_id": job_id,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "models": request.models
    }
    
    if "perplexity" in request.models:
        job_status["perplexity"] = {"status": "running", "progress": 10, "message": "Initializing..."}
        
    if "gemini" in request.models:
        job_status["gemini"] = {"status": "running", "progress": 10, "message": "Initializing..."}
        
    pipeline_state.jobs[job_id] = job_status

    async def run_research(jid, models, prompt_override):
        try:
            pipeline_state.research_status = "generating"
            
            # Simulate progress for better UI experience
            if "perplexity" in models:
                pipeline_state.jobs[jid]["perplexity"]["progress"] = 30
                pipeline_state.jobs[jid]["perplexity"]["message"] = "Fetching market data..."
            
            if "gemini" in models:
                pipeline_state.jobs[jid]["gemini"]["progress"] = 20
                pipeline_state.jobs[jid]["gemini"]["message"] = "Starting macro analysis..."
            
            # Run research stage
            context = PipelineContext()
            
            # configure stage with selection and override
            stage = ResearchStage(selected_models=models, prompt_override=prompt_override)
            
            # Update progress further
            if "perplexity" in models:
                pipeline_state.jobs[jid]["perplexity"]["progress"] = 60
                pipeline_state.jobs[jid]["perplexity"]["message"] = "Consulting Perplexity..."
            
            if "gemini" in models:
                pipeline_state.jobs[jid]["gemini"]["progress"] = 50
                pipeline_state.jobs[jid]["gemini"]["message"] = "Consulting Gemini..."
            
            result_context = await stage.execute(context)

            # Store results
            results = _format_research_for_frontend(result_context)
            pipeline_state.research_packs = results  # Update global state with latest
            pipeline_state.research_status = "complete"
            
            # Update job status
            pipeline_state.jobs[jid]["status"] = "complete"
            pipeline_state.jobs[jid]["completed_at"] = datetime.utcnow().isoformat()
            
            if "perplexity" in models:
                pipeline_state.jobs[jid]["perplexity"] = {"status": "complete", "progress": 100, "message": "Finished"}
            
            if "gemini" in models:
                pipeline_state.jobs[jid]["gemini"] = {"status": "complete", "progress": 100, "message": "Finished"}
                
            pipeline_state.jobs[jid]["results"] = results

        except Exception as e:
            print(f"Error generating research: {e}")
            pipeline_state.research_status = "error"
            pipeline_state.jobs[jid]["status"] = "error"
            pipeline_state.jobs[jid]["error"] = str(e)

    background_tasks.add_task(run_research, job_id, request.models, request.prompt_override)
    return pipeline_state.jobs[job_id]

@app.get("/api/research/status")
async def get_research_status(job_id: str):
    """Poll status of a research job."""
    if job_id not in pipeline_state.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return pipeline_state.jobs[job_id]

@app.get("/api/research/history")
async def get_research_history(days: int = 90):
    """Get research history for calendar widget."""
    import psycopg2
    from datetime import datetime, timedelta
    
    try:
        db_name = os.getenv("DATABASE_NAME", "llm_trading")
        db_user = os.getenv("DATABASE_USER", "luis")
        
        conn = psycopg2.connect(dbname=db_name, user=db_user)
        
        try:
            with conn.cursor() as cur:
                # Get research grouped by date
                cur.execute("""
                    SELECT 
                        DATE(created_at) as research_date,
                        provider,
                        COUNT(*) as count,
                        array_agg(id ORDER BY created_at DESC) as report_ids,
                        array_agg(status ORDER BY created_at DESC) as statuses
                    FROM research_reports
                    WHERE created_at >= NOW() - INTERVAL '90 days'
                    GROUP BY DATE(created_at), provider
                    ORDER BY research_date DESC, provider
                """, (days,))
                
                rows = cur.fetchall()
                
                # Format for frontend
                history = {}
                for row in rows:
                    date_str = row[0].strftime("%Y-%m-%d")
                    provider = row[1]
                    count = row[2]
                    report_ids = row[3]
                    statuses = row[4]
                    
                    if date_str not in history:
                        history[date_str] = {"providers": [], "total": 0}
                    
                    history[date_str]["providers"].append({
                        "name": provider,
                        "count": count,
                        "report_ids": report_ids,
                        "statuses": statuses
                    })
                    history[date_str]["total"] += count
                
                return {"history": history, "days": days}
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error fetching research history: {e}")
        return {"history": {}, "days": days, "error": str(e)}

@app.get("/api/research/{job_id}")
async def get_research_results(job_id: str):
    """Get final results of a research job."""
    if job_id not in pipeline_state.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = pipeline_state.jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail=f"Job is not complete (status: {job['status']})")
    
    return job["results"]

@app.post("/api/research/verify")
async def verify_research(data: Dict[str, Any]):
    """Mark research as verified by human."""
    research_id = data.get("id", "current")
    pipeline_state.research_status = "verified"
    return {"status": "success", "message": f"Research {research_id} verified"}

@app.get("/api/research/report/{report_id}")
async def get_research_report(report_id: str):
    """Get a specific research report by ID."""
    import psycopg2
    
    try:
        db_name = os.getenv("DATABASE_NAME", "llm_trading")
        db_user = os.getenv("DATABASE_USER", "luis")
        
        conn = psycopg2.connect(dbname=db_name, user=db_user)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, week_id, provider, model,
                        natural_language, structured_json,
                        status, error_message, created_at
                    FROM research_reports
                    WHERE id = %s
                """, (report_id,))
                
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Report not found")
                
                return {
                    "id": str(row[0]),
                    "week_id": row[1],
                    "provider": row[2],
                    "model": row[3],
                    "natural_language": row[4],
                    "structured_json": row[5],
                    "status": row[6],
                    "error_message": row[7],
                    "created_at": row[8].isoformat() if row[8] else None
                }
                
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- PM PITCH ENDPOINTS ---

@app.get("/api/pitches/current")
async def get_current_pitches():
    """Get current PM pitches."""
    if pipeline_state.pm_pitches:
        return pipeline_state.pm_pitches
    return []

@app.post("/api/pitches/generate")
async def generate_pitches(background_tasks: BackgroundTasks):
    """Generate PM pitches from research."""

    async def run_pitches():
        try:
            pipeline_state.pm_status = "generating"

            # Run PM pitch stage (requires research)
            context = PipelineContext()

            # Add research if available
            if pipeline_state.research_packs:
                from .pipeline.stages.research import RESEARCH_PACK_A, RESEARCH_PACK_B
                context = context.set(RESEARCH_PACK_A, pipeline_state.research_packs.get("perplexity", {}))
                context = context.set(RESEARCH_PACK_B, pipeline_state.research_packs.get("gemini", {}))

            stage = PMPitchStage()
            result_context = await stage.execute(context)

            # Store results
            pipeline_state.pm_pitches = _format_pitches_for_frontend(result_context)
            pipeline_state.pm_status = "complete"

        except Exception as e:
            print(f"Error generating pitches: {e}")
            pipeline_state.pm_status = "error"

    background_tasks.add_task(run_pitches)
    return {"status": "generating", "message": "PM pitch generation started"}

@app.post("/api/pitches/{id}/approve")
async def approve_pitch(id: int):
    """Approve a PM pitch."""
    return {"status": "success", "message": f"Pitch {id} approved"}


# --- COUNCIL ENDPOINTS ---

@app.get("/api/council/current")
async def get_council_decision():
    """Get current council decision."""
    if pipeline_state.council_decision:
        return pipeline_state.council_decision
    return {}

@app.post("/api/council/synthesize")
async def synthesize_council(background_tasks: BackgroundTasks):
    """Run council synthesis from PM pitches."""

    async def run_council():
        try:
            pipeline_state.council_status = "synthesizing"

            # Run full pipeline up to chairman
            context = PipelineContext()

            # Add research and pitches if available
            if pipeline_state.research_packs:
                from .pipeline.stages.research import RESEARCH_PACK_A, RESEARCH_PACK_B
                context = context.set(RESEARCH_PACK_A, pipeline_state.research_packs.get("perplexity", {}))
                context = context.set(RESEARCH_PACK_B, pipeline_state.research_packs.get("gemini", {}))

            # Create pipeline up to chairman
            pipeline = Pipeline([
                ResearchStage(),
                PMPitchStage(),
                PeerReviewStage(),
                ChairmanStage()
            ])

            result_context = await pipeline.execute(context)

            # Store results
            pipeline_state.research_packs = _format_research_for_frontend(result_context)
            pipeline_state.pm_pitches = _format_pitches_for_frontend(result_context)
            pipeline_state.council_decision = _format_council_for_frontend(result_context)
            pipeline_state.pending_trades = _format_trades_for_frontend(result_context)
            pipeline_state.council_status = "complete"

        except Exception as e:
            print(f"Error synthesizing council: {e}")
            pipeline_state.council_status = "error"

    background_tasks.add_task(run_council)
    return {"status": "synthesizing", "message": "Council synthesis started"}


# --- TRADE ENDPOINTS ---

@app.get("/api/trades/pending")
async def get_pending_trades():
    """Get pending trades."""
    if pipeline_state.pending_trades:
        return pipeline_state.pending_trades
    return []

@app.post("/api/trades/execute")
async def execute_trades(request: ExecuteTradesRequest):
    """Execute approved trades."""

    try:
        # In a real implementation, this would call the ExecutionStage
        # For now, mark trades as executed
        trade_ids = request.trade_ids
        if trade_ids:
            for trade in pipeline_state.pending_trades:
                if trade["id"] in trade_ids:
                    trade["status"] = "filled"
                    pipeline_state.executed_trades.append(trade)
            pipeline_state.pending_trades = [t for t in pipeline_state.pending_trades if t["status"] == "pending"]

        return {"status": "success", "message": f"Executed {len(trade_ids) if trade_ids else 0} trades"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- MONITOR ENDPOINTS ---

@app.get("/api/positions")
async def get_positions():
    """Get current positions across all accounts."""
    try:
        manager = MultiAlpacaManager()
        positions_data = await manager.get_all_positions()

        # Format for frontend
        formatted = []
        for account_name, positions in positions_data.items():
            if not positions:
                formatted.append({
                    "account": account_name,
                    "symbol": "-",
                    "qty": 0,
                    "avg_price": 0,
                    "current_price": 0,
                    "pl": 0
                })
                continue

            for position in positions:
                formatted.append({
                    "account": account_name,
                    "symbol": position.get("symbol"),
                    "qty": int(float(position.get("qty", 0))),
                    "avg_price": float(position.get("avg_entry_price", 0)),
                    "current_price": float(position.get("current_price", 0)),
                    "pl": float(position.get("unrealized_pl", 0))
                })

        return formatted if formatted else MOCK_POSITIONS

    except Exception as e:
        print(f"Error getting positions: {e}")
        return MOCK_POSITIONS

@app.get("/api/accounts")
async def get_accounts():
    """Get account summaries."""
    try:
        manager = MultiAlpacaManager()
        accounts_data = await manager.get_all_accounts()

        # Format for frontend
        formatted = []
        for account_name, account in accounts_data.items():
            formatted.append({
                "name": account_name,
                "equity": float(account.get("portfolio_value", 100000)),
                "cash": float(account.get("cash", 100000)),
                "pl": float(account.get("equity", 100000)) - 100000
            })

        return formatted if formatted else MOCK_ACCOUNTS

    except Exception as e:
        print(f"Error getting accounts: {e}")
        return MOCK_ACCOUNTS


# ============================================================================
# LEGACY CHAT ENDPOINTS
# ============================================================================

@app.get("/api/conversations", response_model=List[Dict])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Dict)
async def create_conversation(request: Dict):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Dict)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: Dict):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.get("content", ""))

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.get("content", ""))
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.get("content", "")
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: Dict):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.get("content", ""))

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.get("content", "")))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.get("content", ""))
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.get("content", ""), stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.get("content", ""), stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    from backend.config import BACKEND_PORT

    print(f"🚀 Starting LLM Trading backend on http://0.0.0.0:{BACKEND_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=BACKEND_PORT)
