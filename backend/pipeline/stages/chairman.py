"""Chairman synthesis stage for final trading decisions."""

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from ...requesty_client import query_chairman, REQUESTY_MODELS
from ..context import PipelineContext, ContextKey
from ..base import Stage
from .pm_pitch import PM_PITCHES
from .peer_review import PEER_REVIEWS, LABEL_TO_MODEL


# Context keys for chairman
CHAIRMAN_DECISION = ContextKey("chairman_decision")


class ChairmanStage(Stage):
    """
    Chairman synthesis stage that creates final council trade decision.
    
    This stage:
    1. Receives all PM pitches and peer reviews
    2. Uses Claude Opus 4.5 to synthesize
    3. Generates final council trade decision
    4. Includes dissent notes from minority views
    5. Provides monitoring plan for checkpoints
    """
    
    # Tradable universe
    INSTRUMENTS = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]
    
    # Conviction scale
    CONVICTION_MIN = -2
    CONVICTION_MAX = 2
    
    @property
    def name(self) -> str:
        return "ChairmanStage"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute chairman synthesis stage.
        
        Args:
            context: Pipeline context with PM pitches and peer reviews
            
        Returns:
            New context with chairman decision added
        """
        print("\n" + "=" * 60)
        print("👑 CHAIRMAN SYNTHESIS STAGE")
        print("=" * 60)
        
        # Get PM pitches and peer reviews from context
        pm_pitches = context.get(PM_PITCHES)
        peer_reviews = context.get(PEER_REVIEWS)
        label_to_model = context.get(LABEL_TO_MODEL, {})
        
        if not pm_pitches or not peer_reviews:
            print("  ❌ Error: PM pitches or peer reviews not found in context")
            return context
        
        print(f"\n📋 Synthesizing {len(pm_pitches)} PM pitches")
        print(f"👥 Considering {len(peer_reviews)} peer reviews")
        
        # Generate chairman decision
        print("\n🧠 Generating council decision...")
        chairman_decision = await self._generate_chairman_decision(
            pm_pitches,
            peer_reviews,
            label_to_model
        )
        
        print(f"  ✅ Council decision: {chairman_decision['instrument']} {chairman_decision['direction']}")
        print(f"  Conviction: {chairman_decision['conviction']} | Horizon: {chairman_decision['horizon']}")
        
        # Return context with chairman decision
        return context.set(CHAIRMAN_DECISION, chairman_decision)
    
    async def _generate_chairman_decision(
        self,
        pm_pitches: List[Dict[str, Any]],
        peer_reviews: List[Dict[str, Any]],
        label_to_model: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Generate chairman decision using Claude Opus 4.5.
        
        Args:
            pm_pitches: List of PM pitch dicts
            peer_reviews: List of peer review dicts
            label_to_model: Mapping from label to model
            
        Returns:
            Chairman decision dict
        """
        # Build prompt for chairman
        prompt = self._build_chairman_prompt(pm_pitches, peer_reviews, label_to_model)
        
        messages = [
            {
                "role": "system",
                "content": """You are the Chief Investment Officer (CIO) of a quantitative trading system. Your task is to synthesize trading recommendations from 5 portfolio managers into a single, optimal council decision.

Your role:
1. Review all PM pitches objectively
2. Consider peer evaluations and critiques
3. Identify consensus and dissent
4. Make a final trade decision
5. Document rationale and dissenting views
6. Provide monitoring plan for checkpoints

Focus on:
- Risk-adjusted returns
- Conviction-weighted decision making
- Clear exit criteria
- Practical execution considerations

Be decisive but thorough. Acknowledge dissent where appropriate."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Query chairman model
        response = await query_chairman(messages)
        
        if response is None:
            print("  ❌ Failed to generate chairman decision")
            return self._fallback_decision(pm_pitches)
        
        # Parse and return chairman decision
        chairman_decision = self._parse_chairman_decision(response["content"])
        
        return chairman_decision
    
    def _build_chairman_prompt(
        self,
        pm_pitches: List[Dict[str, Any]],
        peer_reviews: List[Dict[str, Any]],
        label_to_model: Dict[str, str]
    ) -> str:
        """Build prompt for chairman synthesis."""
        
        # Format PM pitches
        pitches_text = "\n\n".join([
            f"### {pitch.get('model_info', {}).get('account', 'Unknown')} ({pitch['model']})\n"
            f"**Instrument:** {pitch['instrument']}\n"
            f"**Direction:** {pitch['direction']}\n"
            f"**Horizon:** {pitch['horizon']}\n"
            f"**Conviction:** {pitch['conviction']}\n"
            f"**Thesis:**\n"
            + "\n".join([f"  - {bullet}" for bullet in pitch.get("thesis_bullets", [])])
            + f"\n**Indicators:**\n"
            + "\n".join([
                f"  - {ind['name']}: {ind['value']} (threshold: {ind['threshold']}, direction: {ind['direction']})"
                for ind in pitch.get("indicators", [])
            ])
            + f"\n**Invalidation:** {pitch.get('invalidation', 'N/A')}\n"
            for pitch in pm_pitches
        ])
        
        # Format peer reviews
        reviews_text = "\n\n".join([
            f"### {review.get('reviewer_model', {}).get('account', 'Unknown')} Review of {review.get('pitch_label', 'Unknown')}\n"
            f"**Average Score:** {review.get('average_score', 0)}/10\n"
            f"**Scores:**\n"
            + "\n".join([
                f"  - {dim}: {review.get('scores', {}).get(dim, 'N/A')}/10"
                for dim in ["clarity", "edge_plausibility", "timing_catalyst", "risk_definition", "indicator_integrity", "originality", "tradeability"]
            ])
            + f"\n**Best Argument Against:** {review.get('best_argument_against', 'N/A')}\n"
            + f"**One Flip Condition:** {review.get('one_flip_condition', 'N/A')}\n"
            + f"**Suggested Fix:** {review.get('suggested_fix', 'N/A')}\n"
            for review in peer_reviews
        ])
        
        prompt = f"""You are the Chief Investment Officer (CIO) synthesizing recommendations from 5 portfolio managers.

### PM PITCHES:

{pitches_text}

### PEER REVIEWS:

{reviews_text}

### TASK:

Generate a final council trade decision as valid JSON with the following structure:

{{
  "decision_id": "uuid",
  "week_id": "YYYY-MM-DD",
  "selected_trade": {{
    "instrument": "SPY",
    "direction": "LONG",
    "horizon": "1w"
  }},
  "conviction": 1.2,
  "rationale": "Brief synthesis of why this trade was selected...",
  "dissent_summary": [
    {{"model": "account_name", "position": "SHORT on SPY", "reason": "..."}},
    {{"model": "account_name", "position": "FLAT", "reason": "..."}}
  ],
  "monitoring_plan": {{
    "checkpoints": ["09:00", "12:00", "14:00", "15:50"],
    "key_indicators": ["RSI", "MACD", "VIX"],
    "watch_conditions": ["RSI > 75", "VIX spike > 20"]
  }},
  "timestamp": "ISO8601"
}}

### GUIDELINES:

1. SELECT TRADE:
   - Pick ONE instrument from the PM recommendations
   - Choose direction (LONG/SHORT/FLAT) based on consensus
   - Set horizon (1d/3d/1w) based on timing
   - Set conviction (-2 to +2) based on confidence

2. RATIONALE:
   - Explain why this trade was chosen
   - Reference supporting PM pitches
   - Acknowledge peer review consensus
   - Be concise but thorough

3. DISSENT SUMMARY:
   - List any PMs who strongly disagree
   - Include their position and reason
   - Be fair to minority views

4. MONITORING PLAN:
   - Checkpoints: 09:00, 12:00, 14:00, 15:50 ET
   - Key indicators: RSI, MACD, VIX, etc.
   - Watch conditions: When to exit or reduce
   - Be specific about thresholds

5. RISK MANAGEMENT:
   - Consider conviction level for position sizing
   - Define clear exit criteria
   - Account for market volatility

Return as valid JSON only, no markdown formatting."""
        
        return prompt
    
    def _parse_chairman_decision(self, content: str) -> Dict[str, Any]:
        """
        Parse chairman decision from LLM response.
        
        Args:
            content: LLM response content
            
        Returns:
            Parsed chairman decision dict
        """
        import uuid
        from datetime import datetime
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if not json_match:
            print(f"  ⚠️  No JSON found in chairman response")
            return self._fallback_decision([])
        
        json_str = json_match.group(0)
        
        try:
            decision = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "decision_id", "week_id", "selected_trade", 
                "conviction", "rationale", "monitoring_plan"
            ]
            
            for field in required_fields:
                if field not in decision:
                    print(f"  ⚠️  Missing field: {field}")
                    return self._fallback_decision([])
            
            # Validate selected trade
            selected_trade = decision.get("selected_trade", {})
            if "instrument" not in selected_trade:
                print(f"  ⚠️  Missing instrument in selected_trade")
                return self._fallback_decision([])
            
            if selected_trade["instrument"] not in self.INSTRUMENTS:
                print(f"  ⚠️  Invalid instrument: {selected_trade['instrument']}")
                return self._fallback_decision([])
            
            if selected_trade.get("direction") not in ["LONG", "SHORT", "FLAT"]:
                print(f"  ⚠️  Invalid direction: {selected_trade.get('direction')}")
                return self._fallback_decision([])
            
            if selected_trade.get("horizon") not in ["1d", "3d", "1w"]:
                print(f"  ⚠️  Invalid horizon: {selected_trade.get('horizon')}")
                return self._fallback_decision([])
            
            conviction = decision.get("conviction", 0)
            if not isinstance(conviction, (int, float)):
                print(f"  ⚠️  Invalid conviction type")
                return self._fallback_decision([])
            
            if conviction < self.CONVICTION_MIN or conviction > self.CONVICTION_MAX:
                print(f"  ⚠️  Conviction out of range: {conviction}")
                return self._fallback_decision([])
            
            # Validate monitoring plan
            monitoring = decision.get("monitoring_plan", {})
            if not monitoring:
                print(f"  ⚠️  Missing monitoring plan")
                return self._fallback_decision([])
            
            # Add metadata
            decision["model"] = "chairman"
            decision["model_id"] = REQUESTY_MODELS["chairman"]["model_id"]
            decision["account"] = REQUESTY_MODELS["chairman"]["account"]
            decision["alpaca_id"] = REQUESTY_MODELS["chairman"]["alpaca_id"]
            decision["timestamp"] = datetime.utcnow().isoformat()
            
            return decision
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON decode error: {e}")
            return self._fallback_decision([])
    
    def _fallback_decision(self, pm_pitches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate fallback decision when LLM fails.
        
        Args:
            pm_pitches: List of PM pitch dicts
            
        Returns:
            Fallback chairman decision dict
        """
        import uuid
        from datetime import datetime
        
        # Simple heuristic: pick highest conviction LONG/SHORT
        valid_pitches = [p for p in pm_pitches if p.get("direction") in ["LONG", "SHORT"]]
        
        if not valid_pitches:
            # No valid pitches, return FLAT
            return {
                "decision_id": str(uuid.uuid4()),
                "week_id": datetime.utcnow().strftime("%Y-%m-%d"),
                "selected_trade": {
                    "instrument": "SPY",
                    "direction": "FLAT",
                    "horizon": "1w"
                },
                "conviction": 0,
                "rationale": "No valid PM pitches available. Defaulting to FLAT.",
                "dissent_summary": [],
                "monitoring_plan": {
                    "checkpoints": ["09:00", "12:00", "14:00", "15:50"],
                    "key_indicators": ["RSI", "MACD", "VIX"],
                    "watch_conditions": ["Review PM pitches"]
                },
                "model": "chairman",
                "model_id": REQUESTY_MODELS["chairman"]["model_id"],
                "account": REQUESTY_MODELS["chairman"]["account"],
                "alpaca_id": REQUESTY_MODELS["chairman"]["alpaca_id"],
                "timestamp": datetime.utcnow().isoformat(),
                "fallback": True
            }
        
        # Pick pitch with highest conviction
        best_pitch = max(valid_pitches, key=lambda p: p.get("conviction", 0))
        
        return {
            "decision_id": str(uuid.uuid4()),
            "week_id": datetime.utcnow().strftime("%Y-%m-%d"),
            "selected_trade": {
                "instrument": best_pitch["instrument"],
                "direction": best_pitch["direction"],
                "horizon": best_pitch.get("horizon", "1w")
            },
            "conviction": best_pitch.get("conviction", 0),
            "rationale": f"Selected {best_pitch.get('model_info', {}).get('account', 'Unknown')} pitch with highest conviction ({best_pitch.get('conviction', 0)}).",
            "dissent_summary": [
                {
                    "model": p.get("model_info", {}).get("account", "Unknown"),
                    "position": f"{p.get('direction', 'UNKNOWN')} on {p.get('instrument', 'Unknown')}",
                    "reason": "Lower conviction or different view"
                }
                for p in valid_pitches if p != best_pitch
            ],
            "monitoring_plan": {
                "checkpoints": ["09:00", "12:00", "14:00", "15:50"],
                "key_indicators": ["RSI", "MACD", "VIX"],
                "watch_conditions": [
                    f"Exit if conviction drops below 0.5",
                    f"Review at each checkpoint"
                ]
            },
            "model": "chairman",
            "model_id": REQUESTY_MODELS["chairman"]["model_id"],
            "account": REQUESTY_MODELS["chairman"]["account"],
            "alpaca_id": REQUESTY_MODELS["chairman"]["alpaca_id"],
            "timestamp": datetime.utcnow().isoformat(),
            "fallback": True
        }
