# Data Fetcher Setup Guide

The market data fetcher is a **separate script** from the trading logic. It runs via cron to keep the SQLite database populated with the latest market data.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FETCHER (cron)                      │
│  backend/storage/data_fetcher.py                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────────┐                   │
│  │  Alpaca API │───▶│  SQLite DB       │                   │
│  │             │    │  market_data.db  │                   │
│  └─────────────┘    └────────┬─────────┘                   │
│                              │                              │
│                              ▼                              │
│                    ┌──────────────────┐                    │
│                    │  Daily Bars      │                    │
│                    │  (30 days)       │                    │
│                    ├──────────────────┤                    │
│                    │  Hourly Snaps    │                    │
│                    │  (checkpoints)   │                    │
│                    └──────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  TRADING LOGIC                              │
│  ResearchStage, CheckpointEngine, etc.                     │
├─────────────────────────────────────────────────────────────┤
│                     Query DB                                │
│                     (no API calls)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Initial Setup

### 1. Seed the Database

Run once to populate with the last 30 days of historical data:

```bash
cd /research/llm_trading/backend
python -m storage.data_fetcher seed --days 30
```

Expected output:
```
🌱 Seeding initial data: Last 30 days
============================================================

📊 Fetching SPY...
  ✅ Inserted 22 bars for SPY
...
✅ Initial data seeding complete
```

### 2. Verify Database

```bash
sqlite3 backend/storage/market_data.db "SELECT symbol, COUNT(*) as bars FROM daily_bars GROUP BY symbol;"
```

Expected output:
```
SPY|30
QQQ|30
IWM|30
...
```

---

## Cron Job Setup

### Option 1: User Crontab (Recommended)

```bash
crontab -e
```

Add these entries:

```crontab
# Market Data Fetcher
# Daily: 17:05 ET (after market close) - update daily bars
5 17 * * 1-5 cd /research/llm_trading/backend && /usr/bin/python3 -m storage.data_fetcher daily >> /tmp/data_fetcher_daily.log 2>&1

# Hourly: :05 past checkpoint hours - fetch price snapshots
5 9,12,14,15,16 * * 1-5 cd /research/llm_trading/backend && /usr/bin/python3 -m storage.data_fetcher hourly >> /tmp/data_fetcher_hourly.log 2>&1
```

### Option 2: System-Wide Crontab

```bash
sudo nano /etc/cron.d/llm_trading_data
```

```crontab
# LLM Trading Data Fetcher
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/bin:/usr/local/bin/python3

# Daily: 17:05 ET (after market close) - update daily bars
5 17 * * 1-5 cd /research/llm_trading/backend && python3 -m storage.data_fetcher daily >> /var/log/llm_trading/data_fetcher_daily.log 2>&1

# Hourly: :05 past checkpoint hours - fetch price snapshots
5 9,12,14,15,16 * * 1-5 cd /research/llm_trading/backend && python3 -m storage.data_fetcher hourly >> /var/log/llm_trading/data_fetcher_hourly.log 2>&1
```

Then:
```bash
sudo mkdir -p /var/log/llm_trading
sudo touch /var/log/llm_trading/data_fetcher_daily.log
sudo touch /var/log/llm_trading/data_fetcher_hourly.log
sudo chmod 666 /var/log/llm_trading/*.log
sudo service cron restart
```

---

## Cron Schedule Explained

| Time (ET) | Day | Command | Purpose |
|-----------|-----|---------|---------|
| 09:05 | Mon-Fri | `hourly` | Pre-market snapshot |
| 12:05 | Mon-Fri | `hourly` | Midday snapshot |
| 14:05 | Mon-Fri | `hourly` | Afternoon snapshot |
| 15:05 | Mon-Fri | `hourly` | Late afternoon snapshot |
| 16:05 | Mon-Fri | `hourly` | Close snapshot |
| 17:05 | Mon-Fri | `daily` | Update daily bars (after close) |

---

## Manual Commands

### Update Daily Bars
```bash
cd /research/llm_trading/backend
python -m storage.data_fetcher daily
```

### Fetch Hourly Snapshots
```bash
cd /research/llm_trading/backend
python -m storage.data_fetcher hourly
```

### Re-seed Database
```bash
cd /research/llm_trading/backend
python -m storage.data_fetcher seed --days 30
```

---

## Monitoring

### Check Cron Jobs
```bash
# List user crontab
crontab -l

# Check system cron
sudo cat /etc/cron.d/llm_trading_data

# View cron logs
grep CRON /var/log/syslog | tail -20
```

### Check Data Fetcher Logs
```bash
# Daily update log
tail -f /tmp/data_fetcher_daily.log
# or
tail -f /var/log/llm_trading/data_fetcher_daily.log

# Hourly snapshot log
tail -f /tmp/data_fetcher_hourly.log
# or
tail -f /var/log/llm_trading/data_fetcher_hourly.log
```

### Query Database
```bash
sqlite3 backend/storage/market_data.db

# Latest bars
SELECT * FROM v_latest_daily;

# Latest snapshots
SELECT * FROM v_latest_hourly;

# Data freshness
SELECT symbol, date FROM daily_bars WHERE date >= date('now', '-7 days') GROUP BY symbol;

# Exit
.quit
```

---

## Troubleshooting

### Issue: Database locked
**Solution:** Ensure only one data_fetcher process runs at a time. Check for stuck processes:
```bash
ps aux | grep data_fetcher
```

### Issue: No data from Alpaca
**Solution:** Verify credentials in `.env`:
```bash
grep ALPACA_COUNCIL .env
```

### Issue: Cron not running
**Solution:** Check cron service:
```bash
sudo service cron status
# or
sudo systemctl status cron
```

### Issue: Wrong time zone
**Solution:** Cron uses server time. Adjust if server is not in ET:
```crontab
# For UTC server (ET = UTC-5, or UTC-4 during DST)
# 17:05 ET = 21:05 UTC (standard) or 22:05 UTC (DST)
5 21 * * 1-5 ...  # daily
5 13,16,18,19,20 * * 1-5 ...  # hourly
```

---

## Database Schema

### Tables

**`daily_bars`** - 30-day daily OHLCV per instrument
- `symbol`: Ticker (SPY, QQQ, etc.)
- `date`: YYYY-MM-DD
- `open, high, low, close, volume`: OHLCV data

**`hourly_snapshots`** - Checkpoint price snapshots
- `symbol`: Ticker
- `timestamp`: ISO8601 timestamp
- `date`: YYYY-MM-DD
- `hour`: Hour (9, 12, 14, 15, 16)
- `price`: Current price
- `volume`: Volume

**`fetch_log`** - Track fetch attempts
- `fetch_type`: `seed`, `daily_close`, `hourly_snapshot`
- `symbol`: Instrument
- `timestamp`: When fetch occurred
- `success`: True/False
- `error_message`: Error details if failed

### Views

**`v_latest_daily`** - Most recent daily bar per symbol
**`v_latest_hourly`** - Most recent hourly snapshot per symbol
**`v_30day_history`** - Last 30 days of bars per symbol

---

## File Locations

| File | Path |
|------|------|
| Data fetcher | `backend/storage/data_fetcher.py` |
| Database | `backend/storage/market_data.db` |
| Schema | `backend/storage/market_data_schema.sql` |
| Daily log | `/tmp/data_fetcher_daily.log` or `/var/log/llm_trading/data_fetcher_daily.log` |
| Hourly log | `/tmp/data_fetcher_hourly.log` or `/var/log/llm_trading/data_fetcher_hourly.log` |

---

## Security Notes

1. **Database**: `market_data.db` contains market data only (no credentials)
2. **.env file**: Contains Alpaca API keys - keep secure, chmod 600
3. **Logs**: May contain error messages - avoid logging sensitive data
4. **Cron**: User crontab is safer than system-wide (no sudo required)

---

## Next Steps

1. Seed database: `python -m storage.data_fetcher seed --days 30`
2. Set up cron jobs
3. Verify daily updates are working
4. ResearchStage will now query the database instead of Alpaca API
