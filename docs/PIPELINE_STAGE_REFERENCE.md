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
| `MarketSentimentStage` | Gather news and analyze market sentiment | Search provider, search terms, temperature | `MARKET_SNAPSHOT` (optional) | `SENTIMENT_PACK` |
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

#### MarketSentimentStage

**Purpose:** Gather recent news and analyze sentiment for tradable instruments

**Overview:**

`MarketSentimentStage` performs news search and sentiment analysis to complement macro research. It provides context on current market narratives, breaking news, and instrument-specific sentiment that can inform trading decisions.

The stage performs five key operations:
1. Extracts tradable instruments from market snapshot
2. Searches for recent news on each instrument using configured search terms
3. Retrieves full article content via Jina Reader (where available)
4. Generates AI-powered sentiment summary using LLM
5. Returns structured sentiment pack with articles and analysis

**Constructor Parameters:**
- `search_provider` (str | None): Optional search provider ID override
  - Default: None (uses SearchManager default provider)
  - Options: Provider IDs from search configuration (e.g., "exa", "tavily")
  - Use case: Force specific search provider for testing or provider preference
- `search_terms` (List[str] | None): Search terms to append to each ticker query
  - Default: ["latest news", "market outlook", "analysis"]
  - Use case: Customize search focus (e.g., ["earnings", "guidance"] for earnings season)
- `temperature` (float | None): Model temperature for sentiment generation
  - Default: None (uses TemperatureManager default for "market_sentiment")
  - Range: 0.0 (deterministic) to 2.0 (creative)
  - Use case: Control sentiment summary creativity vs consistency

**Context Keys:**

*Input:*
- `MARKET_SNAPSHOT` (dict, optional) - Market data snapshot from previous stage
  - If present, uses `instruments` dict keys as ticker list
  - If absent, skips sentiment analysis gracefully

*Output:*
- `SENTIMENT_PACK` (dict) - Structured sentiment data containing:
  - `asof_et`: Timestamp of sentiment capture (ISO8601)
  - `search_provider`: Search provider used (e.g., "exa", "tavily")
  - `search_terms_used`: List of search terms applied
  - `instrument_sentiments`: Dict mapping tickers to sentiment data
  - `overall_market_sentiment`: Aggregate sentiment ("bullish", "bearish", "neutral")
  - `key_headlines`: Top 10 most relevant headlines across all instruments
  - `sentiment_summary`: LLM-generated narrative summary of market sentiment

**Sentiment Pack Schema:**

```json
{
  "asof_et": "2025-01-22T14:30:00Z",
  "search_provider": "exa",
  "search_terms_used": ["latest news", "market outlook", "analysis"],
  "instrument_sentiments": {
    "SPY": {
      "article_count": 12,
      "articles": [
        {
          "title": "S&P 500 Hits New High on Tech Rally",
          "url": "https://example.com/article1",
          "snippet": "The S&P 500 index surged to a new record...",
          "published_date": "2025-01-22T13:00:00Z",
          "source": "Financial Times"
        }
      ],
      "sentiment": "bullish"
    },
    "TLT": {
      "article_count": 5,
      "articles": [...],
      "sentiment": "bearish"
    }
  },
  "overall_market_sentiment": "bullish",
  "key_headlines": [
    "S&P 500 Hits New High on Tech Rally",
    "Fed Signals Patience on Rate Cuts",
    "..."
  ],
  "sentiment_summary": "Market sentiment is BULLISH driven by tech sector strength and stabilizing inflation data. Key themes include AI infrastructure spending, Fed policy outlook, and earnings optimism. Notable risk: potential profit-taking after extended rally."
}
```

**Configuration Example:**

```python
from backend.pipeline.stages.market_sentiment import MarketSentimentStage

# Basic usage with defaults
stage = MarketSentimentStage()

# With custom search provider
stage = MarketSentimentStage(search_provider="exa")

# With custom search terms for earnings focus
stage = MarketSentimentStage(
    search_terms=["earnings report", "guidance", "analyst estimates"]
)

# With custom temperature for more deterministic sentiment
stage = MarketSentimentStage(temperature=0.3)

# Full customization
stage = MarketSentimentStage(
    search_provider="tavily",
    search_terms=["breaking news", "price action"],
    temperature=0.5
)

# Execute stage
context = await stage.execute(context)
sentiment_pack = context.get(SENTIMENT_PACK)
```

**Error Handling:**

The stage is designed to be fault-tolerant and never crash the pipeline:

1. **Missing Market Snapshot:**
   - Prints warning message
   - Returns original context unchanged
   - Allows pipeline to continue without sentiment data

2. **Search Provider Unavailable:**
   - Falls back to SearchManager default provider
   - Logs provider switch
   - Continues with alternative provider

3. **No Articles Found:**
   - Creates sentiment entry with article_count=0
   - Sets sentiment to "neutral"
   - Continues processing other instruments

4. **LLM Sentiment Generation Failure:**
   - Catches exception and logs error
   - Returns fallback sentiment: "Neutral - sentiment analysis unavailable"
   - Sentiment pack structure remains valid

5. **Partial Search Failures:**
   - Processes successful results
   - Logs warnings for failed instruments
   - Returns partial sentiment pack with available data

**Integration with Other Stages:**

```python
# Typical pipeline integration
from backend.pipeline import Pipeline
from backend.pipeline.stages.market_sentiment import MarketSentimentStage
from backend.pipeline.stages.research import ResearchStage

pipeline = Pipeline([
    MarketSnapshotStage(),      # Provides MARKET_SNAPSHOT
    MarketSentimentStage(),     # Adds SENTIMENT_PACK
    ResearchStage(),            # Uses both MARKET_SNAPSHOT and SENTIMENT_PACK
    # ... PM stages can use SENTIMENT_PACK for additional context
])
```

**Performance Characteristics:**

- **Instrument count:** Typically 8-12 tickers from asset universe
- **Articles per ticker:** 5-15 results (depends on search provider)
- **Search time:** 2-5s per ticker (parallel search not yet implemented)
- **LLM sentiment generation:** 5-10s (Gemini Flash model)
- **Total stage duration:** ~30-60s typical (sequential searches)
- **Future optimization:** Parallel ticker searches could reduce to ~10-20s

**Common Issues and Debugging:**

1. **"No market snapshot found" warning:**
   - Cause: MarketSentimentStage executed before market data stage
   - Impact: Sentiment analysis skipped
   - Fix: Ensure MarketSnapshotStage or ResearchStage runs first

2. **"No articles found" for specific ticker:**
   - Cause: Search terms too specific, or ticker not newsworthy
   - Impact: Sentiment set to "neutral" for that ticker
   - Fix: Adjust search_terms to be more generic, or add fallback terms

3. **"Failed to generate sentiment summary" warning:**
   - Cause: Gemini API rate limit, invalid key, or network issue
   - Impact: Fallback message used, sentiment pack still valid
   - Fix: Verify GEMINI_API_KEY in .env, check rate limits

4. **Search provider errors:**
   - Cause: Provider API key invalid or rate limited
   - Impact: Falls back to default provider
   - Fix: Verify provider API keys in .env (EXA_API_KEY, TAVILY_API_KEY)

5. **Stage takes too long (>2 minutes):**
   - Cause: Sequential search for many tickers with slow provider
   - Impact: Pipeline latency increases
   - Fix: Reduce number of instruments or implement parallel searching

**Data Quality Considerations:**

- **Article freshness:** Search results depend on provider's index update frequency
- **Source reliability:** Article sources vary by provider (financial news vs blogs)
- **Sentiment accuracy:** LLM-generated sentiment is subjective and may not reflect true market impact
- **Geographic bias:** Search providers may favor US news sources
- **Language limitation:** Non-English articles may be excluded or poorly translated

**Use Cases:**

1. **Pre-Research Context:** Run before ResearchStage to inform macro analysis with latest news
2. **Breaking News Detection:** Capture market-moving news that emerged after last pipeline run
3. **Instrument-Specific Sentiment:** Complement macro regime with ticker-level sentiment
4. **Headline Risk Assessment:** Identify potential risks from recent news flow
5. **Narrative Tracking:** Monitor evolving market narratives over time

**See Also:**

- `backend/pipeline/stages/market_sentiment.py` - Full implementation
- `backend/search/manager.py` - SearchManager and provider integration
- `backend/search/providers/` - Individual search provider implementations
- `backend/config/temperature.yaml` - Temperature configuration for sentiment generation

---

### PM Layer

#### PMPitchStage

**Purpose:** Generate structured trading recommendations from all configured PM models based on research data

**Overview:**

`PMPitchStage` is the core decision-making stage where Portfolio Manager (PM) models generate individual trading recommendations. The stage orchestrates parallel queries to 5 PM models, each producing a structured pitch with instrument selection, direction, conviction, thesis bullets, and risk parameters.

This is a **macro-only trading system** that enforces strict rules against technical analysis. Models must base recommendations exclusively on macro regime, policy, economic data, fundamentals, and cross-asset narratives. Any pitch mentioning technical indicators (RSI, MACD, moving averages, etc.) is automatically rejected and retried with a corrective prompt.

The stage performs four key operations:
1. Receives research packs and market data from previous stages
2. Builds comprehensive prompts with tradable universe and constraints
3. Queries all PM models in parallel via Requesty client
4. Parses, validates, and filters pitches (with indicator ban enforcement)

**Constructor Parameters:**
- `temperature` (float | None): Model temperature for pitch generation
  - Default: None (uses TemperatureManager default for "pm_pitch")
  - Range: 0.0 (deterministic) to 2.0 (creative)
  - Typical value: 0.7-1.0 for balanced creativity and consistency

**Context Keys:**

*Input:*
- `RESEARCH_PACK_A` (dict) - Primary research pack from Perplexity/Gemini
  - Contains: macro_regime, top_narratives, tradable_candidates, event_calendar
  - Required: At least one research pack must be present
- `RESEARCH_PACK_B` (dict, optional) - Alternative research pack
  - If only one pack provided, stage uses it for both A and B
  - Allows PM to cross-reference different research perspectives
- `MARKET_METRICS` (dict, optional) - Market metrics from previous stage
  - Contains: 7-day returns by instrument, 30-day correlation matrix
  - Helps PMs understand recent price action and cross-asset relationships
- `CURRENT_PRICES` (dict, optional) - Current prices and volumes
  - Contains: Latest close prices, trading volumes for all instruments
  - Used for limit order pricing and liquidity assessment
- `TARGET_MODELS` (list[str], optional) - Subset of PM models to run
  - Default: None (runs all 5 configured PM models)
  - Use case: Testing specific models or running only council accounts

*Output:*
- `PM_PITCHES` (list[dict]) - List of validated PM pitch objects
  - Each pitch contains full trading recommendation with metadata
  - Only includes pitches that passed all validation checks
  - Typically 5 pitches (one per PM model) unless validation failures occur

**PM Pitch Schema (v2):**

The pitch JSON follows a strict schema with risk profile validation:

```json
{
  "idea_id": "uuid",
  "week_id": "2025-01-22",
  "asof_et": "2025-01-22T16:00:00-05:00",
  "pm_model": "openai/gpt-5.1",
  "selected_instrument": "SPY",
  "direction": "LONG",
  "horizon": "1W",
  "conviction": 1.5,
  "risk_profile": "BASE",
  "thesis_bullets": [
    "Rates: Fed pivot expectations support risk assets",
    "USD: Dollar weakness improves earnings outlook",
    "Policy: Fiscal stimulus providing growth tailwind"
  ],
  "entry_policy": {
    "mode": "limit",
    "limit_price": null
  },
  "exit_policy": {
    "time_stop_days": 7,
    "stop_loss_pct": 0.015,
    "take_profit_pct": 0.025,
    "exit_before_events": ["NFP"]
  },
  "consensus_map": {
    "research_pack_a": "agree",
    "research_pack_b": "neutral"
  },
  "risk_notes": "Key risks: Hotter than expected inflation data, geopolitical escalation",
  "compliance_check": {
    "macro_only": true,
    "no_ta_language": true
  },
  "timestamp": "2025-01-22T21:00:00Z",
  "model": "gpt51",
  "model_info": {
    "model_id": "openai/gpt-5.1",
    "account": "GPT-5.1",
    "priority": 1
  }
}
```

**FLAT Trade Schema:**

When PM chooses not to trade (FLAT), the schema differs:

```json
{
  "idea_id": "uuid",
  "week_id": "2025-01-22",
  "asof_et": "2025-01-22T16:00:00-05:00",
  "pm_model": "openai/gpt-5.1",
  "selected_instrument": "FLAT",
  "direction": "FLAT",
  "horizon": "1W",
  "conviction": 0,
  "risk_profile": null,
  "thesis_bullets": [
    "Policy: Insufficient macro clarity for directional trade",
    "Risk: Market conditions require neutral stance"
  ],
  "entry_policy": {
    "mode": "NONE",
    "limit_price": null
  },
  "exit_policy": null,
  "consensus_map": {
    "research_pack_a": "neutral",
    "research_pack_b": "neutral"
  },
  "risk_notes": "Macro uncertainty requires neutral positioning",
  "compliance_check": {
    "macro_only": true,
    "no_ta_language": true
  },
  "timestamp": "2025-01-22T21:00:00Z"
}
```

**Risk Profile Validation Rules:**

The stage enforces standardized risk profiles (no custom stop-loss values allowed):

```python
RISK_PROFILES = {
    "TIGHT": {
        "stop_loss_pct": 0.010,   # 1.0% stop loss
        "take_profit_pct": 0.015  # 1.5% take profit
    },
    "BASE": {
        "stop_loss_pct": 0.015,   # 1.5% stop loss
        "take_profit_pct": 0.025  # 2.5% take profit
    },
    "WIDE": {
        "stop_loss_pct": 0.020,   # 2.0% stop loss
        "take_profit_pct": 0.035  # 3.5% take profit
    }
}
```

**Validation Rules:**

1. **Risk Profile Consistency:**
   - `exit_policy.stop_loss_pct` must exactly match chosen `risk_profile`
   - `exit_policy.take_profit_pct` must exactly match chosen `risk_profile`
   - FLAT trades must have `risk_profile: null`

2. **Entry Mode Validation:**
   - Valid entry modes: `["limit"]`
   - FLAT trades must use `"mode": "NONE"`

3. **Exit Event Triggers:**
   - Valid events: `["NFP", "CPI", "FOMC"]`
   - Optional field in `exit_policy.exit_before_events`

4. **Direction and Conviction Alignment:**
   - LONG direction requires conviction > 0
   - SHORT direction requires conviction < 0
   - FLAT direction requires conviction == 0
   - Conviction range: -2.0 to +2.0

5. **Thesis Bullet Prefixes:**
   - Each bullet must start with one of: `"Rates:"`, `"USD:"`, `"Inflation:"`, `"Growth:"`, `"Policy:"`, `"Cross-asset:"`, `"Catalyst:"`, `"Positioning:"`, `"Risk:"`
   - Maximum 5 thesis bullets
   - Enforces macro-focused thinking

6. **Tradable Universe:**
   - Valid instruments: `["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH", "FLAT"]`
   - FLAT is special "no trade" instrument

**Banned Indicator Keywords (Case-Insensitive):**

The stage scans all string fields recursively and rejects pitches containing:

```python
BANNED_KEYWORDS = [
    "rsi", "macd", "moving average", "moving-average",
    "ema", "sma", "bollinger", "stochastic",
    "fibonacci", "ichimoku", "adx", "atr"
]
```

**Indicator Ban Enforcement:**

When a banned keyword is detected:
1. **First attempt fails** with `IndicatorError`
2. **Automatic retry** with corrective prompt instructing model to output FLAT
3. **Retry fails:** Generate automatic FLAT fallback pitch
4. **Reasoning:** Prevents contamination of macro-only system with technical analysis

**Configuration Example:**

```python
from backend.pipeline.stages.pm_pitch import PMPitchStage

# Basic usage with defaults
stage = PMPitchStage()

# With custom temperature for more deterministic pitches
stage = PMPitchStage(temperature=0.5)

# Execute stage (requires research packs in context)
context = await stage.execute(context)
pm_pitches = context.get(PM_PITCHES)

print(f"Generated {len(pm_pitches)} pitches")
for pitch in pm_pitches:
    print(f"{pitch['model']}: {pitch['direction']} {pitch['selected_instrument']} (conviction: {pitch['conviction']})")
```

**Pipeline Integration Example:**

```python
from backend.pipeline import Pipeline
from backend.pipeline.stages.research import ResearchStage
from backend.pipeline.stages.pm_pitch import PMPitchStage
from backend.pipeline.stages.peer_review import PeerReviewStage

pipeline = Pipeline([
    ResearchStage(),        # Provides RESEARCH_PACK_A, MARKET_METRICS, CURRENT_PRICES
    PMPitchStage(),         # Uses research to generate PM_PITCHES
    PeerReviewStage(),      # Reviews PM_PITCHES
])
```

**Error Handling:**

The stage is designed to be fault-tolerant and never crash the pipeline:

1. **Missing Research Packs:**
   - Prints error message
   - Falls back to placeholder research data
   - Allows pipeline to continue (for testing)

2. **Single Research Pack (Perplexity-only mode):**
   - Uses same pack for both RESEARCH_PACK_A and RESEARCH_PACK_B
   - Prints info message
   - Normal operation continues

3. **Missing Market Metrics:**
   - Prints warning message
   - Continues without market metrics in prompt
   - PMs can still generate pitches based on research

4. **Missing Current Prices:**
   - Prints warning message
   - Continues without price data in prompt
   - Limit orders may be suboptimal

5. **Model Query Failures:**
   - Catches exceptions per model
   - Logs failure and continues with other models
   - Returns partial pitch list (e.g., 4/5 pitches)

6. **JSON Parsing Errors:**
   - Attempts multiple repair strategies:
     - Remove // comments
     - Remove trailing commas
     - Combined repairs
   - Prints repair attempt success/failure
   - Returns None if all repairs fail

7. **Indicator Ban Violations:**
   - First retry with corrective prompt
   - Second failure: Generate FLAT fallback
   - Ensures pipeline never stops for indicator issues

8. **Validation Failures:**
   - Logs specific validation error (missing fields, invalid values)
   - Returns None for that pitch
   - Continues processing other models

**Common Validation Errors:**

1. **Risk Profile Mismatch:**
   ```
   ERROR: exit_policy.stop_loss_pct (0.020) does not match risk_profile BASE (0.015)
   ```
   - Cause: Model provided custom stop-loss value
   - Fix: Automatic in retry - model forced to use standardized profiles

2. **FLAT Trade with Risk Profile:**
   ```
   ERROR: FLAT trades must not have risk_profile (got: BASE)
   ```
   - Cause: Model confused FLAT rules
   - Fix: Automatic in retry - FLAT schema enforced

3. **Missing Required Fields:**
   ```
   ERROR: Missing required fields: asof_et, risk_profile
   ```
   - Cause: Model didn't follow JSON schema
   - Fix: Improved system prompt, schema examples

4. **Invalid Conviction Range:**
   ```
   ERROR: Conviction out of range: 2.5 (must be -2 to +2)
   ```
   - Cause: Model exceeded conviction bounds
   - Fix: Validation rejects pitch

5. **Direction/Conviction Mismatch:**
   ```
   ERROR: LONG direction must have positive conviction, got -0.5
   ```
   - Cause: Model inconsistency
   - Fix: Validation rejects pitch

6. **Thesis Bullet Format:**
   - Not explicitly validated in code, but prompt enforces
   - Should start with category prefix (e.g., "Rates:", "Policy:")

7. **Indicator Ban Violation:**
   ```
   ERROR: Indicator banned: rsi
   ```
   - Cause: Model mentioned technical indicator
   - Fix: Automatic retry → FLAT fallback

**Performance Characteristics:**

- **Model count:** 5 PM models queried in parallel
- **Query time per model:** 10-30s (depends on model speed)
- **Total stage duration:** ~15-45s (parallel execution)
- **Retry overhead:** +10-20s per model if indicator ban triggered
- **Parse/validate time:** <1s per pitch (negligible)
- **Typical success rate:** 90-100% (most pitches pass validation)
- **Indicator ban trigger rate:** 5-15% (occasional TA language slips in)

**Tradable Universe Reference:**

```python
INSTRUMENTS = [
    "SPY",   # S&P 500 ETF (broad US equities)
    "QQQ",   # Nasdaq 100 ETF (tech-heavy)
    "IWM",   # Russell 2000 ETF (small caps)
    "TLT",   # 20+ Year Treasury Bond ETF (duration)
    "HYG",   # High Yield Corporate Bond ETF (credit)
    "UUP",   # US Dollar Index ETF (USD proxy)
    "GLD",   # Gold ETF (safe haven)
    "USO",   # Oil ETF (commodities/energy)
    "VIXY",  # VIX Short-Term ETF (volatility)
    "SH"     # ProShares Short S&P 500 ETF (short equities)
]
```

**Common Issues and Debugging:**

1. **"No research packs found" error:**
   - Cause: PMPitchStage executed before ResearchStage
   - Impact: Falls back to placeholder data (testing mode)
   - Fix: Ensure ResearchStage runs first in pipeline

2. **"Missing required fields" for specific model:**
   - Cause: Model didn't follow JSON schema exactly
   - Impact: That model's pitch is skipped
   - Fix: Review model's raw output, improve system prompt

3. **Indicator ban triggered repeatedly:**
   - Cause: Model has strong TA bias, ignores macro-only rules
   - Impact: Falls back to FLAT pitch
   - Fix: Review model prompt, consider model replacement

4. **All pitches are FLAT:**
   - Cause: Research data lacks actionable signals, or models too conservative
   - Impact: No directional trades for the week
   - Fix: Review research quality, check if macro regime is truly unclear

5. **Risk profile validation failures:**
   - Cause: Model inventing custom stop-loss values
   - Impact: Pitch rejected, retry enforces standardized profiles
   - Fix: System prompt emphasizes three standard profiles

6. **Conviction/direction mismatches:**
   - Cause: Model logic error (e.g., LONG with negative conviction)
   - Impact: Pitch rejected
   - Fix: Improve model prompt clarity on conviction semantics

7. **JSON parsing fails after all repairs:**
   - Cause: Model output is severely malformed (missing braces, quotes)
   - Impact: That pitch is skipped
   - Fix: Review raw model output, possibly model API issue

8. **Stage takes too long (>2 minutes):**
   - Cause: One or more models very slow, or indicator ban retries
   - Impact: Pipeline latency increases
   - Fix: Consider model timeout settings, review model performance

**Knowledge Graph Integration:**

The stage includes optional knowledge graph digest formatting:
- If `research_pack.weekly_graph` is present, generates digest
- Digest includes: top market edges, asset context, direct drivers
- Helps PMs understand structural relationships and narrative flow
- Falls back gracefully if graph generation fails

**Data Quality Considerations:**

- **Thesis quality:** Varies significantly by model sophistication
- **Conviction calibration:** Each model has different conviction scaling habits
- **Research interpretation:** Models may emphasize different aspects of same research
- **Risk assessment:** Risk notes quality depends on model reasoning depth
- **Macro-only compliance:** Enforced by indicator ban, but language can be ambiguous (e.g., "oversold" is macro-adjacent but often TA-tinged)

**Use Cases:**

1. **Weekly Pipeline Execution:** Generate fresh pitches every Wednesday morning
2. **Individual Account Trading:** Each PM model maps to separate paper trading account
3. **Council Input:** All 5 pitches feed into peer review and chairman synthesis
4. **Model Performance Tracking:** Compare pitch quality and outcomes across models
5. **Regime Adaptation:** Observe how different models adapt to changing macro regimes

**See Also:**

- `backend/pipeline/stages/pm_pitch.py` - Full implementation
- `backend/requesty_client.py` - Parallel model query client
- `backend/config/models.yaml` - PM model configuration
- `backend/config/temperature.yaml` - Temperature configuration
- `backend/pipeline/graph_digest.py` - Knowledge graph digest generation

---

### Peer Review Layer

#### PeerReviewStage

**Purpose:** Anonymized cross-evaluation of PM pitches to prevent model favoritism and ensure objective critique

**Overview:**

`PeerReviewStage` implements a peer review process where each PM model evaluates the other models' trading pitches in a blind review format. This stage is critical for:

1. **Preventing Model Favoritism:** Anonymizing pitches eliminates bias toward specific models or providers
2. **Objective Evaluation:** Models critique ideas on merit, not on who proposed them
3. **Quality Assurance:** Systematic scoring across 7 dimensions ensures comprehensive evaluation
4. **Training Data Quality:** Anonymized reviews create cleaner training data for future model improvements
5. **Kill Shot Critiques:** Each model identifies the strongest counterargument to each pitch
6. **Flip Conditions:** Reviewers suggest what would need to change to invalidate the thesis

The stage performs three key operations:
1. Anonymizes all PM pitches by removing model identity (e.g., "Pitch A", "Pitch B")
2. Each PM model reviews all other pitches (not their own)
3. Generates structured reviews with rubric scores, critiques, and suggestions

**Constructor Parameters:**
- `temperature` (float | None): Model temperature for review generation
  - Default: None (uses TemperatureManager default for "peer_review")
  - Range: 0.0 (deterministic) to 2.0 (creative)
  - Typical: 0.5-0.7 for balanced, critical analysis

**Context Keys:**

*Input:*
- `PM_PITCHES` (list) - Trade pitches from PMPitchStage
  - Each pitch contains: model, instrument, direction, thesis, conviction, risk profile, etc.
  - Minimum 2 pitches required for meaningful peer review

*Output:*
- `PEER_REVIEWS` (list) - Structured review results containing:
  - `review_id`: Unique identifier for this review
  - `pitch_label`: Anonymized label (e.g., "Pitch A")
  - `reviewer_model`: Model that generated the review
  - `scores`: Dict of 7 rubric dimension scores (1-10)
  - `average_score`: Mean score across all dimensions
  - `best_argument_against`: Strongest counterargument to the pitch
  - `one_flip_condition`: What would invalidate the thesis
  - `suggested_fix`: How to improve the pitch
  - `raw_response`: Full text review from the model

- `LABEL_TO_MODEL` (dict) - Mapping from anonymous labels to original model names
  - Example: `{"Pitch A": "openai/gpt-5.1", "Pitch B": "anthropic/claude-sonnet-4.5"}`
  - Used by ChairmanStage to de-anonymize pitches when making final decision

**Anonymization Process:**

The anonymization process ensures reviewers cannot identify which model created which pitch:

1. **Label Assignment:** Each pitch is assigned a random label (Pitch A, Pitch B, Pitch C, Pitch D)
2. **Identity Stripping:** Model name, account name, and any identifying metadata are removed
3. **Content Preservation:** Thesis, conviction, risk profile, entry/exit policies remain intact
4. **Mapping Storage:** Original model identity stored in `LABEL_TO_MODEL` for later de-anonymization
5. **Review Distribution:** Each model reviews all pitches except their own (if identifiable)

**Rubric Dimensions:**

Each pitch is scored on 7 dimensions (1-10 scale):

1. **clarity** - How clear and understandable is the thesis?
   - Logical flow, well-articulated reasoning, no ambiguity

2. **edge_plausibility** - How plausible is the claimed edge?
   - Information advantage, timing advantage, structural advantage

3. **timing_catalyst** - How well-defined is the catalyst and timing?
   - Specific events, clear timeline, catalyst-driven entry

4. **risk_definition** - How well-defined are the risks?
   - Clear invalidation criteria, specific stop loss, scenario analysis

5. **risk_management** - How well-structured are the risk controls?
   - Stop loss placement, take profit targets, time stops, position sizing

6. **originality** - How original is the idea?
   - Non-consensus view, unique angle, not following the herd

7. **tradeability** - How tradable is this idea in practice?
   - Liquid instruments, clear entry/exit, executable in paper trading

**Review Schema:**

```json
{
  "review_id": "uuid-v4",
  "pitch_label": "Pitch A",
  "reviewer_model": "openai/gpt-5.1",
  "reviewer_account": "ACCT_1_GPT5",
  "scores": {
    "clarity": 8,
    "edge_plausibility": 7,
    "timing_catalyst": 6,
    "risk_definition": 9,
    "risk_management": 8,
    "originality": 5,
    "tradeability": 7
  },
  "average_score": 7.14,
  "best_argument_against": "The thesis assumes Fed will pivot, but recent data suggests otherwise. If inflation remains sticky, the entire trade invalidates.",
  "one_flip_condition": "CPI print above 3.5% would invalidate the dovish Fed assumption",
  "suggested_fix": "Add a short-dated time stop (1 week) and tighter stop loss at -2% to limit downside if thesis proves wrong quickly",
  "raw_response": "Full text review from model...",
  "reviewed_at": "2025-01-15T14:30:00Z"
}
```

**Configuration Example:**

```python
from backend.pipeline.stages.peer_review import PeerReviewStage

# Basic usage with default temperature
stage = PeerReviewStage()

# With custom temperature for more deterministic reviews
stage = PeerReviewStage(temperature=0.3)

# With higher temperature for more creative critiques
stage = PeerReviewStage(temperature=0.8)

# Execute stage
context = await stage.execute(context)
peer_reviews = context.get(PEER_REVIEWS)
label_to_model = context.get(LABEL_TO_MODEL)

# Access review data
for review in peer_reviews:
    print(f"Reviewer: {review['reviewer_account']}")
    print(f"Pitch: {review['pitch_label']}")
    print(f"Average Score: {review['average_score']:.2f}/10")
    print(f"Kill Shot: {review['best_argument_against']}")
    print()
```

**Error Handling:**

The stage is designed to be robust and never crash the pipeline:

1. **No Pitches Found:**
   - Returns original context unchanged
   - Prints error message: "❌ Error: PM pitches not found in context"
   - Downstream stages should check for PEER_REVIEWS presence

2. **Model Query Failure:**
   - If a model fails to respond, that model's reviews are skipped
   - Other models' reviews are still collected
   - Prints warning: "❌ {model_account} ({model_key}) - Failed to parse review"
   - Pipeline continues with partial review data

3. **Parse Failure:**
   - If review response cannot be parsed, that review is skipped
   - Prints warning with model details
   - Other reviews proceed normally
   - Common causes: malformed JSON, unexpected response format

4. **Empty Review List:**
   - If all models fail to generate reviews, returns empty list
   - PEER_REVIEWS key will be set but list will be empty
   - ChairmanStage can still proceed (will see pitches without peer scores)

**Anonymization Details:**

The anonymization process preserves all trade-relevant information while hiding identity:

**Preserved Fields:**
- `selected_instrument`: Ticker symbol (e.g., "SPY")
- `direction`: Trade direction ("LONG", "SHORT", "FLAT")
- `horizon`: Time horizon ("1W", "2W", "1M")
- `thesis_bullets`: List of thesis points
- `conviction`: Conviction score (0-2)
- `risk_profile`: Risk profile ("BASE", "AGGRESSIVE", "CONSERVATIVE")
- `entry_policy`: Entry execution rules
- `exit_policy`: Stop loss, take profit, time stop rules
- `risk_notes`: Additional risk management notes

**Stripped Fields:**
- `model`: Original model identifier
- `model_info`: Account name and model details
- Any other metadata that could identify the source

**Added Fields:**
- `anonymized_label`: Random label (e.g., "Pitch A")
- `original_model`: Stored separately in LABEL_TO_MODEL mapping
- `original_account`: Stored separately for post-review de-anonymization

**Integration with Other Stages:**

```python
# Typical pipeline integration
from backend.pipeline import Pipeline
from backend.pipeline.stages.pm_pitch import PMPitchStage
from backend.pipeline.stages.peer_review import PeerReviewStage
from backend.pipeline.stages.chairman import ChairmanStage

pipeline = Pipeline([
    # ... Research stages populate RESEARCH_PACK_A, RESEARCH_PACK_B
    PMPitchStage(),        # Generates PM_PITCHES
    PeerReviewStage(),     # Anonymizes and reviews PM_PITCHES
    ChairmanStage(),       # Uses PEER_REVIEWS and de-anonymized PM_PITCHES
    # ... Execution stages use CHAIRMAN_DECISION
])

# The chairman stage receives:
# - PM_PITCHES (original pitches with model info)
# - PEER_REVIEWS (anonymized reviews with scores)
# - LABEL_TO_MODEL (mapping to de-anonymize if needed)
```

**Common Issues and Debugging:**

1. **"PM pitches not found in context" error:**
   - Cause: PeerReviewStage run before PMPitchStage
   - Impact: No reviews generated, stage returns original context
   - Fix: Ensure PMPitchStage runs before PeerReviewStage in pipeline

2. **"Failed to parse review" warnings:**
   - Cause: Model returned non-JSON response or unexpected format
   - Impact: That model's reviews are skipped
   - Fix: Check model temperature (too high may cause rambling), verify prompt clarity

3. **Empty peer_reviews list:**
   - Cause: All models failed to generate parseable reviews
   - Impact: ChairmanStage proceeds without peer feedback
   - Fix: Check API keys, model availability, temperature settings

4. **Low review scores across the board:**
   - Cause: Models may be too critical or misunderstanding rubric
   - Impact: All pitches score poorly, may bias chairman decision
   - Fix: Review system prompt in peer_review.py, adjust rubric instructions

5. **Duplicate reviews (same reviewer reviewing same pitch twice):**
   - Cause: Bug in review distribution logic
   - Impact: Unfair weighting of certain reviewer opinions
   - Fix: Should not happen; report as bug if seen

**Performance Characteristics:**

- **Execution Time:** 10-30 seconds depending on number of pitches and models
  - Each model reviews all other pitches in parallel
  - 4 PM models × 4 pitches = ~16 reviews total
  - Perplexity models (grok) may be slower than OpenAI/Anthropic

- **API Costs:** ~$0.05-0.20 per review cycle
  - Input tokens: ~1000-2000 per review (pitch content + rubric + system prompt)
  - Output tokens: ~500-1000 per review (scores + critiques + suggestions)
  - Total: ~16 reviews × ~3000 tokens = ~48k tokens per stage execution

- **Rate Limits:** Respects model provider rate limits
  - Uses requesty_client for parallel queries with retry logic
  - Falls back gracefully if rate limit hit (skips that model's reviews)

- **Memory Usage:** Minimal (<50MB)
  - Stores anonymized pitches in memory during review generation
  - Discards immediately after reviews complete
  - PEER_REVIEWS list stored in context (~10-20KB per review)

**Database Persistence:**

Peer reviews are not automatically persisted to database (unlike research reports). To store reviews:

```python
# In your pipeline post-processing
from backend.db_helpers import execute

peer_reviews = context.get(PEER_REVIEWS)
for review in peer_reviews:
    await execute(
        """
        INSERT INTO peer_reviews
        (week_id, pitch_label, reviewer_model, scores, best_argument_against,
         one_flip_condition, suggested_fix, average_score, reviewed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        week_id,
        review["pitch_label"],
        review["reviewer_model"],
        review["scores"],  # JSONB
        review["best_argument_against"],
        review["one_flip_condition"],
        review["suggested_fix"],
        review["average_score"],
        review["reviewed_at"]
    )
```

**Best Practices:**

1. **Temperature Selection:**
   - Use 0.5-0.7 for balanced, critical analysis
   - Lower (0.3-0.5) for more consistent scoring
   - Higher (0.7-1.0) for more creative critiques

2. **Rubric Calibration:**
   - Review scores across multiple weeks to calibrate expectations
   - Adjust system prompt if scores consistently too high/low
   - Track inter-rater reliability (do models agree on good/bad pitches?)

3. **Kill Shot Quality:**
   - Best reviews identify non-obvious counterarguments
   - Weak reviews just restate obvious risks
   - Use kill shot quality as meta-metric for review usefulness

4. **Anonymization Integrity:**
   - Never reveal model identity in prompts or context available to reviewers
   - ChairmanStage should de-anonymize only after reviews complete
   - Preserve LABEL_TO_MODEL for post-mortem analysis

5. **Review Distribution:**
   - Ensure each pitch reviewed by at least 3 other models
   - Track reviewer-pitch matrix to detect biases
   - Consider excluding self-reviews (model reviewing own pitch)

---

### Chairman Layer

#### ChairmanStage

**Purpose:** Synthesize final council trading decision from PM pitches and peer reviews with dissent tracking

**Overview:**

`ChairmanStage` acts as the Chief Investment Officer (CIO) of the trading system, synthesizing all PM pitches and peer reviews into a single, optimal council trading decision. This stage represents the culmination of the council decision-making process where:

1. **Objective Synthesis:** Reviews all PM pitches with peer evaluation context
2. **Consensus Building:** Identifies areas of agreement and disagreement among PMs
3. **Dissent Tracking:** Documents minority views and counterarguments
4. **Risk Integration:** Considers peer-reviewed risk assessments
5. **Monitoring Plan:** Provides checkpoint guidance for tracking decision validity
6. **Conviction Calibration:** Weights conviction based on pitch quality and peer scores

The Chairman uses Claude Opus 4.5 (or equivalent Opus-class model) to provide high-quality strategic synthesis. Unlike individual PM models, the Chairman sees all pitches, all peer reviews, and the full context of the council's deliberations.

**Key Responsibilities:**

1. **Decision Making:** Select the best trade from competing pitches or decide to stay FLAT
2. **Rationale Documentation:** Explain why the chosen trade is superior
3. **Dissent Recording:** Document why other pitches were rejected
4. **Monitoring Setup:** Define what indicators to watch at checkpoints
5. **Conviction Synthesis:** Blend PM conviction with peer review quality scores

**Constructor Parameters:**
- `temperature` (float | None): Model temperature for synthesis generation
  - Default: None (uses TemperatureManager default for "chairman")
  - Range: 0.0 (deterministic) to 2.0 (creative)
  - Typical: 0.5-0.7 for balanced, thoughtful synthesis
  - Lower values (0.3-0.5) for more consistent decision-making
  - Higher values (0.7-1.0) for more creative trade selection

**Context Keys:**

*Input:*
- `PM_PITCHES` (list) - Trade pitches from PMPitchStage
  - Each pitch contains: model, instrument, direction, thesis, conviction, risk profile, entry/exit policies
  - Minimum 1 pitch required (can proceed with single pitch)
  - Typical: 4-5 pitches from different PM models

- `PEER_REVIEWS` (list) - Structured reviews from PeerReviewStage
  - Each review contains: scores, best_argument_against, one_flip_condition, suggested_fix
  - Used to assess pitch quality and identify weaknesses
  - Optional: Chairman can proceed without peer reviews (though quality degrades)

- `LABEL_TO_MODEL` (dict) - De-anonymization mapping from PeerReviewStage
  - Maps anonymous labels (e.g., "Pitch A") to original model names
  - Used to attribute pitches correctly in chairman synthesis
  - Optional: If not provided, Chairman works with pitch data directly

*Output:*
- `CHAIRMAN_DECISION` (dict) - Final council trading decision containing:
  - `instrument`: Selected ticker (e.g., "SPY", "QQQ") or "FLAT"
  - `direction`: "LONG", "SHORT", or "FLAT"
  - `horizon`: Time horizon ("1W", "2W", "1M")
  - `conviction`: Council conviction score (-2 to +2)
  - `rationale`: Explanation for why this trade was chosen
  - `dissent_summary`: List of why other pitches were rejected
  - `monitoring_plan`: What to check at daily checkpoints
  - `risk_profile`: "BASE", "AGGRESSIVE", or "CONSERVATIVE"
  - `entry_policy`: Entry execution rules from selected pitch
  - `exit_policy`: Stop loss, take profit, time stop rules from selected pitch
  - `selected_pitch_model`: Which PM model's pitch was selected
  - `average_peer_score`: Average peer review score for selected pitch
  - `timestamp`: ISO8601 timestamp of decision

**Decision Schema:**

```json
{
  "instrument": "SPY",
  "direction": "LONG",
  "horizon": "1W",
  "conviction": 1.2,
  "rationale": "Council selects SPY LONG based on convergence of growth acceleration thesis and favorable risk/reward. Peer reviews scored this pitch 8.2/10 on average, highlighting strong clarity and risk definition. The timing catalyst (earnings season strength) is well-defined with clear invalidation at 520 level.",
  "dissent_summary": [
    "QQQ LONG pitch rejected due to concentration risk in mega-cap tech",
    "TLT SHORT pitch rejected due to uncertain timing on Fed policy pivot",
    "GLD LONG pitch rejected due to weak conviction and unclear catalyst"
  ],
  "monitoring_plan": {
    "indicators_to_watch": ["SPY price vs 525 support", "VIX staying below 18"],
    "checkpoint_actions": [
      "If SPY breaks below 520, reassess thesis validity",
      "If VIX spikes above 20, consider reducing conviction"
    ]
  },
  "risk_profile": "BASE",
  "entry_policy": {
    "mode": "limit",
    "limit_price": 527.50,
    "good_til": "day_end",
    "allow_partial": true
  },
  "exit_policy": {
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.05,
    "time_stop_days": 7,
    "trailing_stop": false
  },
  "selected_pitch_model": "openai/gpt-5.1",
  "average_peer_score": 8.2,
  "timestamp": "2025-01-15T14:45:00Z"
}
```

**Configuration Example:**

```python
from backend.pipeline.stages.chairman import ChairmanStage

# Basic usage with default temperature
stage = ChairmanStage()

# With custom temperature for more deterministic synthesis
stage = ChairmanStage(temperature=0.4)

# With higher temperature for more creative synthesis
stage = ChairmanStage(temperature=0.8)

# Execute stage
context = await stage.execute(context)
chairman_decision = context.get(CHAIRMAN_DECISION)

# Access decision data
print(f"Council Decision: {chairman_decision['instrument']} {chairman_decision['direction']}")
print(f"Conviction: {chairman_decision['conviction']}")
print(f"Rationale: {chairman_decision['rationale']}")
print(f"Selected from: {chairman_decision['selected_pitch_model']}")
print(f"Peer score: {chairman_decision['average_peer_score']:.2f}/10")
```

**Tradable Universe:**

The Chairman can only select from the approved tradable universe:
- **Equities:** SPY, QQQ, IWM
- **Duration:** TLT, IEF (future support)
- **Credit:** HYG, LQD (future support)
- **Currencies:** UUP
- **Commodities:** GLD, USO
- **Volatility:** VIXY
- **Inverse:** SH

Additionally, the Chairman can decide to stay **FLAT** (no position) if no pitch meets quality standards.

**Conviction Scale:**

The Chairman outputs conviction scores on a -2 to +2 scale:
- **+2.0:** Extremely high conviction (rare, requires exceptional pitch quality and peer consensus)
- **+1.5:** High conviction (strong thesis, good peer scores, clear catalyst)
- **+1.0:** Medium-high conviction (solid thesis, acceptable peer scores)
- **+0.5:** Medium-low conviction (weak thesis or mixed peer feedback)
- **+0.0:** Neutral (staying FLAT, no compelling trades)
- **-0.5 to -2.0:** Short conviction (mirror of long convictions)

**Synthesis Process:**

The Chairman follows a systematic synthesis process:

1. **Pitch Review:**
   - Read all PM pitches with their thesis, conviction, risk profile
   - Note areas of agreement (multiple PMs pitching same direction)
   - Note areas of disagreement (conflicting views)

2. **Peer Review Integration:**
   - Review scores for each pitch across 7 dimensions
   - Identify highest-rated pitches by average peer score
   - Review "kill shot" critiques (best_argument_against)
   - Review flip conditions (one_flip_condition)
   - Review suggested improvements (suggested_fix)

3. **Consensus Identification:**
   - Check if multiple PMs converge on same instrument/direction
   - Check if high-conviction pitches align
   - Weight convergence as positive signal

4. **Dissent Analysis:**
   - Document why competing pitches were rejected
   - Extract valuable counterarguments from peer reviews
   - Note minority views that deserve monitoring

5. **Risk-Adjusted Selection:**
   - Balance conviction with risk management quality
   - Prefer pitches with clear stop loss and invalidation criteria
   - Consider tradeability and execution feasibility

6. **Monitoring Plan Generation:**
   - Define what indicators to check at daily checkpoints
   - Set specific thresholds for reassessing thesis
   - Provide actionable guidance for conviction updates

**JSON Schema Validation:**

The Chairman's output is validated against `schemas/chairman_decision.schema.json`:

```json
{
  "type": "object",
  "required": ["instrument", "direction", "horizon", "conviction", "rationale"],
  "properties": {
    "instrument": {
      "type": "string",
      "enum": ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH", "FLAT"]
    },
    "direction": {
      "type": "string",
      "enum": ["LONG", "SHORT", "FLAT"]
    },
    "horizon": {
      "type": "string",
      "enum": ["1W", "2W", "1M"]
    },
    "conviction": {
      "type": "number",
      "minimum": -2,
      "maximum": 2
    },
    "rationale": {
      "type": "string",
      "minLength": 50
    },
    "dissent_summary": {
      "type": "array",
      "items": {"type": "string"}
    },
    "monitoring_plan": {
      "type": "object",
      "properties": {
        "indicators_to_watch": {"type": "array"},
        "checkpoint_actions": {"type": "array"}
      }
    }
  }
}
```

**Error Handling:**

The stage is designed to never crash the pipeline and always produce a decision:

1. **No Pitches Found:**
   - Returns original context unchanged
   - Prints error: "❌ Error: PM pitches or peer reviews not found in context"
   - Downstream stages should check for CHAIRMAN_DECISION presence

2. **Chairman Query Failure:**
   - If Claude Opus fails to respond, falls back to highest-conviction pitch
   - Prints warning: "❌ Failed to generate chairman decision"
   - Calls `_fallback_decision()` to select best pitch by conviction
   - Fallback logic: Select pitch with highest conviction * average_peer_score

3. **Parse Failure:**
   - If chairman response cannot be parsed, uses fallback decision
   - Prints warning with parse error details
   - Fallback ensures pipeline never blocks on chairman synthesis failure

4. **Schema Validation Failure:**
   - Validates parsed decision against JSON schema
   - If validation fails, attempts to fix common issues
   - Ultimate fallback: Use highest-conviction pitch from PMs

**Fallback Decision Logic:**

When the Chairman cannot generate a decision, the system falls back to a simple heuristic:

```python
def _fallback_decision(self, pm_pitches: List[Dict]) -> Dict:
    """Generate fallback decision by selecting highest conviction pitch."""
    if not pm_pitches:
        return {
            "instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": 0,
            "rationale": "No PM pitches available for synthesis",
            "dissent_summary": [],
            "monitoring_plan": {},
        }

    # Select pitch with highest conviction
    best_pitch = max(pm_pitches, key=lambda p: abs(p.get("conviction", 0)))

    return {
        "instrument": best_pitch.get("selected_instrument", "FLAT"),
        "direction": best_pitch["direction"],
        "horizon": best_pitch["horizon"],
        "conviction": best_pitch["conviction"] * 0.8,  # Reduce conviction due to fallback
        "rationale": f"Fallback selection: Highest conviction pitch from {best_pitch['model']}",
        "dissent_summary": ["Chairman synthesis unavailable - fallback to highest conviction"],
        "monitoring_plan": {},
        "risk_profile": best_pitch.get("risk_profile", "BASE"),
        "entry_policy": best_pitch.get("entry_policy", {}),
        "exit_policy": best_pitch.get("exit_policy", {}),
    }
```

**Integration with Other Stages:**

```python
# Typical pipeline integration
from backend.pipeline import Pipeline
from backend.pipeline.stages.pm_pitch import PMPitchStage
from backend.pipeline.stages.peer_review import PeerReviewStage
from backend.pipeline.stages.chairman import ChairmanStage
from backend.pipeline.stages.execution import ExecutionStage

pipeline = Pipeline([
    # ... Research stages populate RESEARCH_PACK_A, RESEARCH_PACK_B
    PMPitchStage(),        # Generates PM_PITCHES
    PeerReviewStage(),     # Generates PEER_REVIEWS and LABEL_TO_MODEL
    ChairmanStage(),       # Synthesizes CHAIRMAN_DECISION
    ExecutionStage(),      # Executes CHAIRMAN_DECISION via Alpaca
])

# The chairman receives:
# - PM_PITCHES: Original pitches with full context
# - PEER_REVIEWS: Anonymized reviews with scores and critiques
# - LABEL_TO_MODEL: Mapping to de-anonymize pitches if needed

# The chairman outputs:
# - CHAIRMAN_DECISION: Final trade decision for execution
```

**Common Issues and Debugging:**

1. **"PM pitches or peer reviews not found in context" error:**
   - Cause: ChairmanStage run before PMPitchStage or PeerReviewStage
   - Impact: No decision generated, returns original context
   - Fix: Ensure proper stage ordering in pipeline

2. **"Failed to generate chairman decision" warning:**
   - Cause: Claude Opus API failure, rate limit, or network issue
   - Impact: Falls back to highest-conviction pitch (degraded quality)
   - Fix: Verify API key, check rate limits, increase timeout

3. **Fallback decisions appearing frequently:**
   - Cause: Chairman model unavailable or response parsing issues
   - Impact: Lower quality decisions, no dissent tracking or monitoring plans
   - Fix: Check model availability, review temperature settings, verify prompt clarity

4. **Low conviction in chairman decisions:**
   - Cause: Chairman is conservative, peer reviews show concerns, or pitches are weak
   - Impact: Smaller position sizes, less aggressive trading
   - Fix: This may be correct behavior; review pitch quality and peer feedback

5. **Chairman always picks same PM model:**
   - Cause: That model consistently produces highest-quality pitches
   - Impact: Other PMs not getting selected, reducing diversity
   - Fix: Review other PM models' performance, adjust prompts, or add model rotation logic

**Performance Characteristics:**

- **Execution Time:** 5-15 seconds for chairman synthesis
  - Single model query (Claude Opus 4.5)
  - Prompt includes all pitches + peer reviews (~3000-5000 tokens)
  - Response generation: ~1000-2000 tokens
  - JSON parsing and validation: <100ms

- **API Costs:** ~$0.02-0.05 per synthesis
  - Input tokens: ~4000 tokens (all pitches + reviews + system prompt)
  - Output tokens: ~1500 tokens (decision + rationale + dissent)
  - Total: ~5500 tokens per execution at Opus pricing

- **Rate Limits:** Single query, minimal rate limit impact
  - Uses requesty_client with retry logic
  - Falls back gracefully if rate limit hit

- **Memory Usage:** Minimal (<10MB)
  - Loads all pitches and reviews into memory temporarily
  - Discards after synthesis complete
  - CHAIRMAN_DECISION stored in context (~2-5KB)

**Database Persistence:**

Chairman decisions are not automatically persisted to database. To store decisions:

```python
# In your pipeline post-processing
from backend.db_helpers import execute

chairman_decision = context.get(CHAIRMAN_DECISION)
await execute(
    """
    INSERT INTO chairman_decisions
    (week_id, instrument, direction, horizon, conviction, rationale,
     dissent_summary, monitoring_plan, risk_profile, entry_policy,
     exit_policy, selected_pitch_model, average_peer_score, decided_at)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
    """,
    week_id,
    chairman_decision["instrument"],
    chairman_decision["direction"],
    chairman_decision["horizon"],
    chairman_decision["conviction"],
    chairman_decision["rationale"],
    chairman_decision["dissent_summary"],  # JSONB
    chairman_decision["monitoring_plan"],  # JSONB
    chairman_decision.get("risk_profile", "BASE"),
    chairman_decision.get("entry_policy", {}),  # JSONB
    chairman_decision.get("exit_policy", {}),  # JSONB
    chairman_decision.get("selected_pitch_model"),
    chairman_decision.get("average_peer_score"),
    chairman_decision.get("timestamp")
)
```

**Best Practices:**

1. **Temperature Selection:**
   - Use 0.5-0.7 for balanced, thoughtful synthesis
   - Lower (0.3-0.5) for more consistent decision-making
   - Higher (0.7-1.0) for more creative trade selection
   - Never exceed 1.0 (risks incoherent decisions)

2. **Dissent Tracking:**
   - Always review dissent_summary to understand trade-offs
   - Minority views often contain valuable risk insights
   - Use dissent notes for post-mortem analysis

3. **Monitoring Plan Usage:**
   - Checkpoint stages should reference monitoring_plan
   - Define specific, actionable thresholds
   - Update conviction based on monitoring plan indicators

4. **Conviction Calibration:**
   - Track chairman conviction vs actual trade outcomes
   - Adjust if chairman is consistently over/under confident
   - Compare chairman conviction to individual PM convictions

5. **Fallback Awareness:**
   - Monitor frequency of fallback decisions
   - High fallback rate indicates chairman model issues
   - Fallback decisions lack dissent tracking and monitoring plans

**See Also:**

- `backend/pipeline/stages/chairman.py` - Full implementation
- `schemas/chairman_decision.schema.json` - Decision validation schema
- `backend/requesty_client.py` - Chairman model query interface
- [PIPELINE.md](../PIPELINE.md) - Pipeline architecture overview

---

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
