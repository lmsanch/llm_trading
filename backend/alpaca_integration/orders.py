"""Alpaca bracket order utilities."""

from typing import Dict, Any, Optional


def create_bracket_order_from_pitch(client, pitch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a bracket order from PM pitch data.

    A bracket order includes:
    - Main order (market order)
    - Take profit order (limit order)
    - Stop loss order (stop order)

    Args:
        client: AlpacaAccountClient instance
        pitch: PM pitch dict with trade details

    Returns:
        Dict with order details (symbol, side, qty, take_profit_price, stop_loss_price)
    """
    selected_instrument = pitch.get("selected_instrument") or pitch.get("instrument")
    direction = pitch.get("direction", "FLAT")
    conviction = pitch.get("conviction", 1.0)

    if not selected_instrument or direction == "FLAT":
        return None

    # Determine order side
    side = "buy" if direction == "LONG" else "sell"

    # Calculate position size based on conviction
    # Simple logic: conviction 1.0 = 50 shares, scaled up/down
    qty = int(50 * conviction)

    # Get current price for reference (mock for now)
    # In production, this would fetch from market data
    current_price = 100.0  # Placeholder

    # Calculate take profit and stop loss based on conviction
    # Higher conviction = tighter stops, wider targets
    if conviction >= 1.5:
        take_profit_pct = 0.03  # 3%
        stop_loss_pct = 0.02  # 2%
    elif conviction >= 1.0:
        take_profit_pct = 0.02  # 2%
        stop_loss_pct = 0.015  # 1.5%
    else:
        take_profit_pct = 0.015  # 1.5%
        stop_loss_pct = 0.01  # 1%

    if side == "buy":
        take_profit_price = str(round(current_price * (1 + take_profit_pct), 2))
        stop_loss_price = str(round(current_price * (1 - stop_loss_pct), 2))
    else:  # sell
        take_profit_price = str(round(current_price * (1 - take_profit_pct), 2))
        stop_loss_price = str(round(current_price * (1 + stop_loss_pct), 2))

    return {
        "symbol": selected_instrument,
        "side": side,
        "qty": qty,
        "take_profit_price": take_profit_price,
        "stop_loss_price": stop_loss_price,
        "order_id": None,  # Will be set after order placement
    }
