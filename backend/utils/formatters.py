"""Formatting functions for frontend API responses."""

import logging
from typing import Dict, Any, List

from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.research import (
    RESEARCH_PACK_A,
    RESEARCH_PACK_B,
    MARKET_SNAPSHOT,
)
from backend.pipeline.stages.pm_pitch import PM_PITCHES
from backend.pipeline.stages.chairman import CHAIRMAN_DECISION
from backend.pipeline.stages.execution import EXECUTION_RESULT

logger = logging.getLogger(__name__)


def _format_research_for_frontend(context: PipelineContext) -> Dict[str, Any]:
    """
    Format research packs for frontend display.

    Args:
        context: PipelineContext containing research data

    Returns:
        Dict with research_pack_a, research_pack_b, and market_snapshot

    Example Response:
        {
            "perplexity": {
                "source": "perplexity",
                "model": "perplexity-sonar-pro",
                "natural_language": "...",
                "macro_regime": {...},
                "top_narratives": [...],
                "asset_setups": [...],
                "event_calendar": [...],
                "confidence_notes": {...},
                "status": "complete",
                "generated_at": "2024-01-09T12:00:00Z"
            },
            "gemini": {...},
            "market_snapshot": {...}
        }
    """
    research_a = context.get(RESEARCH_PACK_A)
    research_b = context.get(RESEARCH_PACK_B)
    market_snapshot = context.get(MARKET_SNAPSHOT)

    result = {}

    if market_snapshot:
        result["market_snapshot"] = market_snapshot

    if research_a:
        # Extract from new dual-format response (natural_language + structured_json)
        structured = research_a.get("structured_json", {})
        result["perplexity"] = {
            "source": research_a.get("source", "perplexity"),
            "model": research_a.get("model", "perplexity-sonar-pro"),
            "natural_language": research_a.get("natural_language", ""),
            "macro_regime": structured.get("macro_regime", {}),
            "top_narratives": structured.get("top_narratives", []),
            # Support both old (tradable_candidates) and new (asset_setups) formats
            "tradable_candidates": structured.get("tradable_candidates")
            or structured.get("asset_setups", []),
            "asset_setups": structured.get("asset_setups")
            or structured.get("tradable_candidates", []),
            "event_calendar": structured.get("event_calendar")
            or structured.get("event_calendar_next_7d", []),
            "confidence_notes": structured.get("confidence_notes", {}),
            "status": "complete" if not research_a.get("error") else "error",
            "generated_at": research_a.get("generated_at", ""),
        }

    if research_b:
        # Extract from new dual-format response (natural_language + structured_json)
        structured = research_b.get("structured_json", {})
        result["gemini"] = {
            "source": research_b.get("source", "gemini"),
            "model": research_b.get("model", "gemini-2.0-flash-thinking"),
            "natural_language": research_b.get("natural_language", ""),
            "macro_regime": structured.get("macro_regime", {}),
            "top_narratives": structured.get("top_narratives", []),
            # Support both old (tradable_candidates) and new (asset_setups) formats
            "tradable_candidates": structured.get("tradable_candidates")
            or structured.get("asset_setups", []),
            "asset_setups": structured.get("asset_setups")
            or structured.get("tradable_candidates", []),
            "event_calendar": structured.get("event_calendar")
            or structured.get("event_calendar_next_7d", []),
            "confidence_notes": structured.get("confidence_notes", {}),
            "status": "complete" if not research_b.get("error") else "error",
            "generated_at": research_b.get("generated_at", ""),
        }

    return result


def _format_pitches_for_frontend(context: PipelineContext) -> List[Dict[str, Any]]:
    """
    Format PM pitches for frontend display.

    Args:
        context: PipelineContext containing pitch data

    Returns:
        List of pitch dicts with model, account, instrument, direction, etc.

    Example Response:
        [
            {
                "id": 1,
                "model": "gpt-4o",
                "account": "paper",
                "instrument": "SPY",
                "direction": "LONG",
                "horizon": "7 days",
                "conviction": 7,
                "thesis_bullets": ["..."],
                "risk_profile": "BASE",
                "entry_policy": {...},
                "exit_policy": {...},
                "risk_notes": "...",
                "status": "complete"
            }
        ]
    """
    pitches = context.get(PM_PITCHES, [])

    formatted = []
    for i, pitch in enumerate(pitches):
        model_info = pitch.get("model_info", {})
        formatted.append(
            {
                "id": i + 1,
                "model": pitch.get("model", "unknown"),
                "account": model_info.get("account", "Unknown"),
                "instrument": pitch.get(
                    "selected_instrument", pitch.get("instrument", "N/A")
                ),
                "selected_instrument": pitch.get(
                    "selected_instrument", pitch.get("instrument", "N/A")
                ),
                "direction": pitch.get("direction", "FLAT"),
                "horizon": pitch.get("horizon", "N/A"),
                "conviction": pitch.get("conviction", 0),
                "thesis_bullets": pitch.get("thesis_bullets", []),
                "risk_profile": pitch.get("risk_profile", "BASE"),
                "entry_policy": pitch.get("entry_policy", {}),
                "exit_policy": pitch.get("exit_policy", {}),
                "risk_notes": pitch.get("risk_notes", "N/A"),
                "status": "complete",
            }
        )

    return formatted


def _format_council_for_frontend(context: PipelineContext) -> Dict[str, Any]:
    """
    Format council decision for frontend display.

    Args:
        context: PipelineContext containing council decision

    Returns:
        Dict with chairman decision and peer reviews

    Example Response:
        {
            "selected_trade": {
                "instrument": "SPY",
                "direction": "LONG",
                "conviction": 8,
                "position_size": "10%"
            },
            "rationale": "...",
            "dissent_summary": [...],
            "monitoring_plan": {
                "key_levels": [...],
                "event_risks": [...]
            },
            "peer_review_scores": {...},
            "peer_reviews": [...]
        }
    """
    decision = context.get(CHAIRMAN_DECISION)

    if not decision:
        return {}

    selected_trade = decision.get("selected_trade", {})

    return {
        "selected_trade": {
            "instrument": selected_trade.get("instrument", "N/A"),
            "direction": selected_trade.get("direction", "FLAT"),
            "conviction": decision.get("conviction", 0),
            "position_size": selected_trade.get("position_size", "0%"),
        },
        "rationale": decision.get("rationale", ""),
        "dissent_summary": decision.get("dissent_summary", []),
        "monitoring_plan": {
            "key_levels": decision.get("monitoring_plan", {}).get("key_levels", []),
            "event_risks": decision.get("monitoring_plan", {}).get("event_risks", []),
        },
        "peer_review_scores": decision.get("peer_review_scores", {}),
        "peer_reviews": context.get("peer_reviews", []),
    }


def _format_trades_for_frontend(context: PipelineContext) -> List[Dict[str, Any]]:
    """
    Format trades for frontend display.

    Args:
        context: PipelineContext containing trade data

    Returns:
        List of trade dicts with id, account, symbol, direction, qty, etc.

    Example Response:
        [
            {
                "id": 101,
                "account": "COUNCIL",
                "symbol": "SPY",
                "direction": "BUY",
                "qty": 50,
                "status": "pending",
                "conviction": 8
            }
        ]
    """
    execution_result = context.get(EXECUTION_RESULT)

    if not execution_result or not execution_result.get("executed"):
        # Generate pending trades from council decision
        decision = context.get(CHAIRMAN_DECISION)
        if not decision:
            return []

        selected_trade = decision.get("selected_trade", {})
        conviction = decision.get("conviction", 0)

        # Create pending trades for all accounts
        from backend.requesty_client import REQUESTY_MODELS

        trades = []
        for model_key, config in REQUESTY_MODELS.items():
            account = config["account"]
            if account == "COUNCIL":
                # Council trade from chairman decision
                trades.append(
                    {
                        "id": len(trades) + 101,
                        "account": account,
                        "symbol": selected_trade.get("instrument", "SPY"),
                        "direction": "BUY"
                        if selected_trade.get("direction") == "LONG"
                        else "SELL",
                        "qty": 50,  # Would calculate from conviction
                        "status": "pending",
                        "conviction": conviction,
                    }
                )

        return trades

    # Return executed trades
    return execution_result.get("trades", [])
