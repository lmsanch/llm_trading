# Pipeline Stage Reference

Quick reference guide for all pipeline stages in the LLM Trading system.

---

## Overview

The LLM Trading pipeline consists of composable stages that transform data through a series of operations. Each stage:
- Has a clear input/output contract via `PipelineContext`
- Executes asynchronously
- Returns a new immutable context (never mutates)
- Can be combined into different pipeline configurations

For detailed architecture information, see [PIPELINE.md](../PIPELINE.md).

---

## Quick Reference Table

| Stage | Purpose | Parameters | Inputs | Outputs |
|-------|---------|------------|--------|---------|
| `GeminiResearchStage` | Generate deep research report via Gemini | Model config, API key | `USER_QUERY` | `RESEARCH_PACK_A` |
| `PerplexityResearchStage` | Generate deep research report via Perplexity | Model config, API key | `USER_QUERY` | `RESEARCH_PACK_B` |
| `PMPitchStage` | Generate trade pitches from all PM models | PM model list, schemas | `RESEARCH_PACK_A`, `RESEARCH_PACK_B` | `PM_PITCHES` |
| `PeerReviewStage` | Anonymized cross-evaluation of pitches | Review criteria, scoring schema | `PM_PITCHES` | `PEER_REVIEWS`, `LABEL_TO_MODEL` |
| `ChairmanStage` | Synthesize final trading decision | Chairman model, synthesis prompt | `PM_PITCHES`, `PEER_REVIEWS` | `CHAIRMAN_DECISION` |
| `MarketSnapshotStage` | Capture frozen market indicators | Asset list, indicator configs | - | `MARKET_SNAPSHOT`, `EXECUTION_CONSTRAINTS` |
| `RiskManagementStage` | Assess risk and size positions | Risk limits, portfolio constraints | `CHAIRMAN_DECISION`, `MARKET_SNAPSHOT` | `RISK_ASSESSMENT` |
| `ExecutionStage` | Execute trades via Alpaca | Account configs, Alpaca MCP client | `CHAIRMAN_DECISION`, `RISK_ASSESSMENT` | `EXECUTION_RESULT` |

---

## Stage Details

### Research Layer

#### GeminiResearchStage

**Purpose:** Query Gemini Deep Research to generate comprehensive market analysis

**Parameters:**
- `model`: Model identifier (e.g., `gemini/gemini-3.0-pro`)
- `api_key`: Gemini API key
- `timeout`: Request timeout in seconds

**Context Keys:**
- Input: `USER_QUERY` (str) - Research question or topic
- Output: `RESEARCH_PACK_A` (dict) - Structured research report with sources

**Usage:**
```python
from research.providers import GeminiResearchStage

stage = GeminiResearchStage(model="gemini/gemini-3.0-pro")
context = await stage.execute(context)
```

---

#### PerplexityResearchStage

**Purpose:** Query Perplexity Deep Research to generate comprehensive market analysis

**Parameters:**
- `model`: Model identifier (e.g., `perplexity/sonar-pro`)
- `api_key`: Perplexity API key
- `timeout`: Request timeout in seconds

**Context Keys:**
- Input: `USER_QUERY` (str) - Research question or topic
- Output: `RESEARCH_PACK_B` (dict) - Structured research report with sources

**Usage:**
```python
from research.providers import PerplexityResearchStage

stage = PerplexityResearchStage(model="perplexity/sonar-pro")
context = await stage.execute(context)
```

---

#### ResearchStage

**Purpose:** Fetch market data and generate macro research analysis using Perplexity Sonar Deep Research

**Overview:**

`ResearchStage` is the primary research stage that combines market data fetching with AI-powered macro analysis. Unlike the individual provider stages above, this stage handles both data collection and research generation in a single unified workflow.

The stage performs four key operations:
1. Fetches 30-day OHLCV market data from local database (populated by separate data fetcher)
2. Optionally fetches Alpaca account information (buying power, portfolio value)
3. Loads research prompt template from config or uses provided override
4. Queries Perplexity Sonar Deep Research for macro analysis

**Constructor Parameters:**
- `prompt_override` (str | None): Optional custom prompt to override default research template
  - Default: None (loads from `backend/config/prompts/research_prompt.md`)
  - Use case: Custom research questions or different analysis frameworks
- `temperature` (float | None): Model temperature for research generation
  - Default: None (uses TemperatureManager default for "research")
  - Range: 0.0 (deterministic) to 2.0 (creative)

**Context Keys:**

*Input:*
- `SENTIMENT_PACK` (dict, optional) - Market sentiment data from previous sentiment analysis stage
  - If present, included in research prompt for context
  - If absent, research proceeds without sentiment data

*Output:*
- `RESEARCH_PACK_A` (dict) - Structured research report containing:
  - `source`: "perplexity"
  - `model`: Model identifier used
  - `natural_language`: Full text research report
  - `structured_json`: Parsed JSON with macro_regime, top_narratives, tradable_candidates, event_calendar
  - `generated_at`: ISO8601 timestamp
  - `error`: Error message if research failed (optional)
- `MARKET_SNAPSHOT` (dict) - Current market data containing:
  - `asof_et`: Timestamp in ET timezone
  - `instruments`: Dict of instrument data (30-day OHLCV, technical indicators)
  - `account_info`: Alpaca account status (buying_power, cash, portfolio_value)
  - `error`: Error message if data fetch failed (optional)

**Research Report Schema:**

The `structured_json` field in `RESEARCH_PACK_A` follows this schema:

```json
{
  "macro_regime": {
    "risk_mode": "RISK_ON" | "RISK_OFF" | "NEUTRAL",
    "description": "Current market regime explanation"
  },
  "top_narratives": [
    "Key narrative 1 driving markets",
    "Key narrative 2...",
    "..."
  ],
  "tradable_candidates": [
    {
      "ticker": "SPY",
      "directional_bias": "LONG" | "SHORT" | "NEUTRAL",
      "rationale": "Why this bias makes sense"
    }
  ],
  "event_calendar": [
    {
      "date": "2025-01-15",
      "event": "FOMC Meeting",
      "impact": "HIGH" | "MEDIUM" | "LOW"
    }
  ],
  "confidence_notes": {
    "known_unknowns": "Key uncertainties",
    "data_quality_flags": ["flag1", "flag2"]
  },
  "weekly_graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Configuration Example:**

```python
from backend.pipeline.stages.research import ResearchStage

# Basic usage with defaults
stage = ResearchStage()

# With custom prompt override
custom_prompt = """
Analyze current market conditions focusing on:
1. Fed policy trajectory
2. Earnings season dynamics
3. Geopolitical risks
"""
stage = ResearchStage(prompt_override=custom_prompt)

# With custom temperature for more deterministic output
stage = ResearchStage(temperature=0.3)

# Full customization
stage = ResearchStage(
    prompt_override=custom_prompt,
    temperature=0.5
)

# Execute stage
context = await stage.execute(context)
market_snapshot = context.get(MARKET_SNAPSHOT)
research_pack = context.get(RESEARCH_PACK_A)
```

**Error Handling:**

The stage is designed to be fault-tolerant and never crash the pipeline:

1. **Market Data Fetch Failure:**
   - Returns minimal market snapshot with error field
   - Research proceeds with limited data
   - Error logged but doesn't stop execution

2. **Account Info Fetch Failure:**
   - Account info fields set to "N/A"
   - Research proceeds without account context
   - Optional data doesn't block pipeline

3. **Research Prompt Load Failure:**
   - Falls back to built-in default prompt
   - Default prompt covers macro regime, narratives, candidates, events
   - Ensures research always runs

4. **Perplexity API Failure:**
   - Returns error research pack with NEUTRAL regime
   - Includes error message in response
   - Pipeline can continue with degraded data

**Error Research Pack Structure:**
```json
{
  "source": "perplexity",
  "model": "unknown",
  "natural_language": "Research generation failed: <error message>",
  "structured_json": {
    "macro_regime": {
      "risk_mode": "NEUTRAL",
      "description": "Research unavailable"
    },
    "top_narratives": [],
    "tradable_candidates": [],
    "event_calendar": [],
    "confidence_notes": {
      "known_unknowns": "Error: <error message>",
      "data_quality_flags": ["research_failed"]
    }
  },
  "error": "<error message>",
  "generated_at": "<timestamp>"
}
```

**Database Persistence:**

Research results are automatically saved to PostgreSQL database:
- Table: `research_reports`
- Fields: week_id, provider, model, natural_language, structured_json, status, error_message, generated_at
- Knowledge graph auto-generated and stored in `structured_json.weekly_graph`
- Used for historical analysis and backtesting

**Common Issues and Debugging:**

1. **"Prompt file not found" warning:**
   - Cause: `backend/config/prompts/research_prompt.md` doesn't exist
   - Impact: Falls back to default prompt (minimal impact)
   - Fix: Create prompt file or use prompt_override parameter

2. **"Could not fetch account info" warning:**
   - Cause: Alpaca API credentials invalid or network issue
   - Impact: Account info shows "N/A" but research proceeds
   - Fix: Verify APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env

3. **"Error fetching market data" error:**
   - Cause: Database not populated or data_fetcher.py not running
   - Impact: Research proceeds with empty instrument data
   - Fix: Run `python backend/storage/data_fetcher.py` to populate data

4. **"Perplexity research failed" warning:**
   - Cause: API key invalid, rate limit, or network issue
   - Impact: Returns error research pack with NEUTRAL regime
   - Fix: Verify PERPLEXITY_API_KEY in .env, check rate limits

5. **Empty structured_json in response:**
   - Cause: Perplexity returned unparseable response
   - Impact: Research unavailable for downstream stages
   - Fix: Check prompt clarity, increase temperature, verify model availability

**Integration with Other Stages:**

```python
# Typical pipeline integration
from backend.pipeline import Pipeline
from backend.pipeline.stages.research import ResearchStage
from backend.pipeline.stages.market_sentiment import MarketSentimentStage

pipeline = Pipeline([
    MarketSentimentStage(),  # Optional: adds SENTIMENT_PACK to context
    ResearchStage(),         # Uses SENTIMENT_PACK if available
    # ... PM stages use RESEARCH_PACK_A and MARKET_SNAPSHOT
])
```

**Performance Characteristics:**

- **Market data fetch:** <1s (local database query)
- **Account info fetch:** 1-2s (Alpaca API call)
- **Perplexity research:** 30-60s (deep research mode)
- **Total stage duration:** ~45-75s typical
- **Database save:** <100ms (async write)

**See Also:**

- `backend/pipeline/stages/research.py` - Full implementation
- `backend/config/prompts/research_prompt.md` - Default prompt template
- `backend/research/perplexity.py` - Perplexity API integration
- `backend/storage/data_fetcher.py` - Market data collection service

---

### PM Layer

#### PMPitchStage

**Purpose:** Generate trade pitches from all configured PM models

**Parameters:**
- `pm_models`: List of PM model identifiers (e.g., `["openai/gpt-5.1", "anthropic/claude-sonnet-4.5"]`)
- `pitch_schema`: JSON schema for pitch validation
- `prompt_template`: Jinja2 template for pitch generation

**Context Keys:**
- Input: `RESEARCH_PACK_A` (dict), `RESEARCH_PACK_B` (dict) - Research reports
- Output: `PM_PITCHES` (list) - List of trade pitch objects

**Pitch Schema:**
```json
{
  "idea_id": "uuid",
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

---

### Peer Review Layer

#### PeerReviewStage

**Purpose:** Anonymized cross-evaluation of PM pitches to prevent model favoritism

**Parameters:**
- `review_models`: List of models to use for review (typically same as PM models)
- `scoring_schema`: JSON schema defining review scoring criteria
- `anonymize`: Enable anonymization (default: true)

**Context Keys:**
- Input: `PM_PITCHES` (list) - Trade pitches to review
- Output:
  - `PEER_REVIEWS` (list) - Anonymized review results
  - `LABEL_TO_MODEL` (dict) - Mapping from anonymous labels to model names

**Review Schema:**
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

---

### Chairman Layer

#### ChairmanStage

**Purpose:** Synthesize final trading decision from PM pitches and peer reviews

**Parameters:**
- `chairman_model`: Opus-class model for synthesis (e.g., `anthropic/claude-opus-4`)
- `synthesis_prompt`: Jinja2 template for chairman synthesis
- `max_tokens`: Maximum tokens for synthesis response

**Context Keys:**
- Input: `PM_PITCHES` (list), `PEER_REVIEWS` (list)
- Output: `CHAIRMAN_DECISION` (dict) - Final trading decision with rationale

**Decision Schema:**
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

### Market Layer

#### MarketSnapshotStage

**Purpose:** Capture frozen market indicators and execution constraints

**Parameters:**
- `assets`: List of tradable assets from `config/assets.yaml`
- `indicator_configs`: Indicator calculation configurations
- `mcp_client`: Alpaca MCP client for market data

**Context Keys:**
- Input: - (no required inputs)
- Output:
  - `MARKET_SNAPSHOT` (dict) - Frozen indicator values, prices, volatility
  - `EXECUTION_CONSTRAINTS` (dict) - Trading hours, liquidity constraints

**Notes:**
- Indicators are frozen at capture time
- Checkpoints reference frozen values, not live data
- Prevents overfitting to intraday noise

---

#### RiskManagementStage

**Purpose:** Assess risk and calculate position sizing for trades

**Parameters:**
- `risk_limits`: Maximum drawdown, position size limits
- `portfolio_constraints`: Diversification rules, concentration limits
- `account_configs`: Per-account risk parameters

**Context Keys:**
- Input: `CHAIRMAN_DECISION` (dict), `MARKET_SNAPSHOT` (dict)
- Output: `RISK_ASSESSMENT` (dict) - Risk metrics and position sizes

**Risk Assessment Schema:**
```json
{
  "approved": true,
  "position_size": 0.15,
  "stop_loss": 0.02,
  "risk_metrics": {
    "expected_drawdown": 0.03,
    "correlation_risk": "medium",
    "liquidity_score": 0.85
  },
  "warnings": [...]
}
```

---

### Execution Layer

#### ExecutionStage

**Purpose:** Execute trades via Alpaca paper trading accounts

**Parameters:**
- `account_configs`: Configuration for all 6 paper trading accounts
- `mcp_client`: Alpaca MCP client for order placement
- `dry_run`: Simulate execution without placing orders (default: false)

**Context Keys:**
- Input: `CHAIRMAN_DECISION` (dict), `RISK_ASSESSMENT` (dict)
- Output: `EXECUTION_RESULT` (dict) - Order confirmations and execution status

**Execution Result Schema:**
```json
{
  "orders_placed": 6,
  "successful": 5,
  "failed": 1,
  "order_ids": ["...", "..."],
  "errors": [...],
  "timestamp": "ISO8601"
}
```

---

## Pipeline Configurations

### Weekly Pipeline

Runs once per week (Wednesday 08:00 ET) to generate new trading decisions:

```python
weekly_pipeline = Pipeline([
    GeminiResearchStage(),
    PerplexityResearchStage(),
    PMPitchStage(),
    PeerReviewStage(),
    ChairmanStage(),
    MarketSnapshotStage(),
    RiskManagementStage(),
    ExecutionStage(),
])
```

### Checkpoint Pipeline

Runs at daily checkpoints (09:00, 12:00, 14:00, 15:50 ET) for conviction updates:

```python
checkpoint_pipeline = Pipeline([
    MarketSnapshotStage(),
    ConvictionUpdateStage(),  # Not listed above - updates conviction only
    RiskManagementStage(),
    ExecutionStage(),  # Only if action != STAY
])
```

**Note:** Checkpoints use frozen indicators from the weekly run. No new research is performed.

---

## Legacy Stages (llm-council)

These stages are ported from the original llm-council codebase and remain for baseline comparison:

| Stage | Purpose | Inputs | Outputs |
|-------|---------|--------|---------|
| `CollectResponsesStage` | Parallel queries to council models | `USER_QUERY` | `STAGE1_RESULTS` |
| `CollectRankingsStage` | Anonymized peer evaluation | `USER_QUERY`, `STAGE1_RESULTS` | `STAGE2_RESULTS` |
| `SynthesizeFinalStage` | Chairman synthesis | `USER_QUERY`, `STAGE1_RESULTS`, `STAGE2_RESULTS` | `STAGE3_RESULT` |

These stages are used in the baseline `LLMCouncilPipeline` for conversational AI, not trading decisions.

---

## See Also

- [PIPELINE.md](../PIPELINE.md) - Pipeline architecture and design principles
- [PRD.md](../PRD.md) - Product requirements and specifications
- [CLAUDE.md](../CLAUDE.md) - Technical implementation notes
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - REST API documentation
