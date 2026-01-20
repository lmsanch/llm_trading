"""Sample PM pitch fixtures for testing.

This module provides comprehensive PM pitch test data including:
- Valid pitches with various instruments and directions
- Edge case pitches (min/max conviction, boundary values)
- Invalid pitches for validation testing
"""

from datetime import datetime, timezone
from typing import Dict, Any
import uuid


# ==================== Risk Profiles ====================

RISK_PROFILES = {
    "TIGHT": {"stop_loss_pct": 0.010, "take_profit_pct": 0.015},
    "BASE": {"stop_loss_pct": 0.015, "take_profit_pct": 0.025},
    "WIDE": {"stop_loss_pct": 0.020, "take_profit_pct": 0.035},
}


# ==================== Valid Pitch Examples ====================

def get_valid_long_pitch(
    instrument: str = "SPY",
    conviction: float = 1.5,
    model: str = "openai/gpt-4-turbo",
) -> Dict[str, Any]:
    """Generate a valid LONG pitch.

    Args:
        instrument: Trading instrument
        conviction: Conviction level (positive for LONG)
        model: Model name

    Returns:
        Valid PM pitch dictionary
    """
    return {
        "idea_id": str(uuid.uuid4()),
        "week_id": get_current_week_id(),
        "model": model,
        "instrument": instrument,
        "direction": "LONG",
        "horizon": "1w",
        "thesis_bullets": [
            "Fed pivot expectations support risk assets",
            "Seasonal patterns historically bullish in Q1",
            "Liquidity conditions improving"
        ],
        "entry_mode": "limit",
        "entry_price": 450.0,
        "risk_profile": "BASE",
        "exit_event": "NFP",
        "indicators": [
            {
                "name": "Price vs Year High",
                "value": "Within 5% of 52-week high",
                "interpretation": "Strength continuation likely"
            },
            {
                "name": "Volatility Regime",
                "value": "VIX at 15 (low)",
                "interpretation": "Calm environment favors longs"
            }
        ],
        "invalidation": "Break below 445 support",
        "conviction": conviction,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_valid_short_pitch(
    instrument: str = "TLT",
    conviction: float = -1.5,
    model: str = "anthropic/claude-3.5-sonnet",
) -> Dict[str, Any]:
    """Generate a valid SHORT pitch.

    Args:
        instrument: Trading instrument
        conviction: Conviction level (negative for SHORT)
        model: Model name

    Returns:
        Valid PM pitch dictionary
    """
    return {
        "idea_id": str(uuid.uuid4()),
        "week_id": get_current_week_id(),
        "model": model,
        "instrument": instrument,
        "direction": "SHORT",
        "horizon": "1w",
        "thesis_bullets": [
            "Fed maintaining higher-for-longer stance",
            "Strong labor market supports hawkish policy",
            "Inflation risks remain elevated"
        ],
        "entry_mode": "limit",
        "entry_price": 95.0,
        "risk_profile": "TIGHT",
        "exit_event": "CPI",
        "indicators": [
            {
                "name": "Yield Curve",
                "value": "2Y-10Y spread widening",
                "interpretation": "Rate pressure persisting"
            },
            {
                "name": "Central Bank Flow",
                "value": "QT continues at $95B/month",
                "interpretation": "Supply pressure on bonds"
            }
        ],
        "invalidation": "Break above 97 resistance",
        "conviction": conviction,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_valid_flat_pitch(
    model: str = "google/gemini-pro",
) -> Dict[str, Any]:
    """Generate a valid FLAT (no position) pitch.

    Args:
        model: Model name

    Returns:
        Valid FLAT pitch dictionary
    """
    return {
        "idea_id": str(uuid.uuid4()),
        "week_id": get_current_week_id(),
        "model": model,
        "instrument": "NONE",
        "direction": "FLAT",
        "horizon": "1w",
        "thesis_bullets": [
            "Too many conflicting signals",
            "Major event risk (FOMC) this week",
            "Market at critical inflection point"
        ],
        "entry_mode": "NONE",
        "entry_price": None,
        "risk_profile": "NONE",
        "exit_event": None,
        "indicators": [],
        "invalidation": "N/A",
        "conviction": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ==================== Edge Case Pitches ====================

def get_max_conviction_pitch() -> Dict[str, Any]:
    """Get pitch with maximum conviction (+2.0)."""
    pitch = get_valid_long_pitch(conviction=2.0)
    pitch["thesis_bullets"].append("Extremely high conviction setup")
    return pitch


def get_min_conviction_pitch() -> Dict[str, Any]:
    """Get pitch with minimum conviction (-2.0)."""
    pitch = get_valid_short_pitch(conviction=-2.0)
    pitch["thesis_bullets"].append("Extremely high conviction short")
    return pitch


def get_zero_conviction_flat_pitch() -> Dict[str, Any]:
    """Get FLAT pitch with zero conviction."""
    return get_valid_flat_pitch()


def get_low_conviction_long_pitch() -> Dict[str, Any]:
    """Get LONG pitch with low conviction (+0.5)."""
    return get_valid_long_pitch(conviction=0.5)


def get_low_conviction_short_pitch() -> Dict[str, Any]:
    """Get SHORT pitch with low conviction (-0.5)."""
    return get_valid_short_pitch(conviction=-0.5)


# ==================== Invalid Pitches for Testing ====================

def get_invalid_conviction_pitch() -> Dict[str, Any]:
    """Get pitch with invalid conviction (out of range)."""
    pitch = get_valid_long_pitch()
    pitch["conviction"] = 3.0  # Invalid: > 2.0
    return pitch


def get_invalid_instrument_pitch() -> Dict[str, Any]:
    """Get pitch with invalid instrument."""
    pitch = get_valid_long_pitch()
    pitch["instrument"] = "INVALID"
    return pitch


def get_invalid_direction_pitch() -> Dict[str, Any]:
    """Get pitch with invalid direction."""
    pitch = get_valid_long_pitch()
    pitch["direction"] = "SIDEWAYS"  # Invalid direction
    return pitch


def get_banned_indicator_pitch() -> Dict[str, Any]:
    """Get pitch with banned technical indicator."""
    pitch = get_valid_long_pitch()
    pitch["indicators"] = [
        {
            "name": "RSI",  # BANNED!
            "value": "RSI at 70",
            "interpretation": "Overbought condition"
        }
    ]
    pitch["thesis_bullets"].append("Technical indicators show MACD divergence")  # BANNED!
    return pitch


def get_missing_required_field_pitch() -> Dict[str, Any]:
    """Get pitch missing required field."""
    pitch = get_valid_long_pitch()
    del pitch["instrument"]  # Remove required field
    return pitch


def get_invalid_risk_profile_pitch() -> Dict[str, Any]:
    """Get pitch with invalid risk profile."""
    pitch = get_valid_long_pitch()
    pitch["risk_profile"] = "CUSTOM"  # Invalid: not in RISK_PROFILES
    return pitch


def get_invalid_entry_mode_pitch() -> Dict[str, Any]:
    """Get pitch with invalid entry mode."""
    pitch = get_valid_long_pitch()
    pitch["entry_mode"] = "market"  # Invalid: only 'limit' allowed
    return pitch


def get_invalid_exit_event_pitch() -> Dict[str, Any]:
    """Get pitch with invalid exit event."""
    pitch = get_valid_long_pitch()
    pitch["exit_event"] = "EARNINGS"  # Invalid: not in EXIT_EVENTS
    return pitch


# ==================== Multiple Pitch Scenarios ====================

def get_all_pm_pitches() -> list[Dict[str, Any]]:
    """Get pitches from all 5 PM models (realistic scenario).

    Returns:
        List of 5 pitches from different models
    """
    return [
        get_valid_long_pitch(instrument="SPY", conviction=1.5, model="openai/gpt-4-turbo"),
        get_valid_short_pitch(instrument="TLT", conviction=-1.2, model="anthropic/claude-3.5-sonnet"),
        get_valid_long_pitch(instrument="GLD", conviction=1.8, model="google/gemini-pro"),
        get_valid_flat_pitch(model="meta-llama/llama-3-70b"),
        get_valid_long_pitch(instrument="QQQ", conviction=1.0, model="cohere/command-r-plus"),
    ]


def get_conflicting_pitches() -> list[Dict[str, Any]]:
    """Get conflicting pitches (some LONG, some SHORT on same instrument).

    Returns:
        List of conflicting pitches for chairman decision
    """
    return [
        get_valid_long_pitch(instrument="SPY", conviction=1.5, model="openai/gpt-4-turbo"),
        get_valid_short_pitch(instrument="SPY", conviction=-1.0, model="anthropic/claude-3.5-sonnet"),
        get_valid_long_pitch(instrument="SPY", conviction=0.8, model="google/gemini-pro"),
    ]


def get_unanimous_pitches() -> list[Dict[str, Any]]:
    """Get unanimous pitches (all agree on direction).

    Returns:
        List of pitches all agreeing LONG on SPY
    """
    return [
        get_valid_long_pitch(instrument="SPY", conviction=1.5, model="openai/gpt-4-turbo"),
        get_valid_long_pitch(instrument="SPY", conviction=1.8, model="anthropic/claude-3.5-sonnet"),
        get_valid_long_pitch(instrument="SPY", conviction=2.0, model="google/gemini-pro"),
    ]


# ==================== Helper Functions ====================

def get_current_week_id() -> str:
    """Get current week ID in YYYY-MM-DD format (Monday of current week)."""
    from datetime import datetime, timedelta
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.strftime("%Y-%m-%d")


def validate_pitch_structure(pitch: Dict[str, Any]) -> bool:
    """Validate that a pitch has required fields.

    Args:
        pitch: Pitch dictionary to validate

    Returns:
        True if all required fields present
    """
    required_fields = [
        "idea_id",
        "week_id",
        "model",
        "instrument",
        "direction",
        "horizon",
        "thesis_bullets",
        "conviction",
        "timestamp",
    ]
    return all(field in pitch for field in required_fields)
