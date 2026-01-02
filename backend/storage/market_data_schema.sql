-- Market Data Database Schema
-- Stores OHLCV data for tradable instruments
-- Seeded with last 30 days, then appended daily + hourly snapshots

-- ============================================================================
-- TABLES
-- ============================================================================

-- Daily OHLCV data (seeded with last 30 days, appended daily at close)
CREATE TABLE IF NOT EXISTS daily_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,  -- YYYY-MM-DD
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

-- Hourly snapshots at checkpoint times (09:00, 12:00, 14:00, 15:50 ET)
-- Used for daily conviction checks
CREATE TABLE IF NOT EXISTS hourly_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO8601 timestamp
    date TEXT NOT NULL,       -- YYYY-MM-DD (for easy queries)
    hour INTEGER NOT NULL,    -- 9, 12, 14, 15 (ET)
    price REAL NOT NULL,
    volume INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

-- Last fetch tracking (to avoid duplicate API calls)
CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetch_type TEXT NOT NULL,  -- 'daily_close', 'hourly_snapshot'
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    UNIQUE(symbol, fetch_type, timestamp)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_daily_bars_symbol_date ON daily_bars(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_bars_date ON daily_bars(date DESC);
CREATE INDEX IF NOT EXISTS idx_hourly_snapshots_symbol_timestamp ON hourly_snapshots(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hourly_snapshots_date ON hourly_snapshots(date DESC);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Latest daily bar per symbol
CREATE VIEW IF NOT EXISTS v_latest_daily AS
SELECT
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume,
    created_at
FROM daily_bars
WHERE (symbol, date) IN (
    SELECT symbol, MAX(date)
    FROM daily_bars
    GROUP BY symbol
);

-- Most recent hourly snapshot per symbol
CREATE VIEW IF NOT EXISTS v_latest_hourly AS
SELECT
    symbol,
    timestamp,
    date,
    hour,
    price,
    volume,
    created_at
FROM hourly_snapshots
WHERE (symbol, timestamp) IN (
    SELECT symbol, MAX(timestamp)
    FROM hourly_snapshots
    GROUP BY symbol
);

-- 30-day history for a symbol (for research)
-- Usage: SELECT * FROM v_30day_history WHERE symbol = 'SPY'
CREATE VIEW IF NOT EXISTS v_30day_history AS
SELECT
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume,
    CAST(strftime('%s', date) AS INTEGER) as date_epoch
FROM daily_bars
WHERE date >= date('now', '-30 days')
ORDER BY symbol, date DESC;
