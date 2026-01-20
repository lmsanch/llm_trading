"""Market data database operations."""

import logging
from typing import Dict, List, Optional, Any

from backend.db_helpers import fetch_all, fetch_val

logger = logging.getLogger(__name__)


async def fetch_market_metrics() -> Optional[Dict[str, Any]]:
    """
    Fetch market metrics including 7-day returns and correlation matrix.

    Retrieves the latest 7-day log returns and correlation matrix from the database.
    Returns formatted market metrics suitable for analysis and display.

    Returns:
        Dict containing:
            - date: Latest date of the data (ISO format)
            - returns_7d: List of dicts with symbol, log_return_7d, pct_return
            - correlation_matrix: Nested dict of symbol-to-symbol correlations
            - symbols: Sorted list of symbols in the correlation matrix
        Returns None if an error occurs.

    Database Tables:
        - rolling_7day_log_returns: Contains 7-day rolling log returns by symbol/date
        - correlation_matrix: Contains pairwise correlations by symbol/date
    """
    try:
        # Get latest 7-day returns
        returns_rows = await fetch_all("""
            SELECT symbol, log_return_7d
            FROM rolling_7day_log_returns
            WHERE date = (SELECT MAX(date) FROM rolling_7day_log_returns)
            ORDER BY log_return_7d DESC
        """)

        returns = [
            {
                "symbol": row["symbol"],
                "log_return_7d": float(row["log_return_7d"]),
                "pct_return": (float(row["log_return_7d"]) * 100),
            }
            for row in returns_rows
        ]

        # Get latest correlation matrix
        corr_rows = await fetch_all("""
            SELECT symbol_1, symbol_2, correlation
            FROM correlation_matrix
            WHERE date = (SELECT MAX(date) FROM correlation_matrix)
            ORDER BY symbol_1, symbol_2
        """)

        # Build correlation matrix as nested dict
        correlation_matrix = {}
        symbols = sorted(set([row["symbol_1"] for row in corr_rows]))

        for row in corr_rows:
            symbol1 = row["symbol_1"]
            symbol2 = row["symbol_2"]
            corr = row["correlation"]
            if symbol1 not in correlation_matrix:
                correlation_matrix[symbol1] = {}
            correlation_matrix[symbol1][symbol2] = float(corr)

        # Get the date
        latest_date = await fetch_val("SELECT MAX(date) FROM rolling_7day_log_returns")

        return {
            "date": latest_date.isoformat() if latest_date else None,
            "returns_7d": returns,
            "correlation_matrix": correlation_matrix,
            "symbols": symbols,
        }

    except Exception as e:
        logger.error(f"Error fetching market metrics: {e}")
        return None


async def fetch_current_prices() -> Optional[Dict[str, Any]]:
    """
    Fetch current prices for all tracked instruments.

    Retrieves the latest daily bar data (OHLCV) for each symbol from the database.
    Returns the most recent trading day's data for each instrument.

    Returns:
        Dict containing:
            - prices: List of dicts with symbol, date, open, high, low, close, volume
            - asof_date: The date of the price data (ISO format)
        Returns None if an error occurs.

    Database Tables:
        - daily_bars: Contains OHLCV data by symbol/date

    Tracked Symbols:
        SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO, VIXY, SH
    """
    try:
        # Get latest daily bars for all instruments
        rows = await fetch_all("""
            WITH latest_dates AS (
                SELECT symbol, MAX(date) as latest_date
                FROM daily_bars
                WHERE symbol IN ('SPY', 'QQQ', 'IWM', 'TLT', 'HYG', 'UUP', 'GLD', 'USO', 'VIXY', 'SH')
                GROUP BY symbol
            )
            SELECT
                db.symbol,
                db.date,
                db.open,
                db.high,
                db.low,
                db.close,
                db.volume
            FROM daily_bars db
            INNER JOIN latest_dates ld ON db.symbol = ld.symbol AND db.date = ld.latest_date
            ORDER BY db.symbol
        """)

        prices = []
        for row in rows:
            prices.append(
                {
                    "symbol": row["symbol"],
                    "date": row["date"].isoformat() if row["date"] else None,
                    "open": float(row["open"]) if row["open"] else None,
                    "high": float(row["high"]) if row["high"] else None,
                    "low": float(row["low"]) if row["low"] else None,
                    "close": float(row["close"]) if row["close"] else None,
                    "volume": int(row["volume"]) if row["volume"] else None,
                }
            )

        return {
            "prices": prices,
            "asof_date": prices[0]["date"] if prices else None,
        }

    except Exception as e:
        logger.error(f"Error fetching current prices: {e}")
        return None
