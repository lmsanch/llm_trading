# LLM Trading — Implementation Plan v0.1

## Executive Summary

Build a **pipeline-first LLM trading system** using Karpathy's `llm-council` pattern (anonymized peer review + chairman synthesis) combined with Alpaca's MCP server for market data and paper trading.

**Key Innovation:** Separate *research* (2 deep research tools) from *PM decision-making* (4 models via OpenRouter), with anonymized peer review and chairman synthesis. Run **6 parallel paper accounts** to compare individual PMs vs Council trade.

---

## 0) Repos to Use

### A) Base pattern: Karpathy "LLM Council"

- **Source:** `karpathy/llm-council`
- **Description:** Local web app pattern: query multiple models (via OpenRouter), anonymized peer review, then chairman synthesis
- **Action:** Clone as starting point, refactor into **headless pipeline** + optional UI
- **Link:** https://github.com/karpathy/llm-council

### B) Execution + data: Alpaca MCP Server

- **Source:** `alpacahq/alpaca-mcp-server`
- **Description:** Exposes Alpaca data/trading as MCP tools
- **Features:** VS Code MCP settings integration, paper trading support
- **Link:** https://github.com/alpacahq/alpaca-mcp-server

---

## 1) Create Private Repo and Initial Scaffold

### 1.1 Repository Setup

**New private repo name:** `llm-trading` (or "llm_trading")

### Steps

1. Create repo on GitHub (private): `lmsanch/llm-trading`
2. Clone `karpathy/llm-council` locally and push into `llm-trading` as "upstream baseline"
3. Add Alpaca MCP as either:
   - submodule, or
   - sibling folder under `vendor/alpaca-mcp-server/`

### 1.2 Architecture Decision

**Make it a pipeline with logs; UI later.**

Don't keep it as a "Chat UI app" first. Build:
- Headless pipeline execution
- Immutable event logs
- Optional web UI for monitoring (v2)

---

## 2) Tradable Universe (Macro ETFs Only + Gold + Oil)

### 2.1 Core Macro Set

| Category | Instruments | Description |
|----------|-------------|-------------|
| **Risk-on equities** | `SPY`, `QQQ`, `IWM` | S&P 500, Nasdaq 100, Russell 2000 |
| **Duration** | `TLT` (or `IEF`) | 20+ Year Treasury Bond |
| **Credit** | `HYG` (or `LQD`) | High Yield or Investment Grade Corporate |
| **USD proxy** | `UUP` | US Dollar Index |
| **FX proxy** (optional) | `FXY` | JPY risk proxy |
| **Emerging markets** (optional) | `EEM` | EM exposure |

### 2.2 Wrinkle Instruments

| Category | Instruments | Description |
|----------|-------------|-------------|
| **Gold** | `GLD` (or `IAU`) | Gold ETF |
| **Oil** | `USO` (or `BNO`) | Oil ETF |

### 2.3 Trading Rule

> The council can only pick **one instrument per account per week** (LONG/SHORT/FLAT).

---

## 3) System Roles and Flow

### 3.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEEKLY PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐      ┌──────────────────────────────────────────┐   │
│  │  RESEARCH LAYER  │      │           PM LAYER (4 PMs)               │   │
│  ├──────────────────┤      ├──────────────────────────────────────────┤   │
│  │ Gemini Deep      │──────▶│  GPT-5.1    │ Gemini 3.0  │ Sonnet 4.5  │   │
│  │ Research         │      │             │            │   Grok       │   │
│  │ Perplexity Deep  │──────┤             │            │              │   │
│  │ Research         │      │   PM Pitch  │  PM Pitch  │  PM Pitch    │   │
│  └──────────────────┘      └──────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    PEER REVIEW LAYER (Anonymous)                     │ │
│  │   Each PM reviews other pitches → rubric scores + critique            │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                     CHAIRMAN LAYER (CIO)                              │ │
│  │   All pitches + all reviews → Council Trade + dissent notes           │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      PAPER TRADING EXECUTION                          │ │
│  │   6 accounts: 4 PMs + 1 Council + 1 FLAT baseline                     │ │
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

### 3.2 Research Layer (2 "Analysts")

| Analyst | Tool | Output |
|---------|------|--------|
| Gemini Deep Research | Google Gemini Deep Research | Research Pack A |
| Perplexity Deep Research | Perplexity Deep Research | Research Pack B |

### 3.3 PM Layer (4 "PMs" via OpenRouter)

Each PM receives:
- Research Pack A
- Research Pack B

Each PM outputs:
- Trade recommendation
- Conviction level
- Frozen indicators

**Models:**
1. GPT-5.1
2. Gemini 3.0 Pro
3. Claude Sonnet 4.5
4. Grok

### 3.4 Anonymous Peer-Review Layer

Each PM reviews the *other PM pitches* with identities removed.

**Output:**
- Rubric scores (1-10 on multiple dimensions)
- "Kill shot" critique
- Suggested improvements

### 3.5 Chairman Layer (one "CIO")

**Model:** Opus-class model (or strongest "judge/synthesizer")

**Input:**
- All pitches
- All reviews

**Output:**
- Council Trade
- Dissent notes

---

## 4) Paper Trading Accounts (6 Accounts)

Run **both individual and council in parallel:**

| Account | Strategy | Description |
|---------|----------|-------------|
| Acct 1 | GPT-5.1 PM trade | Individual PM trade |
| Acct 2 | Gemini 3 Pro PM trade | Individual PM trade |
| Acct 3 | Sonnet 4.5 PM trade | Individual PM trade |
| Acct 4 | Grok PM trade | Individual PM trade |
| Acct 5 | Chairman Council trade | Council-aggregated trade |
| Acct 6 | FLAT baseline | No trades (churn tax benchmark) |

### 4.1 Baseline Strategy

> Keep Acct 6 as **FLAT** for the first month. This gives a "churn tax" benchmark.

---

## 5) Data Model (What to Store, Always)

Create an **immutable event log** per "week idea".

### 5.1 Entities

| Entity | Description |
|--------|-------------|
| `research_pack` | Output from Gemini/Perplexity deep research |
| `pm_pitch` | Per-model PM trade recommendation |
| `peer_review` | Per reviewer→pitch evaluation |
| `chairman_decision` | Final council trade decision |
| `checkpoint_update` | 9:00 / 12:00 / 14:00 / 15:50 updates |
| `execution_event` | Orders, fills, position changes |
| `weekly_postmortem` | End-of-week analysis |

### 5.2 Storage

- **Start with SQLite** (simple, portable)
- Tables + JSON blobs for prompts/outputs
- Keep raw model outputs + normalized parsed schema

---

## 6) Schemas (Minimal but Strict)

### 6.1 PM Pitch JSON

```json
{
  "idea_id": "uuid",
  "week_id": "YYYY-MM-DD",
  "model": "openai/gpt-5.1",
  "instrument": "SPY",
  "direction": "LONG",  // LONG | SHORT | FLAT
  "horizon": "1w",      // 1d | 3d | 1w
  "thesis_bullets": [   // max 5
    "First reason...",
    "Second reason...",
    "Third reason..."
  ],
  "consensus_map": {
    "gemini_research": "agree",
    "perplexity_research": "disagree"
  },
  "indicators": [       // frozen list with thresholds
    {"name": "RSI", "value": 65, "threshold": 70, "direction": "below"},
    {"name": "MACD", "value": 1.2, "threshold": 0, "direction": "above"}
  ],
  "invalidation": "Exit if RSI crosses above 75 OR MACD turns negative",
  "conviction": 1.5,    // -2 to +2
  "position_size_hint": 0.8,  // 0 to 1 (optional)
  "risk_notes": "Key risks to monitor...",
  "timestamp": "ISO8601"
}
```

### 6.2 Peer Review JSON (Scored Rubric)

```json
{
  "review_id": "uuid",
  "pitch_id": "uuid",
  "reviewer_model": "anthropic/claude-sonnet-4.5",
  "anonymized_pitch_id": "Pitch A",
  "scores": {
    "clarity": 8,           // 1-10
    "edge_plausibility": 7, // 1-10
    "timing_catalyst": 6,   // 1-10
    "risk_definition": 9,   // 1-10
    "indicator_integrity": 8, // 1-10
    "originality": 5,       // 1-10
    "tradeability": 7       // 1-10
  },
  "best_argument_against": "Strongest counter-argument...",
  "one_flip_condition": "Would flip to SHORT if...",
  "suggested_fix": "Improve by...",
  "timestamp": "ISO8601"
}
```

### 6.3 Chairman Decision JSON

```json
{
  "decision_id": "uuid",
  "week_id": "YYYY-MM-DD",
  "selected_trade": {
    "instrument": "SPY",
    "direction": "LONG",
    "horizon": "1w"
  },
  "conviction": 1.2,  // -2 to +2
  "rationale": "Brief synthesis...",
  "dissent_summary": [
    {"model": "grok-4", "position": "SHORT on SPY", "reason": "..."}
  ],
  "monitoring_plan": {
    "checkpoints": ["09:00", "12:00", "14:00", "15:50"],
    "key_indicators": ["RSI", "MACD", "VIX"],
    "watch_conditions": ["RSI > 75", "VIX spike > 20"]
  },
  "timestamp": "ISO8601"
}
```

---

## 7) Checkpoints ("Retro-Feeding", Not Deep Research)

### 7.1 Schedule

**Times:** 09:00, 12:00, 14:00, 15:50 (ET)

### 7.2 Inputs

- Latest indicator values
- Current P/L (per account)
- "Peer performance snapshot" (optional)

### 7.3 Outputs

```json
{
  "checkpoint_id": "uuid",
  "week_id": "YYYY-MM-DD",
  "time": "09:00",
  "account_id": "council",
  "conviction_before": 1.5,
  "conviction_after": 1.2,
  "action": "STAY",  // STAY | EXIT | FLIP | REDUCE
  "reason_delta": "RSI still below threshold, P/L holding...",
  "indicators_snapshot": [
    {"name": "RSI", "value": 68, "previous": 65}
  ],
  "timestamp": "ISO8601"
}
```

### 7.4 Hard Rule

> **No new research sources mid-week.** Only retro-feed from frozen indicators and current state.

---

## 8) Tooling / Integration Plan

### 8.1 OpenRouter

Create single "PM tool" wrapper:

| Component | Description |
|-----------|-------------|
| `model_id` | OpenRouter model identifier |
| `prompt_template` | Jinja2 template for prompts |
| `json_schema` | Expected output schema |
| `validation` | JSON schema validation |
| `retries` | Retry with "fix-json" mode on failure |

### 8.2 Alpaca MCP Server (Paper Trading + Market Data)

Use Alpaca MCP as the **only way** the system touches:

- Price snapshots
- Position / account state
- Paper order placement

#### VS Code `settings.json` Configuration

```json
{
  "mcp": {
    "servers": {
      "alpaca": {
        "command": "python",
        "args": ["-m", "alpaca_mcp_server"],
        "env": {
          "APCA_API_KEY_ID": "${env:APCA_API_KEY_ID}",
          "APCA_API_SECRET_KEY": "${env:APCA_API_SECRET_KEY}",
          "APCA_API_BASE_URL": "https://paper-api.alpaca.markets"
        }
      }
    }
  }
}
```

> **Note:** Exact module/entrypoint may differ depending on Alpaca MCP README. Align to documented launch command.

---

## 9) Repo Layout (What to Build)

```
llm-trading/
├── council/                      # adapted llm-council core
│   ├── __init__.py
│   ├── pipeline/                 # pipeline-first architecture
│   │   ├── __init__.py
│   │   ├── base.py              # Stage, Pipeline base classes
│   │   ├── context.py           # PipelineContext, ContextKey
│   │   └── stages/              # composable stages
│   │       ├── __init__.py
│   │       ├── research.py      # Gemini/Perplexity research
│   │       ├── pm_pitch.py      # PM pitch generation
│   │       ├── peer_review.py   # Anonymized peer review
│   │       └── chairman.py      # Chairman synthesis
│   ├── prompts/                 # Jinja2 prompt templates
│   │   ├── pm_pitch.j2
│   │   ├── peer_review.j2
│   │   └── chairman.j2
│   ├── schemas/                 # JSON schemas for validation
│   │   ├── pm_pitch.json
│   │   ├── peer_review.json
│   │   └── chairman_decision.json
│   ├── anonymizer.py            # identity stripping, randomization
│   └── openrouter.py            # OpenRouter API client
├── research/
│   ├── __init__.py
│   └── providers/
│       ├── gemini_deep.py      # Gemini Deep Research provider
│       └── perplexity_deep.py  # Perplexity Deep Research provider
├── pm/
│   ├── __init__.py
│   ├── models.yaml              # PM models + chairman model config
│   └── pitch_generator.py       # PM pitch orchestration
├── market/
│   ├── __init__.py
│   ├── alpaca_mcp_client.py     # MCP tool wrapper (not raw HTTP)
│   └── indicators.py            # Compute/collect indicator snapshots
├── storage/
│   ├── __init__.py
│   ├── sqlite.py                # SQLite event store
│   └── models.py                # SQLAlchemy ORM models
├── runs/
│   └── week_YYYY-MM-DD/
│       ├── raw/                 # Raw model outputs
│       ├── normalized/          # Parsed and validated JSON
│       └── events.sqlite        # Week-specific event log
├── config/
│   ├── assets.yaml              # Allowed tickers + rules
│   └── schedule.yaml            # Wednesday + checkpoint times
├── cli.py                       # Main CLI entry point
├── pyproject.toml               # uv project config
├── .env.example                 # Environment variables template
├── PRD.md                       # This document
└── README.md                    # How to run
```

---

## 10) Execution Loop (Commands)

### 10.1 Wednesday (Idea Day)

```bash
# Run full weekly pipeline
python cli.py run_weekly

# Or step-by-step
python cli.py research                    # Gemini + Perplexity
python cli.py pm_pitches                  # Generate PM pitches
python cli.py peer_review                 # Anonymized peer review
python cli.py chairman                    # Chairman synthesis
python cli.py execute --all-accounts      # Place paper trades
```

### 10.2 Daily (Checkpoint Day)

```bash
# Run checkpoint at specific time
python cli.py checkpoint --time 09:00
python cli.py checkpoint --time 12:00
python cli.py checkpoint --time 14:00
python cli.py checkpoint --time 15:50

# Or run all checkpoints for today
python cli.py checkpoint --all
```

### 10.3 Next Wednesday (Post-Mortem)

```bash
# Generate post-mortem report
python cli.py postmortem --week 2025-01-08

# Print summary
python cli.py summary --week 2025-01-08
```

---

## 11) Metrics (Compare Individual PMs vs Council)

### 11.1 Per-Account Metrics

| Metric | Description |
|--------|-------------|
| **P/L** | Total profit/loss |
| **Max Drawdown** | Maximum peak-to-trough decline |
| **Turnover** | Number of exits/flips |
| **Conviction Volatility** | Sum of absolute conviction changes |
| **Panic Exits** | Exits not justified by invalidation rule |

### 11.2 Council-Specific Metrics

| Metric | Description | Success Criterion |
|--------|-------------|-------------------|
| **Drawdown Reduction** | Does council reduce max drawdown vs individuals? | Council DD < avg(individual DD) |
| **Hit Rate** | Does council improve win rate? | Council hit rate > avg(individual) |
| **Upside Performance** | Does council underperform on upside due to compromise? | Council return within 20% of best individual |

---

## 12) OpenCode Task List

### Phase 1: Foundation

- [ ] **Task 1:** Create private repo `llm-trading`, import `karpathy/llm-council` as baseline; refactor into pipeline-first architecture
- [ ] **Task 2:** Add `config/assets.yaml` with allowed ETFs: SPY/QQQ/IWM/TLT/HYG/UUP/(optional FXY/EEM) + GLD + USO
- [ ] **Task 3:** Implement strict JSON schemas + validation + json-fix retry for all outputs

### Phase 2: Core Pipeline

- [ ] **Task 4:** Implement anonymized peer-review (identity stripping, randomization)
- [ ] **Task 5:** Implement Chairman aggregation logic
- [ ] **Task 6:** Implement SQLite event store + per-week folder structure

### Phase 3: Market Integration

- [ ] **Task 7:** Integrate Alpaca MCP server (paper trading + account state + quotes)
- [ ] **Task 8:** Implement indicator computation/snapshot engine

### Phase 4: Scheduling & Execution

- [ ] **Task 9:** Implement checkpoint engine and schedule scaffolding
- [ ] **Task 10:** Implement CLI commands for weekly pipeline + checkpoints

### Phase 5: Documentation & Testing

- [ ] **Task 11:** Produce README with "how to run weekly" + "how to run checkpoints"
- [ ] **Task 12:** Add unit tests for pipeline stages
- [ ] **Task 13:** Add integration tests with paper trading sandbox

---

## 13) Environment Variables

```bash
# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...

# Alpaca Paper Trading
APCA_API_KEY_ID=...
APCA_API_SECRET_KEY=...
APCA_API_BASE_URL=https://paper-api.alpaca.markets

# Research Providers
GEMINI_API_KEY=...
PERPLEXITY_API_KEY=...

# Database
DATABASE_PATH=./runs/events.db
```

---

## 14) Success Criteria

### 14.1 Technical

- [ ] Pipeline runs end-to-end without manual intervention
- [ ] All outputs validated against JSON schemas
- [ ] Immutable event log captures all state changes
- [ ] Checkpoints run reliably at scheduled times

### 14.2 Trading

- [ ] 6 accounts running in parallel for 4+ weeks
- [ ] Council trade different from individual PMs (not just copying)
- [ ] Metrics comparison shows meaningful differentiation

### 14.3 Data Quality

- [ ] Clean separation of research vs PM decisions
- [ ] Anonymized peer review prevents model favoritism
- [ ] Frozen indicators are truly frozen (no mid-week updates)

---

## Appendix A: References

- [karpathy/llm-council](https://github.com/karpathy/llm-council) - Base council pattern
- [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server) - MCP tools for trading
- OpenRouter Documentation - Multi-model API access

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.1 | 2025-01-01 | Initial PRD from user requirements |
