#!/usr/bin/env python3
"""
Calculate and store market metrics using pandas.

Calculations:
1. Daily log returns: ln(close_t / close_t-1)
2. 7-day log returns: ln(close_t / close_t-7)
3. 30-day rolling correlation matrix of 7-day log returns

Usage:
    python calculate_metrics.py          # Calculate all metrics
    python calculate_metrics.py --backfill  # Backfill historical metrics
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

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

# Rolling window for correlation
CORRELATION_WINDOW = 30


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class MetricsDB:
    """PostgreSQL database manager for metrics."""

    def __init__(self):
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL database using peer authentication."""
        self.conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER
        )
        print(f"✅ Connected to database: {DB_NAME}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")

    def load_daily_bars(self) -> pd.DataFrame:
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
        df = pd.read_sql_query(query, self.conn, parse_dates=['date'])
        print(f"📊 Loaded {len(df)} daily bars from database")
        return df

    def upsert_daily_log_returns(self, df: pd.DataFrame):
        """
        Upsert daily log returns to database.

        Args:
            df: DataFrame with columns: symbol, date, log_return
        """
        if df.empty:
            print("  ⚠️  No daily log returns to insert")
            return

        # Prepare data for bulk insert
        data = [
            (row['symbol'], row['date'], float(row['log_return']) if pd.notna(row['log_return']) else None)
            for _, row in df.iterrows()
        ]

        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO daily_log_returns (symbol, date, log_return)
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET
                    log_return = EXCLUDED.log_return,
                    created_at = NOW()
                """,
                data,
                template="(%s, %s, %s)"
            )
        self.conn.commit()
        print(f"  ✅ Upserted {len(df)} daily log returns")

    def upsert_7day_log_returns(self, df: pd.DataFrame):
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

        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO rolling_7day_log_returns (symbol, date, log_return_7d)
                VALUES %s
                ON CONFLICT (symbol, date) DO UPDATE SET
                    log_return_7d = EXCLUDED.log_return_7d,
                    created_at = NOW()
                """,
                data,
                template="(%s, %s, %s)"
            )
        self.conn.commit()
        print(f"  ✅ Upserted {len(df)} 7-day log returns")

    def upsert_correlation_matrix(self, df: pd.DataFrame):
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

        with self.conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO correlation_matrix (date, symbol_1, symbol_2, correlation)
                VALUES %s
                ON CONFLICT (date, symbol_1, symbol_2) DO UPDATE SET
                    correlation = EXCLUDED.correlation,
                    created_at = NOW()
                """,
                data,
                template="(%s, %s, %s, %s)"
            )
        self.conn.commit()
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

    def run_all_calculations(self, backfill: bool = False):
        """
        Run all metric calculations and store in database.

        Args:
            backfill: If True, recalculate all historical metrics
        """
        print("\n🚀 Starting metrics calculation...")
        print("=" * 60)

        self.db.connect()

        # Load daily bars
        daily_bars = self.db.load_daily_bars()

        if daily_bars.empty:
            print("❌ No daily bars found in database. Run fetch_market_data.py first.")
            self.db.close()
            return

        # 1. Calculate daily log returns
        daily_log_returns = self.calculate_daily_log_returns(daily_bars)
        self.db.upsert_daily_log_returns(daily_log_returns)

        # 2. Calculate 7-day log returns
        log_returns_7d = self.calculate_7day_log_returns(daily_bars)
        self.db.upsert_7day_log_returns(log_returns_7d)

        # 3. Calculate correlation matrix
        correlation_matrix = self.calculate_correlation_matrix(log_returns_7d, window=CORRELATION_WINDOW)
        self.db.upsert_correlation_matrix(correlation_matrix)

        self.db.close()
        print("\n✅ All metrics calculated and stored successfully")


# ============================================================================
# MAIN
# ============================================================================

def main():
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

    calculator = MetricsCalculator()
    calculator.run_all_calculations(backfill=args.backfill)


if __name__ == "__main__":
    main()
