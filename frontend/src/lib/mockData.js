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
      description: "Markets are pricing in a soft landing with Fed rate cuts expected in Q1. Inflation data is cooperating, leading to a rotation from defensive into cyclical sectors."
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
      description: "While disinflation is tracking, growth signals are mixed. Labor market cooling faster than expected suggests caution. Prefer quality over pure momentum."
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

export const mockPMPitches = [
  {
    id: 1,
    model: "gpt-5.2",
    account: "CHATGPT",
    instrument: "SPY",
    direction: "LONG",
    horizon: "2-4 weeks",
    conviction: 2.0,
    thesis_bullets: [
      "Earnings season showing strong corporate profits",
      "Fed signaling potential rate cuts",
      "Technical breakout above 200-day MA"
    ],
    indicators: [
      "RSI: 65 (not overbought)",
      "MACD: Bullish crossover",
      "Volume: Above average"
    ],
    invalidation: "Break below $470 support level",
    status: "complete"
  },
  {
    id: 2,
    model: "gemini-3-pro",
    account: "GEMINI",
    instrument: "TLT",
    direction: "SHORT",
    horizon: "1 week",
    conviction: -1.0,
    thesis_bullets: [
      "Inflation sticky in services",
      "Supply heavy treasury auctions",
      "Technical resistance at 98.50"
    ],
    indicators: [
      "Yield curve steepening",
      "Momentum divergence"
    ],
    invalidation: "Close above 100.00",
    status: "complete"
  },
    {
    id: 3,
    model: "claude-sonnet-4.5",
    account: "CLAUDE",
    instrument: "GLD",
    direction: "FLAT",
    horizon: "N/A",
    conviction: 0.0,
    thesis_bullets: [
      "No clear directional signal",
      "Waiting for CPI data confirmation",
      "Gold consolidating in tight range"
    ],
    indicators: [
      "Low volatility compression",
      "Volume drying up"
    ],
    invalidation: "N/A",
    status: "complete"
  },
  {
    id: 4,
    model: "grok-4.1",
    account: "GROK",
    instrument: "NVDA",
    direction: "LONG",
    horizon: "Intraday",
    conviction: 1.5,
    thesis_bullets: [
        "Breaking out of bull flag",
        "Sector strength",
        "High relative volume"
    ],
    indicators: [
        "Above VWAP",
        "Order flow bullish"
    ],
    invalidation: "Drop below morning low",
    status: "complete"
  },
  {
    id: 5,
    model: "deepseek-v3",
    account: "DEEPSEEK",
    instrument: "BTC",
    direction: "LONG",
    horizon: "Swing",
    conviction: 1.8,
    thesis_bullets: [
        "ETF inflows accelerating",
        "Halving narrative pricing in",
        "Risk-on correlation"
    ],
    indicators: [
        "Hash rate ATH",
        "Exchange reserves low"
    ],
    invalidation: "Regulatory news shock",
    status: "complete"
  }
];

export const mockCouncilDecision = {
  selected_trade: {
    instrument: "SPY",
    direction: "LONG",
    conviction: 1.5,
    position_size: "25%"
  },
  rationale: "Strong consensus across PMs (4/5 bullish). Clear catalyst from earnings season and Fed signals. Technical setup confirms fundamental view.",
  dissent_summary: [
    "Grok 4.1: Concerned about valuation levels",
    "DeepSeek V3: Prefers duration over equities"
  ],
  monitoring_plan: {
    key_levels: ["$470 support", "$485 target"],
    event_risks: ["Jan 15 FOMC", "Jan 28 CPI"]
  },
  peer_review_scores: {
    clarity: 8.2,
    edge_plausibility: 7.5,
    timing: 8.8,
    risk_definition: 7.0
  }
};

export const mockTrades = [
  { id: 101, account: "COUNCIL", symbol: "SPY", direction: "BUY", qty: 50, status: "pending", conviction: 1.5 },
  { id: 102, account: "CHATGPT", symbol: "SPY", direction: "BUY", qty: 40, status: "pending", conviction: 2.0 },
  { id: 103, account: "GEMINI", symbol: "TLT", direction: "SELL", qty: 30, status: "filled", conviction: -1.0 },
];

export const mockPositions = [
  { account: "COUNCIL", symbol: "SPY", qty: 50, avg_price: 475.20, current_price: 482.30, pl: 355 },
  { account: "CHATGPT", symbol: "SPY", qty: 40, avg_price: 475.20, current_price: 482.30, pl: 284 },
  { account: "GEMINI", symbol: "TLT", qty: -30, avg_price: 98.50, current_price: 97.20, pl: 39 },
  { account: "CLAUDE", symbol: "-", qty: 0, avg_price: 0, current_price: 0, pl: 0 },
];

export const mockAccounts = [
  { name: "COUNCIL", equity: 100355, cash: 75920, pl: 355 },
  { name: "CHATGPT", equity: 100284, cash: 80984, pl: 284 },
  { name: "GEMINI", equity: 99961, cash: 70089, pl: 39 },
];

export const mockPerformanceHistory = {
  account: "COUNCIL",
  history: [
    { date: "2025-01-01", equity: 100000, pl: 0 },
    { date: "2025-01-02", equity: 100150, pl: 150 },
    { date: "2025-01-03", equity: 100280, pl: 280 },
    { date: "2025-01-04", equity: 100220, pl: 220 },
    { date: "2025-01-05", equity: 100355, pl: 355 },
  ]
};

export const mockPerformanceComparison = {
  council: {
    account: "COUNCIL",
    total_pl: 355,
    pl_pct: 0.355,
    equity: 100355,
    max_drawdown: -0.06,
    sharpe_ratio: 1.2
  },
  individuals: [
    {
      account: "CHATGPT",
      total_pl: 284,
      pl_pct: 0.284,
      equity: 100284,
      max_drawdown: -0.12,
      sharpe_ratio: 0.9
    },
    {
      account: "GEMINI",
      total_pl: 39,
      pl_pct: 0.039,
      equity: 99961,
      max_drawdown: -0.15,
      sharpe_ratio: 0.3
    },
    {
      account: "CLAUDE",
      total_pl: -120,
      pl_pct: -0.12,
      equity: 99880,
      max_drawdown: -0.18,
      sharpe_ratio: -0.2
    },
    {
      account: "GROK",
      total_pl: 180,
      pl_pct: 0.18,
      equity: 100180,
      max_drawdown: -0.09,
      sharpe_ratio: 0.7
    }
  ],
  avg_individual_pl: 95.75,
  council_advantage: 259.25
};
