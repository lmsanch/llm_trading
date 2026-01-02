# LLM Trading - Deployment Plan

## Executive Summary

Deploy complete LLM Trading system with Requesty API integration, 5 paper trading accounts, and GUI-based trade approval workflow.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WEEKLY PIPELINE (Wed 08:00 ET)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐      ┌──────────────────────────────────────────┐   │
│  │  RESEARCH LAYER  │      │           PM LAYER (5 PMs)               │   │
│  ├──────────────────┤      ├──────────────────────────────────────────┤   │
│  │ Market Data      │──────▶│  GPT-5.2    │ Gemini 3 Pro │ Grok 4.1  │   │
│  │ Macro Analysis   │      │  (CHATGPT) │  (GEMINI)    │ (GROQ)     │   │
│  │ Sentiment       │      │  DeepSeek V3 │             │            │   │
│  └──────────────────┘      │  (DEEPSEEK) │             │            │   │
│                           └──────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    PEER REVIEW LAYER (Anonymous)                     │ │
│  │   Each PM reviews other pitches → rubric scores + critique            │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                     CHAIRMAN LAYER (CIO)                            │ │
│  │   Claude Sonnet 4.5 synthesizes → Council trade + dissent notes       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    TRADE APPROVAL GUI                                │ │
│  │   User reviews all trades → Approve/Reject before execution          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      PAPER TRADING EXECUTION                          │ │
│  │   5 accounts: 4 PMs + 1 Council via Alpaca Paper Trading          │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            DAILY CHECKPOINTS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Times: 09:00, 12:00, 14:00, 15:50 ET                                      │
│  Input: indicators + P/L + peer snapshot → Output: conviction + action     │
│  Hard rule: No new research sources mid-week                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Paper Trading Account Mapping

| Account ID | Nickname | Alpaca Account | Email | Model | Strategy |
|------------|----------|----------------|-------|--------|----------|
| PA3MQLPXBSO1 | COUNCIL | lmsanch@gmail.com | Claude Opus 4.5 | Council trade |
| PA3M2HMSLN00 | GEMINI | lmsanch@gmail.com | Gemini 3 Pro | Individual PM |
| PA38PAHFRFYC | CLAUDE | lmsanch@gmail.com | GPT-5.2 | Individual PM |
| PA33MEQA4WT7 | GROQ | strategy1a@dnnalpha.ai | Grok 4.1 | Individual PM |
| PA3IUYCYRWGK | CHATGPT | strategy1a@dnnalpha.ai | GPT-5.2 | Individual PM |
| PA3KKW3TN54V | DEEPSEEK | strategy1a@dnnalpha.ai | DeepSeek V3 | Individual PM |

**Note**: Account mapping adjusted based on available models. CLAUDE account will use GPT-5.2 (same as CHATGPT), or we can assign different model if needed.

## Requesty API Integration

### Models Configuration

```python
REQUESTY_MODELS = {
    # PM Layer (Portfolio Managers)
    'chatgpt': {
        'model_id': 'openai/gpt-5.2',
        'account': 'CHATGPT',
        'alpaca_id': 'PA3IUYCYRWGK',
        'role': 'portfolio_manager'
    },
    'gemini': {
        'model_id': 'google/gemini-3-pro-preview',
        'account': 'GEMINI',
        'alpaca_id': 'PA3M2HMSLN00',
        'role': 'portfolio_manager'
    },
    'groq': {
        'model_id': 'xai/grok-4-1-fast-non-reasoning',
        'account': 'GROQ',
        'alpaca_id': 'PA33MEQA4WT7',
        'role': 'portfolio_manager'
    },
    'claude': {
        'model_id': 'anthropic/claude-sonnet-4-5',
        'account': 'CLAUDE',
        'alpaca_id': 'PA38PAHFRFYC',
        'role': 'portfolio_manager'
    },
    'deepseek': {
        'model_id': 'deepseek-ai/DeepSeek-V3',
        'account': 'DEEPSEEK',
        'alpaca_id': 'PA3KKW3TN54V',
        'role': 'portfolio_manager'
    },
    
    # Chairman Layer
    'chairman': {
        'model_id': 'anthropic/claude-opus-4-5',
        'account': 'COUNCIL',
        'alpaca_id': 'PA3MQLPXBSO1',
        'role': 'chairman'
    }
}
```

### API Configuration

```python
# Requesty API (OpenAI-compatible)
REQUESTY_API_URL = "https://router.requesty.ai/v1"
REQUESTY_API_KEY = os.getenv("REQUESTY_API_KEY")

# Use OpenAI SDK for Requesty
from openai import AsyncOpenAI
requesty_client = AsyncOpenAI(
    api_key=REQUESTY_API_KEY,
    base_url=REQUESTY_API_URL
)
```

## Implementation Plan

### Phase 1: API Integration & Configuration

#### 1.1 Replace OpenRouter with Requesty
- **File**: `backend/requesty_client.py` (NEW)
- Create Requesty API client using OpenAI SDK
- Implement `query_model()` and `query_models_parallel()` functions
- Add retry logic with exponential backoff
- Track token usage and costs

#### 1.2 Update Configuration
- **File**: `config/models.yaml` (UPDATE)
- Replace OpenRouter model IDs with Requesty model IDs
- Update API endpoint configuration
- Add account mapping (nickname → Alpaca account ID → model)

#### 1.3 Update Council Module
- **File**: `backend/council.py` (UPDATE)
- Replace OpenRouter imports with Requesty client
- Update model list to use Requesty models
- Ensure compatibility with existing pipeline stages

### Phase 2: Trading Pipeline Stages

#### 2.1 Research Provider Stage
- **File**: `backend/pipeline/stages/research.py` (NEW)
- Fetch market data from Alpaca (prices, indicators)
- Analyze macro regime (risk-on/risk-off, rates, USD, inflation)
- Generate research pack with:
  - Macro regime analysis
  - Top narratives for the week
  - Tradable candidates with directional bias
  - Event calendar
  - Consensus map

#### 2.2 PM Pitch Stage
- **File**: `backend/pipeline/stages/pm_pitch.py` (NEW)
- Generate trade recommendations from all 4 PM models
- Each PM receives Research Pack A and B
- Output structured PM pitch JSON:
  - Instrument (SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO)
  - Direction (LONG/SHORT/FLAT)
  - Horizon (1d/3d/1w)
  - Thesis bullets (max 5)
  - Indicators with thresholds
  - Invalidation rule
  - Conviction score (-2 to +2)

#### 2.3 Peer Review Stage
- **File**: `backend/pipeline/stages/peer_review.py` (NEW)
- Each PM reviews other pitches (anonymized)
- Score on 7 dimensions (1-10 scale):
  - Clarity
  - Edge plausibility
  - Timing catalyst
  - Risk definition
  - Indicator integrity
  - Originality
  - Tradeability
- Provide "kill shot" critique
- Suggest one flip condition

#### 2.4 Chairman Synthesis Stage
- **File**: `backend/pipeline/stages/chairman.py` (NEW)
- Claude Sonnet 4.5 synthesizes all pitches + reviews
- Output council trade decision:
  - Selected instrument and direction
  - Conviction score
  - Rationale
  - Dissent summary
  - Monitoring plan (checkpoints, key indicators, watch conditions)

### Phase 3: Trade Approval GUI

#### 3.1 Backend API
- **File**: `backend/api/approval.py` (NEW)
- FastAPI endpoints:
  - `GET /api/pending-trades` - List trades awaiting approval
  - `POST /api/trades/{trade_id}/approve` - Approve trade
  - `POST /api/trades/{trade_id}/reject` - Reject trade
  - `GET /api/trades/{trade_id}` - Get trade details
  - `GET /api/trades` - List all trades (approved/rejected/executed)

#### 3.2 Frontend Dashboard
- **File**: `frontend/src/components/TradeApproval.jsx` (NEW)
- Display pending trades in a table:
  - Account nickname
  - Model
  - Instrument
  - Direction (LONG/SHORT)
  - Conviction score
  - Thesis bullets
  - Indicators
  - Approve/Reject buttons
- Color-coded by conviction (green = high, yellow = medium, red = low)
- Show trade details in modal on click

#### 3.3 Update Main App
- **File**: `frontend/src/App.jsx` (UPDATE)
- Add navigation between Chat and Trade Approval views
- Auto-refresh pending trades every 30 seconds
- Show notification when new trades await approval

### Phase 4: Execution Stage

#### 4.1 Alpaca Multi-Account Client
- **File**: `backend/multi_alpaca_client.py` (NEW)
- Manage multiple Alpaca accounts with different credentials
- Support 5 paper trading accounts
- Execute trades in parallel across accounts

#### 4.2 Execution Stage
- **File**: `backend/pipeline/stages/execution.py` (NEW)
- Check if trade is approved (from database)
- Calculate position size (based on conviction)
- Place order via Alpaca for each account
- Record order event in PostgreSQL
- Update position events

#### 4.3 Trade Approval Workflow
```
1. PM/Chairman generates trade → Save as "pending" status
2. GUI displays pending trades
3. User reviews trade details
4. User clicks Approve or Reject
5. If Approved:
   - Update status to "approved"
   - Trigger execution stage
   - Place order via Alpaca
   - Update status to "executed"
6. If Rejected:
   - Update status to "rejected"
   - Record rejection reason
   - No order placed
```

### Phase 5: Database & Persistence

#### 5.1 Database Initialization
- **File**: `scripts/init_db.py` (NEW)
- Create PostgreSQL database
- Run migrations to create all tables
- Insert initial configuration data
- Test connection

#### 5.2 Trade Events Table
- **File**: `storage/schema.py` (UPDATE)
- Add `TradeEvent` table for tracking trade lifecycle:
  - trade_id (UUID)
  - week_id
  - account_id
  - model
  - instrument
  - direction
  - conviction
  - status (pending/approved/rejected/executed/failed)
  - approval_timestamp
  - execution_timestamp
  - rejection_reason

#### 5.3 Event Logging
- Log all pipeline stages to PostgreSQL
- Log all trade state changes
- Log all Alpaca orders and fills
- Log all checkpoint updates

### Phase 6: Weekly Pipeline Orchestration

#### 6.1 CLI Command
- **File**: `cli.py` (UPDATE)
- Implement `run_weekly` command:
  ```bash
  python cli.py run_weekly
  ```
- Execute all stages sequentially:
  1. Research Stage
  2. PM Pitch Stage (4 models in parallel)
  3. Peer Review Stage
  4. Chairman Synthesis Stage
  5. Save all trades as "pending" status
  6. Notify user: "Trades ready for approval in GUI"

#### 6.2 Pipeline Integration
- **File**: `backend/pipeline/weekly_pipeline.py` (NEW)
- Compose all trading stages into weekly pipeline
- Handle errors gracefully
- Log progress to console and database

### Phase 7: Checkpoint Engine

#### 7.1 Checkpoint Stage
- **File**: `backend/pipeline/stages/checkpoint.py` (NEW)
- Fetch current positions and P/L from Alpaca
- Fetch latest indicator values
- Evaluate conviction update (STAY/EXIT/FLIP/REDUCE)
- Generate checkpoint event

#### 7.2 CLI Command
- **File**: `cli.py` (UPDATE)
- Implement `checkpoint --time <HH:MM>` command:
  ```bash
  python cli.py checkpoint --time 09:00
  ```
- Run checkpoint for all accounts
- Require approval for EXIT/FLIP actions
- Auto-execute STAY actions

### Phase 8: Testing & Deployment

#### 8.1 Unit Tests
- Test Requesty API client
- Test each pipeline stage with mock data
- Test Alpaca client with paper trading
- Test database operations

#### 8.2 Integration Tests
- Run full weekly pipeline with test query
- Verify trades saved as "pending"
- Test GUI approval workflow
- Verify orders placed in Alpaca paper accounts
- Verify position updates in database

#### 8.3 End-to-End Test
```bash
# 1. Initialize database
python scripts/init_db.py

# 2. Run weekly pipeline
python cli.py run_weekly

# 3. Open GUI and approve trades
# (Navigate to http://localhost:5173/trade-approval)

# 4. Verify trades executed in Alpaca
python cli.py status

# 5. Run checkpoint
python cli.py checkpoint --time 09:00
```

#### 8.4 Deployment Checklist
- [ ] Requesty API key configured in `.env`
- [ ] 5 Alpaca paper trading accounts configured
- [ ] PostgreSQL database running
- [ ] All dependencies installed (`uv sync`)
- [ ] Database initialized
- [ ] GUI running (`npm run dev` in frontend/)
- [ ] CLI commands tested
- [ ] End-to-end pipeline tested

## File Structure

```
llm_trading/
├── backend/
│   ├── requesty_client.py          # NEW - Requesty API client
│   ├── api/
│   │   └── approval.py            # NEW - Trade approval API
│   ├── pipeline/
│   │   ├── stages/
│   │   │   ├── research.py        # NEW - Market data + macro analysis
│   │   │   ├── pm_pitch.py        # NEW - PM pitch generation
│   │   │   ├── peer_review.py     # NEW - Peer review stage
│   │   │   ├── chairman.py        # NEW - Chairman synthesis
│   │   │   ├── execution.py       # NEW - Trade execution
│   │   │   └── checkpoint.py      # NEW - Conviction updates
│   │   └── weekly_pipeline.py     # NEW - Weekly pipeline composition
│   └── multi_alpaca_client.py     # NEW - Multi-account Alpaca client
├── frontend/
│   └── src/
│       └── components/
│           ├── TradeApproval.jsx    # NEW - Trade approval dashboard
│           └── TradeDetail.jsx     # NEW - Trade detail modal
├── scripts/
│   └── init_db.py                 # NEW - Database initialization
├── storage/
│   └── schema.py                  # UPDATE - Add TradeEvent table
├── config/
│   └── models.yaml                # UPDATE - Requesty models + account mapping
├── cli.py                         # UPDATE - Implement run_weekly, checkpoint
└── plans/
    └── deployment_plan.md          # This file
```

## Environment Variables

```bash
# Requesty API
REQUESTY_API_KEY=sk-or-v1-...

# Alpaca Paper Trading (5 accounts)
# Account 1: COUNCIL
ALPACA_COUNCIL_KEY_ID=...
ALPACA_COUNCIL_SECRET_KEY=...

# Account 2: GEMINI
ALPACA_GEMINI_KEY_ID=...
ALPACA_GEMINI_SECRET_KEY=...

# Account 3: CLAUDE
ALPACA_CLAUDE_KEY_ID=...
ALPACA_CLAUDE_SECRET_KEY=...

# Account 4: GROQ
ALPACA_GROQ_KEY_ID=...
ALPACA_GROQ_SECRET_KEY=...

# Account 5: CHATGPT
ALPACA_CHATGPT_KEY_ID=...
ALPACA_CHATGPT_SECRET_KEY=...

# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/llm_trading
```

## Success Criteria

- [ ] Weekly pipeline generates 5 trades (4 PMs + 1 Council)
- [ ] All trades appear in GUI with "pending" status
- [ ] User can approve/reject trades via GUI
- [ ] Approved trades execute in correct Alpaca accounts
- [ ] PostgreSQL logs all events for replay
- [ ] Checkpoints update conviction without new research
- [ ] GUI shows real-time trade status updates

## Next Steps

1. Review and approve this plan
2. Switch to Code mode to implement
3. Test incrementally (each phase)
4. Deploy and verify end-to-end workflow
