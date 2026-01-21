-- ============================================================================
-- LLM Trading - Performance Metrics Schema
-- ============================================================================
-- Tables for tracking account performance over time
-- Supports leaderboard, historical analysis, and model comparison
-- ============================================================================

-- ============================================================================
-- ACCOUNT PERFORMANCE (CUMULATIVE METRICS)
-- ============================================================================

-- Cumulative performance metrics for each account
-- Recalculated periodically based on execution_events
CREATE TABLE IF NOT EXISTS account_performance (
    id SERIAL PRIMARY KEY,

    -- Account identifier (matches execution_events.account)
    account VARCHAR(20) NOT NULL,

    -- Time period filter
    weeks_lookback INTEGER,  -- NULL = all time, 4 = last 4 weeks, etc.

    -- Performance metrics
    total_return DECIMAL(12,6) NOT NULL DEFAULT 0.0,  -- Cumulative return (e.g., 0.1523 = 15.23%)
    sharpe_ratio DECIMAL(12,6),                       -- Risk-adjusted return
    max_drawdown DECIMAL(12,6),                       -- Worst peak-to-trough decline
    volatility DECIMAL(12,6),                         -- Standard deviation of returns

    -- Win/loss statistics
    weeks_traded INTEGER NOT NULL DEFAULT 0,          -- Number of weeks with positions
    profitable_weeks INTEGER NOT NULL DEFAULT 0,      -- Number of weeks with positive returns
    win_rate DECIMAL(5,4),                            -- profitable_weeks / weeks_traded

    -- Position statistics
    avg_conviction DECIMAL(4,2),                      -- Average conviction level
    max_conviction DECIMAL(4,2),                      -- Maximum conviction used

    -- Timestamps
    calculated_at TIMESTAMPTZ NOT NULL,               -- When metrics were last calculated
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one row per account per lookback period
    UNIQUE(account, weeks_lookback)
);

CREATE INDEX IF NOT EXISTS idx_account_performance_account ON account_performance(account);
CREATE INDEX IF NOT EXISTS idx_account_performance_total_return ON account_performance(total_return DESC);
CREATE INDEX IF NOT EXISTS idx_account_performance_sharpe ON account_performance(sharpe_ratio DESC);
CREATE INDEX IF NOT EXISTS idx_account_performance_calculated ON account_performance(calculated_at DESC);

-- ============================================================================
-- WEEKLY PERFORMANCE (PER-WEEK BREAKDOWN)
-- ============================================================================

-- Week-by-week performance for each account
-- Enables detailed historical analysis and win rate calculations
CREATE TABLE IF NOT EXISTS weekly_performance (
    id SERIAL PRIMARY KEY,

    -- Account and time period
    account VARCHAR(20) NOT NULL,
    week_id VARCHAR(10) NOT NULL,  -- Format: YYYY-MM-DD (Monday of week)
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    -- Weekly return metrics
    weekly_return DECIMAL(12,6),           -- Return for this week
    weekly_volatility DECIMAL(12,6),       -- Intraweek volatility

    -- Position details
    instrument VARCHAR(10),                -- Instrument traded (NULL if flat)
    direction VARCHAR(10),                 -- LONG, SHORT, or FLAT
    entry_conviction DECIMAL(4,2),         -- Initial conviction
    exit_conviction DECIMAL(4,2),          -- Final conviction (may differ due to checkpoints)

    -- Trade execution
    entry_price DECIMAL(12,4),
    exit_price DECIMAL(12,4),
    position_size INTEGER,                 -- Number of shares/units

    -- P&L
    realized_pnl DECIMAL(12,2),            -- Realized P&L in USD
    fees DECIMAL(12,2),                    -- Trading fees
    net_pnl DECIMAL(12,2),                 -- Net P&L after fees

    -- Trade metadata
    entry_reason TEXT,                     -- Why this trade was entered
    exit_reason TEXT,                      -- Why this trade was exited
    panic_exit BOOLEAN DEFAULT FALSE,      -- TRUE if exited due to unjustified panic

    -- Market context
    market_regime VARCHAR(50),             -- Macro regime during this week

    -- Timestamps
    calculated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one row per account per week
    UNIQUE(account, week_id)
);

CREATE INDEX IF NOT EXISTS idx_weekly_performance_account ON weekly_performance(account);
CREATE INDEX IF NOT EXISTS idx_weekly_performance_week ON weekly_performance(week_id);
CREATE INDEX IF NOT EXISTS idx_weekly_performance_account_week ON weekly_performance(account, week_id DESC);
CREATE INDEX IF NOT EXISTS idx_weekly_performance_return ON weekly_performance(weekly_return DESC);
CREATE INDEX IF NOT EXISTS idx_weekly_performance_date ON weekly_performance(week_start DESC);

-- ============================================================================
-- MARKET CONDITION CORRELATION
-- ============================================================================

-- Track correlation between market conditions and model performance
-- Answers: "Which models perform best in risk-on vs risk-off environments?"
CREATE TABLE IF NOT EXISTS market_condition_performance (
    id SERIAL PRIMARY KEY,

    -- Market condition
    condition_type VARCHAR(50) NOT NULL,   -- 'macro_regime', 'volatility_regime', etc.
    condition_value VARCHAR(50) NOT NULL,  -- 'RISK_ON', 'HIGH_VOLATILITY', etc.

    -- Account
    account VARCHAR(20) NOT NULL,

    -- Performance in this condition
    weeks_in_condition INTEGER NOT NULL DEFAULT 0,
    avg_return DECIMAL(12,6),
    avg_sharpe DECIMAL(12,6),
    win_rate DECIMAL(5,4),

    -- Time period
    weeks_lookback INTEGER,  -- NULL = all time

    -- Timestamps
    calculated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(condition_type, condition_value, account, weeks_lookback)
);

CREATE INDEX IF NOT EXISTS idx_market_condition_performance_account ON market_condition_performance(account);
CREATE INDEX IF NOT EXISTS idx_market_condition_performance_condition ON market_condition_performance(condition_type, condition_value);
CREATE INDEX IF NOT EXISTS idx_market_condition_performance_return ON market_condition_performance(avg_return DESC);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Leaderboard view (all-time performance, sorted by total return)
CREATE OR REPLACE VIEW v_leaderboard_all_time AS
SELECT
    ROW_NUMBER() OVER (ORDER BY total_return DESC) AS rank,
    account,
    total_return,
    sharpe_ratio,
    max_drawdown,
    volatility,
    win_rate,
    weeks_traded,
    profitable_weeks,
    calculated_at
FROM account_performance
WHERE weeks_lookback IS NULL
ORDER BY total_return DESC;

-- Recent performance (4 weeks)
CREATE OR REPLACE VIEW v_leaderboard_4w AS
SELECT
    ROW_NUMBER() OVER (ORDER BY total_return DESC) AS rank,
    account,
    total_return,
    sharpe_ratio,
    max_drawdown,
    volatility,
    win_rate,
    weeks_traded,
    profitable_weeks,
    calculated_at
FROM account_performance
WHERE weeks_lookback = 4
ORDER BY total_return DESC;

-- Recent performance (8 weeks)
CREATE OR REPLACE VIEW v_leaderboard_8w AS
SELECT
    ROW_NUMBER() OVER (ORDER BY total_return DESC) AS rank,
    account,
    total_return,
    sharpe_ratio,
    max_drawdown,
    volatility,
    win_rate,
    weeks_traded,
    profitable_weeks,
    calculated_at
FROM account_performance
WHERE weeks_lookback = 8
ORDER BY total_return DESC;

-- Council vs Individual comparison
CREATE OR REPLACE VIEW v_council_vs_individuals AS
SELECT
    CASE
        WHEN account = 'COUNCIL' THEN 'Council'
        WHEN account = 'BASELINE' THEN 'Baseline'
        ELSE 'Individual PM'
    END AS strategy_type,
    account,
    total_return,
    sharpe_ratio,
    max_drawdown,
    win_rate,
    weeks_traded
FROM account_performance
WHERE weeks_lookback IS NULL
ORDER BY
    CASE
        WHEN account = 'COUNCIL' THEN 1
        WHEN account = 'BASELINE' THEN 3
        ELSE 2
    END,
    total_return DESC;
