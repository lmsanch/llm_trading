"""Mock council response fixtures for testing.

This module provides mock responses for all 3 stages of council orchestration:
- Stage 1: Individual model responses
- Stage 2: Ranking responses
- Stage 3: Chairman synthesis
"""

from typing import Dict, Any, List
from datetime import datetime, timezone


# ==================== Stage 1: Individual Responses ====================

def get_mock_stage1_response(
    model: str,
    content: str,
    reasoning: str = None
) -> Dict[str, Any]:
    """Generate a mock Stage 1 response from a single model.

    Args:
        model: Model name
        content: Response content
        reasoning: Optional reasoning content (for models that support it)

    Returns:
        Mock response dictionary matching OpenRouter API format
    """
    response = {
        "model": model,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if reasoning:
        response["reasoning_details"] = reasoning
    return response


def get_mock_stage1_responses() -> List[Dict[str, Any]]:
    """Get mock Stage 1 responses from all council models.

    Returns:
        List of mock responses for testing stage1_collect_responses
    """
    return [
        {
            "model": "anthropic/claude-3.5-sonnet",
            "response": "Based on my analysis, the key factors to consider are market structure, liquidity conditions, and macro trends. The current environment suggests cautious optimism with selective opportunities in defensive sectors."
        },
        {
            "model": "openai/gpt-4-turbo",
            "response": "The technical setup shows consolidation near resistance levels. Volume patterns indicate institutional accumulation. I recommend focusing on quality names with strong fundamentals and positive momentum."
        },
        {
            "model": "google/gemini-pro",
            "response": "Market breadth has been deteriorating despite headline indices near highs. This divergence, combined with elevated valuations, suggests increased risk. Consider reducing exposure or hedging positions."
        },
        {
            "model": "meta-llama/llama-3-70b",
            "response": "The macro backdrop remains supportive with easing inflation and stable growth. However, geopolitical risks warrant attention. A balanced approach with exposure to both growth and defensive assets seems prudent."
        },
    ]


def get_mock_stage1_responses_with_failure() -> List[Dict[str, Any]]:
    """Get mock Stage 1 responses with one model failure.

    Returns:
        List of mock responses where one model failed (returned None)
    """
    responses = get_mock_stage1_responses()
    responses[2] = {
        "model": "google/gemini-pro",
        "response": None,  # Simulates API failure
        "error": "API timeout"
    }
    return responses


# ==================== Stage 2: Ranking Responses ====================

def get_mock_ranking_response(
    model: str,
    rankings: List[str],
    include_analysis: bool = True
) -> str:
    """Generate a mock ranking response text.

    Args:
        model: Model name providing the ranking
        rankings: List of response labels in ranked order (e.g., ["Response A", "Response B"])
        include_analysis: Whether to include analysis before the ranking

    Returns:
        Mock ranking response text matching expected format
    """
    analysis = ""
    if include_analysis:
        analysis = """After evaluating all responses:

Response A provides comprehensive analysis with strong reasoning and clear actionable insights.
Response B offers good technical perspective but lacks depth on fundamentals.
Response C gives balanced view but misses some key risk factors.
Response D has interesting points but overall less comprehensive.

"""

    ranking_lines = "\n".join([f"{i+1}. {label}" for i, label in enumerate(rankings)])

    return f"""{analysis}FINAL RANKING:
{ranking_lines}
"""


def get_mock_ranking_response_malformed(model: str) -> str:
    """Generate a malformed ranking response (missing FINAL RANKING section).

    Args:
        model: Model name

    Returns:
        Mock response without proper FINAL RANKING format
    """
    return """I think Response A is best, followed by Response C and then Response B.
Response D was the weakest overall.

So my preference order would be: A, C, B, D
"""


def get_mock_stage2_responses() -> List[Dict[str, Any]]:
    """Get mock Stage 2 ranking responses from all models.

    Returns:
        List of mock ranking responses
    """
    return [
        {
            "model": "anthropic/claude-3.5-sonnet",
            "ranking_text": get_mock_ranking_response(
                "anthropic/claude-3.5-sonnet",
                ["Response C", "Response A", "Response B", "Response D"]
            )
        },
        {
            "model": "openai/gpt-4-turbo",
            "ranking_text": get_mock_ranking_response(
                "openai/gpt-4-turbo",
                ["Response A", "Response C", "Response D", "Response B"]
            )
        },
        {
            "model": "google/gemini-pro",
            "ranking_text": get_mock_ranking_response(
                "google/gemini-pro",
                ["Response A", "Response B", "Response C", "Response D"]
            )
        },
        {
            "model": "meta-llama/llama-3-70b",
            "ranking_text": get_mock_ranking_response(
                "meta-llama/llama-3-70b",
                ["Response C", "Response A", "Response D", "Response B"]
            )
        },
    ]


# ==================== Stage 3: Chairman Synthesis ====================

def get_mock_chairman_response(include_dissent: bool = True) -> str:
    """Generate a mock chairman synthesis response.

    Args:
        include_dissent: Whether to include dissenting opinions

    Returns:
        Mock chairman synthesis text
    """
    dissent_section = ""
    if include_dissent:
        dissent_section = """
**Dissenting Opinions:**
- Some council members advocated for more aggressive positioning
- One member suggested waiting for clearer signals before committing capital
"""

    return f"""After careful consideration of all council member responses and their evaluations, here is my synthesis:

**Consensus View:**
The council generally agrees that the current market environment requires selective positioning with attention to risk management. There is broad support for maintaining exposure while being cognizant of elevated valuations and potential volatility.

**Key Points of Agreement:**
1. Market structure remains constructive but stretched
2. Liquidity conditions are supportive in the near term
3. Macro backdrop suggests cautious optimism
4. Quality and defensive characteristics are important

**Recommended Action:**
Maintain balanced exposure with focus on quality names. Consider modest hedging to protect against tail risks. Monitor key technical levels for signs of deterioration.
{dissent_section}
**Final Decision:**
The council recommends a LONG position in SPY with moderate conviction (+1.2), reflecting cautious optimism with appropriate risk management.
"""


def get_mock_chairman_fallback_response() -> str:
    """Generate a mock chairman fallback response (when API fails).

    Returns:
        Mock fallback response
    """
    return """[Chairman synthesis unavailable - API error]

Based on aggregated rankings from peer review, the highest-ranked response is presented below as the fallback decision:

Response A (Average rank: 1.75) recommended balanced positioning with selective exposure to quality growth names. Risk management through position sizing and hedging was emphasized given elevated valuations.

This fallback represents the consensus view but lacks the depth and synthesis that would come from the Chairman model.
"""


# ==================== Complete Council Flow ====================

def get_mock_full_council_flow() -> Dict[str, Any]:
    """Get complete mock council flow with all 3 stages.

    Returns:
        Dict with stage1, stage2, and stage3 mock data
    """
    return {
        "stage1_responses": get_mock_stage1_responses(),
        "stage2_rankings": get_mock_stage2_responses(),
        "stage3_synthesis": get_mock_chairman_response(),
        "aggregate_rankings": {
            "Response A": 2.0,   # Average position: 2.0
            "Response C": 1.75,  # Highest ranked overall
            "Response D": 3.0,
            "Response B": 3.25,  # Lowest ranked
        }
    }


# ==================== Parsed Rankings ====================

def get_parsed_rankings() -> List[str]:
    """Get example of parsed rankings from a ranking response.

    Returns:
        List of response labels in ranked order
    """
    return ["Response C", "Response A", "Response B", "Response D"]


def get_aggregate_rankings() -> Dict[str, float]:
    """Get example of aggregate rankings (average positions).

    Returns:
        Dict mapping response labels to average rank positions
    """
    return {
        "Response A": 2.0,
        "Response C": 1.5,
        "Response B": 3.25,
        "Response D": 3.25,
    }


# ==================== Error Scenarios ====================

def get_mock_empty_stage1_responses() -> List[Dict[str, Any]]:
    """Get empty Stage 1 responses (all models failed).

    Returns:
        Empty list simulating complete API failure
    """
    return []


def get_mock_partial_stage2_rankings() -> List[Dict[str, Any]]:
    """Get Stage 2 rankings with some models failing to provide valid rankings.

    Returns:
        List of ranking responses with some malformed
    """
    return [
        {
            "model": "anthropic/claude-3.5-sonnet",
            "ranking_text": get_mock_ranking_response(
                "anthropic/claude-3.5-sonnet",
                ["Response A", "Response B", "Response C"]
            )
        },
        {
            "model": "openai/gpt-4-turbo",
            "ranking_text": get_mock_ranking_response_malformed("openai/gpt-4-turbo")
        },
        {
            "model": "google/gemini-pro",
            "ranking_text": get_mock_ranking_response(
                "google/gemini-pro",
                ["Response C", "Response A", "Response B"]
            )
        },
    ]


# ==================== Label Mappings ====================

def get_label_to_model_mapping() -> Dict[str, str]:
    """Get example label_to_model mapping from Stage 2.

    Returns:
        Dict mapping response labels to model names
    """
    return {
        "Response A": "anthropic/claude-3.5-sonnet",
        "Response B": "openai/gpt-4-turbo",
        "Response C": "google/gemini-pro",
        "Response D": "meta-llama/llama-3-70b",
    }


# ==================== Helper Functions ====================

def create_custom_stage1_response(
    model: str,
    content: str,
    success: bool = True
) -> Dict[str, Any]:
    """Create a custom Stage 1 response for testing specific scenarios.

    Args:
        model: Model name
        content: Response content
        success: Whether this is a successful response

    Returns:
        Custom mock response
    """
    if success:
        return {
            "model": model,
            "response": content,
        }
    else:
        return {
            "model": model,
            "response": None,
            "error": "Simulated API failure"
        }


def create_custom_ranking_response(
    model: str,
    rankings: List[str],
    valid_format: bool = True
) -> Dict[str, Any]:
    """Create a custom ranking response for testing specific scenarios.

    Args:
        model: Model name
        rankings: List of response labels in order
        valid_format: Whether to use valid FINAL RANKING format

    Returns:
        Custom mock ranking response
    """
    if valid_format:
        ranking_text = get_mock_ranking_response(model, rankings)
    else:
        ranking_text = get_mock_ranking_response_malformed(model)

    return {
        "model": model,
        "ranking_text": ranking_text,
    }
