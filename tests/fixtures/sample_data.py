"""Sample data fixtures for testing.

This module provides sample data structures used across multiple tests,
including basic market data, account info, and generic test data.
"""

from datetime import datetime, timezone
from typing import Dict, Any


# ==================== Sample Market Data ====================

def get_sample_market_snapshot() -> Dict[str, Any]:
    """Get a sample market snapshot for testing.

    Returns:
        Dict representing a market snapshot with prices and indicators
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prices": {
            "SPY": 450.25,
            "QQQ": 380.50,
            "IWM": 195.75,
            "TLT": 95.30,
            "GLD": 180.40,
            "UUP": 28.15,
        },
        "indicators": {
            "SPY": {
                "sma_20": 448.50,
                "sma_50": 445.00,
                "volume": 85000000,
            },
            "QQQ": {
                "sma_20": 378.25,
                "sma_50": 375.50,
                "volume": 55000000,
            },
        },
    }


def get_sample_account_info() -> Dict[str, Any]:
    """Get sample Alpaca account information.

    Returns:
        Dict representing account information from Alpaca API
    """
    return {
        "account_number": "TEST123456",
        "status": "ACTIVE",
        "currency": "USD",
        "cash": "100000.00",
        "portfolio_value": "100000.00",
        "buying_power": "200000.00",
        "equity": "100000.00",
        "last_equity": "100000.00",
        "long_market_value": "0.00",
        "short_market_value": "0.00",
        "initial_margin": "0.00",
        "maintenance_margin": "0.00",
        "daytrade_count": 0,
        "pattern_day_trader": False,
    }


def get_sample_position() -> Dict[str, Any]:
    """Get a sample position from Alpaca.

    Returns:
        Dict representing a position in a trading account
    """
    return {
        "asset_id": "b0b6dd9d-8b9b-48a9-ba46-b9d54906e415",
        "symbol": "SPY",
        "exchange": "ARCA",
        "asset_class": "us_equity",
        "avg_entry_price": "445.50",
        "qty": "10",
        "side": "long",
        "market_value": "4502.50",
        "cost_basis": "4455.00",
        "unrealized_pl": "47.50",
        "unrealized_plpc": "0.0106",
        "unrealized_intraday_pl": "47.50",
        "unrealized_intraday_plpc": "0.0106",
        "current_price": "450.25",
        "lastday_price": "447.00",
        "change_today": "0.0073",
    }


# ==================== Sample Council Responses ====================

def get_sample_model_response(model_name: str, content: str) -> Dict[str, Any]:
    """Generate a sample model response.

    Args:
        model_name: Name of the model
        content: Response content

    Returns:
        Dict representing a model response
    """
    return {
        "model": model_name,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def get_sample_ranking_response(label: str, rankings: list[str]) -> str:
    """Generate a sample ranking response text.

    Args:
        label: Label of the ranking model (e.g., "Model A")
        rankings: List of response labels in ranked order

    Returns:
        String formatted as a ranking response
    """
    ranking_text = ", ".join(rankings)
    return f"""After careful analysis of all responses, here is my evaluation:

Response A provides a comprehensive view with strong reasoning.
Response B offers interesting perspective but lacks depth.
Response C has good technical analysis.

FINAL RANKING: {ranking_text}
"""


# ==================== Sample Pitch Data ====================

def get_sample_pitch(
    instrument: str = "SPY",
    direction: str = "LONG",
    conviction: float = 1.5
) -> Dict[str, Any]:
    """Generate a sample PM pitch.

    Args:
        instrument: Trading instrument (e.g., "SPY")
        direction: Trade direction ("LONG", "SHORT", or "FLAT")
        conviction: Conviction level (-2.0 to +2.0)

    Returns:
        Dict representing a PM pitch
    """
    return {
        "idea_id": "test-idea-001",
        "week_id": "2025-01-20",
        "model": "openai/gpt-4-turbo",
        "instrument": instrument,
        "direction": direction,
        "horizon": "1w",
        "thesis_bullets": [
            "Strong momentum in tech sector",
            "Fed pause signals continued support",
            "Seasonal patterns favor equities"
        ],
        "indicators": [
            {"name": "Price vs SMA50", "value": "Above by 2%"},
            {"name": "Volume trend", "value": "Increasing"},
        ],
        "invalidation": "Break below 445 support level",
        "conviction": conviction,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ==================== Test Constants ====================

VALID_INSTRUMENTS = ["SPY", "QQQ", "IWM", "TLT", "IEF", "HYG", "LQD", "UUP", "GLD", "USO"]

VALID_DIRECTIONS = ["LONG", "SHORT", "FLAT"]

VALID_EXIT_EVENTS = ["NFP", "CPI", "FOMC"]

RISK_PROFILES = {
    "TIGHT": {"stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    "BASE": {"stop_loss_pct": 0.03, "take_profit_pct": 0.06},
    "WIDE": {"stop_loss_pct": 0.05, "take_profit_pct": 0.10},
}
