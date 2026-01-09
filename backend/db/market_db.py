"""Market data database operations."""

from typing import Dict, Any, List, Optional
from .database import get_connection


def fetch_market_metrics() -> Optional[Dict[str, Any]]:
    """
    Fetch market metrics including 7-day returns and correlation matrix.

    Returns:
        Dictionary containing:
            - date: Latest date for the data
            - returns_7d: List of symbols with 7-day log returns
            - correlation_matrix: Nested dict of symbol correlations
            - symbols: Sorted list of all symbols
        Returns None if error occurs.

    Database Tables:
        - rolling_7day_log_returns: Contains 7-day log returns per symbol/date
        - correlation_matrix: Contains pairwise correlations per date
    """
    try:
        conn = get_connection()

        try:
            with conn.cursor() as cur:
                # Get latest 7-day returns
                cur.execute("""
                    SELECT symbol, log_return_7d
                    FROM rolling_7day_log_returns
                    WHERE date = (SELECT MAX(date) FROM rolling_7day_log_returns)
                    ORDER BY log_return_7d DESC
                """)

                returns_rows = cur.fetchall()
                returns = [
                    {
                        "symbol": row[0],
                        "log_return_7d": float(row[1]),
                        "pct_return": (float(row[1]) * 100),
                    }
                    for row in returns_rows
                ]

                # Get latest correlation matrix
                cur.execute("""
                    SELECT symbol_1, symbol_2, correlation
                    FROM correlation_matrix
                    WHERE date = (SELECT MAX(date) FROM correlation_matrix)
                    ORDER BY symbol_1, symbol_2
                """)

                corr_rows = cur.fetchall()

                # Build correlation matrix as nested dict
                correlation_matrix = {}
                symbols = sorted(set([row[0] for row in corr_rows]))

                for row in corr_rows:
                    symbol1, symbol2, corr = row
                    if symbol1 not in correlation_matrix:
                        correlation_matrix[symbol1] = {}
                    correlation_matrix[symbol1][symbol2] = float(corr)

                # Get the date
                cur.execute("SELECT MAX(date) FROM rolling_7day_log_returns")
                latest_date = cur.fetchone()[0]

                return {
                    "date": latest_date.isoformat() if latest_date else None,
                    "returns_7d": returns,
                    "correlation_matrix": correlation_matrix,
                    "symbols": symbols,
                }

        finally:
            conn.close()

    except Exception as e:
        print(f"Error fetching market metrics: {e}")
        return None


def fetch_current_prices() -> Optional[Dict[str, Any]]:
    """
    Fetch current prices and volumes for all tradable instruments.

    Returns:
        Dictionary containing:
            - prices: List of price data per symbol (OHLCV)
            - asof_date: Date of the price data
        Returns None if error occurs.

    Database Tables:
        - daily_bars: Contains OHLCV data per symbol/date

    Tradable Instruments:
        SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO, VIXY, SH
    """
    try:
        conn = get_connection()

        try:
            with conn.cursor() as cur:
                # Get latest daily bars for all instruments
                cur.execute("""
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

                rows = cur.fetchall()

                prices = []
                for row in rows:
                    prices.append(
                        {
                            "symbol": row[0],
                            "date": row[1].isoformat() if row[1] else None,
                            "open": float(row[2]) if row[2] else None,
                            "high": float(row[3]) if row[3] else None,
                            "low": float(row[4]) if row[4] else None,
                            "close": float(row[5]) if row[5] else None,
                            "volume": int(row[6]) if row[6] else None,
                        }
                    )

                return {
                    "prices": prices,
                    "asof_date": prices[0]["date"] if prices else None,
                }

        finally:
            conn.close()

    except Exception as e:
        print(f"Error fetching current prices: {e}")
        return None
