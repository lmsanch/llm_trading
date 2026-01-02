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
        "indicator_integrity",
        "originality",
        "tradeability"
    ]
    
    @property
    def name(self) -> str:
        return "PeerReviewStage"
    
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
        return (
            context
            .set(PEER_REVIEWS, peer_reviews)
            .set(LABEL_TO_MODEL, label_to_model)
        )
    
    def _anonymize_pitches(
        self,
        pm_pitches: List[Dict[str, Any]]
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
            label: pitch["model"]
            for label, pitch in zip(labels, pm_pitches)
        }
        
        # Create anonymized versions
        anonymized = []
        for label, pitch in zip(labels, pm_pitches):
            anonymized_pitch = pitch.copy()
            anonymized_pitch["anonymized_label"] = label
            anonymized_pitch["original_model"] = pitch["model"]
            anonymized_pitch["original_account"] = pitch.get("model_info", {}).get("account", "Unknown")
            anonymized_pitch["instrument"] = pitch["instrument"]
            anonymized_pitch["direction"] = pitch["direction"]
            anonymized_pitch["horizon"] = pitch["horizon"]
            anonymized_pitch["thesis_bullets"] = pitch["thesis_bullets"]
            anonymized_pitch["conviction"] = pitch["conviction"]
            anonymized_pitch["indicators"] = pitch["indicators"]
            anonymized_pitch["invalidation"] = pitch["invalidation"]
            anonymized_pitches.append(anonymized_pitch)
        
        print(f"  ✅ Anonymized as: {', '.join(labels)}")
        return anonymized_pitches, label_to_model
    
    async def _generate_peer_reviews(
        self,
        anonymized_pitches: List[Dict[str, Any]]
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
2. Plausibility of the edge
3. Timing and catalyst identification
4. Risk definition and management
5. Indicator integrity and threshold logic
6. Originality of the idea
7. Tradeability and execution feasibility

Be fair but critical. Identify weaknesses and suggest improvements."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Query all PM models for peer reviews
        responses = await query_pm_models(messages)
        
        # Parse and return peer reviews
        peer_reviews = []
        for model_key, response in responses.items():
            if response is not None:
                review = self._parse_peer_review(response["content"], model_key)
                if review:
                    peer_reviews.append(review)
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n✅ {model_info['account']} ({model_key.upper()})")
                    print(f"   Reviewed {len(review['scores'])} pitches")
                    print(f"   Average score: {review.get('average_score', 0):.2f}/10")
                else:
                    model_info = REQUESTY_MODELS[model_key]
                    print(f"\n❌ {model_info['account']} ({model_key.upper()}) - Failed to parse review")
        
        return peer_reviews
    
    def _build_peer_review_prompt(self, anonymized_pitches: List[Dict[str, Any]]) -> str:
        """Build prompt for peer review."""
        # Format pitches for prompt
        pitches_text = "\n\n".join([
            f"### {pitch['anonymized_label']}\n"
            f"**Instrument:** {pitch['instrument']}\n"
            f"**Direction:** {pitch['direction']}\n"
            f"**Horizon:** {pitch['horizon']}\n"
            f"**Conviction:** {pitch['conviction']}\n"
            f"**Thesis:**\n"
            + "\n".join([f"  - {bullet}" for bullet in pitch["thesis_bullets"]])
            + f"\n**Indicators:**\n"
            + "\n".join([
                f"  - {ind['name']}: {ind['value']} (threshold: {ind['threshold']}, direction: {ind['direction']})"
                for ind in pitch["indicators"]
            ])
            + f"\n**Invalidation:** {pitch['invalidation']}\n"
            for pitch in anonymized_pitches
        ])
        
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
   - indicator_integrity: Are indicators sound and thresholds logical?
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
        self,
        content: str,
        reviewer_model: str
    ) -> Dict[str, Any] | None:
        """
        Parse peer review from LLM response.
        
        Args:
            content: LLM response content
            reviewer_model: Model identifier
            
        Returns:
            Parsed review dict or None if invalid
        """
        import json
        import uuid
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        
        if not json_match:
            print(f"  ⚠️  No JSON found in review from {reviewer_model}")
            return None
        
        json_str = json_match.group(0)
        
        try:
            review = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "review_id", "pitch_label", "reviewer_model", 
                "scores", "best_argument_against", "one_flip_condition", "suggested_fix"
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
            
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON decode error: {e}")
            return None
