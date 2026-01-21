"""Monitoring API endpoints for positions and accounts."""

import logging
from typing import Dict, Any, List

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
