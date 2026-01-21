#!/usr/bin/env python3
"""
Calculate and store account performance metrics.

Calculations:
1. Cumulative returns from execution events
2. Sharpe ratio (risk-adjusted returns)
3. Maximum drawdown (worst peak-to-trough decline)
4. Volatility (standard deviation of returns)
5. Win rate (percentage of profitable weeks)

ASYNC PATTERNS USED:
    This module demonstrates batch operations with asyncpg connection pool.
    See backend/db/ASYNC_PATTERNS.md for complete documentation.

    Key patterns:
    - Batch inserts use conn.executemany() for performance
    - Connection pool is acquired with 'async with pool.acquire()'
    - All database operations use 'await'
    - Parameter placeholders use $1, $2, $3 (not %s)

Usage:
    python calculate_performance.py              # Calculate all-time metrics
    python calculate_performance.py --weeks 4    # Calculate 4-week metrics
    python calculate_performance.py --weeks 8    # Calculate 8-week metrics
    python calculate_performance.py --all        # Calculate all time periods
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
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

# 6 Paper trading accounts
ACCOUNTS = ["GPT", "GEMINI", "CLAUDE", "GROK", "COUNCIL", "BASELINE"]

# Risk-free rate for Sharpe ratio (annualized, e.g., 0.04 = 4%)
RISK_FREE_RATE = 0.04

# Weeks per year for annualization
WEEKS_PER_YEAR = 52


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class PerformanceDB:
    """PostgreSQL database manager for performance calculations using async connection pool."""

    def __init__(self):
        # No longer stores connection - uses pool from get_pool()
        pass

    async def load_execution_events(self, weeks_lookback: int = None) -> pd.DataFrame:
        """
        Load execution events from database into pandas DataFrame.

        Args:
            weeks_lookback: Number of weeks to look back (None = all time)

        Returns:
            DataFrame with columns: account, week_id, event_type, event_data, occurred_at
        """
        # Calculate cutoff date if weeks_lookback is specified
        where_clause = ""
        params = []

        if weeks_lookback:
            cutoff_date = datetime.now() - timedelta(weeks=weeks_lookback)
            where_clause = "WHERE occurred_at >= $1"
            params.append(cutoff_date)

        query = f"""
            SELECT account, week_id, event_type, event_data, occurred_at
            FROM execution_events
            {where_clause}
            ORDER BY account, occurred_at
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
            rows = await conn.fetch(query, *params)
            # Convert to list of dicts for DataFrame
            data = [dict(row) for row in rows]
            df = pd.DataFrame(data)

            # Ensure occurred_at column is datetime
            if not df.empty:
                df['occurred_at'] = pd.to_datetime(df['occurred_at'])

            print(f"📊 Loaded {len(df)} execution events from database")
            return df

    async def upsert_account_performance(self, df: pd.DataFrame):
        """
        Upsert account performance to database.

        Args:
            df: DataFrame with columns: account, weeks_lookback, total_return, sharpe_ratio,
                max_drawdown, volatility, weeks_traded, profitable_weeks, win_rate,
                avg_conviction, max_conviction
        """
        if df.empty:
            print("  ⚠️  No account performance to insert")
            return

        # ASYNC PATTERN: Batch operations (efficient bulk insert)
        # - Prepare list of tuples for executemany()
        # - Each tuple contains parameters for one row ($1, $2, $3, ...)
        # - Much faster than calling execute() in a loop (single transaction)
        # - For 100 rows: 1 round-trip vs 100 round-trips
        data = [
            (
                row['account'],
                row['weeks_lookback'] if pd.notna(row['weeks_lookback']) else None,
                float(row['total_return']) if pd.notna(row['total_return']) else 0.0,
                float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else None,
                float(row['max_drawdown']) if pd.notna(row['max_drawdown']) else None,
                float(row['volatility']) if pd.notna(row['volatility']) else None,
                int(row['weeks_traded']) if pd.notna(row['weeks_traded']) else 0,
                int(row['profitable_weeks']) if pd.notna(row['profitable_weeks']) else 0,
                float(row['win_rate']) if pd.notna(row['win_rate']) else None,
                float(row['avg_conviction']) if pd.notna(row['avg_conviction']) else None,
                float(row['max_conviction']) if pd.notna(row['max_conviction']) else None,
                datetime.now()
            )
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
                INSERT INTO account_performance (
                    account, weeks_lookback, total_return, sharpe_ratio, max_drawdown,
                    volatility, weeks_traded, profitable_weeks, win_rate,
                    avg_conviction, max_conviction, calculated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (account, weeks_lookback) DO UPDATE SET
                    total_return = EXCLUDED.total_return,
                    sharpe_ratio = EXCLUDED.sharpe_ratio,
                    max_drawdown = EXCLUDED.max_drawdown,
                    volatility = EXCLUDED.volatility,
                    weeks_traded = EXCLUDED.weeks_traded,
                    profitable_weeks = EXCLUDED.profitable_weeks,
                    win_rate = EXCLUDED.win_rate,
                    avg_conviction = EXCLUDED.avg_conviction,
                    max_conviction = EXCLUDED.max_conviction,
                    calculated_at = EXCLUDED.calculated_at,
                    updated_at = NOW()
                """,
                data
            )
        print(f"  ✅ Upserted {len(df)} account performance records")


# ============================================================================
# PERFORMANCE CALCULATIONS
# ============================================================================

def calculate_weekly_returns(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate weekly returns for each account from execution events.

    Args:
        events_df: DataFrame with execution events

    Returns:
        DataFrame with columns: account, week_id, weekly_return, conviction
    """
    if events_df.empty:
        return pd.DataFrame(columns=['account', 'week_id', 'weekly_return', 'conviction'])

    weekly_data = []

    # Group by account and week_id
    for (account, week_id), group in events_df.groupby(['account', 'week_id']):
        # Extract entry and exit events
        entries = group[group['event_type'] == 'ENTRY']
        exits = group[group['event_type'] == 'EXIT']

        # Calculate return if we have both entry and exit
        if not entries.empty and not exits.empty:
            entry = entries.iloc[0]
            exit_event = exits.iloc[-1]

            # Extract prices from event_data
            entry_price = entry['event_data'].get('price', 0)
            exit_price = exit_event['event_data'].get('price', 0)
            direction = entry['event_data'].get('direction', 'FLAT')
            conviction = entry['event_data'].get('conviction', 0)

            # Calculate return based on direction
            if entry_price > 0:
                if direction == 'LONG':
                    weekly_return = (exit_price - entry_price) / entry_price
                elif direction == 'SHORT':
                    weekly_return = (entry_price - exit_price) / entry_price
                else:
                    weekly_return = 0.0
            else:
                weekly_return = 0.0

            weekly_data.append({
                'account': account,
                'week_id': week_id,
                'weekly_return': weekly_return,
                'conviction': conviction
            })
        # If no exit yet (still holding), assume 0 return for now
        elif not entries.empty:
            entry = entries.iloc[0]
            conviction = entry['event_data'].get('conviction', 0)
            weekly_data.append({
                'account': account,
                'week_id': week_id,
                'weekly_return': 0.0,
                'conviction': conviction
            })

    return pd.DataFrame(weekly_data)


def calculate_account_metrics(weekly_df: pd.DataFrame, account: str) -> dict:
    """
    Calculate performance metrics for a single account.

    Args:
        weekly_df: DataFrame with weekly returns
        account: Account name

    Returns:
        Dictionary with performance metrics
    """
    account_data = weekly_df[weekly_df['account'] == account]

    if account_data.empty:
        return {
            'account': account,
            'total_return': 0.0,
            'sharpe_ratio': None,
            'max_drawdown': None,
            'volatility': None,
            'weeks_traded': 0,
            'profitable_weeks': 0,
            'win_rate': None,
            'avg_conviction': None,
            'max_conviction': None
        }

    # Basic statistics
    returns = account_data['weekly_return'].values
    weeks_traded = len(returns)
    profitable_weeks = (returns > 0).sum()
    win_rate = profitable_weeks / weeks_traded if weeks_traded > 0 else None

    # Cumulative return (product of (1 + r) - 1)
    total_return = np.prod(1 + returns) - 1

    # Volatility (annualized)
    volatility = np.std(returns) * np.sqrt(WEEKS_PER_YEAR) if len(returns) > 1 else None

    # Sharpe ratio (annualized)
    if volatility and volatility > 0:
        avg_weekly_return = np.mean(returns)
        risk_free_weekly = RISK_FREE_RATE / WEEKS_PER_YEAR
        sharpe_ratio = (avg_weekly_return - risk_free_weekly) / (np.std(returns) + 1e-10) * np.sqrt(WEEKS_PER_YEAR)
    else:
        sharpe_ratio = None

    # Maximum drawdown
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = np.min(drawdown) if len(drawdown) > 0 else None

    # Conviction statistics
    convictions = account_data['conviction'].values
    avg_conviction = np.mean(convictions) if len(convictions) > 0 else None
    max_conviction = np.max(convictions) if len(convictions) > 0 else None

    return {
        'account': account,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'volatility': volatility,
        'weeks_traded': weeks_traded,
        'profitable_weeks': profitable_weeks,
        'win_rate': win_rate,
        'avg_conviction': avg_conviction,
        'max_conviction': max_conviction
    }


async def calculate_performance(weeks_lookback: int = None):
    """
    Calculate performance metrics for all accounts.

    Args:
        weeks_lookback: Number of weeks to look back (None = all time)
    """
    period_label = f"{weeks_lookback}w" if weeks_lookback else "all-time"
    print(f"\n{'='*60}")
    print(f"Calculating {period_label} performance metrics")
    print(f"{'='*60}\n")

    db = PerformanceDB()

    # Load execution events
    events_df = await db.load_execution_events(weeks_lookback)

    if events_df.empty:
        print(f"⚠️  No execution events found for {period_label}")
        return

    # Calculate weekly returns
    print("📈 Calculating weekly returns...")
    weekly_df = calculate_weekly_returns(events_df)

    if weekly_df.empty:
        print(f"⚠️  No weekly returns calculated for {period_label}")
        return

    print(f"  ✅ Calculated returns for {len(weekly_df)} weeks")

    # Calculate metrics for each account
    print("📊 Calculating account metrics...")
    metrics = []
    for account in ACCOUNTS:
        account_metrics = calculate_account_metrics(weekly_df, account)
        account_metrics['weeks_lookback'] = weeks_lookback
        metrics.append(account_metrics)

        # Print summary
        total_ret = account_metrics['total_return'] * 100
        sharpe = account_metrics['sharpe_ratio']
        win_rate = account_metrics['win_rate'] * 100 if account_metrics['win_rate'] else 0
        print(f"  {account:10s}: Return={total_ret:+7.2f}%, Sharpe={sharpe:6.2f}, Win Rate={win_rate:5.1f}%")

    # Convert to DataFrame and upsert
    metrics_df = pd.DataFrame(metrics)
    print(f"\n💾 Saving {period_label} metrics to database...")
    await db.upsert_account_performance(metrics_df)

    print(f"\n✅ {period_label.capitalize()} performance calculation complete!")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calculate and store account performance metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculate_performance.py              # Calculate all-time metrics
  python calculate_performance.py --weeks 4    # Calculate 4-week metrics
  python calculate_performance.py --weeks 8    # Calculate 8-week metrics
  python calculate_performance.py --all        # Calculate all time periods
        """
    )
    parser.add_argument(
        '--weeks',
        type=int,
        default=None,
        help='Number of weeks to look back (default: None = all time)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Calculate all time periods (all-time, 4w, 8w)'
    )

    args = parser.parse_args()

    # Initialize connection pool
    await init_pool()

    try:
        if args.all:
            # Calculate all time periods
            await calculate_performance(None)  # All-time
            await calculate_performance(4)     # 4 weeks
            await calculate_performance(8)     # 8 weeks
        else:
            # Calculate single time period
            await calculate_performance(args.weeks)
    finally:
        # Close connection pool
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
