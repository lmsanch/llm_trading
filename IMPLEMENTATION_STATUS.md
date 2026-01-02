# LLM Trading Project - Implementation Status

**Compaction Date**: 2025-01-01
**Phase**: Phase 1 - Core Infrastructure (Pipeline, Config, CLI)

---

## Mission Statement

Building a **pipeline-first LLM trading system** that separates research from PM decision-making using anonymized peer review + chairman synthesis. Current focus: Complete Phase 1 implementation TODAY with real research and trades ready for Monday Jan 5, 2026 (today is holiday, Jan 1, 2026).

**Target**: End-to-end weekly pipeline working with CLI, ready for paper trading execution.

---

## Critical Files

### Planning Documents
- `/research/llm_trading/PRD.md` - Complete implementation plan (v0.1) with all requirements
- `/research/llm_trading/PIPELINE.md` - Pipeline-first architecture (Stage, Pipeline, PipelineContext)
- `/research/llm_trading/README.md` - Project overview, quick start, architecture
- `/research/llm_trading/CLAUDE.md` - Technical notes for AI assistance
- `/research/llm_trading/WEEKLY_RESEARCH.MD` - Research prompt templates and integration instructions

### Configuration (Complete)
- `/research/llm_trading/.env.template` - API key template created (user needs to fill)
- `/research/llm_trading/config/assets.yaml` - Tradable universe (SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO)
- `/research/llm_trading/config/schedule.yaml` - Weekly (Wed 08:00 ET), daily checkpoints (09:00, 12:00, 14:00, 15:50)
- `/research/llm_trading/config/models.yaml` - PM models, chairman, research providers, OpenRouter config

### Storage (Complete)
- `/research/llm_trading/storage/schema.py` - PostgreSQL event store schema with tables:
  - Event (base events table)
  - ResearchPackEvent (research from Gemini/Perplexity)
  - PMPitchEvent (PM pitches)
  - PeerReviewEvent (peer reviews)
  - ChairmanDecisionEvent (final council decisions)
  - CheckpointUpdateEvent (daily conviction updates)
  - OrderEvent (orders placed)
  - PositionEvent (position snapshots)
  - WeeklyPostmortemEvent (end-of-week analysis)
  - WeekMetadata (denormalized week summary)
  - **Note**: Type hint error fixed (`url: Optional[str] = None`)

### Backend (Existing - llm-council baseline)
- `/research/llm_trading/backend/pipeline/context.py` - PipelineContext class (immutable, type-safe ContextKey)
- `/research/llm_trading/backend/pipeline/__init__.py` - Pipeline module exports
  - **ERROR**: Imports `.base` which does NOT exist - CRITICAL BLOCKER
- `/research/llm_trading/backend/council.py` - 3-stage council orchestration
  - stage1_collect_responses (parallel model queries via OpenRouter)
  - stage2_collect_rankings (anonymized peer evaluation)
  - stage3_synthesize_final (chairman synthesis)
  - **WARNING**: LSP error at line 200:57 ("group" attribute)
- `/research/llm_trading/backend/openrouter.py` - OpenRouter API client (async, with parallel query)
- `/research/llm_trading/backend/config.py` - Hardcoded config (COUNCIL_MODELS, CHAIRMAN_MODEL, etc.)
- `/research/llm_trading/backend/storage.py` - JSON-based conversation storage (legacy, will be replaced)
- `/research/llm_trading/backend/main.py` - FastAPI web app (to be refactored later)

### Files Needing Creation (CRITICAL)
- `/research/llm_trading/backend/pipeline/base.py` - **MISSING** - Stage and Pipeline base classes (blocks all progress)
- `/research/llm_trading/config/loader.py` - **MISSING** - YAML config loader
- `/research/llm_trading/cli.py` - **MISSING** - CLI entry point
- `/research/llm_trading/market/alpaca_client.py` - **MISSING** - Alpaca REST API client

### Files to Create Later (Phase 2)
- `/research/llm_trading/council/prompts/` - Jinja2 templates (pm_pitch.j2, peer_review.j2, chairman.j2)
- `/research/llm_trading/council/schemas/` - JSON schemas (pm_pitch.json, peer_review.json, chairman_decision.json)
- `/research/llm_trading/research/providers/` - Research provider implementations
- `/research/llm_trading/storage/` - PostgreSQL connection utility

---

## Resume Instructions

### Immediate Priority After Compaction Resume

**CRITICAL BLOCKER**: Create `backend/pipeline/base.py` first - this fixes import error in `__init__.py` and unblocks everything else.

Then:

1. Implement YAML config loader in `config/loader.py`
2. Port council stages to new pipeline format (3 stages wrapping existing functions)
3. Create CLI skeleton in `cli.py` with basic `council` command
4. Implement `market/alpaca_client.py` for direct REST API calls (paper trading)

### Implementation Sequence

```
1. backend/pipeline/base.py (Stage, Pipeline base classes)
   └─> Fixes __init__.py import error
   └─> Enables all pipeline work

2. config/loader.py (YAML config loader)
   └─> Reads assets.yaml, schedule.yaml, models.yaml
   └─> Provides unified config interface

3. backend/pipeline/stages/ (council stages in new format)
   └─> CollectResponsesStage (wraps stage1_collect_responses)
   └─> CollectRankingsStage (wraps stage2_collect_rankings)
   └─> SynthesizeFinalStage (wraps stage3_synthesize_final)

4. cli.py (CLI entry point)
   └─> Commands: council, run_weekly, checkpoint, postmortem
   └─> Tests end-to-end pipeline

5. market/alpaca_client.py (Alpaca REST API client)
   └─> Paper trading URL: https://paper-api.alpaca.markets
   └─> Functions: get_positions, place_order, get_account, etc.
```

### Testing Strategy

After above 5 files are created:

1. Test CLI: `python cli.py council "test query"`
2. Verify pipeline execution through all 3 stages
3. Check PostgreSQL event logging works
4. User provides API keys in `.env`
5. Test Alpaca client with paper trading credentials
6. **TODAY IS HOLIDAY** - place orders but verify they don't execute until Monday

---

## Technical Decisions

### Architecture Decisions

1. **Pipeline-First Headless Design**
   - CLI is primary orchestration interface
   - FastAPI web app will be refactored later to call same pipeline logic
   - All stages are composable via Pipeline class
   - PipelineContext is immutable (never mutated, each stage returns new context)

2. **Event Sourcing with PostgreSQL**
   - All state changes are immutable events
   - Events include week_id (Wednesday date) for partitioning
   - Per-week sharding concept (even though using single PostgreSQL instance)
   - Denormalized WeekMetadata table for quick lookups

3. **Configuration Architecture**
   - YAML files are single source of truth
   - Environment variables only for API keys and DATABASE_URL
   - `backend/config.py` will be shim for backward compatibility with FastAPI

4. **Research Provider Strategy**
   - Official APIs when available (Gemini Deep Research Agent, Perplexity Sonar Pro)
   - Prompt-based fallback for development/testing
   - Wrapped in stable `ResearchProvider` interface

5. **Alpaca Integration**
   - Direct REST API (not MCP initially)
   - Paper trading URL: `https://paper-api.alpaca.markets`
   - User hasn't set up Alpaca MCP server yet

### Data Model Decisions

1. **Research Pack Schema** (from WEEKLY_RESEARCH.MD)
   - week_id, asof_et, research_source
   - macro_regime (risk_mode, rates_impulse, usd_impulse, inflation_impulse, growth_impulse)
   - top_narratives (name, why_it_moves_prices_this_week, key_catalysts_next_7d, what_would_falsify_it)
   - consensus_map (street_consensus, positioning_guess, what_market_is_priced_for, what_would_surprise)
   - tradable_candidates (instrument, directional_bias, one_week_thesis, primary_risks, watch_indicators, invalidation_rule)
   - event_calendar_next_7d
   - confidence_notes (known_unknowns, data_quality_flags)

2. **PM Pitch Schema** (from PRD.md)
   - idea_id, week_id, model, instrument, direction, horizon
   - thesis_bullets (max 5)
   - indicators (frozen list with thresholds)
   - invalidation, conviction, timestamp

3. **Peer Review Schema** (from PRD.md)
   - review_id, pitch_id, reviewer_model, anonymized_pitch_id
   - scores (clarity, edge_plausibility, timing_catalyst, risk_definition, indicator_integrity, originality, tradeability) - 1-10 scale
   - best_argument_against, one_flip_condition, suggested_fix

4. **Chairman Decision Schema** (from PRD.md)
   - selected_trade (instrument, direction, horizon)
   - conviction, rationale
   - dissent_summary (list of dissenting opinions)
   - monitoring_plan (checkpoints, key_indicators, watch_conditions)

5. **Checkpoint Schema** (from PRD.md)
   - checkpoint_id, week_id, time, account_id
   - conviction_before, conviction_after
   - action (STAY | EXIT | FLIP | REDUCE)
   - reason_delta, indicators_snapshot

### Trading System Decisions

1. **6 Parallel Paper Trading Accounts**
   - acct_1: GPT-5.1 PM trade
   - acct_2: Gemini 3 Pro PM trade
   - acct_3: Sonnet 4.5 PM trade
   - acct_4: Grok 4 PM trade
   - acct_5: Chairman Council trade
   - acct_6: FLAT baseline (no trades)

2. **Tradable Universe**
   - Risk-on equities: SPY, QQQ, IWM
   - Duration: TLT, IEF
   - Credit: HYG, LQD
   - USD proxy: UUP
   - Gold: GLD, IAU
   - Oil: USO, BNO
   - Rule: One instrument per account per week (LONG/SHORT/FLAT)

3. **Weekly Schedule**
   - Wednesday 08:00 ET: Weekly pipeline (research → PM pitches → peer review → chairman → execution)
   - Daily checkpoints: 09:00, 12:00, 14:00, 15:50 ET
   - Hard rule: No new research mid-week (only frozen indicators + P/L)

4. **Conviction Scale**
   - Range: -2 to +2
   - -2 = strong SHORT, 0 = FLAT, +2 = strong LONG
   - Checkpoints can update conviction (stay, exit, flip, reduce)

### Dependencies Status

**Already in pyproject.toml:**
- fastapi, uvicorn, python-dotenv, httpx, pydantic

**Need to add:**
- `jinja2` - for prompt templates
- `pyyaml` - for config loading
- `psycopg2-binary` or `asyncpg` - for PostgreSQL

---

## Outstanding Issues

### Critical Blockers
- [ ] **CRITICAL**: `backend/pipeline/base.py` missing - blocks import in `__init__.py`
- [ ] LSP warning: `backend/council.py` line 200:57 ("group" attribute) - investigate after base.py creation

### User Action Items
- [ ] Fill in `.env` with API keys (template provided at `.env.template`)
- [ ] Set up PostgreSQL database (run migrations, create tables)
- [ ] Get Alpaca paper trading keys
- [ ] Provide API keys for OpenRouter, Gemini, Perplexity

### Technical Debt
- [ ] Refactor `backend/config.py` to use YAML loader instead of hardcoded values
- [ ] Replace `backend/storage.py` (JSON storage) with PostgreSQL event store
- [ ] Refactor FastAPI `backend/main.py` to call pipeline functions instead of direct council logic
- [ ] Add logging infrastructure (structured logging with levels)

---

## Architecture Patterns Established

### Pipeline Design
- **Stage base class**: Abstract class with `name` property and `async execute(self, context) -> context`
- **Pipeline class**: Chains stages, executes sequentially, returns final context
- **Context keys**: Type-safe via `ContextKey` class (e.g., USER_QUERY, RESEARCH_PACK_A, PM_PITCHES)

### Event Sourcing
- **Immutable events**: Never UPDATE existing rows, only INSERT new events
- **Per-week partitioning**: All events have `week_id` column
- **Account tracking**: Events have `account_id` for 6 parallel accounts

### Configuration Loading
- **YAML parsing**: Use `pyyaml.safe_load` for config/assets.yaml, schedule.yaml, models.yaml
- **Environment override**: API keys and DATABASE_URL from environment variables
- **Validation**: Config validation before pipeline execution

### API Integration
- **OpenRouter**: All PM and chairman model calls via `openrouter.py`
- **Research**: Separate providers with async `run_research(topic)` interface
- **Alpaca**: Direct REST API client with async methods for paper trading

---

## Next Session Goals

### Phase 1 Completion Criteria
- [ ] `backend/pipeline/base.py` created and tested
- [ ] `config/loader.py` reads all YAML configs
- [ ] Council stages ported to new pipeline format
- [ ] CLI with `council` command works end-to-end
- [ ] PostgreSQL event store tables created
- [ ] Alpaca client implements basic CRUD operations

### Phase 2 Goals (After Phase 1)
- [ ] Define trading JSON schemas
- [ ] Create Jinja2 prompt templates
- [ ] Implement research providers
- [ ] Build full weekly pipeline orchestration
- [ ] Implement checkpoint engine
- [ ] Test with real research and paper trades

---

## Important Reminders

1. **TODAY IS HOLIDAY (Jan 1, 2026)**: Trades will be placed via Alpaca but not executed. Everything ready for Monday Jan 5, 2026.
2. **Alpaca Paper Trading URL**: `https://paper-api.alpaca.markets` (not live trading)
3. **No mid-week research**: Checkpoints can only use frozen indicators + current P/L
4. **Event sourcing**: All state changes must be events, never UPDATE statements
5. **API keys required**: User must fill in `.env` before testing
6. **PostgreSQL ready**: Schema defined, just need to create tables
