#!/usr/bin/env python3
"""
Fetch market data using alpaca-py SDK and store in PostgreSQL.

This script uses the modern alpaca-py library with StockHistoricalDataClient
for reliable market data access. It's designed to run via cron for periodic updates.

Usage:
    python fetch_market_data.py seed --days 30    # Initial seed (30 days)
    python fetch_market_data.py daily             # Daily update (run after market close)
    python fetch_market_data.py hourly            # Hourly snapshots (run during market hours)

Cron Setup (in crontab -e):
    # Daily update at 5:00 PM ET (after market close)
    0 17 * * 1-5 cd /research/llm_trading && python backend/storage/fetch_market_data.py daily

    # Hourly snapshots during market hours (9 AM, 12 PM, 2 PM, 3:50 PM ET)
    0 9,12,14 * * 1-5 cd /research/llm_trading && python backend/storage/fetch_market_data.py hourly
    50 15 * * 1-5 cd /research/llm_trading && python backend/storage/fetch_market_data.py hourly
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Modern Alpaca SDK
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Tradable universe (ETFs for macro trading)
INSTRUMENTS = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]

# PostgreSQL connection
DB_NAME = os.getenv("DATABASE_NAME", "llm_trading")
DB_USER = os.getenv("DATABASE_USER", "luis")

# Alpaca credentials - Use personal trading account (has market data access)
ALPACA_API_KEY = os.getenv("ALPACA_PERSONAL_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("ALPACA_PERSONAL_SECRET_KEY")

# Checkpoint hours for hourly snapshots (ET)
CHECKPOINT_HOURS = [9, 12, 14, 15, 16]


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class MarketDataDB:
    """PostgreSQL database manager for market data."""

    def __init__(self):
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL database using peer authentication."""
        self.conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER
            # No password - uses peer authentication
        )
        print(f"✅ Connected to database: {DB_NAME}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")

    def insert_daily_bar(self, symbol: str, bar: Dict[str, Any]) -> bool:
        """Insert or update a daily bar."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """, (
                    symbol,
                    bar["date"],
                    float(bar["open"]),
                    float(bar["high"]),
                    float(bar["low"]),
                    float(bar["close"]),
                    int(bar["volume"])
                ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"  ❌ Error inserting bar for {symbol}: {e}")
            self.conn.rollback()
            return False

    def log_fetch(self, fetch_type: str, symbol: str, success: bool, error: str = None):
        """Log a fetch attempt."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fetch_log (fetch_type, symbol, status, error_message)
                VALUES (%s, %s, %s, %s)
            """, (fetch_type, symbol, 'success' if success else 'error', error))
        self.conn.commit()


# ============================================================================
# MARKET DATA FETCHER (using alpaca-py SDK)
# ============================================================================

class AlpacaMarketDataFetcher:
    """Fetch market data using modern alpaca-py SDK."""

    def __init__(self):
        self.db = MarketDataDB()
        
        # Initialize Alpaca data client (modern SDK)
        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            raise ValueError("Alpaca API credentials not found in .env file")
        
        self.client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        print(f"✅ Initialized Alpaca data client")

    def seed_initial_data(self, days: int = 30):
        """
        Seed database with initial historical data.
        
        Args:
            days: Number of days of historical data to fetch
        """
        print(f"\n🌱 Seeding initial data: Last {days} days")
        print("=" * 60)

        self.db.connect()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)  # Extra buffer for weekends

        for symbol in INSTRUMENTS:
            print(f"\n📊 Fetching {symbol}...")

            try:
                # Create request using modern SDK
                request_params = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )

                # Fetch bars
                bars_response = self.client.get_stock_bars(request_params)
                
                # Convert to DataFrame for easier processing
                df = bars_response.df
                
                if df.empty:
                    print(f"  ⚠️  No bars returned for {symbol}")
                    self.db.log_fetch("seed", symbol, False, "No data returned")
                    continue

                # Insert each bar into database
                # Note: DataFrame has MultiIndex (symbol, timestamp)
                inserted = 0
                for index, row in df.iterrows():
                    # index is a tuple: (symbol, timestamp)
                    symbol_from_index, timestamp = index
                    bar_data = {
                        "date": timestamp.strftime("%Y-%m-%d"),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume'])
                    }
                    if self.db.insert_daily_bar(symbol, bar_data):
                        inserted += 1

                print(f"  ✅ Inserted {inserted} bars for {symbol}")
                self.db.log_fetch("seed", symbol, True)

            except Exception as e:
                print(f"  ❌ Error fetching {symbol}: {e}")
                self.db.log_fetch("seed", symbol, False, str(e))

        self.db.close()
        print("\n✅ Initial data seeding complete")

    def update_daily_bars(self):
        """
        Update daily bars (run after market close).
        Fetches the last 5 days to ensure we catch any missed days.
        """
        print(f"\n📈 Updating daily bars")
        print("=" * 60)

        self.db.connect()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)

        for symbol in INSTRUMENTS:
            print(f"\n📊 Updating {symbol}...")

            try:
                request_params = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )

                bars_response = self.client.get_stock_bars(request_params)
                df = bars_response.df

                if df.empty:
                    print(f"  ⚠️  No new bars for {symbol}")
                    continue

                inserted = 0
                for index, row in df.iterrows():
                    # index is a tuple: (symbol, timestamp)
                    symbol_from_index, timestamp = index
                    bar_data = {
                        "date": timestamp.strftime("%Y-%m-%d"),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume'])
                    }
                    if self.db.insert_daily_bar(symbol, bar_data):
                        inserted += 1

                print(f"  ✅ Updated {inserted} bars for {symbol}")
                self.db.log_fetch("daily", symbol, True)

            except Exception as e:
                print(f"  ❌ Error updating {symbol}: {e}")
                self.db.log_fetch("daily", symbol, False, str(e))

        self.db.close()
        print("\n✅ Daily update complete")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Market Data Fetcher using alpaca-py SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "command",
        choices=["seed", "daily", "hourly"],
        help="Command: seed (initial data), daily (update bars), hourly (snapshots)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Days to seed (default: 30)"
    )

    args = parser.parse_args()

    fetcher = AlpacaMarketDataFetcher()

    if args.command == "seed":
        fetcher.seed_initial_data(days=args.days)
    elif args.command == "daily":
        fetcher.update_daily_bars()
    elif args.command == "hourly":
        print("⚠️  Hourly snapshots not yet implemented")
        # TODO: Implement hourly snapshots if needed


if __name__ == "__main__":
    main()
