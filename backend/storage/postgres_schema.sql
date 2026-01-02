-- ============================================================================
-- LLM Trading - PostgreSQL Schema
-- ============================================================================
-- Database: llm_trading
-- Stores: Market data, research reports, PM pitches, peer reviews, executions
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- MARKET DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_bars (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_bars_symbol_date ON daily_bars(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_bars_date ON daily_bars(date DESC);

-- Hourly snapshots at checkpoint times (for conviction updates)
CREATE TABLE IF NOT EXISTS hourly_snapshots (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    date DATE NOT NULL,
    hour INTEGER NOT NULL,
    price DECIMAL(12,4),
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_hourly_snapshots_symbol_timestamp ON hourly_snapshots(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_hourly_snapshots_date ON hourly_snapshots(date DESC);

-- ============================================================================
-- RESEARCH REPORTS (RAW STORAGE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS research_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_id VARCHAR(10) NOT NULL,

    -- Provider metadata
    provider VARCHAR(20) NOT NULL,
    model VARCHAR(100) NOT NULL,

    -- Raw responses (stored for full audit trail)
    natural_language TEXT NOT NULL,
    structured_json JSONB NOT NULL,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,

    -- Timestamps
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT provider_valid CHECK (provider IN ('perplexity', 'gemini'))
);

CREATE INDEX IF NOT EXISTS idx_research_week_provider ON research_reports(week_id, provider);
CREATE INDEX IF NOT EXISTS idx_research_status ON research_reports(status);

-- JSONB indexes for querying structured fields
CREATE INDEX IF NOT EXISTS idx_research_macro_regime ON research_reports USING GIN ((structured_json->'macro_regime'));
CREATE INDEX IF NOT EXISTS idx_research_candidates ON research_reports USING GIN ((structured_json->'tradable_candidates'));

-- ============================================================================
-- PM PITCHES (RAW STORAGE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pm_pitches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_id VARCHAR(10) NOT NULL,

    -- Pitch metadata
    model VARCHAR(100) NOT NULL,
    account VARCHAR(20) NOT NULL,

    -- Full pitch (stored as JSONB)
    pitch_data JSONB NOT NULL,

    -- Quick access fields (copied from JSONB for performance)
    instrument VARCHAR(10),
    direction VARCHAR(10),
    conviction DECIMAL(4,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pm_pitches_week ON pm_pitches(week_id);
CREATE INDEX IF NOT EXISTS idx_pm_pitches_account ON pm_pitches(account);
CREATE INDEX IF NOT EXISTS idx_pm_pitches_instrument ON pm_pitches(instrument);

-- ============================================================================
-- PEER REVIEWS (RAW STORAGE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS peer_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_id VARCHAR(10) NOT NULL,

    pitch_id UUID NOT NULL,
    reviewer_model VARCHAR(100) NOT NULL,

    -- Anonymized label (A, B, C, D, E)
    pitch_label VARCHAR(5) NOT NULL,

    -- Full review (stored as JSONB)
    review_data JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_peer_reviews_week ON peer_reviews(week_id);
CREATE INDEX IF NOT EXISTS idx_peer_reviews_pitch ON peer_reviews(pitch_id);

-- ============================================================================
-- CHAIRMAN DECISIONS (RAW STORAGE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS chairman_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_id VARCHAR(10) NOT NULL UNIQUE,

    -- Full decision (stored as JSONB)
    decision_data JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- EXECUTION EVENTS (Event Sourcing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS execution_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_id VARCHAR(10) NOT NULL,

    -- Event metadata
    event_type VARCHAR(50) NOT NULL,
    account VARCHAR(20) NOT NULL,

    -- Full event data (stored as JSONB)
    event_data JSONB NOT NULL,

    -- Timestamp
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_week ON execution_events(week_id);
CREATE INDEX IF NOT EXISTS idx_events_account ON execution_events(account);
CREATE INDEX IF NOT EXISTS idx_events_type ON execution_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_occurred ON execution_events(occurred_at DESC);

-- ============================================================================
-- FETCH LOG (for monitoring data collection)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fetch_log (
    id SERIAL PRIMARY KEY,
    fetch_type VARCHAR(50) NOT NULL,
    symbol VARCHAR(10),
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fetch_log_timestamp ON fetch_log(timestamp DESC);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Latest research for a week (both providers)
CREATE OR REPLACE VIEW v_latest_research AS
SELECT
    week_id,
    provider,
    model,
    natural_language,
    structured_json,
    status,
    generated_at
FROM research_reports
WHERE (week_id, provider, generated_at) IN (
    SELECT week_id, provider, MAX(generated_at)
    FROM research_reports
    GROUP BY week_id, provider
);

-- Latest daily bar per symbol
CREATE OR REPLACE VIEW v_latest_daily AS
SELECT
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume
FROM daily_bars
WHERE (symbol, date) IN (
    SELECT symbol, MAX(date)
    FROM daily_bars
    GROUP BY symbol
);

-- All pitches for a week with review counts
CREATE OR REPLACE VIEW v_weekly_pitches AS
SELECT
    p.id,
    p.week_id,
    p.model,
    p.account,
    p.pitch_data->>'instrument' as instrument,
    p.pitch_data->>'direction' as direction,
    (p.pitch_data->>'conviction')::decimal as conviction,
    COUNT(r.id) as review_count
FROM pm_pitches p
LEFT JOIN peer_reviews r ON r.pitch_id = p.id
GROUP BY p.id
ORDER BY (p.pitch_data->>'conviction')::decimal DESC;

-- Execution history for an account
CREATE OR REPLACE VIEW v_account_history AS
SELECT
    week_id,
    account,
    event_type,
    event_data,
    occurred_at
FROM execution_events
ORDER BY occurred_at DESC;

-- ============================================================================
-- SAMPLE DATA FOR TESTING
-- ============================================================================

-- Insert sample market data (optional - can be removed)
-- INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
-- SELECT 'SPY', current_date - i, 480.00 + (i * 0.5), 485.00 + (i * 0.5), 478.00 + (i * 0.5), 482.00 + (i * 0.5), 50000000
-- FROM generate_series(1, 30) AS i;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Get week ID (Wednesday date)
CREATE OR REPLACE FUNCTION get_week_id()
RETURNS VARCHAR(10) AS $$
BEGIN
    RETURN TO_CHAR(
        date_trunc('week', CURRENT_DATE) + INTERVAL '3 days',
        'YYYY-MM-DD'
    );
END;
$$ LANGUAGE plpgsql;

-- Get or insert daily bar (upsert)
CREATE OR REPLACE FUNCTION upsert_daily_bar(
    p_symbol VARCHAR,
    p_date DATE,
    p_open DECIMAL,
    p_high DECIMAL,
    p_low DECIMAL,
    p_close DECIMAL,
    p_volume BIGINT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
    VALUES (p_symbol, p_date, p_open, p_high, p_low, p_close, p_volume)
    ON CONFLICT (symbol, date) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;
