#!/usr/bin/env python3
"""
Market Data Fetcher - Separate from trading logic

Fetches and stores OHLCV data for tradable instruments:
1. Daily bars (seed last 30 days, then append daily close)
2. Hourly snapshots at checkpoint times (09:00, 12:00, 14:00, 15:50 ET)

Runs via cron job:
- Daily: 17:00 ET (after market close) - fetch daily bars
- Hourly: :00, :05 past checkpoint hours - fetch snapshots

Database: PostgreSQL (llm_trading)
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_alpaca_client import MultiAlpacaManager
from backend.db.pool import get_pool

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Tradable universe
INSTRUMENTS = ["SPY", "QQQ", "IWM", "TLT", "HYG", "UUP", "GLD", "USO", "VIXY", "SH"]

# Checkpoint hours (ET) for hourly snapshots
CHECKPOINT_HOURS = [9, 12, 14, 15, 16]

# PostgreSQL connection (uses peer auth, no password)
DB_NAME = os.getenv("DATABASE_NAME", "llm_trading")
DB_USER = os.getenv("DATABASE_USER", "luis")

# ============================================================================
# DATABASE MANAGER
# ============================================================================

class MarketDataManager:
    """Manage PostgreSQL market data operations using async pool."""

    def __init__(self):
        # No longer stores connection - uses pool from get_pool()
        pass

    async def get_latest_date(self, symbol: str) -> Optional[str]:
        """Get the latest daily bar date for a symbol."""
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(date) as latest_date FROM daily_bars WHERE symbol = $1",
                symbol
            )
            return row["latest_date"] if row and row["latest_date"] else None

    async def insert_daily_bar(self, symbol: str, bar: Dict[str, Any]) -> bool:
        """Insert or replace a daily bar using upsert."""
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        created_at = NOW()
                """,
                    symbol,
                    bar["date"],
                    float(bar["open"]),
                    float(bar["high"]),
                    float(bar["low"]),
                    float(bar["close"]),
                    int(bar["volume"])
                )
            return True
        except Exception as e:
            print(f"  ❌ Error inserting bar for {symbol}: {e}")
            return False

    async def insert_hourly_snapshot(self, symbol: str, snapshot: Dict[str, Any]) -> bool:
        """Insert or replace an hourly snapshot."""
        try:
            # Parse timestamp for date and hour
            ts = datetime.fromisoformat(snapshot["timestamp"])
            date_str = ts.date()
            hour = ts.hour

            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO hourly_snapshots (symbol, timestamp, date, hour, price, volume)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (symbol, timestamp) DO UPDATE SET
                        price = EXCLUDED.price,
                        volume = EXCLUDED.volume,
                        created_at = NOW()
                """,
                    symbol,
                    snapshot["timestamp"],
                    date_str,
                    hour,
                    float(snapshot["price"]),
                    int(snapshot.get("volume", 0))
                )
            return True
        except Exception as e:
            print(f"  ❌ Error inserting snapshot for {symbol}: {e}")
            return False

    async def log_fetch(self, fetch_type: str, symbol: str, success: bool, error: str = None):
        """Log a fetch attempt."""
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO fetch_log (fetch_type, symbol, status, error_message)
                VALUES ($1, $2, $3, $4)
            """, fetch_type, symbol, 'success' if success else 'error', error)

    # ==========================================================================
    # QUERIES FOR RESEARCH STAGE
    # ==========================================================================

    async def get_30day_bars(self, symbol: str) -> List[Dict[str, Any]]:
        """Get 30 days of daily bars for a symbol."""
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT date, open, high, low, close, volume
                FROM daily_bars
                WHERE symbol = $1 AND date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY date DESC
            """, symbol)
            result = []
            for row in rows:
                r = dict(row)
                # Ensure numerics are floats
                for key in ['open', 'high', 'low', 'close']:
                    if r.get(key) is not None:
                        r[key] = float(r[key])
                if r.get('volume') is not None:
                    r['volume'] = int(r['volume'])
                result.append(r)
            return result

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the most recent price for a symbol."""
        pool = get_pool()
        async with pool.acquire() as conn:
            # Try hourly snapshot first
            row = await conn.fetchrow("""
                SELECT price FROM hourly_snapshots
                WHERE symbol = $1
                ORDER BY timestamp DESC
                LIMIT 1
            """, symbol)
            if row:
                return float(row["price"])

            # Fall back to daily close
            row = await conn.fetchrow("""
                SELECT close as price FROM daily_bars
                WHERE symbol = $1
                ORDER BY date DESC
                LIMIT 1
            """, symbol)
            return float(row["price"]) if row else None

    async def get_checkpoint_snapshot(self, symbol: str, date: str, hour: int) -> Optional[Dict[str, Any]]:
        """Get a specific checkpoint snapshot for a symbol."""
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT timestamp, price, volume
                FROM hourly_snapshots
                WHERE symbol = $1 AND date = $2 AND hour = $3
            """, symbol, date, hour)
            return dict(row) if row else None


# ============================================================================
# DATA FETCHER
# ============================================================================

class MarketDataFetcher:
    """Fetch market data from Alpaca and store in PostgreSQL."""

    def __init__(self):
        self.db = MarketDataManager()
        self.manager = MultiAlpacaManager()
        self.client = self.manager.get_client("COUNCIL")

    async def seed_initial_data(self, days: int = 30):
        """Seed database with initial historical data."""
        from datetime import datetime, timedelta

        print(f"\n🌱 Seeding initial data: Last {days} days")
        print("=" * 60)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)

        for symbol in INSTRUMENTS:
            print(f"\n📊 Fetching {symbol}...")

            # Try multiple accounts if one fails with 401
            accounts_to_try = ["COUNCIL", "GEMINI", "CLAUDE", "CHATGPT"]
            success = False

            for account_name in accounts_to_try:
                try:
                    # Switch to different account if needed
                    if account_name != "COUNCIL":
                        print(f"  🔄 Trying {account_name} account...")
                        self.client = self.manager.get_client(account_name)

                    bars = await self.client.get_bars(
                        symbol=symbol,
                        timeframe="1Day",
                        limit=100,
                        start=start_date.isoformat() + "Z",
                        end=end_date.isoformat() + "Z",
                        adjustment="raw"
                    )

                    if not bars:
                        print(f"  ⚠️  No bars returned for {symbol}")
                        break  # No point trying other accounts if no data exists

                    inserted = 0
                    for bar in bars:
                        bar_data = {
                            "date": bar["t"][:10],
                            "open": float(bar["o"]),
                            "high": float(bar["h"]),
                            "low": float(bar["l"]),
                            "close": float(bar["c"]),
                            "volume": int(bar["v"])
                        }
                        if await self.db.insert_daily_bar(symbol, bar_data):
                            inserted += 1

                    print(f"  ✅ Inserted {inserted} bars for {symbol} (via {account_name})")
                    await self.db.log_fetch("seed", symbol, True)
                    success = True
                    break  # Success, move to next symbol

                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg and account_name != accounts_to_try[-1]:
                        # Try next account
                        continue
                    else:
                        # Last account or different error
                        print(f"  ❌ Error fetching {symbol}: {e}")
                        await self.db.log_fetch("seed", symbol, False, str(e))
                        break

        print("\n✅ Initial data seeding complete")

    async def update_daily_bars(self):
        """Fetch and update daily bars for all instruments."""
        print("\n📈 Updating daily bars")
        print("=" * 60)

        for symbol in INSTRUMENTS:
            print(f"\n📊 Updating {symbol}...")

            try:
                bars = await self.client.get_bars(
                    symbol=symbol,
                    timeframe="1Day",
                    limit=1
                )

                if not bars:
                    print(f"  ⚠️  No bars returned for {symbol}")
                    continue

                bar = bars[0]
                bar_data = {
                    "date": bar["t"][:10],
                    "open": float(bar["o"]),
                    "high": float(bar["h"]),
                    "low": float(bar["l"]),
                    "close": float(bar["c"]),
                    "volume": int(bar["v"])
                }

                latest_date = await self.db.get_latest_date(symbol)
                if latest_date == bar_data["date"]:
                    print(f"  ✓ Already have data for {bar_data['date']}")
                    continue

                if await self.db.insert_daily_bar(symbol, bar_data):
                    print(f"  ✅ Inserted bar for {bar_data['date']}")
                    await self.db.log_fetch("daily_close", symbol, True)
                else:
                    await self.db.log_fetch("daily_close", symbol, False, "Insert failed")

            except Exception as e:
                print(f"  ❌ Error updating {symbol}: {e}")
                await self.db.log_fetch("daily_close", symbol, False, str(e))

        print("\n✅ Daily bars updated")

    async def fetch_hourly_snapshots(self):
        """Fetch current price snapshots for all instruments."""
        now = datetime.now()
        hour = now.hour
        timestamp = now.isoformat()

        print(f"\n⏰ Fetching hourly snapshots at {hour}:00 ET")
        print("=" * 60)

        if hour not in CHECKPOINT_HOURS:
            print(f"  ⏭️  Skipping (not a checkpoint hour)")
            return

        for symbol in INSTRUMENTS:
            print(f"  📸 {symbol}...", end=" ")

            try:
                bars = await self.client.get_bars(
                    symbol=symbol,
                    timeframe="1Min",
                    limit=1
                )

                if not bars:
                    print("⚠️  No data")
                    continue

                bar = bars[0]
                snapshot = {
                    "timestamp": timestamp,
                    "price": float(bar["c"]),
                    "volume": int(bar["v"])
                }

                if await self.db.insert_hourly_snapshot(symbol, snapshot):
                    print("✅")
                    await self.db.log_fetch("hourly_snapshot", symbol, True)
                else:
                    print("❌")
                    await self.db.log_fetch("hourly_snapshot", symbol, False, "Insert failed")

            except Exception as e:
                print(f"❌ {e}")
                await self.db.log_fetch("hourly_snapshot", symbol, False, str(e))

        print("\n✅ Hourly snapshots updated")

    async def get_market_snapshot_for_research(self) -> Dict[str, Any]:
        """Get market snapshot for research (called by ResearchStage)."""
        market_data = {
            "asof_et": datetime.now().isoformat(),
            "instruments": {}
        }

        for symbol in INSTRUMENTS:
            bars = await self.db.get_30day_bars(symbol)

            if not bars:
                print(f"  ⚠️  No data for {symbol}")
                continue

            closes = [bar["close"] for bar in bars]
            sma_20 = sum(closes[:20]) / 20 if len(closes) >= 20 else None
            sma_50 = sum(closes[:50]) / 50 if len(closes) >= 50 else None
            rsi_14 = self._calculate_rsi(closes, 14) if len(closes) >= 14 else None

            current_price = await self.db.get_current_price(symbol)
            latest = bars[0]
            previous = bars[1] if len(bars) > 1 else latest
            change_pct = ((current_price - previous["close"]) / previous["close"]) * 100 if previous["close"] > 0 else 0.0

            market_data["instruments"][symbol] = {
                "symbol": symbol,
                "current": {
                    "price": round(current_price, 2),
                    "change_pct": round(change_pct, 2)
                },
                "daily_ohlcv_30d": bars,
                "indicators": {
                    "sma_20": round(sma_20, 2) if sma_20 else None,
                    "sma_50": round(sma_50, 2) if sma_50 else None,
                    "rsi_14": round(rsi_14, 2) if rsi_14 else None,
                    "above_sma20": current_price > sma_20 if sma_20 else None,
                    "above_sma50": current_price > sma_50 if sma_50 else None,
                    "uptrend_20d": closes[0] > sma_20 if sma_20 else None,
                    "uptrend_50d": closes[0] > sma_50 if sma_50 else None
                }
            }

        return market_data

    async def get_checkpoint_snapshot_for_conviction(self) -> Dict[str, Any]:
        """Get checkpoint snapshot for daily conviction updates."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        snapshot = {
            "asof_et": now.isoformat(),
            "date": today,
            "hour": now.hour,
            "instruments": {}
        }

        pool = get_pool()
        for symbol in INSTRUMENTS:
            current_price = await self.db.get_current_price(symbol)

            # Get week open
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT close FROM daily_bars
                    WHERE symbol = $1 AND date >= date_trunc('week', CURRENT_DATE) + INTERVAL '3 days'
                        AND date < date_trunc('week', CURRENT_DATE) + INTERVAL '10 days'
                    ORDER BY date ASC
                    LIMIT 1
                """, symbol)
                week_open = row["close"] if row else None

            if current_price and week_open:
                change_pct = ((current_price - week_open) / week_open) * 100
            else:
                change_pct = None

            snapshot["instruments"][symbol] = {
                "price": round(current_price, 2) if current_price else None,
                "change_since_week_open_pct": round(change_pct, 2) if change_pct else None
            }

        return snapshot

    @staticmethod
    def _calculate_rsi(prices: list, period: int = 14) -> float:
        """Calculate Relative Strength Index (RSI)."""
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point for data fetcher."""
    import argparse

    parser = argparse.ArgumentParser(description="Market Data Fetcher (PostgreSQL)")
    parser.add_argument("command", choices=["seed", "daily", "hourly"],
                        help="Command: seed (initial data), daily (update bars), hourly (snapshots)")
    parser.add_argument("--days", type=int, default=30,
                        help="Days to seed (default: 30)")

    args = parser.parse_args()

    fetcher = MarketDataFetcher()

    if args.command == "seed":
        await fetcher.seed_initial_data(days=args.days)
    elif args.command == "daily":
        await fetcher.update_daily_bars()
    elif args.command == "hourly":
        await fetcher.fetch_hourly_snapshots()


if __name__ == "__main__":
    asyncio.run(main())
