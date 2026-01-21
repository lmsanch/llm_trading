"""Peer review stage for anonymized evaluation of PM pitches."""

import re
from typing import Dict, Any, List
from datetime import datetime
import random
import string

from ...requesty_client import query_pm_models, REQUESTY_MODELS
from ..context import PipelineContext, ContextKey
from ..base import Stage
from .pm_pitch import PM_PITCHES


# Context keys for peer review
PEER_REVIEWS = ContextKey("peer_reviews")
LABEL_TO_MODEL = ContextKey("label_to_model")


class PeerReviewStage(Stage):
    """
    Peer review stage that anonymizes and evaluates PM pitches.

    This stage:
    1. Anonymizes all PM pitches (removes model identity)
    2. Each PM model reviews other pitches
    3. Provides rubric scores on 7 dimensions
    4. Generates "kill shot" critiques
    5. Suggests flip conditions
    """

    # Rubric dimensions
    RUBRIC_DIMENSIONS = [
        "clarity",
        "edge_plausibility",
        "timing_catalyst",
        "risk_definition",
        "risk_management",
        "originality",
        "tradeability",
    ]

    @property
    def name(self) -> str:
        return "PeerReviewStage"

    def __init__(self, temperature: float | None = None):
        super().__init__()
        from ..utils.temperature_manager import TemperatureManager

        self.temperature = temperature or TemperatureManager().get_temperature(
            "peer_review"
        )

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute peer review stage.

        Args:
            context: Pipeline context with PM pitches

        Returns:
            New context with peer reviews added
        """
        print("\n" + "=" * 60)
        print("👥 PEER REVIEW STAGE")
        print("=" * 60)

        # Get PM pitches from context
        pm_pitches = context.get(PM_PITCHES)

        if not pm_pitches:
            print("  ❌ Error: PM pitches not found in context")
            return context

        print(f"\n📋 Found {len(pm_pitches)} PM pitches to review")

        # Step 1: Anonymize pitches
        print("\n🔍 Anonymizing pitches...")
        anonymized_pitches, label_to_model = self._anonymize_pitches(pm_pitches)

        # Step 2: Generate peer reviews
        print("🎯 Generating peer reviews...")
        peer_reviews = await self._generate_peer_reviews(anonymized_pitches)

        print(f"  ✅ Generated {len(peer_reviews)} peer reviews")

        # Return context with peer reviews
        return context.set(PEER_REVIEWS, peer_reviews).set(
            LABEL_TO_MODEL, label_to_model
        )

    def _anonymize_pitches(
        self, pm_pitches: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Anonymize PM pitches by removing model identity.

        Args:
            pm_pitches: List of PM pitch dicts

        Returns:
            Tuple of (anonymized pitches, label_to_model mapping)
        """
        # Generate random labels (Pitch A, Pitch B, etc.)
        labels = [f"Pitch {chr(65 + i)}" for i in range(len(pm_pitches))]

        # Create mapping from label to model
        label_to_model = {
            label: pitch["model"] for label, pitch in zip(labels, pm_pitches)
        }

        # Create anonymized versions
        anonymized_pitches = []
        for label, pitch in zip(labels, pm_pitches):
            anonymized_pitch = pitch.copy()
            anonymized_pitch["anonymized_label"] = label
            anonymized_pitch["original_model"] = pitch["model"]
            anonymized_pitch["original_account"] = pitch.get("model_info", {}).get(
                "account", "Unknown"
            )
            # Use selected_instrument (v2 schema) or fall back to instrument (v1)
            anonymized_pitch["instrument"] = pitch.get(
                "selected_instrument"
            ) or pitch.get("instrument", "FLAT")
            anonymized_pitch["direction"] = pitch.get("direction", "FLAT")
            anonymized_pitch["horizon"] = pitch.get("horizon", "1W")
            anonymized_pitch["thesis_bullets"] = pitch.get("thesis_bullets", [])
            anonymized_pitch["conviction"] = pitch.get("conviction", 0)
            anonymized_pitch["risk_profile"] = pitch.get("risk_profile", "BASE")
            anonymized_pitch["entry_policy"] = pitch.get("entry_policy", {})
            anonymized_pitch["exit_policy"] = pitch.get("exit_policy", {})
            anonymized_pitch["risk_notes"] = pitch.get("risk_notes", "N/A")
            anonymized_pitches.append(anonymized_pitch)

        print(f"  ✅ Anonymized as: {', '.join(labels)}")
        return anonymized_pitches, label_to_model

    async def _generate_peer_reviews(
        self, anonymized_pitches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate peer reviews from all PM models.

        Args:
            anonymized_pitches: List of anonymized pitch dicts

        Returns:
            List of peer review dicts
        """
        # Build prompt for peer review
        prompt = self._build_peer_review_prompt(anonymized_pitches)

        messages = [
            {
                "role": "system",
                "content": """You are an expert trader evaluating trading recommendations from other portfolio managers. Your task is to provide constructive, critical feedback on each pitch.

Focus on:
1. Clarity of thesis and reasoning
2. Plausibility of edge
3. Timing and catalyst identification
4. Risk definition and management
5. Risk management quality (stop loss, take profit, time stop alignment)
6. Originality of idea
7. Tradeability and execution feasibility

Be fair but critical. Identify weaknesses and suggest improvements.""",
            },
            {"role": "user", "content": prompt},
        ]

        # Query all PM models for peer reviews
        responses = await query_pm_models(messages, temperature=self.temperature)

        # Parse and return peer reviews
        peer_reviews = []
        for model_key, response in responses.items():
            if response is not None:
                reviews = self._parse_peer_review(response["content"], model_key)
                if reviews:
                    peer_reviews.extend(reviews)
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n✅ {model_info['account']} ({model_key.upper()})")
                    print(f"   Reviewed {len(reviews)} pitches")
                    # Calculate average score across all reviews
                    avg_score = sum(r.get('average_score', 0) for r in reviews) / len(reviews)
                    print(f"   Average score: {avg_score:.2f}/10")
                else:
                    model_info = REQUESTY_MODELS[model_key]
                    print(
                        f"\n❌ {model_info['account']} ({model_key.upper()}) - Failed to parse review"
                    )

        return peer_reviews

    def _build_peer_review_prompt(
        self, anonymized_pitches: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for peer review."""
        # region agent log
        try:
            import json, time

            with open("/research/llm_trading/.cursor/debug.log", "a") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "pre-fix",
                            "hypothesisId": "H2",
                            "location": "peer_review.py:_build_peer_review_prompt:start",
                            "message": "Peer review prompt build start",
                            "data": {"count": len(anonymized_pitches)},
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # endregion

        # Format pitches for prompt
        pitches_text = "\n\n".join(
            [
                f"### {pitch['anonymized_label']}\n"
                f"**Instrument:** {pitch.get('selected_instrument', pitch.get('instrument', 'N/A'))}\n"
                f"**Direction:** {pitch['direction']}\n"
                f"**Horizon:** {pitch['horizon']}\n"
                f"**Conviction:** {pitch['conviction']}\n"
                f"**Thesis:**\n"
                + "\n".join([f"  - {bullet}" for bullet in pitch["thesis_bullets"]])
                + f"\n**Risk Profile:** {pitch.get('risk_profile', 'BASE') or 'NONE'}\n"
                + (
                    f"**Exit Policy:**\n"
                    f"  Stop Loss: {(pitch.get('exit_policy') or {}).get('stop_loss_pct', 0) * 100:.1f}%\n"
                    f"  Take Profit: {(pitch.get('exit_policy') or {}).get('take_profit_pct', 0) * 100:.1f}%\n"
                    f"  Time Stop: {(pitch.get('exit_policy') or {}).get('time_stop_days', 7)} days\n"
                    if pitch.get("exit_policy")
                    else "**Exit Policy:** N/A (FLAT position)\n"
                )
                + f"**Entry Policy:** {(pitch.get('entry_policy') or {}).get('mode', 'limit')}\n"
                + f"**Risk Notes:** {pitch.get('risk_notes', 'N/A')}\n"
                for pitch in anonymized_pitches
            ]
        )

        # region agent log
        try:
            import json, time

            sample = anonymized_pitches[0] if anonymized_pitches else {}
            with open("/research/llm_trading/.cursor/debug.log", "a") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "pre-fix",
                            "hypothesisId": "H3",
                            "location": "peer_review.py:_build_peer_review_prompt:sample",
                            "message": "Sample pitch exit/entry",
                            "data": {
                                "direction": sample.get("direction"),
                                "exit_policy": sample.get("exit_policy"),
                                "entry_policy": sample.get("entry_policy"),
                            },
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # endregion

        prompt = f"""You are evaluating trading recommendations from multiple portfolio managers.

 ### AVAILABLE PITCHES TO REVIEW:

 {pitches_text}

 ### TASK:

 For EACH pitch (except your own), provide:

 1. RUBRIC SCORES (1-10 scale for each dimension):
    - clarity: How clear and well-reasoned is the thesis?
    - edge_plausibility: Does the edge make sense?
    - timing_catalyst: Is the timing and catalyst identified?
    - risk_definition: Are risks clearly defined?
    - risk_management: Is the risk profile and exit policy appropriate?
    - originality: Is this a novel or unique idea?
    - tradeability: Is this trade executable and practical?

 2. BEST ARGUMENT AGAINST:
    What is the strongest counter-argument to this pitch?

 3. ONE FLIP CONDITION:
    What single event would make you flip to the opposite direction?

4. SUGGESTED FIX:
   One specific improvement to make this pitch stronger.

### OUTPUT FORMAT:

For each pitch, return as valid JSON:

{{
  "review_id": "uuid",
  "pitch_label": "Pitch A",
  "reviewer_model": "model_name",
  "scores": {{
    "clarity": 8,
    "edge_plausibility": 7,
    "timing_catalyst": 6,
    "risk_definition": 9,
    "indicator_integrity": 8,
    "originality": 5,
    "tradeability": 7
  }},
  "best_argument_against": "Strongest counter-argument...",
  "one_flip_condition": "Would flip to SHORT if...",
  "suggested_fix": "Improve by...",
  "timestamp": "ISO8601"
}}

IMPORTANT:
- Review ALL pitches (don't skip any)
- Be fair and objective
- Provide specific, actionable feedback
- Return as valid JSON only, no markdown"""

        return prompt

    def _parse_peer_review(
        self, content: str, reviewer_model: str
    ) -> List[Dict[str, Any]]:
        """
        Parse peer review from LLM response.

        Args:
            content: LLM response content
            reviewer_model: Model identifier

        Returns:
            List of parsed review dicts (empty list if invalid)
        """
        import json
        import uuid
        from json import JSONDecodeError, JSONDecoder

        # region agent log
        try:
            import time

            with open("/research/llm_trading/.cursor/debug.log", "a") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "pre-fix",
                            "hypothesisId": "H4",
                            "location": "peer_review.py:_parse_peer_review:start",
                            "message": "Parsing peer review",
                            "data": {
                                "reviewer": reviewer_model,
                                "content_head": content[:200],
                            },
                            "timestamp": int(time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # endregion

        # Strip common code fences from models
        content_stripped = content.strip()
        for fence in ["```json", "```", "~~~json", "~~~"]:
            if content_stripped.lower().startswith(fence):
                content_stripped = content_stripped[len(fence) :].strip()
            if content_stripped.endswith(fence):
                content_stripped = content_stripped[: -len(fence)].strip()

        # Try to extract JSON from response (non-greedy)
        review = None
        json_match = re.search(r"\{.*?\}", content_stripped, re.DOTALL)
        if json_match:
            try:
                review = json.loads(json_match.group(0))
            except JSONDecodeError:
                review = None

        # Fallback: raw_decode first JSON object even with trailing text
        if review is None:
            try:
                review, idx = JSONDecoder().raw_decode(content_stripped)
                # region agent log
                try:
                    import time

                    with open("/research/llm_trading/.cursor/debug.log", "a") as f:
                        f.write(
                            json.dumps(
                                {
                                    "sessionId": "debug-session",
                                    "runId": "pre-fix",
                                    "hypothesisId": "H4",
                                    "location": "peer_review.py:_parse_peer_review:raw_decode_fallback",
                                    "message": "Used raw_decode fallback",
                                    "data": {"reviewer": reviewer_model, "idx": idx},
                                    "timestamp": int(time.time() * 1000),
                                }
                            )
                            + "\n"
                        )
                except Exception:
                    pass
                # endregion
            except JSONDecodeError as e:
                print(f"  ⚠️  JSON decode error: {e}")
                return []

        if review is None:
            print(f"  ⚠️  No JSON found in review from {reviewer_model}")
            return []

        # If model returned a list of reviews, validate and return all
        if isinstance(review, list):
            if not review:
                print(f"  ⚠️  Empty review list from {reviewer_model}")
                return []
            reviews_to_return = []
            for single_review in review:
                validated = self._validate_and_enrich_review(single_review, reviewer_model)
                if validated:
                    reviews_to_return.append(validated)
            return reviews_to_return

        # Single review - validate and return as list
        validated = self._validate_and_enrich_review(review, reviewer_model)
        return [validated] if validated else []

    def _validate_and_enrich_review(
        self, review: Dict[str, Any], reviewer_model: str
    ) -> Dict[str, Any] | None:
        """
        Validate and enrich a single review dict.

        Args:
            review: Review dict to validate
            reviewer_model: Model identifier

        Returns:
            Validated and enriched review dict or None if invalid
        """

        # Validate required fields
        required_fields = [
            "review_id",
            "pitch_label",
            "reviewer_model",
            "scores",
            "best_argument_against",
            "one_flip_condition",
            "suggested_fix",
        ]

        for field in required_fields:
            if field not in review:
                print(f"  ⚠️  Missing field: {field}")
                return None

        # Validate scores
        scores = review.get("scores", {})
        for dimension in self.RUBRIC_DIMENSIONS:
            if dimension not in scores:
                print(f"  ⚠️  Missing score dimension: {dimension}")
                return None
            score = scores[dimension]
            if not isinstance(score, int) or score < 1 or score > 10:
                print(f"  ⚠️  Invalid score for {dimension}: {score}")
                return None

        # Calculate average score
        valid_scores = [scores[dim] for dim in self.RUBRIC_DIMENSIONS if dim in scores]
        average_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

        review["average_score"] = round(average_score, 2)
        review["timestamp"] = datetime.utcnow().isoformat()

        return review
