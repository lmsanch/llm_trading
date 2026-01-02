"""Gemini Deep Research API client (direct Google API with async polling)."""

import os
import json
import re
import time
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
import httpx

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini Deep Research model
GEMINI_DEEP_RESEARCH_MODEL = "deep-research-pro-preview-12-2025"


async def query_gemini_research(
    prompt: str,
    market_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Query Gemini Deep Research API for macro research.

    Uses agentic Deep Research model with async polling.

    Args:
        prompt: Research prompt (from config/prompts/research_prompt.md)
        market_data: Market snapshot data (prices, account info, etc.)

    Returns:
        Dict with:
        - natural_language: Full research report text
        - structured_json: Parsed JSON research pack
        - model: Model identifier
        - source: "gemini"
    """
    if not GEMINI_API_KEY:
        return _error_response("GEMINI_API_KEY not found in environment")

    # Build the full prompt with market context
    full_prompt = _build_prompt(prompt, market_data)

    try:
        # 1. Start the research task (background=true)
        interaction_id = await _start_research(full_prompt)
        print(f"  🧠 Gemini Deep Research started. ID: {interaction_id}")

        # 2. Poll for completion
        result = await _poll_research(interaction_id)

        if not result or result.get("state") != "completed":
            return _error_response(f"Research failed or timed out. State: {result.get('state') if result else 'unknown'}")

        # 3. Extract content - try outputs array first, then output object
        outputs = result.get("outputs", [])
        if outputs and len(outputs) > 0:
            last_output = outputs[-1]
            if isinstance(last_output, dict):
                content = last_output.get("text", "").strip()
            else:
                content = str(last_output).strip()
        else:
            # Fallback to output object
            content = result.get("output", {}).get("text", "").strip()

        if not content:
            return _error_response("Empty response from Gemini Deep Research")

        # Parse the response
        return _parse_research_response(content, "gemini", GEMINI_DEEP_RESEARCH_MODEL)

    except Exception as e:
        return _error_response(f"Error: {str(e)}")


async def _start_research(prompt: str) -> str:
    """Start a Deep Research task and return interaction ID."""
    # Note: No trailing slash before ?key=
    url = f"https://generativelanguage.googleapis.com/v1beta/interactions?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "agent": GEMINI_DEEP_RESEARCH_MODEL,
        "input": prompt,
        "background": True  # Required for Deep Research
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Debug: print full response to understand format
        print(f"  🐛 Gemini API response: {json.dumps(data, indent=2)}")

        # Extract interaction ID
        # The API can return "name": "interactions/ID" or just "id": "ID"
        interaction_id = data.get("name", "") or data.get("id", "") or data.get("interactionId", "")
        
        if not interaction_id:
            print(f"  ❌ Gemini API response missing identifier. Full response: {data}")
            raise ValueError(f"Gemini Deep Research API did not return an interaction ID. Response: {data}")

        # Extract just the ID from "interactions/ID" format if present
        if "/" in interaction_id:
            parts = interaction_id.split("/")
            # Find the part after "interactions" if it exists, otherwise take the last part
            if "interactions" in parts:
                idx = parts.index("interactions")
                if idx + 1 < len(parts):
                    interaction_id = parts[idx + 1]
                else:
                    interaction_id = parts[-1]
            else:
                interaction_id = parts[-1]

        # Ensure we don't return an empty string if split result is empty
        if not interaction_id or interaction_id == "interactions":
             # Fallback: take the whole 'name' if split failed somehow, 
             # but check if there's any other field
             interaction_id = data.get("id", "") or data.get("interactionId", "") or interaction_id

        print(f"  ✅ Gemini interaction ID: {interaction_id}")
        return interaction_id


async def _poll_research(interaction_id: str, max_wait_seconds: int = 600) -> Dict[str, Any]:
    """Poll for research completion."""
    url = f"https://generativelanguage.googleapis.com/v1beta/interactions/{interaction_id}?key={GEMINI_API_KEY}"

    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # The API might use "state" or "status"
            state = data.get("state") or data.get("status") or ""
            state = state.lower()

            if state in ["completed", "complete", "done", "succeeded"]:
                print("  🧠 Gemini Deep Research completed!")
                # Ensure we have state set to completed for the caller
                data["state"] = "completed"
                return data
            elif state in ["failed", "error", "canceled", "cancelled"]:
                print(f"  ❌ Gemini Deep Research failed! (state: {state})")
                data["state"] = "failed"
                return data
            else:
                # Still running: in_progress, running, pending, active
                print(f"  ⏳ Gemini Deep Research polling... (state: {state})")
                await asyncio.sleep(10)  # Wait 10 seconds before polling again

    return {"state": "timeout"}


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
        "source": "gemini",
        "model": GEMINI_DEEP_RESEARCH_MODEL,
        "natural_language": f"Error: {error_msg}",
        "structured_json": _empty_research_pack(),
        "error": error_msg,
        "generated_at": _get_timestamp()
    }


def _get_timestamp() -> str:
    """Get current ISO timestamp."""
    from datetime import datetime
    return datetime.utcnow().isoformat()
