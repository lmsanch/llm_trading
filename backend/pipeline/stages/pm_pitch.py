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


# Context keys for PM pitches
PM_PITCHES = ContextKey("pm_pitches")


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
        
        if not research_pack_a or not research_pack_b:
            print("  ❌ Error: Research packs not found in context")
            print("  ⚠️  Running with placeholder research data")
            research_pack_a = self._placeholder_research_pack()
            research_pack_b = self._placeholder_research_pack()
        
        # Generate pitches from all PM models
        print("\n🎯 Generating PM pitches from all 5 models...")
        pm_pitches = await self._generate_pm_pitches(
            research_pack_a,
            research_pack_b
        )
        
        print(f"  ✅ Generated {len(pm_pitches)} PM pitches")
        
        # Return context with PM pitches
        return context.set(PM_PITCHES, pm_pitches)
    
    async def _generate_pm_pitches(
        self,
        research_pack_a: Dict[str, Any],
        research_pack_b: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate PM pitches from all models in parallel.
        
        Args:
            research_pack_a: Primary research pack
            research_pack_b: Alternative research pack
            
        Returns:
            List of PM pitch dicts
        """
        # Build prompt for each PM model
        prompt = self._build_pm_prompt(research_pack_a, research_pack_b)
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert portfolio manager for a quantitative trading system. Your task is to generate a single, well-reasoned trading recommendation based on research analysis.

Rules:
1. Pick ONE instrument from the tradable universe
2. Choose direction: LONG, SHORT, or FLAT
3. Set horizon: 1d, 3d, or 1w
4. Provide 3-5 thesis bullets (max 5)
5. Include frozen indicators with thresholds
6. Set conviction score from -2 to +2
7. Define clear invalidation rule
8. Be specific and actionable

Return as valid JSON."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Query all PM models in parallel
        responses = await query_pm_models(messages)
        
        # Parse and validate pitches
        pm_pitches = []
        for model_key, response in responses.items():
            if response is not None:
                pitch = self._parse_pm_pitch(response["content"], model_key)
                if pitch:
                    pm_pitches.append(pitch)
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n✅ {model_info['account']} ({model_key.upper()})")
                    print(f"   Instrument: {pitch['instrument']} | Direction: {pitch['direction']}")
                    print(f"   Conviction: {pitch['conviction']} | Horizon: {pitch['horizon']}")
                else:
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n❌ {model_info['account']} ({model_key.upper()}) - Failed to parse pitch")
        
        return pm_pitches
    
    def _build_pm_prompt(
        self,
        research_pack_a: Dict[str, Any],
        research_pack_b: Dict[str, Any]
    ) -> str:
        """Build prompt for PM pitch generation."""
        week_id = get_week_id()
        
        # Format research packs for prompt
        research_text_a = self._format_research_pack(research_pack_a, "Research Pack A")
        research_text_b = self._format_research_pack(research_pack_b, "Research Pack B")
        
        prompt = f"""You are a portfolio manager for a quantitative trading system. Generate a trading recommendation for week {week_id}.

RESEARCH PACK A (Gemini Deep Research):
{research_text_a}

RESEARCH PACK B (DeepSeek Alternative Research):
{research_text_b}

TRADABLE UNIVERSE:
- SPY: S&P 500 ETF
- QQQ: Nasdaq 100 ETF
- IWM: Russell 2000 ETF
- TLT: 20+ Year Treasury Bond ETF
- HYG: High Yield Corporate Bond ETF
- UUP: US Dollar Index ETF
- GLD: Gold ETF
- USO: Oil ETF

TASK: Generate a single trading recommendation as valid JSON with the following structure:

{{
  "idea_id": "uuid",
  "week_id": "{week_id}",
  "model": "model_name",
  "instrument": "SPY",
  "direction": "LONG",  // LONG | SHORT | FLAT
  "horizon": "1w",      // 1d | 3d | 1w
  "thesis_bullets": [   // max 5
    "First reason...",
    "Second reason...",
    "Third reason..."
  ],
  "consensus_map": {{
    "research_pack_a": "agree" | "disagree" | "neutral",
    "research_pack_b": "agree" | "disagree" | "neutral"
  }},
  "indicators": [       // frozen list with thresholds
    {{"name": "RSI", "value": 65, "threshold": 70, "direction": "below"}},
    {{"name": "MACD", "value": 1.2, "threshold": 0, "direction": "above"}}
  ],
  "invalidation": "Exit if RSI crosses above 75 OR MACD turns negative",
  "conviction": 1.5,    // -2 to +2
  "position_size_hint": 0.8,  // 0 to 1 (optional)
  "risk_notes": "Key risks to monitor...",
  "timestamp": "ISO8601"
}}

IMPORTANT:
- Pick ONLY ONE instrument
- Be specific and data-driven
- Consider both research packs
- Set conviction based on confidence level
- Define clear exit criteria

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
    
    def _parse_pm_pitch(
        self,
        content: str,
        model_key: str
    ) -> Dict[str, Any] | None:
        """
        Parse PM pitch from LLM response.
        
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
            return None
        
        json_str = json_match.group(0)
        
        try:
            pitch = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "idea_id", "week_id", "model", "instrument", 
                "direction", "horizon", "thesis_bullets", 
                "indicators", "invalidation", "conviction"
            ]
            
            for field in required_fields:
                if field not in pitch:
                    print(f"  ⚠️  Missing field: {field}")
                    return None
            
            # Validate values
            if pitch["instrument"] not in self.INSTRUMENTS:
                print(f"  ⚠️  Invalid instrument: {pitch['instrument']}")
                return None
            
            if pitch["direction"] not in ["LONG", "SHORT", "FLAT"]:
                print(f"  ⚠️  Invalid direction: {pitch['direction']}")
                return None
            
            if pitch["horizon"] not in ["1d", "3d", "1w"]:
                print(f"  ⚠️  Invalid horizon: {pitch['horizon']}")
                return None
            
            conviction = pitch.get("conviction", 0)
            if not isinstance(conviction, (int, float)):
                print(f"  ⚠️  Invalid conviction type")
                return None
            
            if conviction < self.CONVICTION_MIN or conviction > self.CONVICTION_MAX:
                print(f"  ⚠️  Conviction out of range: {conviction}")
                return None
            
            # Add metadata
            pitch["model"] = model_key
            pitch["model_info"] = REQUESTY_MODELS[model_key]
            pitch["timestamp"] = datetime.utcnow().isoformat()
            
            return pitch
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON decode error: {e}")
            return None
    
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
