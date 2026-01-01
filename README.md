# LLM Trading

> **Pipeline-first LLM trading system** using anonymized peer review + chairman synthesis for macro ETF trading decisions.

**Status:** Planning Phase - See [PRD.md](PRD.md) for complete implementation plan.

---

## Overview

This project extends Andrej Karpathy's `llm-council` pattern into a **headless pipeline** for systematic trading decisions. The system separates research from PM decision-making, runs 6 parallel paper trading accounts, and uses checkpoint-based conviction updates.

### Key Innovation

```
Research Layer (2 Analysts)
    ↓
PM Layer (4 PMs via OpenRouter)
    ↓
Anonymous Peer Review Layer
    ↓
Chairman Synthesis (CIO)
    ↓
6 Parallel Paper Trading Accounts
```

### Tradable Universe

| Category | Instruments |
|----------|-------------|
| Risk-on equities | SPY, QQQ, IWM |
| Duration | TLT (or IEF) |
| Credit | HYG (or LQD) |
| USD proxy | UUP |
| Gold | GLD |
| Oil | USO |

**Rule:** One instrument per account per week (LONG/SHORT/FLAT).

---

## Quick Start (TODO - After Implementation)

### Prerequisites

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js (for frontend, optional)
```

### Setup

```bash
# Clone repository
git clone git@github.com:lmsanch/llm-trading.git
cd llm-trading

# Install Python dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run Weekly Pipeline

```bash
# Full weekly pipeline (Wednesday)
python cli.py run_weekly

# Step-by-step
python cli.py research        # Gemini + Perplexity
python cli.py pm_pitches      # Generate PM pitches
python cli.py peer_review     # Anonymized peer review
python cli.py chairman        # Chairman synthesis
python cli.py execute --all-accounts  # Place paper trades
```

### Run Checkpoints

```bash
# Single checkpoint
python cli.py checkpoint --time 09:00

# All checkpoints for today
python cli.py checkpoint --all
```

---

## Architecture

### Pipeline-First Design

```
llm-trading/
├── council/                      # llm-council core, refactored
│   ├── pipeline/                 # composable Stage classes
│   ├── prompts/                  # Jinja2 templates
│   ├── schemas/                  # JSON schemas
│   └── openrouter.py             # OpenRouter client
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
├── config/                       # Assets, schedule, models
└── cli.py                        # Main CLI
```

### Data Flow

```
Week Start (Wednesday)
├── Research: Gemini + Perplexity → Research Packs A/B
├── PM Pitches: 4 models → Individual trade ideas
├── Peer Review: Anonymized cross-evaluation
├── Chairman: Synthesis → Council trade
└── Execute: Place trades in 6 paper accounts

Daily Checkpoints (9am, 12pm, 2pm, 3:50pm ET)
├── Snapshot: Indicators + P/L
├── Evaluate: Conviction update (STAY/EXIT/FLIP/REDUCE)
└── No new research (hard rule)

Week End
└── Postmortem: Analysis + metrics
```

---

## Paper Trading Accounts

| Account | Strategy |
|---------|----------|
| Acct 1 | GPT-5.1 PM trade |
| Acct 2 | Gemini 3 Pro PM trade |
| Acct 3 | Sonnet 4.5 PM trade |
| Acct 4 | Grok PM trade |
| Acct 5 | Chairman Council trade |
| Acct 6 | FLAT baseline |

### Council Pipeline Schema Files

**New files added for enhanced trading council workflow:**

- **Weekly Research Prompt:** `config/prompts/weekly_research_prompt_v1_5.md`
  - 7-day focused macro research template with instrument ranking
  - Replaces default llm-council research prompts (to be wired in stage 1)
  
- **PM Pitch Schema:** `config/schemas/pm_pitch_with_ranking.schema.json`
  - Full universe ranking (1-10) with expected outperformance buckets
  - Selected trade with invalidation rules and monitoring plan
  - Replaces default PM pitch schema (to be wired in stage 2)
  
- **Peer Review Schema:** `config/schemas/peer_review_ranking_vs_choice.schema.json`
  - Scores ranking quality and trade choice consistency
  - Includes kill-shot analysis and flip conditions
  - Replaces default peer review schema (to be wired in stage 2)

**Note:** These schemas will be integrated into `council.py` pipeline stages in a future update.

### Metrics


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

# Optional (for research providers)
GEMINI_API_KEY=...
PERPLEXITY_API_KEY=...
```

---

## References

- **Baseline:** [karpathy/llm-council](https://github.com/karpathy/llm-council) - Original council pattern
- **Execution:** [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server) - MCP tools for trading
- **OpenRouter** - Multi-model API access

---

## License

Private repository - All rights reserved.

---

## Development Status

See [PRD.md](PRD.md) for complete implementation plan and task list.

**Current Phase:** Planning & Architecture Design

**Next Steps:**
1. Implement pipeline-first architecture (Stage, Pipeline, PipelineContext)
2. Port llm-council stages to new pipeline format
3. Add Market Snapshot stage
4. Add Risk Management stage
5. Integrate Alpaca MCP server
6. Implement SQLite event store
7. Add checkpoint engine
