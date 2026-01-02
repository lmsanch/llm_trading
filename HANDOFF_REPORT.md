# Handoff Report: LLM Trading System Implementation

**Date**: December 31, 2025
**Project**: LLM Trading System - Council-Based Macro ETF Trading
**Status**: Phase 1 Complete - Import Error Blocking Progress

---

## Executive Summary

This project implements a pipeline-first LLM trading system using a "council" pattern for systematic macro ETF trading decisions. The system uses 6 parallel paper trading accounts (Alpaca), each associated with a different AI model, coordinated through a structured pipeline with a chairman model for final decisions.

**Current Status**: Backend infrastructure is 80% complete. All core components have been implemented, but there is an import error in `cli.py` that is blocking testing and deployment.

---

## Project Architecture

### System Components

1. **Requesty API Integration** - Replaces OpenRouter with Requesty's OpenAI-compatible API
2. **Multi-Alpaca Client** - Manages 6 paper trading accounts in parallel
3. **Pipeline Stages** - Composable, event-sourced trading pipeline
4. **Database Layer** - PostgreSQL for state persistence
5. **CLI Interface** - Command-line interface for pipeline execution
6. **GUI Dashboard** - React-based trade approval interface

### 6 Paper Trading Accounts

| Account ID | Model | Role |
|------------|-------|------|
| PA3IUYCYRWGK | GPT-5.2 PM | CHATGPT |
| PA3M2HMSLN00 | Gemini 3 Pro PM | GEMINI |
| PA38PAHFRFYC | GPT-5.2 PM | CLAUDE |
| PA33MEQA4WT7 | Grok 4.1 PM | GROQ |
| PA3KKW3TN54V | DeepSeek V3 PM | DEEPSEEK |
| PA3MQLPXBSO1 | Claude Opus 4.5 | COUNCIL (Chairman) |

### Pipeline Flow

```
Research → PM Pitch → Peer Review → Chairman → Execution
```

1. **Research Stage**: Fetch market data, generate macro analysis (Gemini + DeepSeek)
2. **PM Pitch Stage**: 5 models generate trading ideas in parallel
3. **Peer Review Stage**: Anonymized evaluation using 7-dimension rubric
4. **Chairman Stage**: Claude Opus 4.5 synthesizes final council decision
5. **Execution Stage**: Position sizing and parallel order placement

---

## Completed Work (Phase 1)

### 1. Requesty API Integration
**File**: `backend/requesty_client.py`

- Implemented `RequestyClient` class using OpenAI SDK
- Configured 6 models with Requesty API endpoint (`https://router.requesty.ai/v1`)
- Model mapping:
  - `gpt-5.2-pm`: GPT-5.2 (CHATGPT, CLAUDE accounts)
  - `gemini-3-pro-pm`: Gemini 3 Pro (GEMINI account)
  - `grok-4.1-pm`: Grok 4.1 (GROQ account)
  - `claude-sonnet-4.5-pm`: Claude Sonnet 4.5 (not currently used)
  - `deepseek-v3-pm`: DeepSeek V3 (DEEPSEEK account)
  - `claude-opus-4.5-chairman`: Claude Opus 4.5 (COUNCIL account)
- Functions: `query_model()`, `query_models_parallel()`, `query_pm_models()`, `query_chairman()`

### 2. Multi-Alpaca Client
**File**: `backend/multi_alpaca_client.py`

- Implemented `MultiAlpacaManager` class for managing all 6 accounts
- Implemented `AlpacaAccountClient` class for single account operations
- Functions:
  - `get_all_accounts()`: Fetch account data for all 6 accounts
  - `get_all_positions()`: Fetch positions for all accounts
  - `place_orders_parallel()`: Place orders across multiple accounts in parallel
  - `close_all_positions()`: Close all positions across all accounts
- Error handling and retry logic for API failures

### 3. Pipeline Stages

#### Research Stage
**File**: `backend/pipeline/stages/research.py`

- `ResearchStage` class fetches market data and generates macro analysis
- Uses Gemini and DeepSeek in parallel for dual research packs
- Research pack structure:
  - `macro_regime`: Current macroeconomic regime
  - `top_narratives`: Top 3-5 market narratives
  - `consensus_map`: Market consensus on key assets
  - `tradable_candidates`: List of tradable ETFs with rationale
  - `event_calendar`: Upcoming economic events

#### PM Pitch Stage
**File**: `backend/pipeline/stages/pm_pitch.py`

- `PMPitchStage` class generates pitches from 5 PM models in parallel
- PM pitch structure:
  - `instrument`: ETF ticker
  - `direction`: LONG/SHORT
  - `horizon`: Time horizon
  - `thesis_bullets`: 3-5 bullet points explaining thesis
  - `indicators`: Key technical/fundamental indicators
  - `conviction`: Conviction score (-2 to +2)
  - `invalidation`: What would invalidate the thesis
- JSON validation and parsing with fallback to regex extraction

#### Peer Review Stage
**File**: `backend/pipeline/stages/peer_review.py`

- `PeerReviewStage` class for anonymized evaluation
- 7-dimension rubric:
  1. Clarity
  2. Edge Plausibility
  3. Timing/Catalyst
  4. Risk Definition
  5. Indicator Integrity
  6. Originality
  7. Tradeability
- Generates "kill shot" critiques and flip conditions
- Each PM reviews all other PMs' pitches (cross-review)

#### Chairman Stage
**File**: `backend/pipeline/stages/chairman.py`

- `ChairmanStage` class using Claude Opus 4.5 for synthesis
- Generates final council decision with:
  - Approved trades
  - Rejected trades with reasons
  - Dissent summary
  - Monitoring plan
- Incorporates peer review scores into decision

#### Execution Stage
**File**: `backend/pipeline/stages/execution.py`

- `ExecutionStage` class for placing approved trades
- Position sizing based on conviction scale:
  - +2: 20% of portfolio
  - +1: 10% of portfolio
  - -1: 10% short
  - -2: 20% short
- Parallel order placement across all 6 accounts
- Order types: MARKET or LIMIT (based on conviction)

### 4. Weekly Pipeline Orchestration
**File**: `backend/pipeline/weekly_pipeline.py`

- `WeeklyTradingPipeline` class composing all stages
- Functions:
  - `run_weekly_pipeline()`: Run full pipeline (Research → PM Pitch → Peer Review → Chairman → Execution)
  - `run_research_only()`: Run only research stage
  - `run_pm_pitches_only()`: Run PM pitch stage only
  - `extract_results()`: Extract and format pipeline results
- Result extraction and summary printing

### 5. Database Initialization
**File**: `scripts/init_db.py`

- Database initialization script
- Creates all tables from `storage/schema.py`
- Tests connection
- Usage: `python scripts/init_db.py`

### 6. Environment Configuration
**File**: `.env.template`

- Environment variables template with all 12 Alpaca keys:
  - `ALPACA_PAPER_KEY_CHATGPT`, `ALPACA_PAPER_SECRET_CHATGPT`
  - `ALPACA_PAPER_KEY_GEMINI`, `ALPACA_PAPER_SECRET_GEMINI`
  - `ALPACA_PAPER_KEY_CLAUDE`, `ALPACA_PAPER_SECRET_CLAUDE`
  - `ALPACA_PAPER_KEY_GROQ`, `ALPACA_PAPER_SECRET_GROQ`
  - `ALPACA_PAPER_KEY_DEEPSEEK`, `ALPACA_PAPER_SECRET_DEEPSEEK`
  - `ALPACA_PAPER_KEY_COUNCIL`, `ALPACA_PAPER_SECRET_COUNCIL`
- Requesty API key: `REQUESTY_API_KEY`
- Database URL: `DATABASE_URL`

### 7. CLI Interface
**File**: `cli.py`

- Command-line interface for pipeline execution
- Commands:
  - `run_weekly`: Run full weekly pipeline
  - `run_research`: Run research stage only
  - `run_pm_pitches`: Run PM pitch stage only
  - `init_db`: Initialize database
- **CURRENT ISSUE**: Import error (see below)

### 8. Documentation
**Files Created**:
- `IMPLEMENTATION_PROGRESS.md` - Detailed progress tracking
- `IMPLEMENTATION_SUMMARY.md` - Complete implementation summary
- `plans/deployment_plan.md` - Updated deployment plan
- `plans/architecture_diagram.md` - Mermaid architecture diagrams

---

## Current Issues / Blockers

### Primary Issue: Import Error in cli.py

**Error Message**:
```
ModuleNotFoundError: No module named 'backend.pipeline.weekly_pipeline'; 'backend.pipeline' is not a package
```

**Location**: `cli.py` lines 12-18

**Problem Code**:
```python
from backend.pipeline.weekly_pipeline import (
    WeeklyTradingPipeline,
    run_weekly_pipeline,
    run_research_only,
    run_pm_pitches_only
)
```

**Root Cause**:
Python is incorrectly interpreting the dot (`.`) in the import path as a package separator. The actual file structure is:
```
backend/pipeline/
├── __init__.py
├── base.py
├── context.py
├── context_keys.py
├── weekly_pipeline.py
└── stages/
```

The import `from backend.pipeline.weekly_pipeline import` is being interpreted by Python as importing a submodule named `weekly_pipeline` from the `pipeline` package, but the actual file is `backend/pipeline/weekly_pipeline.py`.

**Potential Solutions** (untested):
1. Use relative imports from a proper package structure
2. Add the project root to `sys.path` before imports
3. Restructure the import to use absolute imports with proper package setup
4. Create a proper `__init__.py` in the project root
5. Use `importlib` for dynamic imports

**Impact**: This error blocks all CLI functionality, which means:
- Cannot run the weekly pipeline
- Cannot test research generation
- Cannot test PM pitches
- Cannot test trade placement
- Cannot verify end-to-end functionality

---

## Remaining Work (Phase 2)

### 1. Fix Import Error (BLOCKING)
**Priority**: CRITICAL
**Estimated Time**: 1-2 hours

Tasks:
- Fix the import error in `cli.py`
- Test that all CLI commands work correctly
- Verify imports in all pipeline stage files

### 2. Create Checkpoint Engine
**Priority**: HIGH
**Estimated Time**: 4-6 hours

Tasks:
- Implement `backend/pipeline/stages/checkpoint.py`
- Daily checkpoint logic (09:00, 12:00, 14:00, 15:50 ET)
- Conviction score updates based on market data
- Position adjustment logic
- Trade modification/cancellation logic

### 3. Implement GUI Trade Approval
**Priority**: HIGH
**Estimated Time**: 6-8 hours

Tasks:
- Complete frontend React components
- Implement backend API endpoints for trade approval
- WebSocket integration for real-time updates
- Trade approval workflow:
  1. Display pending trades from Chairman stage
  2. Allow user to approve/reject/modify trades
  3. Send approved trades to Execution stage

### 4. End-to-End Testing
**Priority**: HIGH
**Estimated Time**: 4-6 hours

Tasks:
- Test research generation with Requesty API
- Test PM pitch generation with all 5 models
- Test peer review stage
- Test chairman synthesis
- Test trade placement with all 6 accounts
- Verify database persistence
- Test error handling and retry logic

### 5. Deployment
**Priority**: MEDIUM
**Estimated Time**: 2-4 hours

Tasks:
- Set up production environment
- Configure environment variables
- Initialize production database
- Set up scheduled tasks (cron/systemd)
- Monitor and log setup

---

## Technical Details

### Requesty API Configuration

```python
REQUESTY_MODELS = {
    "gpt-5.2-pm": {
        "requesty_id": "openai/gpt-5.2-preview",
        "accounts": ["CHATGPT", "CLAUDE"],
        "max_tokens": 4000,
        "temperature": 0.7
    },
    "gemini-3-pro-pm": {
        "requesty_id": "google/gemini-3-pro",
        "accounts": ["GEMINI"],
        "max_tokens": 4000,
        "temperature": 0.7
    },
    # ... other models
}
```

### Alpaca Account Configuration

Each account has:
- API Key
- API Secret
- Base URL: `https://paper-api.alpaca.markets`
- Associated AI model

### Pipeline Context

The `PipelineContext` class (in `backend/pipeline/context.py`) maintains immutable state across pipeline stages:
- `user_query`: Original user query
- `research_pack`: Research stage output
- `pm_pitches`: PM pitch stage output
- `peer_reviews`: Peer review stage output
- `chairman_decision`: Chairman stage output
- `execution_results`: Execution stage output
- `metadata`: Additional metadata (timestamps, model versions, etc.)

### Database Schema

Tables defined in `storage/schema.py`:
- `pipeline_runs`: Track pipeline executions
- `research_packs`: Store research outputs
- `pm_pitches`: Store PM pitch outputs
- `peer_reviews`: Store peer review outputs
- `chairman_decisions`: Store chairman decisions
- `trades`: Store executed trades
- `positions`: Store current positions

---

## Environment Setup

### Prerequisites

1. Python 3.11+
2. Node.js 18+ (for GUI)
3. PostgreSQL 14+
4. Alpaca paper trading accounts (6 accounts)
5. Requesty API key

### Installation Steps

1. Clone repository:
```bash
git clone <repo-url>
cd llm_trading
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
```

4. Set up environment variables:
```bash
cp .env.template .env
# Edit .env with your API keys and credentials
```

5. Initialize database:
```bash
python scripts/init_db.py
```

---

## Testing Strategy

### Unit Tests (Not Yet Implemented)

- Test Requesty client
- Test Alpaca client
- Test each pipeline stage
- Test database operations

### Integration Tests (Not Yet Implemented)

- Test full pipeline execution
- Test parallel model queries
- Test parallel order placement
- Test error handling

### Manual Testing (Pending)

1. Test research generation:
```bash
python cli.py run_research
```

2. Test PM pitches:
```bash
python cli.py run_pm_pitches
```

3. Test full pipeline:
```bash
python cli.py run_weekly
```

---

## Known Issues

1. **Import Error** (CRITICAL): `cli.py` cannot import from `backend.pipeline.weekly_pipeline`
2. **GUI Not Implemented**: Frontend components exist but backend API not connected
3. **Checkpoint Engine**: Not implemented yet
4. **Error Handling**: Limited error handling in some stages
5. **Logging**: Minimal logging throughout the system
6. **Testing**: No unit or integration tests

---

## Recommendations for Next Developer

1. **Priority 1**: Fix the import error in `cli.py` - this is blocking everything
2. **Priority 2**: Implement the checkpoint engine for daily updates
3. **Priority 3**: Complete the GUI trade approval workflow
4. **Priority 4**: Add comprehensive logging throughout the system
5. **Priority 5**: Write unit tests for all components
6. **Priority 6**: Add integration tests for the full pipeline
7. **Priority 7**: Implement monitoring and alerting
8. **Priority 8**: Add performance optimization (caching, connection pooling)

---

## File Structure

```
llm_trading/
├── backend/
│   ├── __init__.py
│   ├── config.py
│   ├── council.py
│   ├── main.py
│   ├── openrouter.py (deprecated)
│   ├── storage.py
│   ├── requesty_client.py (NEW)
│   ├── multi_alpaca_client.py (NEW)
│   ├── council_trading.py
│   └── pipeline/
│       ├── __init__.py
│       ├── base.py
│       ├── context.py
│       ├── context_keys.py
│       ├── stages/
│       │   ├── __init__.py
│       │   ├── research.py (NEW)
│       │   ├── pm_pitch.py (NEW)
│       │   ├── peer_review.py (NEW)
│       │   ├── chairman.py (NEW)
│       │   └── execution.py (NEW)
│       └── weekly_pipeline.py (NEW)
├── config/
│   ├── __init__.py
│   ├── assets.yaml
│   ├── loader.py
│   ├── models.yaml
│   └── schedule.yaml
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api.js
│       ├── App.jsx
│       └── components/
│           ├── ChatInterface.jsx
│           ├── Sidebar.jsx
│           ├── Stage1.jsx
│           ├── Stage2.jsx
│           └── Stage3.jsx
├── market/
│   ├── __init__.py
│   └── alpaca_client.py
├── storage/
│   └── schema.py
├── scripts/
│   └── init_db.py (NEW)
├── plans/
│   ├── deployment_plan.md (NEW)
│   └── architecture_diagram.md (NEW)
├── cli.py (HAS ISSUE)
├── main.py
├── .env.template (NEW)
├── IMPLEMENTATION_PROGRESS.md (NEW)
├── IMPLEMENTATION_SUMMARY.md (NEW)
└── HANDOFF_REPORT.md (THIS FILE)
```

---

## Contact Information

**Original Developer**: Kilo Code (AI Assistant)
**Handoff Date**: December 31, 2025
**Project Repository**: `/research/llm_trading`

---

## Appendix: Code Snippets

### Sample Research Pack Output

```json
{
  "macro_regime": "Late-cycle expansion with inflation concerns",
  "top_narratives": [
    "Fed rate cuts expected in Q1 2026",
    "Tech sector rotation to value",
    "Geopolitical tensions driving commodity prices"
  ],
  "consensus_map": {
    "SPY": "Bullish",
    "TLT": "Bearish",
    "GLD": "Neutral"
  },
  "tradable_candidates": [
    {
      "ticker": "SPY",
      "rationale": "Strong earnings season expected"
    },
    {
      "ticker": "TLT",
      "rationale": "Yield curve inversion risk"
    }
  ],
  "event_calendar": [
    {
      "date": "2025-01-15",
      "event": "Fed FOMC meeting",
      "impact": "High"
    }
  ]
}
```

### Sample PM Pitch Output

```json
{
  "model": "gpt-5.2-pm",
  "account": "CHATGPT",
  "instrument": "SPY",
  "direction": "LONG",
  "horizon": "2-4 weeks",
  "thesis_bullets": [
    "Earnings season showing strong corporate profits",
    "Fed signaling potential rate cuts",
    "Technical breakout above 200-day MA"
  ],
  "indicators": [
    "RSI: 65 (not overbought)",
    "MACD: Bullish crossover",
    "Volume: Above average"
  ],
  "conviction": 2,
  "invalidation": "Break below 470 support level"
}
```

### Sample Peer Review Output

```json
{
  "reviewer_model": "gemini-3-pro-pm",
  "pitch_author": "gpt-5.2-pm",
  "scores": {
    "clarity": 8,
    "edge_plausibility": 7,
    "timing_catalyst": 9,
    "risk_definition": 6,
    "indicator_integrity": 8,
    "originality": 5,
    "tradeability": 9
  },
  "kill_shot": "Thesis ignores upcoming inflation data which could reverse Fed expectations",
  "flip_condition": "If CPI comes in above 3.5%, flip to SHORT"
}
```

### Sample Chairman Decision Output

```json
{
  "approved_trades": [
    {
      "instrument": "SPY",
      "direction": "LONG",
      "conviction": 2,
      "position_size": "20%",
      "rationale": "Strong consensus across PMs with clear catalyst"
    }
  ],
  "rejected_trades": [
    {
      "instrument": "TLT",
      "direction": "SHORT",
      "reason": "Low conviction scores and conflicting indicators"
    }
  ],
  "dissent_summary": "2 PMs opposed SPY LONG due to valuation concerns",
  "monitoring_plan": "Monitor CPI data release on Jan 15, Fed FOMC on Jan 28"
}
```

---

**End of Handoff Report**
