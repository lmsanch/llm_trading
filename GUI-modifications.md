# GUI Modifications - Research Tab Update

## Purpose

Design document for updating the Research Tab to:
1. Display **both** natural language research reports AND structured JSON fields
2. Implement **prompt review + send + polling** workflow for Stage 1
3. Display **30-day OHLCV time series** context

---

## CRITICAL: 7-Day Trading Horizon

The research prompt is configured for a **7-day trading horizon only**.
- All research focuses on the next 7 trading days
- NOT quarter-ahead or decade-ahead analysis
- Catalysts, risks, and tradable ideas are all for THIS WEEK

---

## Current State

### Files
- `frontend/src/components/dashboard/tabs/ResearchTab.jsx`
- `frontend/src/components/dashboard/tabs/ResearchPackCard.jsx`
- `frontend/src/lib/mockData.js`

### Current Data Structure (mockData.js)
```javascript
{
  source: "perplexity" | "gemini",
  model: "model-name",
  macro_regime: {
    risk_mode: "RISK_ON" | "RISK_OFF" | "NEUTRAL",
    description: "..."
  },
  top_narratives: ["...", ...],
  tradable_candidates: [
    { ticker: "...", rationale: "..." }
  ],
  event_calendar: [
    { date: "...", event: "...", impact: "HIGH|MEDIUM|LOW" }
  ]
}
```

### Current Display
The current `ResearchPackCard.jsx` displays ONLY the structured JSON fields:
- Macro Regime (risk_mode badge + description)
- Top Narratives (bullet list)
- Tradable Candidates (ticker + rationale)
- Event Calendar (date + event + impact)

**MISSING:** The natural language research report - the full text analysis from the research provider.

---

## New Backend Data Format

The backend now returns **dual format** from both Perplexity and Gemini:

```javascript
{
  source: "perplexity" | "gemini",
  model: "model-name",
  // NEW: Full natural language research report
  natural_language: "Complete research report in prose form...",
  // Existing: Structured JSON for parsing
  macro_regime: {
    risk_mode: "RISK_ON" | "RISK_OFF" | "NEUTRAL",
    description: "..."
  },
  top_narratives: ["...", ...],
  tradable_candidates: [
    { ticker: "...", rationale: "..." }
  ],
  event_calendar: [
    { date: "...", event: "...", impact: "HIGH|MEDIUM|LOW" }
  ],
  confidence_notes: {
    known_unknowns: "...",
    data_quality_flags: ["..."]
  },
  status: "complete" | "error",
  generated_at: "ISO8601 timestamp"
}
```

---

## Requirements

### 1. NEW: Prompt Review + Send + Polling Workflow (Stage 1)

**This is the primary workflow change.** The Research Tab should NOT auto-fetch research on load. Instead:

#### Initial State: Awaiting Input

```
+----------------------------------------------------------+
|  RESEARCH PHASE                          [AWAITING INPUT] |
+----------------------------------------------------------+
|                                                          |
|  [Review Prompt & Send to Research]                      |
|                                                          |
|                                                          |
+----------------------------------------------------------+
|                                                          |
|  [Send to Perplexity & Gemini]        [Pass to PMs]      |
|                                                          |
+----------------------------------------------------------+
```

#### Step 1: Review Prompt Modal

When user clicks "Review Prompt & Send to Research", show an attractive modal/panel:

```
+----------------------------------------------------------+
|  📋 Research Prompt Review                               |
+----------------------------------------------------------+
|                                                          |
|  Market snapshot will include 30-day OHLCV data for:     |
|  ✓ SPY  ✓ QQQ  ✓ IWM  ✓ TLT  ✓ HYG  ✓ UUP  ✓ GLD  ✓ USO |
|                                                          |
|  +------------------------------------------------------+|
|  | Trading Horizon: 7 DAYS ONLY                        ||
|  |                                                      ||
|  | [Read Full Prompt...]                                ||
|  +------------------------------------------------------+|
|                                                          |
|  Prompt: config/prompts/research_prompt.md              |
|  Version: 1.1 | Last updated: [date]                     |
|                                                          |
|                        [Send to Research]  [Cancel]     |
|                                                          |
+----------------------------------------------------------+
```

When user clicks "Read Full Prompt", show the actual prompt content in a scrollable area.

#### Step 2: Send Button → Triggers Research + Polling

After user reviews prompt and clicks "Send to Research":

1. **POST to backend:**
   ```
   POST /api/research/generate
   ```

2. **Backend spawns async research jobs** for both Perplexity and Gemini

3. **Frontend begins polling:**
   ```
   GET /api/research/status?job_id={uuid}
   ```

4. **Poll every 2-3 seconds** until both are complete

#### Step 3: Progress State During Polling

```
+----------------------------------------------------------+
|  RESEARCH PHASE                              [RUNNING...] |
+----------------------------------------------------------+
|                                                          |
|  +------------------------------------------------------+|
|  | 📊 Perplexity Deep Research                          ||
|  | Status: [███████████████████████] 75% complete      ||
|  | Message: "Fetching latest market data..."           ||
|  +------------------------------------------------------+|
|  |                                                      ||
|  | 🧠 Gemini Deep Research                             ||
|  | Status: [████████████░░░░░░░░░░] 45% complete       ||
|  | Message: "Analyzing macro regime..."                ||
|  +------------------------------------------------------+|
|                                                          |
|  Estimated time remaining: ~45 seconds                   |
|                                                          |
+----------------------------------------------------------+
|                                                          |
|  [Cancel]                                    [Pass to PMs]|
|                                                      (greyed out)|
+----------------------------------------------------------+
```

**Important:** "Pass to PMs" button is **greyed out/disabled** until BOTH research providers return `status: "complete"`.

#### Step 4: Complete State - Display Results

When both are complete, show the two research cards side-by-side (as currently designed, but with real data):

```
+----------------------------------------------------------+
|  RESEARCH PHASE                                 [COMPLETE] |
+----------------------------------------------------------+
|                                                          |
|  +-----------------------------+  +---------------------+|
|  | 📊 Perplexity Research      |  | 🧠 Gemini Research  ||
|  | [Full Report ▼]            |  | [Full Report ▼]    ||
|  |                             |  |                     ||
|  | [Structured fields...]      |  | [Structured fields] ||
|  |                             |  |                     ||
|  | [Regenerate] [Verify]       |  | [Regenerate] [Verify]||
|  +-----------------------------+  +---------------------+|
|                                                          |
+----------------------------------------------------------+
|                                                          |
|  [Review Prompt & Send Again]              [Pass to PMs]  |
|                                              (enabled)    |
+----------------------------------------------------------+
```

#### Polling API Specification

**Generate Research:**
```
POST /api/research/generate
Content-Type: application/json

{
  "force_refresh": false  // true to skip cache
}

Response:
{
  "job_id": "uuid-123",
  "status": "pending",
  "started_at": "2025-01-08T09:00:00Z"
}
```

**Poll Status:**
```
GET /api/research/status?job_id={uuid}

Response:
{
  "job_id": "uuid-123",
  "status": "running",  // pending | running | complete | error
  "started_at": "2025-01-08T09:00:00Z",
  "perplexity": {
    "status": "running",  // pending | running | complete | error
    "progress": 75,
    "message": "Generating research report..."
  },
  "gemini": {
    "status": "running",
    "progress": 45,
    "message": "Analyzing macro regime..."
  }
}
```

**Get Final Results:**
```
GET /api/research/{job_id}

Response:
{
  "job_id": "uuid-123",
  "status": "complete",
  "completed_at": "2025-01-08T09:01:30Z",
  "perplexity": { /* dual format data */ },
  "gemini": { /* dual format data */ },
  "market_snapshot": { /* 30-day OHLCV data */ }
}
```

---

### 2. Update ResearchPackCard Component

Add a new section to display the **Natural Language Report** at the top of each card:

#### Recommended Layout (top to bottom):

1. **Header** (existing)
   - Source icon + name
   - Model name
   - Source badge

2. **NEW: Natural Language Report Section**
   - Collapsible or scrollable text area
   - Contains full prose research report
   - Styling suggestion: muted background, monospace font for readability
   - Max height with scroll if content is long

3. **Structured JSON Fields** (existing)
   - Macro Regime
   - Top Narratives
   - Tradable Candidates
   - Event Calendar

4. **Footer Actions** (existing)
   - Regenerate button
   - Verify button

### 3. Suggested Component Structure

```jsx
<Card className="flex flex-col h-full">
  <CardHeader className="pb-3">
    {/* Existing header */}
  </CardHeader>

  <CardContent className="flex-1 space-y-4 overflow-y-auto">

    {/* NEW: Natural Language Report */}
    {data.natural_language && (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <FileText className="h-4 w-4" /> Full Report
        </h4>
        <div className="bg-muted/50 p-3 rounded-md text-sm max-h-48 overflow-y-auto">
          <p className="whitespace-pre-wrap">{data.natural_language}</p>
        </div>
      </div>
    )}

    {/* Existing: Macro Regime */}
    {/* Existing: Top Narratives */}
    {/* Existing: Tradable Candidates */}
    {/* Existing: Event Calendar */}

  </CardContent>

  <div className="p-4 pt-0 mt-auto flex gap-2">
    {/* Existing footer buttons */}
  </div>
</Card>
```

### 4. Styling Considerations

- **Natural language section** should be visually distinct from structured fields
- Use `whitespace-pre-wrap` to preserve line breaks from the LLM output
- Add `max-h-48 overflow-y-auto` to prevent cards from becoming too tall
- Consider a toggle button to show/hide the natural language section

---

## Implementation Steps

### Step 1: Update ResearchTab.jsx - New Polling Workflow

**Remove** auto-fetch on mount. **Add** state machine for research workflow:

```jsx
const [researchState, setResearchState] = useState('idle'); // idle | pending | running | complete | error
const [jobId, setJobId] = useState(null);
const [researchData, setResearchData] = useState(null);

// Initial render: show "Review Prompt & Send" button
if (researchState === 'idle') {
  return <InitialPromptReview onSend={handleStartResearch} />;
}

// After user sends: start polling
const handleStartResearch = async () => {
  const response = await fetch('/api/research/generate', { method: 'POST' });
  const { job_id } = await response.json();
  setJobId(job_id);
  setResearchState('running');
  startPolling(job_id);
};

// Poll every 2-3 seconds
const startPolling = (jobId) => {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/research/status?job_id=${jobId}`);
    const status = await response.json();

    setPollingStatus(status);

    if (status.status === 'complete') {
      clearInterval(interval);
      setResearchState('complete');
      // Fetch final results
      const results = await fetch(`/api/research/${jobId}`);
      const data = await results.json();
      setResearchData(data);
    }
  }, 2500);
};
```

### Step 2: Create PromptReviewModal Component

New component to display:
- List of instruments with 30-day OHLCV data
- "Trading Horizon: 7 DAYS ONLY" badge
- Full prompt content (fetch from `/api/research/prompt` endpoint)
- Send to Research button
- Cancel button

### Step 3: Update ResearchPackCard.jsx
- Add natural language report section at top of card content
- Import `FileText` icon from lucide-react
- Ensure proper scrolling for long content
- Handle case where `natural_language` is empty/missing

### Step 4: Add New Backend Endpoints

The backend needs to implement:
1. `GET /api/research/prompt` - Returns the current prompt text for review
2. `POST /api/research/generate` - Starts async research jobs
3. `GET /api/research/status?job_id={uuid}` - Poll status
4. `GET /api/research/{job_id}` - Get final results

### Step 5: Update mockData.js (optional)
- Add `natural_language` field to mock data for testing
- Add 30-day OHLCV structure to `market_snapshot.instruments`
- This allows frontend development without backend dependency

---

## 30-Day OHLCV Data Architecture

### Tradable Universe

The following instruments require 30-day daily OHLCV data:

| Ticker | Description | Alpaca Symbol |
|--------|-------------|---------------|
| SPY | S&P 500 | SPY |
| QQQ | Nasdaq 100 | QQQ |
| IWM | Russell 2000 | IWM |
| TLT | 20+ Year Treasury | TLT |
| HYG | High Yield Corporate | HYG |
| UUP | US Dollar Index | UUP |
| GLD | Gold | GLD |
| USO | Oil | USO |

### Data Structure per Instrument

```json
{
  "symbol": "SPY",
  "current": {
    "price": 480.50,
    "change_pct": 1.2
  },
  "daily_ohlcv_30d": [
    {
      "date": "2024-12-09",
      "open": 475.0,
      "high": 478.5,
      "low": 474.0,
      "close": 477.2,
      "volume": 45000000
    },
    // ... 30 trading days total (approximately 6 weeks)
  ],
  "indicators": {
    "sma_20": 475.5,
    "sma_50": 468.0,
    "rsi_14": 58.2,
    "above_sma20": true,
    "above_sma50": true,
    "uptrend_20d": true,
    "uptrend_50d": true
  }
}
```

### Backend Implementation Required

File: `backend/pipeline/stages/research.py` - `_fetch_market_data()` method

**Current:** Fetches placeholder prices only

**Required:** Fetch 30 days of daily bars from Alpaca

```python
async def _fetch_market_data(self) -> Dict[str, Any]:
    instruments = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO"]
    manager = MultiAlpacaManager()
    client = manager.get_client("COUNCIL")

    market_data = {
        "asof_et": self._get_timestamp(),
        "account_info": {...},
        "instruments": {}
    }

    for symbol in instruments:
        # Fetch 30 days of daily bars
        bars = await client.get_bars(
            symbol,
            timeframe=TimeFrame.Day,
            limit=30,
            adjustment='raw'
        )

        # Calculate indicators
        closes = [bar.close for bar in bars]
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None

        market_data["instruments"][symbol] = {
            "current": {
                "price": bars[-1].close,
                "change_pct": ((bars[-1].close - bars[-2].close) / bars[-2].close) * 100
            },
            "daily_ohlcv_30d": [
                {
                    "date": bar.timestamp.strftime("%Y-%m-%d"),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume
                }
                for bar in bars
            ],
            "indicators": {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "rsi_14": calculate_rsi(closes, 14),
                "above_sma20": closes[-1] > sma_20 if sma_20 else None,
                "above_sma50": closes[-1] > sma_50 if sma_50 else None
            }
        }

    return market_data
```

### Why 30 Days?

- **Appropriate for weekly trading:** 30 days ≈ 6 weeks of context
- **Token efficiency:** ~30 bars × 8 instruments = 240 data points (manageable)
- **Technical analysis:** Sufficient for 20/50 day moving averages, RSI, trend detection
- **Not too much:** Avoids overwhelming the LLM with noise
- **Not too little:** Captures recent market regime, key support/resistance levels

### Daily Conviction Checkpoints (Reduced Data)

For daily conviction updates, use MUCH less data:
- Current prices only (no history)
- Change since week open
- Current position P/L
- Frozen indicators captured at research time

See `checkpoint_snapshot` structure above in this document.

---

## New Field: confidence_notes

The backend now returns `confidence_notes` with:
- `known_unknowns`: Caveats and limitations mentioned by the LLM
- `data_quality_flags`: Any data quality issues

Consider adding a small section to display this, perhaps as a collapsible "Confidence Notes" section near the bottom of the card.

---

## Backend API Details

**Endpoint:** `GET /api/research`

**Response:**
```json
{
  "week_id": "2025-01-08",
  "perplexity": {
    "source": "perplexity",
    "model": "sonar-pro-online",
    "natural_language": "Full prose research report...",
    "macro_regime": { "risk_mode": "RISK_ON", "description": "..." },
    "top_narratives": ["...", ...],
    "tradable_candidates": [{ "ticker": "...", "rationale": "..." }],
    "event_calendar": [{ "date": "...", "event": "...", "impact": "..." }],
    "confidence_notes": { "known_unknowns": "...", "data_quality_flags": [...] },
    "status": "complete",
    "generated_at": "2025-01-08T12:00:00Z"
  },
  "gemini": {
    "source": "gemini",
    "model": "gemini-2.0-flash-thinking-exp",
    "natural_language": "Full prose research report...",
    "macro_regime": { "risk_mode": "NEUTRAL", "description": "..." },
    "top_narratives": ["...", ...],
    "tradable_candidates": [{ "ticker": "...", "rationale": "..." }],
    "event_calendar": [{ "date": "...", "event": "...", "impact": "..." }],
    "confidence_notes": { "known_unknowns": "...", "data_quality_flags": [...] },
    "status": "complete",
    "generated_at": "2025-01-08T12:00:00Z"
  },
  "market_snapshot": {
    "asof_et": "2025-01-08T12:00:00Z",
    "account_info": {
      "portfolio_value": 100000,
      "cash": 75000,
      "buying_power": 300000
    },
    "instruments": {
      "SPY": {
        "current": { "price": 480.50, "change_pct": 1.2 },
        "daily_ohlcv_30d": [
          {
            "date": "2024-12-09",
            "open": 475.0,
            "high": 478.5,
            "low": 474.0,
            "close": 477.2,
            "volume": 45000000
          }
          // ... 30 trading days total
        ],
        "indicators": {
          "sma_20": 475.5,
          "sma_50": 468.0,
          "rsi_14": 58.2,
          "above_sma20": true,
          "above_sma50": true
        }
      }
      // ... other instruments (QQQ, IWM, TLT, HYG, UUP, GLD, USO)
    }
  }
}
```

---

## Testing Checklist

### Polling Workflow
- [ ] Initial state shows "Review Prompt & Send to Research" button
- [ ] Prompt review modal shows full prompt content
- [ ] Modal displays "7 DAYS ONLY" trading horizon badge
- [ ] Modal lists all instruments with 30-day OHLCV data
- [ ] Send button triggers POST to `/api/research/generate`
- [ ] Polling starts every 2-3 seconds after send
- [ ] Progress bars show for both Perplexity and Gemini
- [ ] "Pass to PMs" button is greyed out until both complete
- [ ] When both complete, "Pass to PMs" button becomes enabled
- [ ] Cancel button stops polling and returns to idle state

### Research Display
- [ ] Natural language report displays correctly
- [ ] Long reports scroll within their container
- [ ] Structured JSON fields still display below natural language
- [ ] Both Perplexity and Gemini cards display correctly
- [ ] Card height doesn't exceed viewport (scroll within card)

### Backend APIs
- [ ] `GET /api/research/prompt` returns current prompt text
- [ ] `POST /api/research/generate` returns job_id
- [ ] `GET /api/research/status?job_id={uuid}` returns current status
- [ ] `GET /api/research/{job_id}` returns final results with 30-day OHLCV
- [ ] Error handling if API fails
- [ ] 30-day OHLCV data included in market_snapshot

---

## Example: Updated mockData for Testing

```javascript
export const mockResearchPacks = {
  perplexity: {
    source: "perplexity",
    model: "sonar-pro-online",
    natural_language: `**Macro Research Report - Week of Jan 8, 2025**

**Executive Summary**
Markets are pricing in a soft landing with Fed rate cuts expected in Q1. Inflation data is cooperating, leading to a rotation from defensive into cyclical sectors.

**Key Drivers**
1. **Fed Pivot:** Fed funds futures pricing 90% probability of a March cut. Fed speakers have shifted tone to acknowledge progress on inflation.
2. **AI Capex Cycle:** Major cloud providers are increasing infrastructure spend, signaling confidence in AI demand persistence.
3. **China Stimulus:** New fiscal measures announced including targeted support for manufacturing sectors.

**Risks to Monitor**
- Inflation re-acceleration in services
- Geopolitical escalation in Middle East
- Earnings disappointments in high-multiple tech

**Bottom Line**
Risk-on conditions favor equity exposure. Consider scaling into cyclicals while maintaining quality bias.`,
    macro_regime: {
      risk_mode: "RISK_ON",
      description: "Markets pricing soft landing with Fed cuts expected Q1."
    },
    top_narratives: [
      "Fed Pivot Imminent: 90% chance of cut in March",
      "AI Capex Cycle: Cloud providers increasing spend",
      "China Stimulus: New fiscal measures announced"
    ],
    tradable_candidates: [
      { ticker: "SPY", rationale: "Broad equity exposure in risk-on regime" },
      { ticker: "IWM", rationale: "Small caps benefit from lower rates" },
      { ticker: "TLT", rationale: "Yields likely to fall further" }
    ],
    event_calendar: [
      { date: "2025-01-08", event: "CPI Data Release", impact: "HIGH" },
      { date: "2025-01-15", event: "Fed FOMC Meeting", impact: "CRITICAL" }
    ],
    confidence_notes: {
      known_unknowns: "Fed reaction function may change if inflation re-accelerates",
      data_quality_flags: ["real-time_quotes_unavailable"]
    },
    status: "complete",
    generated_at: "2025-01-08T12:00:00Z"
  },
  gemini: {
    source: "gemini",
    model: "gemini-2.0-flash-thinking-exp",
    natural_language: `**Macro Research Report - Week of Jan 8, 2025**

**Executive Summary**
While disinflation is tracking, growth signals are mixed. Labor market cooling faster than expected suggests caution. Prefer quality over pure momentum.

**Key Drivers**
1. **Consumer Weakness:** Credit card delinquencies rising, particularly in sub-prime segments.
2. **Tech Valuation:** Multiples at historic highs, leaving little room for disappointment.
3. **Energy Sector Rotation:** Oil supply constraints creating opportunities in energy complex.

**Risks to Monitor**
- Labor market deterioration accelerating
- Earnings misses in high-flying tech
- Geopolitical supply shocks

**Bottom Line**
Cautious outlook favors defensive positioning and quality names. Consider reducing exposure to high-momentum speculative names.`,
    macro_regime: {
      risk_mode: "NEUTRAL",
      description: "Mixed growth signals, labor market cooling faster than expected."
    },
    top_narratives: [
      "Consumer Weakness: Credit card delinquencies rising",
      "Tech Valuation concerns: Multiples at historic highs",
      "Energy Sector rotation: Oil supply constraints"
    ],
    tradable_candidates: [
      { ticker: "MSFT", rationale: "Defensive growth play with strong cash flows" },
      { ticker: "XLE", rationale: "Energy hedge against geopolitics" },
      { ticker: "GLD", rationale: "Safe haven demand" }
    ],
    event_calendar: [
      { date: "2025-01-10", event: "Bank Earnings Start", impact: "MEDIUM" },
      { date: "2025-01-20", event: "Inauguration Day", impact: "MEDIUM" }
    ],
    confidence_notes: {
      known_unknowns: "Fiscal policy changes after inauguration difficult to model",
      data_quality_flags: []
    },
    status: "complete",
    generated_at: "2025-01-08T12:00:00Z"
  }
};
```

---

## File Locations

- ResearchTab: `/research/llm_trading/frontend/src/components/dashboard/tabs/ResearchTab.jsx`
- ResearchPackCard: `/research/llm_trading/frontend/src/components/dashboard/tabs/ResearchPackCard.jsx`
- MockData: `/research/llm_trading/frontend/src/lib/mockData.js`
- Backend API: `/research/llm_trading/backend/main.py`
