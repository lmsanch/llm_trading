"""PM pitch generation stage for trading recommendations."""

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from ...requesty_client import query_pm_models, REQUESTY_MODELS
from ...multi_alpaca_client import MultiAlpacaManager
from ..context import PipelineContext, ContextKey
from ..base import Stage
from .research import get_week_id, RESEARCH_PACK_A, RESEARCH_PACK_B
from ..graph_digest import make_digest


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

# Valid entry modes
ENTRY_MODES = ["MOO", "limit"]

# Valid event triggers for early exit
EXIT_EVENTS = ["NFP", "CPI", "FOMC"]

# Banned indicator keywords (case-insensitive)
BANNED_KEYWORDS = [
    "rsi", "macd", "moving average", "moving-average",
    "ema", "sma", "bollinger", "stochastic",
    "fibonacci", "ichimoku", "adx", "atr"
]


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
                "content": """You are an expert portfolio manager for a quantitative trading system. Your task is to generate a single, well-reasoned trading recommendation based on research analysis.

Rules:
1. Pick ONE instrument from the tradable universe
2. Choose direction: LONG, SHORT, or FLAT
3. Set horizon to "1W" exactly
4. Provide 3-5 thesis bullets (max 5)
5. Include frozen indicators with thresholds
6. Set conviction score from -2 to +2
7. Define clear invalidation rule
8. Be specific and actionable

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
            if response is not None:
                pitch = self._parse_pm_pitch(response["content"], model_key)
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
        
        prompt = f"""You are a portfolio manager for a quantitative trading system. Generate a trading recommendation for week {week_id}.

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
    "First reason...",
    "Second reason...",
    "Third reason..."
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
  "consensus_map": {{
    "research_pack_a": "agree",
    "research_pack_b": "agree"
  }},
  "risk_notes": "Key risks to monitor...",
  "timestamp": "ISO8601"
}}

IMPORTANT RULES:
- Use "pm_model" field with your model name
- Use "selected_instrument" for the ticker (one of the 10 instruments above)
- Set "horizon" to "1W" exactly (only 1W is supported in v1)
- Include "asof_et" with current timestamp in ET timezone (ISO8601 format with -05:00 offset)
- Set "risk_profile" to one of: TIGHT | BASE | WIDE
  * TIGHT: 1.0% stop / 1.5% take-profit (tight risk for choppy markets)
  * BASE:  1.5% stop / 2.5% take-profit (balanced risk for normal conditions)
  * WIDE:  2.0% stop / 3.5% take-profit (wide risk for trending markets)
- Define "entry_policy":
  * mode: "MOO" (market-on-open) or "limit"
  * limit_price: Required if mode is "limit", otherwise null
- Define "exit_policy":
  * time_stop_days: Always 7 (close position after 7 days)
  * stop_loss_pct: Must match risk_profile (0.010 | 0.015 | 0.020)
  * take_profit_pct: Must match risk_profile (0.015 | 0.025 | 0.035)
  * exit_before_events: Optional array ["NFP", "CPI", "FOMC"]
- **FORBIDDEN**: Do NOT use technical indicators (RSI, MACD, moving averages, Bollinger bands, Stochastic, Fibonacci, ADX, ATR, etc.)
  * Base your thesis on macro regime, narratives, fundamental catalysts only
  * If you mention any indicator, your pitch will be REJECTED and regenerated
- Use "risk_notes" (not "invalidation_rule") to describe primary risks for the week
- Direction options: LONG | SHORT | FLAT
- Conviction range: -2 to +2 (negative for SHORT, positive for LONG, 0 for FLAT)
- Maximum 5 thesis bullets
- Consider both research packs

VALIDATION RULES:
- Your pitch will be REJECTED if it contains: RSI, MACD, EMA, SMA, Bollinger, Stochastic, Fibonacci, or any chart pattern references
- Risk profile must exactly match one of the three standardized profiles (TIGHT/BASE/WIDE)
- All percentages in exit_policy must match the chosen risk_profile
- Do NOT include position sizing hints - sizing is handled separately

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
    
    def _validate_no_indicators(self, pitch: Dict[str, Any]) -> None:
        """Reject pitches that mention technical indicators."""
        # Check all string fields
        fields_to_check = [
            "thesis_bullets",  # list of strings
            "risk_notes",      # string
        ]
        
        text_to_scan = []
        
        for field in fields_to_check:
            value = pitch.get(field)
            if isinstance(value, str):
                text_to_scan.append(value.lower())
            elif isinstance(value, list):
                text_to_scan.extend([str(v).lower() for v in value])
        
        combined_text = " ".join(text_to_scan)
        
        for keyword in BANNED_KEYWORDS:
            if keyword in combined_text:
                raise ValueError(
                    f"❌ REJECTED: Pitch contains banned indicator keyword '{keyword}'. "
                    f"Use macro/fundamental reasoning only."
                )
    
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
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if not json_match:
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
        except ValueError as e:
            print(f"  {str(e)}")
            return None
            
        # Validate required fields (v2 schema)
        required_fields = [
            "week_id", "asof_et", "pm_model", "selected_instrument",
            "direction", "conviction", "horizon", "thesis_bullets",
            "risk_profile", "entry_policy", "exit_policy", "risk_notes"  # NEW
        ]
        
        missing_fields = [f for f in required_fields if f not in pitch]
        if missing_fields:
            print(f"  ⚠️  Missing required fields: {', '.join(missing_fields)}")
            print(f"  ℹ️  Fields present: {', '.join(pitch.keys())}")
            return None
        
        # Validate risk_profile
        if pitch.get("risk_profile") not in ["TIGHT", "BASE", "WIDE"]:
            raise ValueError(f"Invalid risk_profile: {pitch.get('risk_profile')}")
        
        # Validate entry_policy structure
        entry_policy = pitch.get("entry_policy", {})
        if "mode" not in entry_policy:
            raise ValueError("entry_policy missing required field: mode")
        if entry_policy["mode"] not in ENTRY_MODES:
            raise ValueError(f"Invalid entry_policy.mode: {entry_policy['mode']}")
        
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
        
        # Validate selected_instrument (allow FLAT)
        valid_instruments = self.INSTRUMENTS + ["FLAT"]
        if pitch["selected_instrument"] not in valid_instruments:
            print(f"  ⚠️  Invalid selected_instrument: {pitch['selected_instrument']}")
            return None
        
        # Validate direction
        if pitch["direction"] not in ["LONG", "SHORT", "FLAT"]:
            print(f"  ⚠️  Invalid direction: {pitch['direction']}")
            return None
        
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
                    "one_week_thesis": "Testing support at key levels",
                    "primary_risks": "Volatility spike, liquidity concerns",
                    "watch_indicators": ["RSI", "VIX", "SPY 200-day MA"],
                    "invalidation_rule": "Break below 4700"
                },
                {
                    "instrument": "TLT",
                    "directional_bias": "LONG",
                    "one_week_thesis": "Yields attractive vs equities",
                    "primary_risks": "Fed rate hike, inflation concerns",
                    "watch_indicators": ["10Y yield", "TLT volume"],
                    "invalidation_rule": "Yield spike above 4.5%"
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
