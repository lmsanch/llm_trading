"""Monitoring API endpoints for positions and accounts."""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter
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

MOCK_LEADERBOARD = [
    {
        "rank": 1,
        "account": "COUNCIL",
        "total_return": 0.0355,
        "sharpe_ratio": 1.42,
        "max_drawdown": -0.0125,
        "win_rate": 0.7500,
        "weeks_traded": 4,
        "profitable_weeks": 3,
    },
    {
        "rank": 2,
        "account": "CHATGPT",
        "total_return": 0.0284,
        "sharpe_ratio": 1.15,
        "max_drawdown": -0.0158,
        "win_rate": 0.7500,
        "weeks_traded": 4,
        "profitable_weeks": 3,
    },
    {
        "rank": 3,
        "account": "GROQ",
        "total_return": 0.0249,
        "sharpe_ratio": 1.05,
        "max_drawdown": -0.0210,
        "win_rate": 0.6667,
        "weeks_traded": 3,
        "profitable_weeks": 2,
    },
    {
        "rank": 4,
        "account": "DEEPSEEK",
        "total_return": 0.0018,
        "sharpe_ratio": 0.12,
        "max_drawdown": -0.0095,
        "win_rate": 0.5000,
        "weeks_traded": 2,
        "profitable_weeks": 1,
    },
    {
        "rank": 5,
        "account": "CLAUDE",
        "total_return": 0.0000,
        "sharpe_ratio": 0.00,
        "max_drawdown": 0.0000,
        "win_rate": 0.0000,
        "weeks_traded": 0,
        "profitable_weeks": 0,
    },
    {
        "rank": 6,
        "account": "GEMINI",
        "total_return": -0.0039,
        "sharpe_ratio": -0.25,
        "max_drawdown": -0.0198,
        "win_rate": 0.2500,
        "weeks_traded": 4,
        "profitable_weeks": 1,
    },
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


class LeaderboardEntry(BaseModel):
    """Response model for leaderboard entry."""

    rank: int = Field(description="Ranking by total return (1 = best)")
    account: str = Field(description="Account name (e.g., 'COUNCIL', 'CHATGPT')")
    total_return: float = Field(description="Cumulative return as decimal (e.g., 0.1523 = 15.23%)")
    sharpe_ratio: float = Field(description="Risk-adjusted return metric")
    max_drawdown: float = Field(description="Worst peak-to-trough decline")
    win_rate: float = Field(description="Percentage of profitable weeks (e.g., 0.6667 = 66.67%)")
    weeks_traded: int = Field(description="Number of weeks with positions")
    profitable_weeks: int = Field(description="Number of weeks with positive returns")


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


@router.get("/leaderboard")
async def get_leaderboard(weeks: Optional[int] = None) -> List[LeaderboardEntry]:
    """
    Get performance leaderboard ranked by total return.

    Retrieves cumulative performance metrics for all accounts over a specified time period.
    Ranks accounts by total return (highest to lowest) and includes risk-adjusted metrics.

    Args:
        weeks: Number of weeks to look back (query parameter).
               None = all time (default)
               4 = last 4 weeks
               8 = last 8 weeks
               Custom values are supported but use non-optimized queries.

    Returns:
        List of leaderboard entries, each containing:
            - rank: Ranking by total return (1 = best)
            - account: Account name (e.g., 'COUNCIL', 'CHATGPT', etc.)
            - total_return: Cumulative return as decimal (e.g., 0.1523 = 15.23%)
            - sharpe_ratio: Risk-adjusted return metric
            - max_drawdown: Worst peak-to-trough decline
            - win_rate: Percentage of profitable weeks (e.g., 0.6667 = 66.67%)
            - weeks_traded: Number of weeks with positions
            - profitable_weeks: Number of weeks with positive returns

        Falls back to MOCK_LEADERBOARD if live data unavailable or on error.

    Example Response:
        [
            {
                "rank": 1,
                "account": "COUNCIL",
                "total_return": 0.0355,
                "sharpe_ratio": 1.42,
                "max_drawdown": -0.0125,
                "win_rate": 0.7500,
                "weeks_traded": 4,
                "profitable_weeks": 3
            },
            {
                "rank": 2,
                "account": "CHATGPT",
                "total_return": 0.0284,
                "sharpe_ratio": 1.15,
                "max_drawdown": -0.0158,
                "win_rate": 0.7500,
                "weeks_traded": 4,
                "profitable_weeks": 3
            }
        ]

    Notes:
        - All 6 accounts are included: COUNCIL, CHATGPT, GEMINI, CLAUDE, GROQ, DEEPSEEK
        - Accounts are ranked by total_return (descending)
        - Uses optimized database views for common time periods (all-time, 4w, 8w)
        - Performance metrics are calculated by backend/storage/calculate_performance.py
        - Returns mock data to avoid breaking frontend if database unavailable
    """
    try:
        from backend.db.performance_db import get_leaderboard as db_get_leaderboard

        # Query database for leaderboard data
        leaderboard_data = await db_get_leaderboard(weeks_filter=weeks)

        # Format for frontend (convert to list of dicts)
        formatted = []
        for entry in leaderboard_data:
            formatted.append(
                {
                    "rank": entry["rank"],
                    "account": entry["account"],
                    "total_return": float(entry["total_return"]),
                    "sharpe_ratio": float(entry.get("sharpe_ratio", 0)),
                    "max_drawdown": float(entry.get("max_drawdown", 0)),
                    "win_rate": float(entry.get("win_rate", 0)),
                    "weeks_traded": int(entry.get("weeks_traded", 0)),
                    "profitable_weeks": int(entry.get("profitable_weeks", 0)),
                }
            )

        # Return formatted data if available, otherwise mock data
        result = formatted if formatted else MOCK_LEADERBOARD
        logger.info(
            f"Retrieved leaderboard (weeks={weeks}): {len(result)} accounts"
        )
        return result

    except Exception as e:
        logger.error(
            f"Error getting leaderboard (weeks={weeks}): {e}", exc_info=True
        )
        logger.warning("Falling back to mock leaderboard data")
        return MOCK_LEADERBOARD
