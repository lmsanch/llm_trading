"""Market data API endpoints."""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.market_service import MarketService

logger = logging.getLogger(__name__)

# Create router for market endpoints
router = APIRouter(prefix="/api/market", tags=["market"])

# Initialize market service
market_service = MarketService()


# ============================================================================
# Response Models
# ============================================================================


class MarketSnapshotResponse(BaseModel):
    """Response model for market snapshot."""

    market_snapshot: Dict[str, Any] = Field(
        description="Comprehensive market data including indicators and context"
    )
    timestamp: str = Field(description="ISO timestamp of the snapshot")


class Return7DayData(BaseModel):
    """7-day return data for a single symbol."""

    symbol: str = Field(description="Stock ticker symbol")
    log_return_7d: float = Field(description="7-day log return")
    pct_return: float = Field(description="7-day percentage return")


class MarketMetricsResponse(BaseModel):
    """Response model for market metrics."""

    date: str = Field(description="Latest date of the data (ISO format)")
    returns_7d: List[Return7DayData] = Field(
        description="7-day returns for all tracked symbols"
    )
    correlation_matrix: Dict[str, Dict[str, float]] = Field(
        description="Nested dict of symbol-to-symbol correlations"
    )
    symbols: List[str] = Field(
        description="Sorted list of symbols in the correlation matrix"
    )


class PriceData(BaseModel):
    """OHLCV price data for a single symbol."""

    symbol: str = Field(description="Stock ticker symbol")
    date: str = Field(description="Date of the price data (YYYY-MM-DD)")
    open: float = Field(description="Opening price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Closing price")
    volume: int = Field(description="Trading volume")


class CurrentPricesResponse(BaseModel):
    """Response model for current prices."""

    asof_date: str = Field(description="The date of the price data (ISO format)")
    prices: List[PriceData] = Field(
        description="List of OHLCV data for all tracked symbols"
    )


@router.get("/snapshot")
async def get_market_snapshot() -> MarketSnapshotResponse:
    """
    Get current market snapshot for research context.

    Fetches comprehensive market data suitable for research analysis including
    technical indicators, fundamental data, and market context from MarketDataFetcher.

    Returns:
        Dict containing market snapshot with various market indicators and data.
        Returns empty dict if MarketDataFetcher is unavailable or error occurs.

    Raises:
        HTTPException: 500 if there's an error fetching the market snapshot

    Example Response:
        {
            "market_snapshot": {...},
            "timestamp": "2024-01-09T12:00:00Z"
        }
    """
    try:
        snapshot = await market_service.get_market_snapshot()
        return snapshot
    except Exception as e:
        logger.error(f"Error in get_market_snapshot endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_market_metrics() -> MarketMetricsResponse:
    """
    Get latest 7-day returns and correlation matrix.

    Fetches the latest market metrics from the database including:
    - 7-day log returns for all tracked symbols
    - Correlation matrix showing pairwise correlations
    - Latest data date

    Returns:
        Dict containing:
            - date: Latest date of the data (ISO format)
            - returns_7d: List of dicts with symbol, log_return_7d, pct_return
            - correlation_matrix: Nested dict of symbol-to-symbol correlations
            - symbols: Sorted list of symbols in the correlation matrix

    Raises:
        HTTPException: 404 if no metrics data is available
        HTTPException: 500 if there's an error fetching metrics

    Database Tables:
        - rolling_7day_log_returns: Contains 7-day rolling log returns by symbol/date
        - correlation_matrix: Contains pairwise correlations by symbol/date

    Example Response:
        {
            "date": "2024-01-08",
            "returns_7d": [
                {"symbol": "SPY", "log_return_7d": 0.025, "pct_return": 2.5},
                {"symbol": "QQQ", "log_return_7d": 0.031, "pct_return": 3.1}
            ],
            "correlation_matrix": {
                "SPY": {"SPY": 1.0, "QQQ": 0.85},
                "QQQ": {"SPY": 0.85, "QQQ": 1.0}
            },
            "symbols": ["SPY", "QQQ"]
        }
    """
    try:
        metrics = await market_service.get_market_metrics()

        if metrics is None:
            logger.warning("No market metrics data available")
            raise HTTPException(
                status_code=404,
                detail="No market metrics data available"
            )

        return metrics
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in get_market_metrics endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices")
async def get_current_prices() -> CurrentPricesResponse:
    """
    Get current prices and volumes for all tradable instruments.

    Fetches the latest daily bar data (OHLCV) for each tracked symbol from
    the database. Returns the most recent trading day's data for each instrument.

    Returns:
        Dict containing:
            - prices: List of dicts with symbol, date, open, high, low, close, volume
            - asof_date: The date of the price data (ISO format)

    Raises:
        HTTPException: 404 if no price data is available
        HTTPException: 500 if there's an error fetching prices

    Database Tables:
        - daily_bars: Contains OHLCV data by symbol/date

    Tracked Symbols:
        SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO, VIXY, SH

    Example Response:
        {
            "asof_date": "2024-01-08",
            "prices": [
                {
                    "symbol": "SPY",
                    "date": "2024-01-08",
                    "open": 470.50,
                    "high": 472.30,
                    "low": 469.80,
                    "close": 471.20,
                    "volume": 75000000
                }
            ]
        }
    """
    try:
        prices = await market_service.get_current_prices()

        if prices is None:
            logger.warning("No price data available")
            raise HTTPException(
                status_code=404,
                detail="No price data available"
            )

        return prices
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error in get_current_prices endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
