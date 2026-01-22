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
