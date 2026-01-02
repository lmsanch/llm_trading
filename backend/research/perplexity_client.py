"""Perplexity Sonar Deep Research API client (direct Perplexity API)."""

import os
import json
import re
from typing import Dict, Any
from dotenv import load_dotenv
import httpx

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Perplexity Sonar Deep Research model
PERPLEXITY_DEEP_RESEARCH_MODEL = "sonar-deep-research"


async def query_perplexity_research(
    prompt: str,
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Query Perplexity Sonar Deep Research API for macro research.

    Uses agentic Deep Research model with reasoning_effort parameter.

    Args:
        prompt: Research prompt (from config/prompts/research_prompt.md)
        market_data: Market snapshot data (prices, account info, etc.)

    Returns:
        Dict with:
        - natural_language: Full research report text
        - structured_json: Parsed JSON research pack
        - model: Model identifier
        - source: "perplexity"
    """
    if not PERPLEXITY_API_KEY:
        return _error_response("PERPLEXITY_API_KEY not found in environment")

    # Build the full prompt with market context
    full_prompt = _build_prompt(prompt, market_data)

    # Perplexity Sonar Deep Research API endpoint
    url = "https://api.perplexity.ai/chat/completions"

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": PERPLEXITY_DEEP_RESEARCH_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a senior macro research analyst providing actionable trading insights. Keep your report SHORT (1000-2000 words max) and focused on the NEXT 7 DAYS ONLY. Always provide both a natural language report AND structured JSON data."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        "reasoning_effort": "high",  # Options: low, medium, high
        "temperature": 0.7,
        "max_tokens": 16384,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            print("  📊 Querying Perplexity Sonar Deep Research...")
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract the content
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                return _error_response("Empty response from Perplexity")

            print("  ✅ Perplexity Sonar Deep Research completed!")
            # Parse the response
            return _parse_research_response(content, "perplexity", PERPLEXITY_DEEP_RESEARCH_MODEL)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 401:
            return _error_response("Invalid API key. Check PERPLEXITY_API_KEY.")
        elif status == 429:
            return _error_response("Rate limit exceeded. Try again later.")
        else:
            return _error_response(f"HTTP error: {status}")
    except Exception as e:
        return _error_response(f"Error: {str(e)}")


def _build_prompt(prompt_template: str, market_data: Dict[str, Any]) -> str:
    """Build full prompt with market context."""
    asof = market_data.get("asof_et", "Unknown")
    account_info = market_data.get("account_info", {})
    instruments = market_data.get("instruments", {})

    market_context = f"""
MARKET SNAPSHOT:
- As of: {asof}
- Portfolio Value: ${account_info.get('portfolio_value', 'N/A')}
- Cash: ${account_info.get('cash', 'N/A')}
- Buying Power: ${account_info.get('buying_power', 'N/A')}

CURRENT PRICES:
{_format_instruments(instruments)}
"""

    return f"{prompt_template}\n\n{market_context}"


def _format_instruments(instruments: Dict[str, Any]) -> str:
    """Format instruments for prompt."""
    lines = []
    for symbol, data in instruments.items():
        error = data.get("error", "")
        if error:
            lines.append(f"- {symbol}: Error - {error}")
        else:
            current = data.get("current", {})
            price = current.get("price", 0.0)
            change = current.get("change_pct", 0.0)
            direction = "▲" if change > 0 else "▼" if change < 0 else "▬"
            lines.append(f"- {symbol}: ${price:.2f} ({direction} {abs(change):.2f}%)")
    return "\n".join(lines)


def _parse_research_response(content: str, source: str, model: str) -> Dict[str, Any]:
    """
    Parse research response from LLM.

    Returns dict with natural_language and structured_json.
    """
    # The full content is the natural language report
    natural_language = content

    # Extract JSON from the response
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON without markdown code blocks
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        json_str = json_match.group(0) if json_match else "{}"

    # Parse JSON
    try:
        structured_json = json.loads(json_str)
    except json.JSONDecodeError:
        # If JSON parsing fails, return empty structure
        structured_json = _empty_research_pack()

    return {
        "source": source,
        "model": model,
        "natural_language": natural_language,
        "structured_json": structured_json,
        "generated_at": _get_timestamp()
    }


def _empty_research_pack() -> Dict[str, Any]:
    """Return empty research pack structure."""
    return {
        "macro_regime": {
            "risk_mode": "NEUTRAL",
            "description": "Research unavailable"
        },
        "top_narratives": [],
        "tradable_candidates": [],
        "event_calendar": [],
        "confidence_notes": {
            "known_unknowns": "Parse error",
            "data_quality_flags": ["json_parse_failed"]
        }
    }


def _error_response(error_msg: str) -> Dict[str, Any]:
    """Return error response."""
    return {
        "source": "perplexity",
        "model": PERPLEXITY_DEEP_RESEARCH_MODEL,
        "natural_language": f"Error: {error_msg}",
        "structured_json": _empty_research_pack(),
        "error": error_msg,
        "generated_at": _get_timestamp()
    }


def _get_timestamp() -> str:
    """Get current ISO timestamp."""
    from datetime import datetime
    return datetime.utcnow().isoformat()
