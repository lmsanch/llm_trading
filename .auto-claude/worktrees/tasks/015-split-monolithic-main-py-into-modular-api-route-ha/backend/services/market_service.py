"""Market service for market data business logic."""

import logging
from typing import Dict, Optional, Any

from backend.db.market_db import fetch_market_metrics, fetch_current_prices

logger = logging.getLogger(__name__)


class MarketService:
    """
    Service class for market data operations.

    Provides business logic for fetching market data including:
    - Market snapshots for research context
    - Market metrics (7-day returns and correlation matrix)
    - Current prices (latest OHLCV data)

    This service acts as a bridge between API routes and database operations,
    encapsulating business logic and data transformations.
    """

    def __init__(self):
        """Initialize the MarketService."""
        pass

    async def get_market_snapshot(self) -> Dict[str, Any]:
        """
        Get current market snapshot for research context.

        Fetches comprehensive market data suitable for research analysis including
        technical indicators, fundamental data, and market context.

        Returns:
            Dict containing market snapshot with various market indicators and data.
            Returns empty dict if MarketDataFetcher is unavailable or error occurs.

        Raises:
            Exception: If there's an error fetching the market snapshot
        """
        try:
            # Import here to avoid circular dependencies
            from backend.storage.data_fetcher import MarketDataFetcher

            fetcher = MarketDataFetcher()
            snapshot = fetcher.get_market_snapshot_for_research()
            return snapshot
        except ImportError as e:
            logger.error(f"Failed to import MarketDataFetcher: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching market snapshot: {e}")
            raise

    async def get_market_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get latest 7-day returns and correlation matrix.

        Fetches the latest market metrics including:
        - 7-day log returns for all tracked symbols
        - Correlation matrix showing pairwise correlations
        - Latest data date

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
            metrics = fetch_market_metrics()
            if metrics is None:
                logger.warning("Failed to fetch market metrics from database")
            return metrics
        except Exception as e:
            logger.error(f"Error in get_market_metrics: {e}")
            return None

    async def get_current_prices(self) -> Optional[Dict[str, Any]]:
        """
        Get current prices and volumes for all tradable instruments.

        Fetches the latest daily bar data (OHLCV) for each tracked symbol.
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
            prices = fetch_current_prices()
            if prices is None:
                logger.warning("Failed to fetch current prices from database")
            return prices
        except Exception as e:
            logger.error(f"Error in get_current_prices: {e}")
            return None

    async def get_latest_data_package(self) -> Dict[str, Any]:
        """
        Get the latest complete data package with all market data.

        Combines market metrics and current prices into a single data package.
        Useful for endpoints that need comprehensive market data in one call.

        Returns:
            Dict containing:
                - market_metrics: Latest 7-day returns and correlation matrix
                - current_prices: Latest OHLCV data for tracked symbols
                - date: The date of the data (ISO format)
        """
        try:
            metrics = await self.get_market_metrics()
            prices = await self.get_current_prices()

            # Determine the most recent date from available data
            date = None
            if metrics and metrics.get("date"):
                date = metrics["date"]
            elif prices and prices.get("asof_date"):
                date = prices["asof_date"]

            return {
                "date": date,
                "market_metrics": metrics,
                "current_prices": prices,
            }
        except Exception as e:
            logger.error(f"Error in get_latest_data_package: {e}")
            return {
                "date": None,
                "market_metrics": None,
                "current_prices": None,
            }
