# Market Data Fetching - Documentation

## Overview
This system fetches historical market data from Alpaca and stores it in PostgreSQL for the LLM Trading application.

## ⚠️ IMPORTANT: Credentials Required

**For Historical Market Data Access:**
- You MUST use your **personal trading account** credentials
- Paper trading account credentials do NOT have access to historical market data API
- The personal account credentials are stored in `.env` as:
  - `ALPACA_PERSONAL_KEY_ID`
  - `ALPACA_PERSONAL_SECRET_KEY`

## Scripts

### 1. `fetch_market_data.py` (Modern - Uses alpaca-py SDK)
**Location:** `/research/llm_trading/backend/storage/fetch_market_data.py`

**Usage:**
```bash
# Initial seed (30 days of historical data)
python backend/storage/fetch_market_data.py seed --days 30

# Daily update (run after market close at 5 PM ET)
python backend/storage/fetch_market_data.py daily

# Hourly snapshots (not yet implemented)
python backend/storage/fetch_market_data.py hourly
```

**Features:**
- Uses modern `alpaca-py` library with `StockHistoricalDataClient`
- Properly handles MultiIndex DataFrames from alpaca-py
- Stores data in PostgreSQL `daily_bars` table
- Logs all fetch attempts to `fetch_log` table

### 2. `data_fetcher.py` (Legacy - Custom httpx client)
**Location:** `/research/llm_trading/backend/storage/data_fetcher.py`

**Status:** Deprecated - has authentication issues with Alpaca Data API
**Recommendation:** Use `fetch_market_data.py` instead

## Tradable Universe

Current instruments (10 ETFs):
- **SPY** - S&P 500
- **QQQ** - Nasdaq 100
- **IWM** - Russell 2000
- **TLT** - 20+ Year Treasury Bonds
- **HYG** - High Yield Corporate Bonds
- **UUP** - US Dollar Index
- **GLD** - Gold
- **USO** - Oil
- **VIXY** - VIX Short-Term Futures (volatility)
- **SH** - ProShares Short S&P500 (inverse SPY)

## Cron Setup

Add to crontab (`crontab -e`):

```bash
# Daily market data update at 5:00 PM ET (after market close)
0 17 * * 1-5 cd /research/llm_trading && python backend/storage/fetch_market_data.py daily >> /tmp/market_data_daily.log 2>&1

# Optional: Weekly full refresh on Sunday at 2 AM
0 2 * * 0 cd /research/llm_trading && python backend/storage/fetch_market_data.py seed --days 30 >> /tmp/market_data_seed.log 2>&1
```

## Database Schema

### `daily_bars` table
```sql
CREATE TABLE daily_bars (
    symbol VARCHAR(10),
    date DATE,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);
```

### `fetch_log` table
```sql
CREATE TABLE fetch_log (
    id SERIAL PRIMARY KEY,
    fetch_type VARCHAR(20),
    symbol VARCHAR(10),
    status VARCHAR(20),
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

## Troubleshooting

### 401 Unauthorized Errors
**Problem:** Getting 401 errors when fetching market data

**Solution:** 
1. Verify you're using **personal account** credentials (not paper trading)
2. Check `.env` file has correct values for:
   - `ALPACA_PERSONAL_KEY_ID`
   - `ALPACA_PERSONAL_SECRET_KEY`
3. Test credentials:
   ```bash
   python -c "from alpaca.data.historical import StockHistoricalDataClient; client = StockHistoricalDataClient('YOUR_KEY', 'YOUR_SECRET'); print('✅ Credentials work!')"
   ```

### No Data Returned
**Problem:** Script runs but no bars inserted

**Solution:**
1. Check if market was open on the requested dates
2. Verify symbol is valid and tradable
3. Check `fetch_log` table for error messages:
   ```sql
   SELECT * FROM fetch_log ORDER BY timestamp DESC LIMIT 10;
   ```

### Database Connection Errors
**Problem:** `connection to server failed`

**Solution:**
1. Ensure PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify database exists: `psql -U luis -l | grep llm_trading`
3. Check peer authentication is enabled in `pg_hba.conf`

## Adding New Instruments

1. Edit `INSTRUMENTS` list in `fetch_market_data.py`:
   ```python
   INSTRUMENTS = ["SPY", "QQQ", ..., "NEW_SYMBOL"]
   ```

2. Run seed command to populate historical data:
   ```bash
   python backend/storage/fetch_market_data.py seed --days 30
   ```

3. Verify data was inserted:
   ```sql
   SELECT symbol, COUNT(*) FROM daily_bars WHERE symbol = 'NEW_SYMBOL' GROUP BY symbol;
   ```

## API Integration

The market data is served via FastAPI endpoints:

- `GET /api/market/snapshot` - Returns current snapshot with 30-day OHLCV data
- `GET /api/research/prompt` - Includes instrument list in response

The frontend Research tab displays this data in the Market Context Snapshot section.
