"""PM pitch generation stage for trading recommendations."""

import json
import re
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime

from ...requesty_client import query_pm_models, REQUESTY_MODELS
from ...multi_alpaca_client import MultiAlpacaManager
from ..context import PipelineContext, ContextKey
from ..base import Stage
from .research import get_week_id, RESEARCH_PACK_A, RESEARCH_PACK_B
from ..graph_digest import make_digest

#region agent log
def _agent_log(payload: Dict[str, Any]) -> None:
    """Append small NDJSON log for debug session."""
    try:
        payload.setdefault("timestamp", int(time.time() * 1000))
        payload.setdefault("sessionId", "debug-session")
        with open("/research/llm_trading/.cursor/debug.log", "a") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
#endregion


# Context keys for PM pitches
PM_PITCHES = ContextKey("pm_pitches")
MARKET_METRICS = ContextKey("market_metrics")
CURRENT_PRICES = ContextKey("current_prices")


# ========================================
# Risk Profile Constants (v2 Schema)
# ========================================

# Standardized risk profiles (PMs must choose one)
RISK_PROFILES = {
    "TIGHT": {"stop_loss_pct": 0.010, "take_profit_pct": 0.015},
    "BASE":  {"stop_loss_pct": 0.015, "take_profit_pct": 0.025},
    "WIDE":  {"stop_loss_pct": 0.020, "take_profit_pct": 0.035}
}

# Valid entry modes (NONE is only for FLAT, validated separately)
ENTRY_MODES = ["MOO", "limit"]

# Valid event triggers for early exit
EXIT_EVENTS = ["NFP", "CPI", "FOMC"]

# Banned indicator keywords (case-insensitive)
# Banned indicator keywords (case-insensitive)
BANNED_KEYWORDS = [
    "rsi", "macd", "moving average", "moving-average",
    "ema", "sma", "bollinger", "stochastic",
    "fibonacci", "ichimoku", "adx", "atr"
]


class IndicatorError(Exception):
    """Raised when a pitch contains banned technical indicators."""
    def __init__(self, keyword: str):
        super().__init__(f"Indicator banned: {keyword}")
        self.keyword = keyword


class PMPitchStage(Stage):
    """
    PM pitch generation stage that creates trading recommendations from all PM models.
    
    This stage:
    1. Receives research packs from Research stage
    2. Queries all 5 PM models in parallel
    3. Each PM generates a structured trading recommendation
    4. Returns all pitches for peer review stage
    """
    
    # Tradable universe
    INSTRUMENTS = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]
    
    # Conviction scale
    CONVICTION_MIN = -2
    CONVICTION_MAX = 2
    
    @property
    def name(self) -> str:
        return "PMPitchStage"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute PM pitch generation stage.
        
        Args:
            context: Pipeline context with research data
            
        Returns:
            New context with PM pitches added
        """
        print("\n" + "=" * 60)
        print("📈 PM PITCH STAGE")
        print("=" * 60)
        
        # Get research packs from context
        research_pack_a = context.get(RESEARCH_PACK_A)
        research_pack_b = context.get(RESEARCH_PACK_B)
        
        # Handle single research pack (Perplexity-only mode)
        if not research_pack_a and not research_pack_b:
            print("  ❌ Error: No research packs found in context")
            print("  ⚠️  Running with placeholder research data")
            research_pack_a = self._placeholder_research_pack()
            research_pack_b = self._placeholder_research_pack()
        elif not research_pack_b:
            print("  ℹ️  Using single research pack (Perplexity-only mode)")
            research_pack_b = research_pack_a  # Use same pack for both if only one provided
        
        # Get market metrics and prices from context
        market_metrics = context.get(MARKET_METRICS)
        current_prices = context.get(CURRENT_PRICES)
        
        if not market_metrics:
            print("  ⚠️  Warning: Market metrics not found in context")
        if not current_prices:
            print("  ⚠️  Warning: Current prices not found in context")
        
        # Get target models if specified
        target_models = context.get("target_models")

        # Generate pitches from all PM models
        print(f"\n🎯 Generating PM pitches from {len(target_models) if target_models else 'all'} models...")
        pm_pitches = await self._generate_pm_pitches(
            research_pack_a,
            research_pack_b,
            market_metrics,
            current_prices,
            target_models=target_models
        )
        
        print(f"  ✅ Generated {len(pm_pitches)} PM pitches")
        
        # Return context with PM pitches
        return context.set(PM_PITCHES, pm_pitches)
    
    async def _generate_pm_pitches(
        self,
        research_pack_a: Dict[str, Any],
        research_pack_b: Dict[str, Any],
        market_metrics: Dict[str, Any] | None = None,
        current_prices: Dict[str, Any] | None = None,
        target_models: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Generate PM pitches from all models in parallel.
        
        Args:
            research_pack_a: Primary research pack
            research_pack_b: Alternative research pack
            market_metrics: Market metrics (7-day returns, correlation matrix)
            current_prices: Current prices and volumes
            target_models: Optional list of models to run
            
        Returns:
            List of PM pitch dicts
        """
        # Build prompt for each PM model
        prompt = self._build_pm_prompt(research_pack_a, research_pack_b, market_metrics, current_prices)
        
        messages = [
            {
                "role": "system",
                "content": """You are a macro/fundamental portfolio manager for a quantitative trading system.

You MUST produce a 1-week trade pitch using ONLY macro regime, policy, economic data, fundamentals, and cross-asset narratives.
DO NOT use or mention technical analysis, charts, indicators, levels, patterns, "support/resistance", or any TA terminology — even to deny it.
If you cannot comply, output FLAT with conviction 0.

Rules:
1. Pick ONE instrument from the tradable universe
2. Choose direction: LONG, SHORT, or FLAT
3. Set horizon to "1W" exactly
4. Provide 3-5 thesis bullets (max 5) - each MUST start with one prefix: "Rates:", "USD:", "Inflation:", "Growth:", "Policy:", "Cross-asset:", "Catalyst:", "Positioning:", or "Risk:"
5. Set conviction score from -2 to +2
6. Define clear risk notes (macro/fundamental only)
7. Be specific and actionable

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no comments. 
- Do NOT use trailing commas
- Do NOT add // comments
- Ensure all strings are properly quoted
- Ensure all JSON syntax is correct

Return as valid JSON only."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Query all PM models in parallel
        responses = await query_pm_models(messages, model_keys=target_models)
        
        # Parse and validate pitches
        pm_pitches = []
        for model_key, response in responses.items():
            #region agent log
            _agent_log({
                "runId": "post-fix",
                "hypothesisId": "H1",
                "location": "pm_pitch:_generate_pm_pitches",
                "message": "Model response received",
                "data": {
                    "model": model_key,
                    "has_response": response is not None,
                    "content_len": len(response.get("content", "")) if response else 0
                }
            })
            #endregion
            if response is not None:
                pitch = None
                try:
                    pitch = self._parse_pm_pitch(response["content"], model_key)
                except IndicatorError as ie:
                    #region agent log
                    _agent_log({
                        "runId": "post-fix",
                        "hypothesisId": "H2",
                        "location": "pm_pitch:_generate_pm_pitches:retry",
                        "message": "Retrying model due to indicator ban",
                        "data": {"model": model_key, "keyword": ie.keyword}
                    })
                    #endregion
                    # Retry once with a corrective prompt
                    retry_messages = [
                        {
                            "role": "system",
                            "content": """Your previous pitch was REJECTED for mentioning technical indicators.
You MUST output a FLAT trade with conviction 0 and macro-only thesis bullets.
Return EXACTLY this JSON structure (replace week_id and asof_et with current values):
{
  "idea_id": "uuid",
  "week_id": "YYYY-MM-DD",
  "asof_et": "ISO8601-ET",
  "pm_model": "your_model_name",
  "selected_instrument": "FLAT",
  "direction": "FLAT",
  "horizon": "1W",
  "conviction": 0,
  "risk_profile": "BASE",
  "thesis_bullets": [
    "Policy: Insufficient macro clarity for directional trade",
    "Risk: Market conditions require neutral stance"
  ],
  "entry_policy": {"mode": "MOO", "limit_price": null},
  "exit_policy": {"time_stop_days": 7, "stop_loss_pct": 0.015, "take_profit_pct": 0.025, "exit_before_events": []},
  "consensus_map": {"research_pack_a": "neutral", "research_pack_b": "neutral"},
  "risk_notes": "Macro uncertainty requires neutral positioning",
  "compliance_check": {"macro_only": true, "no_ta_language": true},
  "timestamp": "ISO8601"
}
Return ONLY this JSON, no other text."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                    retry_resp = await query_pm_models(retry_messages, model_keys=[model_key])
                    retry_content = retry_resp.get(model_key, {}).get("content") if retry_resp else None
                    if retry_content:
                        try:
                            pitch = self._parse_pm_pitch(retry_content, model_key)
                        except IndicatorError as ie2:
                            #region agent log
                            _agent_log({
                                "runId": "post-fix",
                                "hypothesisId": "H2",
                                "location": "pm_pitch:_generate_pm_pitches:retry_failed",
                                "message": "Retry still contains indicators, generating FLAT fallback",
                                "data": {"model": model_key, "keyword": ie2.keyword}
                            })
                            #endregion
                            # Generate FLAT fallback pitch
                            week_id = get_week_id()
                            from datetime import datetime, timezone, timedelta
                            et_tz = timezone(timedelta(hours=-5))
                            asof_et = datetime.now(et_tz).isoformat()
                            pitch = {
                                "idea_id": str(uuid.uuid4()),
                                "week_id": week_id,
                                "asof_et": asof_et,
                                "pm_model": model_key,
                                "selected_instrument": "FLAT",
                                "direction": "FLAT",
                                "horizon": "1W",
                                "conviction": 0,
                                "risk_profile": None,  # FLAT trades don't need risk profiles
                                "thesis_bullets": [
                                    "Policy: Insufficient macro clarity for directional trade",
                                    "Risk: Market conditions require neutral stance"
                                ],
                                "entry_policy": {"mode": "NONE", "limit_price": None},  # FLAT uses NONE, not MOO
                                "exit_policy": None,  # FLAT trades don't need exit policies
                                "consensus_map": {"research_pack_a": "neutral", "research_pack_b": "neutral"},
                                "risk_notes": "Macro uncertainty requires neutral positioning",
                                "compliance_check": {"macro_only": True, "no_ta_language": True},
                                "timestamp": datetime.utcnow().isoformat(),
                                "model": model_key,
                                "model_info": REQUESTY_MODELS[model_key]
                            }
                        except Exception as e2:
                            #region agent log
                            _agent_log({
                                "runId": "post-fix",
                                "hypothesisId": "H2",
                                "location": "pm_pitch:_generate_pm_pitches:retry_parse_error",
                                "message": "Retry parse failed",
                                "data": {"model": model_key, "error": str(e2)}
                            })
                            #endregion
                            pitch = None
                    else:
                        pitch = None
                except Exception as e:
                    #region agent log
                    _agent_log({
                        "runId": "post-fix",
                        "hypothesisId": "H2",
                        "location": "pm_pitch:_generate_pm_pitches:parse_error",
                        "message": "Parse failed",
                        "data": {"model": model_key, "error": str(e)}
                    })
                    #endregion
                    pitch = None

                if pitch:
                    pm_pitches.append(pitch)
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n✅ {model_info['account']} ({model_key.upper()})")
                    print(f"   Instrument: {pitch['selected_instrument']} | Direction: {pitch['direction']}")
                    print(f"   Conviction: {pitch['conviction']} | Horizon: {pitch['horizon']}")
                else:
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n❌ {model_info['account']} ({model_key.upper()}) - Failed to parse pitch")
        
        return pm_pitches
    
    def _build_pm_prompt(
        self,
        research_pack_a: Dict[str, Any],
        research_pack_b: Dict[str, Any],
        market_metrics: Dict[str, Any] | None = None,
        current_prices: Dict[str, Any] | None = None
    ) -> str:
        """Build prompt for PM pitch generation."""
        week_id = get_week_id()
        
        # Format research packs for prompt
        research_text_a = self._format_research_pack(research_pack_a, "Perplexity Research")
        # research_text_b = self._format_research_pack(research_pack_b, "Research Pack B")  # Not used in single-pack mode
        
        # Format market metrics
        market_metrics_text = ""
        if market_metrics:
            market_metrics_text = self._format_market_metrics(market_metrics)
        
        # Format current prices
        current_prices_text = ""
        if current_prices:
            current_prices_text = self._format_current_prices(current_prices)
        
        # Format knowledge graph digest if available
        graph_digest_text = ""
        weekly_graph_a = research_pack_a.get("weekly_graph")
        weekly_graph_b = research_pack_b.get("weekly_graph")
        
        # Prefer research pack A's graph, fallback to B
        weekly_graph = weekly_graph_a or weekly_graph_b
        
        if weekly_graph:
            try:
                digest = make_digest(weekly_graph)
                graph_digest_text = self._format_graph_digest(digest)
            except Exception as e:
                print(f"  ⚠️ Failed to generate graph digest: {e}")
        
        prompt = f"""Generate a trading recommendation for week {week_id}.

THIS IS A MACRO/FUNDAMENTAL-ONLY TRADING SYSTEM.
Base your thesis ONLY on macro regime, policy, economic data, fundamentals, and cross-asset narratives.
Do not use or mention technical analysis, charts, indicators, or TA terminology.

RESEARCH PACK (Perplexity Sonar Deep Research):
{research_text_a}

{market_metrics_text}

{current_prices_text}

{graph_digest_text}

TRADABLE UNIVERSE:
- SPY: S&P 500 ETF
- QQQ: Nasdaq 100 ETF
- IWM: Russell 2000 ETF
- TLT: 20+ Year Treasury Bond ETF
- HYG: High Yield Corporate Bond ETF
- UUP: US Dollar Index ETF
- GLD: Gold ETF
- USO: Oil ETF
- VIXY: VIX Short-Term ETF
- SH: ProShares Short S&P 500 ETF

TASK: Generate a single trading recommendation as valid JSON with the following structure:

Thesis bullet rules:
- 3-5 bullets max
- Each bullet MUST start with one prefix: "Rates:", "USD:", "Inflation:", "Growth:", "Policy:", "Cross-asset:", "Catalyst:", "Positioning:", or "Risk:"
- Do not reference charts/technicals in any way

{{
  "idea_id": "uuid",
  "week_id": "{week_id}",
  "asof_et": "2026-01-02T16:00:00-05:00",
  "pm_model": "your_model_name",
  "selected_instrument": "SPY",
  "direction": "LONG",
  "horizon": "1W",
  "conviction": 1.5,
  "risk_profile": "BASE",
  "thesis_bullets": [
    "Rates: Fed policy stance supports risk assets",
    "USD: Dollar weakness benefits exporters",
    "Policy: Fiscal stimulus expectations"
  ],
  "entry_policy": {{
    "mode": "MOO",
    "limit_price": null
  }},
  "exit_policy": {{
    "time_stop_days": 7,
    "stop_loss_pct": 0.015,
    "take_profit_pct": 0.025,
    "exit_before_events": ["NFP"]
  }},
  "risk_notes": "Key risks to monitor...",
  "timestamp": "ISO8601"
}}

For FLAT trades, use this structure instead:
{{
  "idea_id": "uuid",
  "week_id": "{week_id}",
  "asof_et": "2026-01-02T16:00:00-05:00",
  "pm_model": "your_model_name",
  "selected_instrument": "FLAT",
  "direction": "FLAT",
  "horizon": "1W",
  "conviction": 0,
  "risk_profile": null,
  "thesis_bullets": [
    "Policy: Insufficient macro clarity for directional trade",
    "Risk: Market conditions require neutral stance"
  ],
  "entry_policy": {{
    "mode": "NONE",
    "limit_price": null
  }},
  "exit_policy": null,
  "consensus_map": {{
    "research_pack_a": "agree",
    "research_pack_b": "agree"
  }},
  "risk_notes": "Key risks to monitor...",
  "compliance_check": {{
    "macro_only": true,
    "no_ta_language": true
  }},
  "timestamp": "ISO8601"
}}

IMPORTANT RULES:

REQUIRED FIELDS:
- Use "pm_model" field with your model name
- Use "selected_instrument" for the ticker (one of the 10 instruments above)
- Set "horizon" to "1W" exactly (only 1W is supported in v1)
- Include "asof_et" with current timestamp in ET timezone (ISO8601 format with -05:00 offset)
- For LONG or SHORT trades:
  * Set "risk_profile" to one of: TIGHT | BASE | WIDE
    - TIGHT: 1.0% stop / 1.5% take-profit (tight risk for choppy markets)
    - BASE:  1.5% stop / 2.5% take-profit (balanced risk for normal conditions)
    - WIDE:  2.0% stop / 3.5% take-profit (wide risk for trending markets)
  * Define "exit_policy":
    - time_stop_days: Always 7 (close position after 7 days)
    - stop_loss_pct: Must match risk_profile (0.010 | 0.015 | 0.020)
    - take_profit_pct: Must match risk_profile (0.015 | 0.025 | 0.035)
    - exit_before_events: Optional array ["NFP", "CPI", "FOMC"]
- For FLAT trades:
  * Set "risk_profile": null (or omit it)
  * Set "exit_policy": null (or omit it)
  * Set "entry_policy": {{"mode": "NONE", "limit_price": null}}
  * Do NOT include stop_loss_pct, take_profit_pct, or time_stop_days
- Define "entry_policy":
  * mode: "MOO" (market-on-open) or "limit"
  * limit_price: Required if mode is "limit", otherwise null
- Use "risk_notes" (not "invalidation_rule") to describe primary risks for the week
- Direction options: LONG | SHORT | FLAT
- Conviction range: -2 to +2 (negative for SHORT, positive for LONG, 0 for FLAT)
- Maximum 5 thesis bullets
- Consider both research packs

VALIDATION RULES:
- Risk profile must exactly match one of the three standardized profiles (TIGHT/BASE/WIDE)
- All percentages in exit_policy must match the chosen risk_profile
- Do NOT include position sizing hints - sizing is handled separately
- compliance_check field is optional but recommended

JSON FORMATTING REQUIREMENTS:
- NO trailing commas (e.g., do not write {{"a": 1,}})
- NO comments (e.g., do not write // comment)
- NO markdown code blocks (do not wrap in ```json```)
- Return ONLY the raw JSON object starting with {{ and ending with }}
- All strings must be properly quoted
- All nested objects and arrays must be properly closed

Return as valid JSON only, no markdown formatting."""
        
        return prompt
    
    def _format_research_pack(
        self,
        research_pack: Dict[str, Any],
        label: str
    ) -> str:
        """Format research pack for prompt."""
        lines = [f"### {label}"]
        
        # Macro regime
        regime = research_pack.get("macro_regime", {})
        risk_mode = regime.get("risk_mode", "Unknown")
        lines.append(f"**Macro Regime:** {risk_mode}")
        lines.append(f"  Rates: {regime.get('rates_impulse', 'Unknown')}")
        lines.append(f"  USD: {regime.get('usd_impulse', 'Unknown')}")
        lines.append(f"  Inflation: {regime.get('inflation_impulse', 'Unknown')}")
        lines.append(f"  Growth: {regime.get('growth_impulse', 'Unknown')}")
        
        # Top narratives
        narratives = research_pack.get("top_narratives", [])
        if narratives:
            lines.append("\n**Top Narratives:**")
            for i, narrative in enumerate(narratives[:3], 1):
                lines.append(f"{i}. {narrative.get('name', 'Unknown')}")
                lines.append(f"   Why it moves prices: {narrative.get('why_it_moves_prices_this_week', '')}")
                lines.append(f"   Key catalysts: {narrative.get('key_catalysts_next_7d', [])}")
        
        # Consensus map
        consensus = research_pack.get("consensus_map", {})
        lines.append("\n**Consensus Map:**")
        lines.append(f"  Street consensus: {consensus.get('street_consensus', 'Unknown')}")
        lines.append(f"  Positioning: {consensus.get('positioning_guess', 'Unknown')}")
        lines.append(f"  Priced for: {consensus.get('what_market_is_priced_for', 'Unknown')}")
        lines.append(f"  Surprise would be: {consensus.get('what_would_surprise', 'Unknown')}")
        
        # Tradable candidates
        candidates = research_pack.get("tradable_candidates", [])
        if candidates:
            lines.append("\n**Tradable Candidates:**")
            for candidate in candidates[:5]:
                lines.append(f"- {candidate.get('instrument', 'Unknown')}: {candidate.get('directional_bias', 'Unknown')}")
                lines.append(f"  Thesis: {candidate.get('one_week_thesis', '')}")
        
        return "\n".join(lines)
    
    def _format_market_metrics(self, market_metrics: Dict[str, Any]) -> str:
        """Format market metrics for prompt."""
        lines = ["MARKET METRICS:"]
        
        # 7-day returns
        returns_7d = market_metrics.get("returns_7d", [])
        if returns_7d:
            lines.append("\n**7-Day Returns:**")
            for item in returns_7d:
                symbol = item.get("symbol", "Unknown")
                pct_return = item.get("pct_return", 0)
                lines.append(f"  {symbol}: {pct_return:+.2f}%")
        
        # Correlation matrix (show key correlations)
        correlation_matrix = market_metrics.get("correlation_matrix", {})
        if correlation_matrix:
            lines.append("\n**Key Correlations (30-day):**")
            # Show correlation between major pairs
            key_pairs = [
                ("SPY", "QQQ"),
                ("SPY", "TLT"),
                ("GLD", "TLT"),
                ("USO", "SPY")
            ]
            for sym1, sym2 in key_pairs:
                if sym1 in correlation_matrix and sym2 in correlation_matrix[sym1]:
                    corr = correlation_matrix[sym1][sym2]
                    lines.append(f"  {sym1} vs {sym2}: {corr:+.3f}")
        
        date = market_metrics.get("date", "Unknown")
        lines.append(f"\n**As of:** {date}")
        
        return "\n".join(lines)
    
    def _format_current_prices(self, current_prices: Dict[str, Any]) -> str:
        """Format current prices for prompt."""
        lines = ["CURRENT PRICES & VOLUMES:"]
        
        prices = current_prices.get("prices", [])
        if prices:
            lines.append("")
            for item in prices:
                symbol = item.get("symbol", "Unknown")
                close = item.get("close", 0)
                volume = item.get("volume", 0)
                lines.append(f"  {symbol}: ${close:.2f} | Volume: {volume:,}")
        
        asof_date = current_prices.get("asof_date", "Unknown")
        lines.append(f"\n**As of:** {asof_date}")
        
        return "\n".join(lines)
    
    def _format_graph_digest(self, digest: Dict[str, Any]) -> str:
        """Format knowledge graph digest for prompt."""
        lines = ["=== KNOWLEDGE GRAPH DIGEST ==="]
        lines.append("")
        
        # Add summary notes
        notes = digest.get("notes", [])
        if notes:
            for note in notes:
                lines.append(f"📊 {note}")
            lines.append("")
        
        # Format top market edges
        top_edges = digest.get("top_edges", [])
        if top_edges:
            lines.append("TOP MARKET EDGES:")
            lines.append("")
            
            for i, edge in enumerate(top_edges, 1):
                source_type = edge.get("source_type", "")
                source_label = edge.get("source_label", "")
                relation = edge.get("relation", "")
                target_type = edge.get("target_type", "")
                target_label = edge.get("target_label", "")
                sign = edge.get("sign", "0")
                strength = edge.get("strength", 0)
                confidence = edge.get("confidence", 0)
                impact_score = edge.get("impact_score", 0)
                evidence = edge.get("evidence", [])
                condition = edge.get("condition", "")
                
                # Format sign indicator
                sign_indicator = {"+" : "↑", "-": "↓", "0": "•"}[sign]
                
                lines.append(f"{i}. [{source_type}] {source_label} → {relation} → [{target_type}] {target_label}")
                lines.append(f"   Impact: {impact_score:.3f} (Strength: {strength:.2f}, Confidence: {confidence:.2f}, Sign: {sign} {sign_indicator})")
                
                if condition:
                    lines.append(f"   Condition: {condition}")
                
                if evidence:
                    lines.append(f"   Evidence: \"{evidence[0]}\"")
                
                lines.append("")
        
        # Format asset context summaries
        asset_subgraphs = digest.get("asset_subgraphs", {})
        
        # Filter to assets with meaningful drivers
        assets_with_drivers = {
            ticker: subgraph 
            for ticker, subgraph in asset_subgraphs.items()
            if subgraph.get("direct_drivers") or subgraph.get("setup_signals")
        }
        
        if assets_with_drivers:
            lines.append("ASSET CONTEXT:")
            lines.append("")
            
            # Sort assets by strength score descending
            sorted_assets = sorted(
                assets_with_drivers.items(),
                key=lambda x: x[1].get("strength_score", 0),
                reverse=True
            )
            
            for ticker, subgraph in sorted_assets:
                direct_drivers = subgraph.get("direct_drivers", [])
                setup_signals = subgraph.get("setup_signals", [])
                strength_score = subgraph.get("strength_score", 0)
                strongest_evidence = subgraph.get("strongest_evidence", "")
                
                lines.append(f"• {ticker} (Strength Score: {strength_score:.3f})")
                
                # Show direct drivers
                if direct_drivers:
                    lines.append("  Direct Drivers:")
                    for driver in direct_drivers:
                        label = driver.get("label", "")
                        sign = driver.get("sign", "0")
                        impact = driver.get("impact_score", 0)
                        condition = driver.get("condition", "")
                        
                        sign_indicator = {"+" : "↑", "-": "↓", "0": "•"}[sign]
                        
                        driver_line = f"    - {label} {sign_indicator} (Impact: {impact:.3f})"
                        if condition:
                            driver_line += f" [Condition: {condition}]"
                        lines.append(driver_line)
                
                # Show setup signals
                if setup_signals:
                    lines.append("  Setup Signals:")
                    for signal in setup_signals:
                        label = signal.get("label", "")
                        impact = signal.get("impact_score", 0)
                        lines.append(f"    - {label} (Impact: {impact:.3f})")
                
                # Show strongest evidence
                if strongest_evidence:
                    lines.append(f"  Key Evidence: \"{strongest_evidence}\"")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _recursive_scan_strings(self, obj: Any, text_collector: List[str]) -> None:
        """Recursively scan all string fields in a nested structure."""
        if isinstance(obj, str):
            text_collector.append(obj.lower())
        elif isinstance(obj, dict):
            for value in obj.values():
                self._recursive_scan_strings(value, text_collector)
        elif isinstance(obj, list):
            for item in obj:
                self._recursive_scan_strings(item, text_collector)
    
    def _validate_no_indicators(self, pitch: Dict[str, Any]) -> None:
        """Reject pitches that mention technical indicators. Scans all string fields recursively."""
        text_to_scan = []
        self._recursive_scan_strings(pitch, text_to_scan)
        
        combined_text = " ".join(text_to_scan)
        
        for keyword in BANNED_KEYWORDS:
            if keyword in combined_text:
                raise IndicatorError(keyword)
    
    def _parse_pm_pitch(
        self,
        content: str,
        model_key: str
    ) -> Dict[str, Any] | None:
        """
        Parse PM pitch from LLM response with robust JSON repair.
        
        Args:
            content: LLM response content
            model_key: Model identifier
            
        Returns:
            Parsed pitch dict or None if invalid
        """
        #region agent log
        _agent_log({
                "runId": "post-fix",
            "hypothesisId": "H2",
            "location": "pm_pitch:_parse_pm_pitch:entry",
            "message": "Parsing pitch",
            "data": {
                "model": model_key,
                "content_len": len(content or "")
            }
        })
        #endregion
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if not json_match:
            #region agent log
            _agent_log({
                "runId": "post-fix",
                "hypothesisId": "H2",
                "location": "pm_pitch:_parse_pm_pitch:no_json",
                "message": "No JSON found in response",
                "data": {
                    "model": model_key,
                    "preview": (content or "")[:160]
                }
            })
            #endregion
            print(f"  ⚠️  No JSON found in response from {model_key}")
            print(f"  📄 Raw content preview: {content[:200]}...")
            return None
        
        json_str = json_match.group(0)
        
        # Try parsing, with repair attempts if needed
        pitch = None
        parse_attempts = [
            ("original", json_str),
            ("remove_comments", re.sub(r'//.*?\n', '\n', json_str)),  # Remove // comments
            ("fix_trailing_commas", re.sub(r',(\s*[}\]])', r'\1', json_str)),  # Remove trailing commas
            ("fix_both", re.sub(r',(\s*[}\]])', r'\1', re.sub(r'//.*?\n', '\n', json_str)))
        ]
        
        for attempt_name, attempt_str in parse_attempts:
            try:
                pitch = json.loads(attempt_str)
                if attempt_name != "original":
                    print(f"  ✓ Parsed JSON from {model_key} after repair: {attempt_name}")
                else:
                    print(f"  ✓ Successfully parsed JSON from {model_key}")
                print(f"  📋 Fields present: {list(pitch.keys())}")
                break
            except json.JSONDecodeError as e:
                if attempt_name == parse_attempts[-1][0]:  # Last attempt
                    print(f"  ⚠️  JSON decode error after all repair attempts: {e}")
                    print(f"  📄 Attempted to parse: {attempt_str[:500]}...")
                    return None
                continue
        
        if not pitch:
            return None
        
        # Validate no technical indicators
        try:
            self._validate_no_indicators(pitch)
        except IndicatorError as e:
            #region agent log
            _agent_log({
                "runId": "post-fix",
                "hypothesisId": "H2",
                "location": "pm_pitch:_parse_pm_pitch:indicator_ban",
                "message": "Banned indicator detected",
                "data": {
                    "model": model_key,
                    "error": str(e),
                    "keyword": e.keyword
                }
            })
            #endregion
            print(f"  {str(e)}")
            raise
            
        # Validate direction first (needed for FLAT checks)
        direction = pitch.get("direction")
        if direction not in ["LONG", "SHORT", "FLAT"]:
            print(f"  ⚠️  Invalid direction: {direction}")
            return None
        
        # Validate required fields (v2 schema)
        required_fields = [
            "week_id", "asof_et", "pm_model", "selected_instrument",
            "direction", "conviction", "horizon", "thesis_bullets",
            "entry_policy", "risk_notes"
        ]
        
        # For LONG/SHORT, risk_profile and exit_policy are required
        # For FLAT, they are optional
        if direction != "FLAT":
            required_fields.extend(["risk_profile", "exit_policy"])
        
        missing_fields = [f for f in required_fields if f not in pitch]
        if missing_fields:
            #region agent log
            _agent_log({
                "runId": "post-fix",
                "hypothesisId": "H2",
                "location": "pm_pitch:_parse_pm_pitch:missing_fields",
                "message": "Pitch missing required fields",
                "data": {
                    "model": model_key,
                    "missing": missing_fields,
                    "present": list(pitch.keys())
                }
            })
            #endregion
            print(f"  ⚠️  Missing required fields: {', '.join(missing_fields)}")
            print(f"  ℹ️  Fields present: {', '.join(pitch.keys())}")
            return None
        
        # Validate entry_policy structure
        entry_policy = pitch.get("entry_policy", {})
        if "mode" not in entry_policy:
            raise ValueError("entry_policy missing required field: mode")
        # For FLAT, mode must be "NONE", for LONG/SHORT it must be in ENTRY_MODES
        if direction == "FLAT":
            if entry_policy["mode"] not in ["NONE", None]:
                raise ValueError(f"FLAT trades must have entry_policy.mode='NONE' (got: {entry_policy['mode']})")
        else:
            if entry_policy["mode"] not in ENTRY_MODES:
                raise ValueError(f"Invalid entry_policy.mode: {entry_policy['mode']}")
        
        # For FLAT trades, REJECT if they have risk profiles or exit policies
        if direction == "FLAT":
            # FLAT trades must NOT have risk profiles or exit policies
            if pitch.get("risk_profile") not in [None, "NONE"]:
                raise ValueError(f"FLAT trades must not have risk_profile (got: {pitch.get('risk_profile')})")
            if pitch.get("exit_policy") not in [None, {}]:
                exit_policy = pitch.get("exit_policy", {})
                if exit_policy and (exit_policy.get("stop_loss_pct") or exit_policy.get("take_profit_pct") or exit_policy.get("time_stop_days")):
                    raise ValueError(f"FLAT trades must not have exit_policy with stop_loss/take_profit/time_stop")
            # FLAT entry_policy should be NONE or omitted
            if entry_policy.get("mode") not in ["NONE", None]:
                raise ValueError(f"FLAT trades must have entry_policy.mode='NONE' (got: {entry_policy.get('mode')})")
        else:
            # For LONG/SHORT, risk_profile and exit_policy are required
            if pitch.get("risk_profile") not in ["TIGHT", "BASE", "WIDE"]:
                raise ValueError(f"Invalid risk_profile: {pitch.get('risk_profile')}")
            
            # Validate exit_policy structure
            exit_policy = pitch.get("exit_policy", {})
            required_exit_fields = ["time_stop_days", "stop_loss_pct"]
            for field in required_exit_fields:
                if field not in exit_policy:
                    raise ValueError(f"exit_policy missing required field: {field}")
            
            # Validate risk profile consistency
            risk_profile = pitch["risk_profile"]
            expected_stops = RISK_PROFILES[risk_profile]
            actual_stop = exit_policy.get("stop_loss_pct")
            if abs(actual_stop - expected_stops["stop_loss_pct"]) > 0.0001:
                raise ValueError(
                    f"exit_policy.stop_loss_pct ({actual_stop}) does not match "
                    f"risk_profile {risk_profile} ({expected_stops['stop_loss_pct']})"
                )
            # Validate take_profit_pct matches risk_profile
            actual_tp = exit_policy.get("take_profit_pct")
            if actual_tp is not None:
                expected_tp = expected_stops["take_profit_pct"]
                if abs(actual_tp - expected_tp) > 0.0001:
                    raise ValueError(
                        f"exit_policy.take_profit_pct ({actual_tp}) does not match "
                        f"risk_profile {risk_profile} ({expected_tp})"
                    )
        
        # Validate selected_instrument (allow FLAT)
        valid_instruments = self.INSTRUMENTS + ["FLAT"]
        if pitch["selected_instrument"] not in valid_instruments:
            print(f"  ⚠️  Invalid selected_instrument: {pitch['selected_instrument']}")
            return None
        
        # Direction already validated above
        
        # Validate horizon (v1 only supports 1W)
        if pitch["horizon"] != "1W":
            print(f"  ⚠️  Invalid horizon: {pitch['horizon']} (v1 only supports 1W)")
            return None
        
        # Validate conviction
        conviction = pitch.get("conviction", 0)
        if not isinstance(conviction, (int, float)):
            print(f"  ⚠️  Invalid conviction type: {type(conviction)}")
            return None
        
        if conviction < self.CONVICTION_MIN or conviction > self.CONVICTION_MAX:
            print(f"  ⚠️  Conviction out of range: {conviction} (must be -2 to +2)")
            return None
        
        # Validate conviction matches direction
        if pitch["direction"] == "FLAT" and conviction != 0:
            print(f"  ⚠️  FLAT direction must have conviction=0, got {conviction}")
            return None
        
        if pitch["direction"] == "LONG" and conviction <= 0:
            print(f"  ⚠️  LONG direction must have positive conviction, got {conviction}")
            return None
        
        if pitch["direction"] == "SHORT" and conviction >= 0:
            print(f"  ⚠️  SHORT direction must have negative conviction, got {conviction}")
            return None
        
        # Add metadata
        pitch["model"] = model_key
        pitch["model_info"] = REQUESTY_MODELS[model_key]
        pitch["timestamp"] = datetime.utcnow().isoformat()
        
        #region agent log
        _agent_log({
            "runId": "post-fix",
            "hypothesisId": "H2",
            "location": "pm_pitch:_parse_pm_pitch:success",
            "message": "Pitch parsed successfully",
            "data": {
                "model": model_key,
                "fields": list(pitch.keys())
            }
        })
        #endregion
        return pitch
    
    def _placeholder_research_pack(self) -> Dict[str, Any]:
        """Return placeholder research pack for testing."""
        return {
            "macro_regime": {
                "risk_mode": "neutral",
                "rates_impulse": "neutral",
                "usd_impulse": "neutral",
                "inflation_impulse": "neutral",
                "growth_impulse": "neutral"
            },
            "top_narratives": [
                {
                    "name": "Market uncertainty",
                    "why_it_moves_prices_this_week": "Awaiting economic data and Fed signals",
                    "key_catalysts_next_7d": ["FOMC minutes", "NFP report"],
                    "what_would_falsify_it": "Stronger than expected economic data"
                }
            ],
            "consensus_map": {
                "street_consensus": "Cautiously optimistic",
                "positioning_guess": "Moderately long equities",
                "what_market_is_priced_for": "Soft landing scenario",
                "what_would_surprise": "Hard landing or recession"
            },
            "tradable_candidates": [
                {
                    "instrument": "SPY",
                    "directional_bias": "NEUTRAL",
                    "one_week_thesis": "Awaiting Fed policy signals and economic data releases",
                    "primary_risks": "Policy uncertainty, geopolitical tensions",
                    "key_catalysts": ["FOMC minutes", "NFP report"]
                },
                {
                    "instrument": "TLT",
                    "directional_bias": "LONG",
                    "one_week_thesis": "Yields attractive relative to equity risk premiums given macro regime",
                    "primary_risks": "Fed rate hike expectations, inflation data surprises",
                    "key_catalysts": ["Fed policy signals", "Inflation data"]
                }
            ],
            "event_calendar_next_7d": [
                {"date": "2025-01-03", "event": "FOMC Minutes", "impact": "High"},
                {"date": "2025-01-07", "event": "NFP Report", "impact": "High"}
            ],
            "confidence_notes": {
                "known_unknowns": ["Fed policy path", "Geopolitical risks"],
                "data_quality_flags": ["placeholder_data"]
            }
        }
