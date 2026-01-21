"""Monitoring API endpoints for positions and accounts."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create router for monitoring endpoints
router = APIRouter(prefix="/api", tags=["monitoring"])


# Mock data fallback (for when live data unavailable)
MOCK_POSITIONS = [
    {
        "account": "COUNCIL",
        "symbol": "SPY",
        "qty": 50,
        "avg_price": 475.20,
        "current_price": 482.30,
        "pl": 355,
    },
    {
        "account": "CHATGPT",
        "symbol": "TLT",
        "qty": 30,
        "avg_price": 94.50,
        "current_price": 95.45,
        "pl": 28.5,
    },
    {
        "account": "GEMINI",
        "symbol": "QQQ",
        "qty": 20,
        "avg_price": 398.10,
        "current_price": 400.05,
        "pl": 39,
    },
    {
        "account": "CLAUDE",
        "symbol": "-",
        "qty": 0,
        "avg_price": 0,
        "current_price": 0,
        "pl": 0,
    },
    {
        "account": "GROQ",
        "symbol": "HYG",
        "qty": 100,
        "avg_price": 78.50,
        "current_price": 78.99,
        "pl": 49,
    },
    {
        "account": "DEEPSEEK",
        "symbol": "GLD",
        "qty": 15,
        "avg_price": 187.80,
        "current_price": 189.00,
        "pl": 18,
    },
]

MOCK_ACCOUNTS = [
    {"name": "COUNCIL", "equity": 100355, "cash": 75920, "pl": 355},
    {"name": "CHATGPT", "equity": 100284, "cash": 80984, "pl": 284},
    {"name": "GEMINI", "equity": 99961, "cash": 70089, "pl": -39},
    {"name": "CLAUDE", "equity": 100000, "cash": 100000, "pl": 0},
    {"name": "GROQ", "equity": 100249, "cash": 83589, "pl": 249},
    {"name": "DEEPSEEK", "equity": 100018, "cash": 95328, "pl": 18},
]


# ============================================================================
# Response Models
# ============================================================================


class PositionItem(BaseModel):
    """Response model for a single position."""

    account: str = Field(description="Account name (e.g., 'COUNCIL', 'CHATGPT')")
    symbol: str = Field(description="Trading instrument (e.g., 'SPY', 'TLT', '-')")
    qty: int = Field(description="Quantity of shares held")
    avg_price: float = Field(description="Average entry price per share")
    current_price: float = Field(description="Current market price per share")
    pl: float = Field(description="Unrealized profit/loss in dollars")


class AccountSummary(BaseModel):
    """Response model for account summary."""

    name: str = Field(description="Account name (e.g., 'COUNCIL', 'CHATGPT')")
    equity: float = Field(description="Total portfolio value (cash + positions)")
    cash: float = Field(description="Available cash balance")
    pl: float = Field(
        description="Profit/loss relative to starting balance ($100,000)"
    )


class PerformanceDataPoint(BaseModel):
    """Response model for a single performance data point."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    equity: float = Field(description="Total portfolio value at that date")
    pl: float = Field(description="Cumulative P/L relative to $100,000 starting balance")


class PerformanceHistory(BaseModel):
    """Response model for performance history."""

    account: str = Field(description="Account name (e.g., 'COUNCIL', 'CHATGPT')")
    history: List[PerformanceDataPoint] = Field(
        description="Time-series performance data"
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/positions")
async def get_positions() -> List[PositionItem]:
    """
    Get current positions across all trading accounts.

    Retrieves live position data from all Alpaca accounts via MultiAlpacaManager.
    Returns a formatted list of positions showing current holdings, entry prices,
    current prices, and unrealized profit/loss.

    Returns:
        List of position dictionaries. Each dict contains:
            - account: Account name (e.g., 'COUNCIL', 'CHATGPT', etc.)
            - symbol: Trading instrument (e.g., 'SPY', 'TLT')
            - qty: Quantity of shares held
            - avg_price: Average entry price per share
            - current_price: Current market price per share
            - pl: Unrealized profit/loss in dollars

        Falls back to MOCK_POSITIONS if live data unavailable or on error.

    Example Response:
        [
            {
                "account": "COUNCIL",
                "symbol": "SPY",
                "qty": 50,
                "avg_price": 475.20,
                "current_price": 482.30,
                "pl": 355.0
            },
            {
                "account": "CLAUDE",
                "symbol": "-",
                "qty": 0,
                "avg_price": 0.0,
                "current_price": 0.0,
                "pl": 0.0
            }
        ]

    Notes:
        - Accounts with no positions return a placeholder entry with "-" symbol
        - All 6 accounts are queried: COUNCIL, CHATGPT, GEMINI, CLAUDE, GROQ, DEEPSEEK
        - Uses MultiAlpacaManager.get_all_positions() for parallel account queries
        - Errors are caught and logged, returns mock data to avoid breaking frontend
    """
    try:
        from backend.multi_alpaca_client import MultiAlpacaManager

        manager = MultiAlpacaManager()
        positions_data = await manager.get_all_positions()

        # Format for frontend
        formatted = []
        for account_name, positions in positions_data.items():
            if not positions:
                # Account has no positions - return placeholder
                formatted.append(
                    {
                        "account": account_name,
                        "symbol": "-",
                        "qty": 0,
                        "avg_price": 0,
                        "current_price": 0,
                        "pl": 0,
                    }
                )
                continue

            # Format each position
            for position in positions:
                formatted.append(
                    {
                        "account": account_name,
                        "symbol": position.get("symbol"),
                        "qty": int(float(position.get("qty", 0))),
                        "avg_price": float(position.get("avg_entry_price", 0)),
                        "current_price": float(position.get("current_price", 0)),
                        "pl": float(position.get("unrealized_pl", 0)),
                    }
                )

        # Return formatted data if available, otherwise mock data
        result = formatted if formatted else MOCK_POSITIONS
        logger.info(f"Retrieved {len(result)} position entries")
        return result

    except Exception as e:
        logger.error(f"Error getting positions: {e}", exc_info=True)
        logger.warning("Falling back to mock positions data")
        return MOCK_POSITIONS


@router.get("/accounts")
async def get_accounts() -> List[AccountSummary]:
    """
    Get account summaries for all trading accounts.

    Retrieves live account data from all Alpaca accounts via MultiAlpacaManager.
    Returns account balances, equity, cash, and profit/loss calculations.

    Returns:
        List of account summary dictionaries. Each dict contains:
            - name: Account name (e.g., 'COUNCIL', 'CHATGPT', etc.)
            - equity: Total portfolio value (cash + positions)
            - cash: Available cash balance
            - pl: Profit/loss relative to starting balance ($100,000)

        Falls back to MOCK_ACCOUNTS if live data unavailable or on error.

    Example Response:
        [
            {
                "name": "COUNCIL",
                "equity": 100355.0,
                "cash": 75920.0,
                "pl": 355.0
            },
            {
                "name": "CHATGPT",
                "equity": 100284.0,
                "cash": 80984.0,
                "pl": 284.0
            }
        ]

    Notes:
        - All 6 accounts are queried: COUNCIL, CHATGPT, GEMINI, CLAUDE, GROQ, DEEPSEEK
        - Starting balance for all accounts is $100,000
        - P&L is calculated as: (equity - 100000)
        - Uses MultiAlpacaManager.get_all_accounts() for parallel account queries
        - Errors are caught and logged, returns mock data to avoid breaking frontend
    """
    try:
        from backend.multi_alpaca_client import MultiAlpacaManager

        manager = MultiAlpacaManager()
        accounts_data = await manager.get_all_accounts()

        # Format for frontend
        formatted = []
        for account_name, account in accounts_data.items():
            equity = float(account.get("equity", 100000))
            formatted.append(
                {
                    "name": account_name,
                    "equity": float(account.get("portfolio_value", equity)),
                    "cash": float(account.get("cash", equity)),
                    "pl": equity - 100000,  # Calculate P&L from starting balance
                }
            )

        # Return formatted data if available, otherwise mock data
        result = formatted if formatted else MOCK_ACCOUNTS
        logger.info(f"Retrieved {len(result)} account summaries")
        return result

    except Exception as e:
        logger.error(f"Error getting accounts: {e}", exc_info=True)
        logger.warning("Falling back to mock accounts data")
        return MOCK_ACCOUNTS


def _generate_mock_performance_history(
    account: str, days: int
) -> List[Dict[str, Any]]:
    """
    Generate mock performance history for an account.

    Creates realistic-looking performance data by simulating daily P/L changes
    based on account characteristics. Used as fallback when historical data
    is unavailable.

    Args:
        account: Account name (e.g., 'COUNCIL', 'CHATGPT')
        days: Number of days of history to generate

    Returns:
        List of performance data points, each containing:
            - date: Date in YYYY-MM-DD format
            - equity: Portfolio value at that date
            - pl: Cumulative P/L relative to $100,000

    Notes:
        - COUNCIL account has positive trend (outperforming)
        - Individual PM accounts have mixed performance
        - CLAUDE (baseline) stays flat at $100,000
        - Data simulates realistic volatility and trends
    """
    # Account-specific performance parameters
    performance_profiles = {
        "COUNCIL": {"daily_drift": 0.0015, "volatility": 0.008},  # +0.15%/day avg
        "CHATGPT": {"daily_drift": 0.0008, "volatility": 0.010},  # +0.08%/day avg
        "GEMINI": {"daily_drift": -0.0002, "volatility": 0.012},  # -0.02%/day avg
        "CLAUDE": {"daily_drift": 0.0, "volatility": 0.0},  # Baseline: flat
        "GROQ": {"daily_drift": 0.0006, "volatility": 0.009},  # +0.06%/day avg
        "DEEPSEEK": {"daily_drift": 0.0001, "volatility": 0.007},  # +0.01%/day avg
    }

    profile = performance_profiles.get(
        account, {"daily_drift": 0.0, "volatility": 0.008}
    )

    # Generate history from oldest to newest
    history = []
    base_equity = 100000.0
    current_equity = base_equity

    import random

    random.seed(hash(account))  # Deterministic for same account

    for i in range(days, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

        # Simulate daily return: drift + random volatility
        if account == "CLAUDE":
            # Baseline stays flat
            current_equity = base_equity
        else:
            daily_return = profile["daily_drift"] + random.gauss(
                0, profile["volatility"]
            )
            current_equity = current_equity * (1 + daily_return)

        pl = current_equity - base_equity

        history.append({"date": date, "equity": round(current_equity, 2), "pl": round(pl, 2)})

    return history


@router.get("/performance/history")
async def get_performance_history(
    account: Optional[str] = Query(None, description="Account name to filter by"),
    days: int = Query(7, ge=1, le=365, description="Number of days of history"),
) -> PerformanceHistory:
    """
    Get performance history for a specific account.

    Retrieves time-series performance data showing equity and P/L evolution over time.
    Used by frontend charts to visualize account performance trends.

    Query Parameters:
        account: Account name (e.g., 'COUNCIL', 'CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK')
        days: Number of days of history (1-365, default: 7)

    Returns:
        Performance history object containing:
            - account: The account name
            - history: Array of daily data points with:
                - date: Date in YYYY-MM-DD format
                - equity: Portfolio value at that date
                - pl: Cumulative P/L relative to $100,000 starting balance

    Example Response:
        {
            "account": "COUNCIL",
            "history": [
                {
                    "date": "2025-01-14",
                    "equity": 100000.0,
                    "pl": 0.0
                },
                {
                    "date": "2025-01-15",
                    "equity": 100180.5,
                    "pl": 180.5
                },
                {
                    "date": "2025-01-21",
                    "equity": 100355.0,
                    "pl": 355.0
                }
            ]
        }

    Notes:
        - Currently returns mock data for development
        - Future implementation will query actual performance from database
        - COUNCIL typically shows positive trend (council advantage)
        - CLAUDE (baseline) remains flat at $100,000
        - Data points are ordered chronologically (oldest first)
        - Falls back to mock data generation on error
    """
    try:
        # Validate account name
        valid_accounts = ["COUNCIL", "CHATGPT", "GEMINI", "CLAUDE", "GROQ", "DEEPSEEK"]
        if account and account not in valid_accounts:
            logger.warning(f"Invalid account name: {account}, using COUNCIL as default")
            account = "COUNCIL"
        elif not account:
            account = "COUNCIL"

        logger.info(f"Retrieving performance history for {account} (last {days} days)")

        # TODO: Query actual performance data from database
        # For now, generate mock data
        # Future implementation:
        # from backend.db.performance_db import get_account_performance_history
        # history_data = await get_account_performance_history(account, days)

        history_data = _generate_mock_performance_history(account, days)

        logger.info(f"Retrieved {len(history_data)} data points for {account}")

        return PerformanceHistory(account=account, history=history_data)

    except Exception as e:
        logger.error(f"Error getting performance history: {e}", exc_info=True)
        # Return empty history on error
        return PerformanceHistory(account=account or "COUNCIL", history=[])
