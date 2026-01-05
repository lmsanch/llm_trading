# Market Metrics System - User Guide

## Overview

The market metrics system automatically calculates and stores key financial metrics using pandas DataFrames for all ETFs in the trading universe.

## What Was Implemented

### 1. Database Tables

Three new tables were added to PostgreSQL:

- **`daily_log_returns`**: Daily log returns ln(close_t / close_t-1)
- **`rolling_7day_log_returns`**: 7-day log returns ln(close_t / close_t-7)
- **`correlation_matrix`**: 30-day rolling correlation matrix of 7-day log returns

### 2. Scripts

#### `calculate_metrics.py`
Calculates all metrics using pandas DataFrames:
- Loads daily bars from database
- Calculates daily log returns (shift 1)
- Calculates 7-day log returns (shift 7)
- Calculates 30-day rolling correlation matrix (10x10 matrix per date)
- Stores results in PostgreSQL with upsert (no duplicates)

#### `fetch_market_data.py` (Enhanced)
- Now automatically runs metrics calculation after fetching data
- Can skip metrics with `--skip-metrics` flag
- Default: 180 days of historical data

#### `daily_update.sh`
- Bash script for cron job execution
- Handles environment setup and logging
- Runs daily data fetch + metrics calculation

### 3. Cron Job

Installed cron job runs Monday-Friday at 5:30 PM ET:
```bash
30 17 * * 1-5 /bin/bash /research/llm_trading/backend/storage/daily_update.sh
```

View logs:
```bash
tail -f /tmp/llm_trading_daily.log
```

## Current Data Status

- **Daily bars:** 1,300 records (130 per ETF)
- **Daily log returns:** 1,290 records
- **7-day log returns:** 1,230 records
- **Correlation pairs:** 9,400 records across 94 dates

## Sample Results

### Daily Log Returns (SPY)
```
 symbol |    date    | log_return
--------+------------+-------------
 SPY    | 2025-12-31 | -0.00743650
 SPY    | 2025-12-30 | -0.00122194
 SPY    | 2025-12-29 | -0.00356998
```

### 7-Day Log Returns (SPY)
```
 symbol |    date    | log_return_7d
--------+------------+---------------
 SPY    | 2025-12-31 |    0.00195228
 SPY    | 2025-12-30 |    0.01546075
```

### Correlation Matrix (SPY vs QQQ)
```
    date    | symbol_1 | symbol_2 | correlation
------------+----------+----------+-------------
 2025-12-31 | SPY      | QQQ      |  0.97579161
 2025-12-30 | SPY      | QQQ      |  0.97632449
```

## Usage

### Manual Data Update
```bash
# Fetch latest data and calculate metrics
python backend/storage/fetch_market_data.py daily

# Calculate metrics only (no data fetch)
python backend/storage/calculate_metrics.py

# Backfill all historical metrics
python backend/storage/calculate_metrics.py --backfill
```

### Query Data from Python

```python
import psycopg2
import pandas as pd

# Connect to database
conn = psycopg2.connect(dbname="llm_trading", user="luis")

# Load daily log returns
df = pd.read_sql_query(
    "SELECT * FROM daily_log_returns WHERE symbol = 'SPY' ORDER BY date DESC LIMIT 30",
    conn
)

# Load correlation matrix for a specific date
corr_df = pd.read_sql_query(
    """
    SELECT symbol_1, symbol_2, correlation
    FROM correlation_matrix
    WHERE date = '2025-12-31'
    """,
    conn
)

# Pivot to matrix format
corr_matrix = corr_df.pivot(index='symbol_1', columns='symbol_2', values='correlation')
print(corr_matrix)
```

### Query Data from SQL

```bash
# Daily log returns for SPY
psql -U luis -d llm_trading -c \
  "SELECT * FROM daily_log_returns WHERE symbol = 'SPY' ORDER BY date DESC LIMIT 10;"

# 7-day log returns for all symbols on latest date
psql -U luis -d llm_trading -c \
  "SELECT symbol, log_return_7d FROM rolling_7day_log_returns
   WHERE date = (SELECT MAX(date) FROM rolling_7day_log_returns)
   ORDER BY symbol;"

# Correlation matrix for latest date (10x10)
psql -U luis -d llm_trading -c \
  "SELECT symbol_1, symbol_2, ROUND(correlation::numeric, 4) as corr
   FROM correlation_matrix
   WHERE date = (SELECT MAX(date) FROM correlation_matrix)
   ORDER BY symbol_1, symbol_2;"
```

## Architecture

```
Daily OHLCV Data (daily_bars)
        ↓
[calculate_metrics.py]
        ↓
    ┌───────────────────┬────────────────────┬──────────────────────┐
    ↓                   ↓                    ↓                      ↓
Daily Log Returns   7-Day Log Returns   Correlation Matrix    (Future metrics)
(1 day lag)         (7 day lag)         (30-day window)       (volatility, etc)
```

## Cron Schedule

The system runs automatically:

1. **5:30 PM ET (Mon-Fri)**: Daily data fetch + metrics calculation
2. Market closes at 4:00 PM ET, data available by ~4:15 PM ET
3. Our fetch at 5:30 PM ET ensures data is ready
4. Metrics calculated immediately after fetch

## Files Reference

| File | Purpose |
|------|---------|
| `backend/storage/postgres_schema.sql` | Database schema with new tables |
| `backend/storage/fetch_market_data.py` | Fetch daily bars from Alpaca (180 days default) |
| `backend/storage/calculate_metrics.py` | Calculate metrics using pandas |
| `backend/storage/daily_update.sh` | Cron job script |
| `backend/storage/crontab_setup.txt` | Cron installation instructions |
| `backend/storage/METRICS_GUIDE.md` | This file |

## Next Steps

To add more metrics (e.g., volatility, Sharpe ratio):

1. Add new table to `postgres_schema.sql`
2. Add calculation method to `calculate_metrics.py`
3. Add upsert method to `MetricsDB` class
4. Call from `run_all_calculations()`
5. Run `python calculate_metrics.py --backfill`

## Troubleshooting

**Q: Metrics not calculating?**
```bash
# Run manually to see errors
python backend/storage/calculate_metrics.py
```

**Q: Cron job not running?**
```bash
# Check cron logs
tail -f /tmp/llm_trading_daily.log

# Test cron script manually
bash backend/storage/daily_update.sh
```

**Q: Missing data in correlation matrix?**
- Correlation requires at least 30 days of 7-day log returns
- First correlation appears on day 37 (7 days for lag + 30 days for window)

**Q: NaN values in log returns?**
- First daily log return is NaN (requires previous day)
- First 7 7-day log returns are NaN (require 7 previous days)
- This is expected behavior

## Performance Notes

- Pandas operations are fast even on large datasets
- Current 180 days × 10 ETFs = 1,800 bars processes in <1 second
- Correlation calculation for 94 dates × 100 pairs = ~2 seconds
- All upserts use bulk insert for speed

## Data Integrity

- All inserts use `ON CONFLICT ... DO UPDATE` to prevent duplicates
- Tables have `UNIQUE(symbol, date)` constraints
- Correlation matrix has `UNIQUE(date, symbol_1, symbol_2)` constraint
- Metrics are recalculated on each run (idempotent)
