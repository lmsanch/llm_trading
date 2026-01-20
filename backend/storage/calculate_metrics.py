#!/usr/bin/env python3
"""
Calculate and store market metrics using pandas.

Calculations:
1. Daily log returns: ln(close_t / close_t-1)
2. 7-day log returns: ln(close_t / close_t-7)
3. 30-day rolling correlation matrix of 7-day log returns

ASYNC PATTERNS USED:
    This module demonstrates batch operations with asyncpg connection pool.
    See backend/db/ASYNC_PATTERNS.md for complete documentation.

    Key patterns:
    - Batch inserts use conn.executemany() for performance
    - Connection pool is acquired with 'async with pool.acquire()'
    - All database operations use 'await'
    - Parameter placeholders use $1, $2, $3 (not %s)

Usage:
    python calculate_metrics.py          # Calculate all metrics
    python calculate_metrics.py --backfill  # Backfill historical metrics
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import asyncio
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.pool import get_pool, init_pool, close_pool

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Tradable universe (ETFs for macro trading)
INSTRUMENTS = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]

# PostgreSQL connection
DB_NAME = os.getenv("DATABASE_NAME", "llm_trading")
DB_USER = os.getenv("DATABASE_USER", "luis")

# Rolling window for correlation
CORRELATION_WINDOW = 30


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class MetricsDB:
    """PostgreSQL database manager for metrics using async connection pool."""

    def __init__(self):
        # No longer stores connection - uses pool from get_pool()
        pass

    async def load_daily_bars(self) -> pd.DataFrame:
        """
        Load all daily bars from database into pandas DataFrame.

        Returns:
            DataFrame with columns: symbol, date, open, high, low, close, volume
        """
        query = """
            SELECT symbol, date, open, high, low, close, volume
            FROM daily_bars
            ORDER BY symbol, date
        """
        # ASYNC PATTERN: Direct pool usage (advanced)
        # - Use when you need fine-grained control over connection
        # - get_pool() returns the global connection pool singleton
        # - 'async with pool.acquire()' automatically gets/releases connection
        # - Connection is returned to pool on exit (even on exception)
        pool = get_pool()
        async with pool.acquire() as conn:
            # ASYNC PATTERN: Use await with conn.fetch()
            # - conn.fetch() returns all rows as list of Record objects
            # - Records are dict-like: access with row["column_name"]
            rows = await conn.fetch(query)
            # Convert to list of dicts for DataFrame
            data = [dict(row) for row in rows]
            df = pd.DataFrame(data)
            # Ensure date column is datetime
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            print(f"📊 Loaded {len(df)} daily bars from database")
            return df

    async def upsert_daily_log_returns(self, df: pd.DataFrame):
        """
        Upsert daily log returns to database.

        Args:
            df: DataFrame with columns: symbol, date, log_return
        """
        if df.empty:
            print("  ⚠️  No daily log returns to insert")
            return

        # ASYNC PATTERN: Batch operations (efficient bulk insert)
        # - Prepare list of tuples for executemany()
        # - Each tuple contains parameters for one row ($1, $2, $3)
        # - Much faster than calling execute() in a loop (single transaction)
        # - For 100 rows: 1 round-trip vs 100 round-trips
        data = [
            (row['symbol'], row['date'], float(row['log_return']) if pd.notna(row['log_return']) else None)
            for _, row in df.iterrows()
        ]

        pool = get_pool()
        async with pool.acquire() as conn:
            # ASYNC PATTERN: Use await with conn.executemany() for batch operations
            # - executemany() runs all operations in a single transaction
            # - All rows succeed or all fail (atomic)
            # - 10-100x faster than individual execute() calls
            # - Use $1, $2, $3 placeholders (not %s, %s, %s)
            await conn.executemany(
                """
                INSERT INTO daily_log_returns (symbol, date, log_return)
                VALUES ($1, $2, $3)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    log_return = EXCLUDED.log_return,
                    created_at = NOW()
                """,
                data
            )
        print(f"  ✅ Upserted {len(df)} daily log returns")

    async def upsert_7day_log_returns(self, df: pd.DataFrame):
        """
        Upsert 7-day log returns to database.

        Args:
            df: DataFrame with columns: symbol, date, log_return_7d
        """
        if df.empty:
            print("  ⚠️  No 7-day log returns to insert")
            return

        # Prepare data for bulk insert
        data = [
            (row['symbol'], row['date'], float(row['log_return_7d']) if pd.notna(row['log_return_7d']) else None)
            for _, row in df.iterrows()
        ]

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO rolling_7day_log_returns (symbol, date, log_return_7d)
                VALUES ($1, $2, $3)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    log_return_7d = EXCLUDED.log_return_7d,
                    created_at = NOW()
                """,
                data
            )
        print(f"  ✅ Upserted {len(df)} 7-day log returns")

    async def upsert_correlation_matrix(self, df: pd.DataFrame):
        """
        Upsert correlation matrix to database.

        Args:
            df: DataFrame with columns: date, symbol_1, symbol_2, correlation
        """
        if df.empty:
            print("  ⚠️  No correlation data to insert")
            return

        # Prepare data for bulk insert
        data = [
            (row['date'], row['symbol_1'], row['symbol_2'], float(row['correlation']) if pd.notna(row['correlation']) else None)
            for _, row in df.iterrows()
        ]

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO correlation_matrix (date, symbol_1, symbol_2, correlation)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (date, symbol_1, symbol_2) DO UPDATE SET
                    correlation = EXCLUDED.correlation,
                    created_at = NOW()
                """,
                data
            )
        print(f"  ✅ Upserted {len(df)} correlation pairs")


# ============================================================================
# METRICS CALCULATOR
# ============================================================================

class MetricsCalculator:
    """Calculate market metrics using pandas."""

    def __init__(self):
        self.db = MetricsDB()

    def calculate_daily_log_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate daily log returns: ln(close_t / close_t-1)

        Args:
            df: DataFrame with columns: symbol, date, close

        Returns:
            DataFrame with columns: symbol, date, log_return
        """
        print("\n📈 Calculating daily log returns...")

        # Sort by symbol and date
        df = df.sort_values(['symbol', 'date'])

        # Calculate log returns for each symbol
        df['log_return'] = df.groupby('symbol')['close'].transform(
            lambda x: np.log(x / x.shift(1))
        )

        # Return only relevant columns, excluding NaN values
        result = df[['symbol', 'date', 'log_return']].dropna()

        print(f"  ✅ Calculated {len(result)} daily log returns")
        return result

    def calculate_7day_log_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate 7-day log returns: ln(close_t / close_t-7)

        Args:
            df: DataFrame with columns: symbol, date, close

        Returns:
            DataFrame with columns: symbol, date, log_return_7d
        """
        print("\n📈 Calculating 7-day log returns...")

        # Sort by symbol and date
        df = df.sort_values(['symbol', 'date'])

        # Calculate 7-day log returns for each symbol
        df['log_return_7d'] = df.groupby('symbol')['close'].transform(
            lambda x: np.log(x / x.shift(7))
        )

        # Return only relevant columns, excluding NaN values
        result = df[['symbol', 'date', 'log_return_7d']].dropna()

        print(f"  ✅ Calculated {len(result)} 7-day log returns")
        return result

    def calculate_correlation_matrix(self, df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
        """
        Calculate 30-day rolling correlation matrix of 7-day log returns.

        Args:
            df: DataFrame with columns: symbol, date, log_return_7d
            window: Rolling window size (default: 30)

        Returns:
            DataFrame with columns: date, symbol_1, symbol_2, correlation
        """
        print(f"\n📊 Calculating {window}-day rolling correlation matrix...")

        # Pivot to wide format: dates as rows, symbols as columns
        pivot_df = df.pivot(index='date', columns='symbol', values='log_return_7d')

        # Sort by date
        pivot_df = pivot_df.sort_index()

        # Calculate rolling correlation
        correlation_records = []

        for i in range(window - 1, len(pivot_df)):
            # Get window of data
            window_data = pivot_df.iloc[i - window + 1:i + 1]
            current_date = pivot_df.index[i]

            # Calculate correlation matrix for this window
            corr_matrix = window_data.corr()

            # Extract correlation pairs
            for symbol_1 in corr_matrix.columns:
                for symbol_2 in corr_matrix.columns:
                    correlation_records.append({
                        'date': current_date,
                        'symbol_1': symbol_1,
                        'symbol_2': symbol_2,
                        'correlation': corr_matrix.loc[symbol_1, symbol_2]
                    })

        result = pd.DataFrame(correlation_records)

        print(f"  ✅ Calculated {len(result)} correlation pairs ({len(result) // (len(INSTRUMENTS) ** 2)} dates)")
        return result

    async def run_all_calculations(self, backfill: bool = False):
        """
        Run all metric calculations and store in database.

        Args:
            backfill: If True, recalculate all historical metrics
        """
        print("\n🚀 Starting metrics calculation...")
        print("=" * 60)

        # Load daily bars
        daily_bars = await self.db.load_daily_bars()

        if daily_bars.empty:
            print("❌ No daily bars found in database. Run fetch_market_data.py first.")
            return

        # 1. Calculate daily log returns
        daily_log_returns = self.calculate_daily_log_returns(daily_bars)
        await self.db.upsert_daily_log_returns(daily_log_returns)

        # 2. Calculate 7-day log returns
        log_returns_7d = self.calculate_7day_log_returns(daily_bars)
        await self.db.upsert_7day_log_returns(log_returns_7d)

        # 3. Calculate correlation matrix
        correlation_matrix = self.calculate_correlation_matrix(log_returns_7d, window=CORRELATION_WINDOW)
        await self.db.upsert_correlation_matrix(correlation_matrix)

        print("\n✅ All metrics calculated and stored successfully")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate market metrics using pandas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Recalculate all historical metrics (default: only new data)"
    )

    args = parser.parse_args()

    # Initialize database connection pool
    await init_pool()

    try:
        calculator = MetricsCalculator()
        await calculator.run_all_calculations(backfill=args.backfill)
    finally:
        # Close database connection pool
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
