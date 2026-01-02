# Prompt for Gemini Design Agent

You are a **Senior UI/UX Designer** specializing in **financial trading dashboards** and **real-time data interfaces**. You will be designing a modern web interface for an **AI-powered trading system**.

## Project Context

The LLM Trading System uses a "council" of AI models to make trading decisions:

1. **Research Phase**: Two deep research providers (Perplexity, Gemini) generate market analysis
2. **PM Pitch Phase**: 5 AI "Portfolio Manager" models generate trading convictions
3. **Council Phase**: A "Chairman" model synthesizes decisions and recommends trades
4. **Execution Phase**: Approved trades are placed across 6 paper trading accounts
5. **Checkpoint Phase**: Daily conviction updates evaluate positions

**Key Constraint**: The system supports both **MANUAL** (human-in-the-loop at each stage) and **AUTOMATIC** (fully autonomous) modes.

---

## Your Task

Design a modern, professional trading dashboard UI that:

1. **Displays all pipeline phases** in a clear, tabbed interface
2. **Shows real-time status** of each phase (Waiting, Processing, Complete)
3. **Enables human review** at each stage in Manual mode
4. **Provides actionable controls** (Verify, Approve, Reject, Regenerate)
5. **Displays trading data** clearly (positions, P/L, convictions)
6. **Supports both modes** with clear visual indicators

---

## Design Requirements

### Visual Style
- **Modern financial aesthetic** (think Bloomberg Terminal meets modern SaaS)
- **Dark mode default** (traders prefer dark themes)
- **High contrast data displays** for quick scanning
- **Clean typography** with clear hierarchy
- **Color coding**:
  - Green = Bullish/LONG
  - Red = Bearish/SHORT
  - Blue = Neutral/FLAT
  - Yellow = Pending/Awaiting Input
  - Gray = Inactive

### Tab Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  🏛️ LLM TRADING  |  Week: 2025-W01  |  Mode: [MANUAL ●] [AUTO ○]  │
├─────────────────────────────────────────────────────────────────────┤
│  [Research] [PMs] [Council] [Trades] [Monitor] [Settings]           │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Designs Needed

#### 1. Research Tab
- Side-by-side view of Perplexity and Gemini research packs
- Expandable sections for: Macro Regime, Narratives, Tradable Candidates, Events
- "Verify" and "Regenerate" buttons
- Visual indicator of research quality/agreement

#### 2. PMs Tab
- Card layout for each of 5 PMs (GPT-5.2, Gemini 3 Pro, Claude Sonnet 4.5, Grok 4.1, DeepSeek V3)
- Each card shows:
  - Model name and associated account
  - Conviction score (-2 to +2) with visual gauge
  - Instrument and direction
  - Thesis bullets (expandable)
  - Key indicators
  - Invalidation condition
  - Action buttons (Regenerate, Approve, Reject)
- Bulk actions: "Regenerate All", "Verify All", "Pass to Council"

#### 3. Council Tab
- Chairman decision prominently displayed
- Selected trade card with all details
- Dissenting views summary
- Peer review score visualization (radar or bar chart)
- Monitoring plan display
- Approve/Reject controls

#### 4. Trades Tab
- Pending trades list
- Each trade shows: Account, Symbol, Direction, Qty, Conviction
- Modify capability (qty, conviction adjustment)
- Approve/Reject individual or bulk
- Execution history table

#### 5. Monitor Tab
- Live positions table (all 6 accounts)
- Account summary (Equity, Cash, P/L)
- Checkpoint schedule with status
- Conviction history chart
- Manual "Run Checkpoint" button

#### 6. Settings Tab
- Configuration forms
- API key management
- Model configuration
- Schedule editing

---

## Technical Context

### Stack
- **Frontend**: React + Vite
- **Styling**: Tailwind CSS (preferred) or CSS modules
- **Charts**: Recharts or Chart.js
- **Icons**: Lucide React or Heroicons
- **API**: REST + WebSocket/SSE for real-time updates

### Existing Codebase
The frontend is at `/research/llm_trading/frontend/` with:
- React + Vite setup
- Basic components in `src/components/`
- API client in `src/api.js`
- Existing llm-council chat interface (can be reused/modified)

---

## Deliverables

Please provide:

1. **Component Structure** - File hierarchy for React components
2. **Key Components** - Code for the most important components (at minimum):
   - App shell (Header + Navigation)
   - ResearchTab (ResearchPackCard)
   - PMPitchesTab (PMPitchCard)
   - CouncilTab (CouncilDecisionCard)
   - TradesTab (TradeCard)
3. **Styling System** - Tailwind config or CSS variables for the color scheme
4. **Data Types** - TypeScript interfaces for the data structures
5. **API Integration** - Example API calls using the tradingApi client
6. **Layout Mockup** - ASCII or description of the overall layout

---

## Design Principles

1. **Information Density**: Traders need to see a lot of data at once
2. **Quick Actions**: Common actions should be one click
3. **Clear Status**: Always show what's happening and what's needed
4. **Progressive Disclosure**: Hide details behind expand/collapse
5. **Responsive**: Works on desktop and tablet (mobile optional)
6. **Accessible**: High contrast, clear labels, keyboard navigation

---

## Example Data Structures

```typescript
interface ResearchPack {
  source: "perplexity" | "gemini";
  macro_regime: {
    risk_mode: string;
    description: string;
  };
  top_narratives: string[];
  consensus_map: Record<string, string>;
  tradable_candidates: Array<{
    ticker: string;
    rationale: string;
  }>;
  event_calendar: Array<{
    date: string;
    event: string;
    impact: string;
  }>;
}

interface PMPitch {
  model: string;
  account: string;
  instrument: string;
  direction: "LONG" | "SHORT" | "FLAT";
  horizon: string;
  conviction: number; // -2 to +2
  thesis_bullets: string[];
  indicators: string[];
  invalidation: string;
  status: "pending" | "complete" | "approved" | "rejected";
}

interface CouncilDecision {
  selected_trade: {
    instrument: string;
    direction: string;
    conviction: number;
    position_size: number;
  };
  rationale: string;
  dissent_summary: string[];
  monitoring_plan: {
    key_levels: string[];
    event_risks: string[];
  };
  peer_review_scores: Record<string, number>;
}
```

---

## Please begin with:

1. A brief analysis of the design requirements
2. Your proposed design system (colors, typography, spacing)
3. The component file structure
4. Then provide code for the key components

Focus on creating a **professional, information-dense trading dashboard** that a real trader would use daily.
