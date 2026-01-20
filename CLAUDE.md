# CLAUDE.md - Technical Notes for LLM Trading

This file contains technical details, architectural decisions, and important implementation notes for the LLM Trading system.

---

## Project Overview

LLM Trading is a **pipeline-first** extension of Andrej Karpathy's `llm-council` pattern for systematic trading decisions. The system:

1. Separates **research** (2 deep research providers) from **PM decision-making** (4 models)
2. Uses **anonymized peer review** to prevent model favoritism
3. Synthesizes decisions via a **Chairman (CIO)** model
4. Runs **6 parallel paper trading accounts** to compare performance
5. Uses **checkpoint-based conviction updates** (no new research mid-week)

### Key Documents

| Document | Purpose |
|----------|---------|
| [PRD.md](PRD.md) | Complete implementation plan and requirements |
| [PIPELINE.md](PIPELINE.md) | Pipeline-first architecture details |
| [README.md](README.md) | Project overview and quick start |

---

## Architecture Overview

### Pipeline-First Design

The system uses composable `Stage` classes that can be chained together:

```
Research Stage → PM Pitch Stage → Peer Review Stage → Chairman Stage → Execution Stage
```

Each stage:
- Has a **clear input/output contract**
- Is **async by default**
- Returns a **new immutable PipelineContext** (never mutates)

### Directory Structure

```
llm-trading/
├── council/                      # llm-council core, refactored
│   ├── pipeline/                 # Stage, Pipeline, PipelineContext
│   ├── prompts/                  # Jinja2 templates
│   ├── schemas/                  # JSON schemas for validation
│   └── openrouter.py             # OpenRouter API client
├── research/                     # Research providers
│   └── providers/
│       ├── gemini_deep.py
│       └── perplexity_deep.py
├── pm/                           # PM orchestration
├── market/                       # Alpaca MCP integration
│   ├── alpaca_mcp_client.py
│   └── indicators.py
├── storage/                      # SQLite event store
├── runs/                         # Per-week execution data
│   └── week_YYYY-MM-DD/
│       ├── raw/
│       ├── normalized/
│       └── events.sqlite
├── config/                       # Configuration files
│   ├── assets.yaml               # Tradable universe
│   ├── schedule.yaml             # Checkpoint schedule
│   └── models.yaml               # Model configuration
├── cli.py                        # Main CLI entry point
└── backend/                      # Original llm-council (baseline)
```

---

## Configuration

### Assets (`config/assets.yaml`)

Defines the tradable universe:

- **Risk-on equities:** SPY, QQQ, IWM
- **Duration:** TLT, IEF
- **Credit:** HYG, LQD
- **USD proxy:** UUP
- **Gold:** GLD
- **Oil:** USO

### Schedule (`config/schedule.yaml`)

Defines:
- Weekly pipeline day: Wednesday 08:00 ET
- Daily checkpoints: 09:00, 12:00, 14:00, 15:50 ET

### Models (`config/models.yaml`)

Defines:
- Research providers (Gemini, Perplexity)
- PM models (GPT-5.1, Gemini 3 Pro, Sonnet 4.5, Grok)
- Chairman model (Opus-class)

### Ports (`backend/config/ports.py`)

Centralized port configuration system:

**Default Ports:**
- **Backend API:** 8200 (avoids conflicts with port 8000)
- **Frontend Dev:** 4173 (Vite preview port)
- **Test Utilities:** 8201 (for verify_snapshot.py)
- **PostgreSQL:** 5432 (future use)

**Configuration:**
All ports are configurable via environment variables in `.env`:

```bash
PORT_BACKEND=8200      # Backend API server
PORT_FRONTEND=4173     # Frontend dev server
PORT_TEST=8201         # Test utilities
PORT_POSTGRES=5432     # PostgreSQL (future)
TAILSCALE_IP=100.100.238.72  # For CORS configuration
```

**Key Features:**
- **Environment-based:** All ports read from env vars with sensible defaults
- **CORS Generation:** `get_cors_origins()` generates allowed origins dynamically
- **Port Validation:** `get_port()` validates and handles invalid values
- **Centralized:** Single source of truth for all port configuration

**Usage in Code:**
```python
from backend.config import BACKEND_PORT, FRONTEND_PORT, TEST_PORT, get_cors_origins

# Backend uses BACKEND_PORT
uvicorn.run(app, host="0.0.0.0", port=BACKEND_PORT)

# CORS uses get_cors_origins()
app.add_middleware(CORSMiddleware, allow_origins=get_cors_origins())
```

**Port Conflict Checking:**
`start.sh` automatically checks port availability before starting:
```bash
./start.sh
# Checks if PORT_BACKEND and PORT_FRONTEND are available
# Fails with helpful error message if port is in use
```

---

## Database Architecture

### Async PostgreSQL Connection Pool

The application uses **asyncpg** with a connection pool for all database operations. This provides:
- **2-3x faster** queries than psycopg2
- **Non-blocking I/O** (doesn't block the event loop)
- **Connection reuse** (50-90% latency reduction)
- **Automatic lifecycle management**

**Implementation:** `backend/db/pool.py`

### Pool Configuration

Environment variables (in `.env`):

```bash
# Connection (use DATABASE_URL OR individual components)
DATABASE_URL=postgresql://user:pass@localhost:5432/llm_trading
# OR
DATABASE_NAME=llm_trading
DATABASE_USER=luis
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_PASSWORD=secret

# Pool settings (defaults shown)
DB_MIN_POOL_SIZE=10           # Minimum connections
DB_MAX_POOL_SIZE=50           # Maximum connections
DB_COMMAND_TIMEOUT=60.0       # Query timeout (seconds)
DB_MAX_QUERIES=50000          # Queries before connection recycling
DB_MAX_INACTIVE_CONNECTION_LIFETIME=300.0  # Max idle time (seconds)
```

### Lifecycle Management

The pool is initialized on FastAPI startup and closed on shutdown:

```python
# backend/main.py
from backend.db.pool import init_pool, close_pool

@app.on_event("startup")
async def startup_event():
    await init_pool()  # Initialize connection pool
    logger.info("✓ Database pool initialized")

@app.on_event("shutdown")
async def shutdown_event():
    await close_pool()  # Gracefully close pool
    logger.info("✓ Database pool closed")
```

### Writing Database Queries

#### Using Helper Functions (Recommended)

The `backend/db_helpers.py` module provides high-level async utilities:

```python
from backend.db_helpers import fetch_one, fetch_all, fetch_val, execute, transaction

# Fetch single row
async def get_user(user_id: int):
    user = await fetch_one("SELECT * FROM users WHERE id = $1", user_id)
    return user  # dict with column names as keys, or None

# Fetch all rows
async def get_active_users():
    users = await fetch_all("SELECT * FROM users WHERE active = $1", True)
    return users  # list of dicts

# Fetch single value
async def count_users():
    count = await fetch_val("SELECT COUNT(*) FROM users")
    return count  # single value

# Execute INSERT/UPDATE/DELETE
async def create_user(name: str, email: str):
    await execute(
        "INSERT INTO users (name, email) VALUES ($1, $2)",
        name, email
    )

# Execute with RETURNING clause
async def create_user_with_id(name: str, email: str):
    result = await execute_with_returning(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, created_at",
        name, email
    )
    return result["id"]  # dict with returned columns

# Transactions
async def transfer_money(from_id: int, to_id: int, amount: float):
    async with transaction() as conn:
        await conn.execute(
            "UPDATE accounts SET balance = balance - $1 WHERE id = $2",
            amount, from_id
        )
        await conn.execute(
            "UPDATE accounts SET balance = balance + $1 WHERE id = $2",
            amount, to_id
        )
        # Automatically commits on success, rolls back on exception
```

#### Using the Pool Directly (Advanced)

For fine-grained control, acquire connections directly from the pool:

```python
from backend.db.pool import get_pool

async def custom_query():
    pool = get_pool()

    async with pool.acquire() as conn:
        # Use connection for multiple operations
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", 42)
        logs = await conn.fetch("SELECT * FROM logs WHERE user_id = $1", 42)

        # Connection is automatically returned to pool
        return dict(user), [dict(log) for log in logs]
```

### Key Differences from psycopg2

| Aspect | psycopg2 (Old) | asyncpg (New) |
|--------|----------------|---------------|
| **I/O Model** | Synchronous (blocks) | Asynchronous (non-blocking) |
| **Function Type** | Regular functions | `async def` functions |
| **Calling** | `result = func()` | `result = await func()` |
| **Parameters** | `%s, %s` placeholders | `$1, $2` placeholders |
| **Connection** | `psycopg2.connect()` | `pool.acquire()` context manager |
| **Row Access** | `row[0], row[1]` (index) | `row["column"]` (dict) |
| **JSONB** | `Json(data)` wrapper | Pass dict directly |
| **Cursor** | `cursor.execute()` | `conn.execute()` or helpers |

### Migration Example

**Before (psycopg2):**
```python
import psycopg2
from psycopg2.extras import RealDictCursor, Json

def get_user(user_id):
    conn = psycopg2.connect(...)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def save_data(data):
    conn = psycopg2.connect(...)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (data) VALUES (%s)",
            (Json(data),)
        )
        conn.commit()
    finally:
        conn.close()
```

**After (asyncpg):**
```python
from backend.db_helpers import fetch_one, execute

async def get_user(user_id):
    return await fetch_one("SELECT * FROM users WHERE id = $1", user_id)

async def save_data(data):
    await execute("INSERT INTO logs (data) VALUES ($1)", data)
```

### Best Practices

1. **Always use `async def`** for functions that access the database
2. **Always `await`** database operations
3. **Use helper functions** (`fetch_one`, `fetch_all`, etc.) instead of raw pool access
4. **Use `$1, $2, $3`** parameter placeholders, not `%s`
5. **Access rows with dict keys**, not indices: `row["name"]` not `row[0]`
6. **Pass dicts directly** to JSONB columns (no `Json()` wrapper)
7. **Use `transaction()` context manager** for multi-statement transactions
8. **Don't create connections manually** - always use the global pool

### Health Monitoring

The `/api/health` endpoint checks pool status:

```bash
curl http://localhost:8200/api/health
```

Response:
```json
{
  "status": "healthy",
  "redis": "connected",
  "database": {
    "status": "healthy",
    "pool_size": 15,
    "free_connections": 12,
    "min_size": 10,
    "max_size": 50
  }
}
```

### Testing

#### Unit Tests

Tests for connection pool functionality:
```bash
pytest tests/test_db_pool.py -v
```

#### Integration Tests

Tests for async database operations (requires PostgreSQL):
```bash
# Set DATABASE_URL in .env first
pytest tests/test_async_db.py -v
```

#### Load Tests

Tests for connection pool performance under stress:
```bash
pytest tests/test_load_pool.py -v
```

**Expected Results:**
- Connection reuse rate: >50%
- Simple queries: <100ms avg latency
- Write queries: <200ms avg latency
- Complex queries: <500ms avg latency
- Pool exhaustion: Zero failures (graceful queuing)

### Common Gotchas

1. **Forgetting `await`:** `fetch_one()` returns a coroutine, not the result
   ```python
   # ❌ Wrong
   user = fetch_one("SELECT * FROM users WHERE id = $1", 42)

   # ✓ Correct
   user = await fetch_one("SELECT * FROM users WHERE id = $1", 42)
   ```

2. **Wrong parameter placeholders:** Use `$1`, not `%s`
   ```python
   # ❌ Wrong
   await fetch_one("SELECT * FROM users WHERE id = %s", 42)

   # ✓ Correct
   await fetch_one("SELECT * FROM users WHERE id = $1", 42)
   ```

3. **Index-based row access:** Use dict keys, not indices
   ```python
   # ❌ Wrong
   name = row[0]

   # ✓ Correct
   name = row["name"]
   ```

4. **Creating connections manually:** Never call `asyncpg.connect()` directly
   ```python
   # ❌ Wrong
   conn = await asyncpg.connect(...)

   # ✓ Correct
   pool = get_pool()
   async with pool.acquire() as conn:
       ...
   ```

5. **Using `Json()` wrapper:** Pass dicts directly to JSONB columns
   ```python
   # ❌ Wrong (psycopg2 pattern)
   await execute("INSERT INTO logs (data) VALUES ($1)", Json(data))

   # ✓ Correct (asyncpg automatically serializes dicts)
   await execute("INSERT INTO logs (data) VALUES ($1)", data)
   ```

### Migration Scripts Exception

**One-off scripts can still use psycopg2** (connection pooling not needed):
- `backend/migrate_db.py`
- `backend/migrate_pm_pitches.py`
- `backend/storage/migrate_sqlite_to_pg.py`
- `scripts/backfill_graphs.py`

These scripts are documented with a note explaining why psycopg2 is acceptable.

---

## Pipeline Context Keys

Type-safe keys for context data:

```python
# Input keys
USER_QUERY = ContextKey("user_query")
CONVERSATION_ID = ContextKey("conversation_id")

# Stage outputs
RESEARCH_PACK_A = ContextKey("research_pack_a")
RESEARCH_PACK_B = ContextKey("research_pack_b")
PM_PITCHES = ContextKey("pm_pitches")
PEER_REVIEWS = ContextKey("peer_reviews")
CHAIRMAN_DECISION = ContextKey("chairman_decision")

# Trading-specific
MARKET_SNAPSHOT = ContextKey("market_snapshot")
EXECUTION_CONSTRAINTS = ContextKey("execution_constraints")
RISK_ASSESSMENT = ContextKey("risk_assessment")
```

---

## Data Model

### PM Pitch JSON

```json
{
  "idea_id": "uuid",
  "week_id": "YYYY-MM-DD",
  "model": "openai/gpt-5.1",
  "instrument": "SPY",
  "direction": "LONG",
  "horizon": "1w",
  "thesis_bullets": ["..."],
  "indicators": [...],
  "invalidation": "...",
  "conviction": 1.5,
  "timestamp": "ISO8601"
}
```

### Peer Review JSON

```json
{
  "review_id": "uuid",
  "pitch_id": "uuid",
  "scores": {
    "clarity": 8,
    "edge_plausibility": 7,
    "timing_catalyst": 6,
    "risk_definition": 9,
    "indicator_integrity": 8,
    "originality": 5,
    "tradeability": 7
  },
  "best_argument_against": "...",
  "one_flip_condition": "...",
  "suggested_fix": "..."
}
```

### Chairman Decision JSON

```json
{
  "selected_trade": {
    "instrument": "SPY",
    "direction": "LONG",
    "horizon": "1w"
  },
  "conviction": 1.2,
  "rationale": "...",
  "dissent_summary": [...],
  "monitoring_plan": {...}
}
```

---

## CLI Commands

### Weekly Pipeline

```bash
# Full pipeline
python cli.py run_weekly

# Step-by-step
python cli.py research
python cli.py pm_pitches
python cli.py peer_review
python cli.py chairman
python cli.py execute --all-accounts
```

### Checkpoints

```bash
# Single checkpoint
python cli.py checkpoint --time 09:00

# All checkpoints
python cli.py checkpoint --all
```

### Postmortem

```bash
python cli.py postmortem --week 2025-01-08
python cli.py summary --week 2025-01-08
```

---

## Paper Trading Accounts

| Account | Strategy | Model |
|---------|----------|-------|
| Acct 1 | Individual PM | GPT-5.1 |
| Acct 2 | Individual PM | Gemini 3 Pro |
| Acct 3 | Individual PM | Sonnet 4.5 |
| Acct 4 | Individual PM | Grok |
| Acct 5 | Council | Chairman synthesis |
| Acct 6 | Baseline | FLAT (no trades) |

### Metrics Tracked

- P/L, Max Drawdown, Turnover
- Conviction Volatility
- Panic Exits (unjustified exits)
- Council vs Individual comparison

---

## Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...
APCA_API_KEY_ID=...
APCA_API_SECRET_KEY=...

# Optional - API Keys
GEMINI_API_KEY=...
PERPLEXITY_API_KEY=...

# Optional - Configuration
DATABASE_PATH=./runs/events.db
LOG_LEVEL=INFO

# Port Configuration (New - see backend/config/ports.py)
PORT_BACKEND=8200       # Backend API server (default: 8200)
PORT_FRONTEND=4173      # Frontend dev server (default: 4173)
PORT_TEST=8201          # Test utilities (default: 8201)
PORT_POSTGRES=5432      # PostgreSQL (default: 5432, future use)
TAILSCALE_IP=100.100.238.72  # Tailscale IP for CORS
```

---

## Baseline: llm-council

The original `llm-council` backend is preserved in `backend/` for reference. Key components:

### `backend/council.py`

- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_collect_rankings()`: Anonymized peer evaluation
- `stage3_synthesize_final()`: Chairman synthesis
- `parse_ranking_from_text()`: Extract rankings from model output
- `calculate_aggregate_rankings()`: Aggregate peer rankings

### `backend/openrouter.py`

- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries with `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'

### Porting to Pipeline

| Original | New Pipeline Stage |
|----------|-------------------|
| `stage1_collect_responses()` | `CollectResponsesStage` |
| `stage2_collect_rankings()` | `CollectRankingsStage` |
| `stage3_synthesize_final()` | `SynthesizeFinalStage` |
| `run_full_council()` | `LLMCouncilPipeline` |

---

## Key Design Decisions

### 1. Immutable Context

`PipelineContext` is never mutated. Each stage returns a new context. This enables:

- Easy debugging (can inspect intermediate contexts)
- Replay capability (can re-run from any point)
- Concurrent execution (no shared state)

### 2. Anonymized Peer Review

Models receive "Response A, B, C" instead of model names. This prevents favoritism and creates cleaner training data.

### 3. Frozen Indicators

Indicators are captured once per week and frozen. Checkpoints can only reference these frozen values, not fetch new ones. This prevents overfitting to intraday noise.

### 4. Event Sourcing

All state changes are stored as immutable events in SQLite. This enables:

- Full replay for debugging
- Analysis of decision flow
- Audit trail for all trades

### 5. Hard Rule: No Mid-Week Research

Checkpoints can only use:
- Frozen indicator values
- Current P/L
- Peer performance snapshot

No new research sources are allowed during the week.

---

## Integration Points

### OpenRouter

Single "PM tool" wrapper:
- Model ID
- Prompt template (Jinja2)
- JSON schema validation
- Retry with "fix-json" mode

### Alpaca MCP Server

Used via MCP tools (not raw HTTP):
- Price snapshots
- Position / account state
- Paper order placement

### Research Providers

- **Gemini Deep Research:** Research Pack A
- **Perplexity Deep Research:** Research Pack B

---

## Common Gotchas

1. **Module Imports:** Use relative imports (`from .config import ...`) not absolute imports
2. **Port Configuration:** Backend runs on 8001 (not 8000) to avoid conflicts
3. **Context Immutability:** Never mutate context in place - always return a new context
4. **Anonymization:** Models receive anonymous labels - de-anonymization happens via `label_to_model` mapping
5. **Frozen Indicators:** Checkpoints cannot fetch new indicator values

---

## Development Status

**Current Phase:** Planning & Architecture Design

**Completed:**
- [x] PRD.md with full requirements
- [x] PIPELINE.md with architecture details
- [x] Config file skeletons (assets, schedule, models)
- [x] README.md and CLAUDE.md

**Next Steps:**
1. Implement core pipeline classes (Stage, Pipeline, PipelineContext)
2. Port llm-council stages to new pipeline format
3. Implement Research providers (Gemini, Perplexity)
4. Add Market Snapshot stage
5. Add Risk Management stage
6. Integrate Alpaca MCP server
7. Implement SQLite event store
8. Add checkpoint engine
9. Implement CLI commands

---

## References

- [karpathy/llm-council](https://github.com/karpathy/llm-council) - Baseline pattern
- [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server) - MCP tools for trading
- [OpenRouter](https://openrouter.ai/) - Multi-model API access
