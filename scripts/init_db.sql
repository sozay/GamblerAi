-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create stock_prices table with time-series optimization
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    timeframe VARCHAR(10),
    PRIMARY KEY (symbol, timestamp, timeframe)
);

-- Convert to hypertable (TimescaleDB time-series optimization)
SELECT create_hypertable('stock_prices', 'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_time
    ON stock_prices (symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_stock_prices_timeframe
    ON stock_prices (timeframe, timestamp DESC);

-- Create momentum_events table
CREATE TABLE IF NOT EXISTS momentum_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    direction VARCHAR(10) NOT NULL,
    initial_price DECIMAL(10,2),
    peak_price DECIMAL(10,2),
    duration_seconds INT,
    max_move_percentage DECIMAL(5,2),
    initial_volume BIGINT,
    continuation_duration_seconds INT,
    reversal_percentage DECIMAL(5,2),
    reversal_time_seconds INT,
    timeframe VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_momentum_events_symbol
    ON momentum_events (symbol, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_momentum_events_direction
    ON momentum_events (direction, start_time DESC);

-- Create pattern_statistics table
CREATE TABLE IF NOT EXISTS pattern_statistics (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    direction VARCHAR(10),
    avg_continuation_duration INT,
    median_continuation_duration INT,
    avg_reversal_percentage DECIMAL(5,2),
    median_reversal_percentage DECIMAL(5,2),
    avg_reversal_time INT,
    median_reversal_time INT,
    confidence_score DECIMAL(3,2),
    sample_size INT,
    win_rate DECIMAL(3,2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pattern_type, timeframe, direction)
);

-- Create table for storing computed features (caching)
CREATE TABLE IF NOT EXISTS computed_features (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    timeframe VARCHAR(10),
    feature_name VARCHAR(50),
    feature_value DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, timestamp, timeframe, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_computed_features_lookup
    ON computed_features (symbol, timestamp DESC, feature_name);

-- Create data quality log table
CREATE TABLE IF NOT EXISTS data_quality_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    check_date DATE NOT NULL,
    timeframe VARCHAR(10),
    missing_periods INT DEFAULT 0,
    total_periods INT,
    quality_score DECIMAL(3,2),
    issues TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gambler;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gambler;

-- Create a view for easy momentum event analysis
CREATE OR REPLACE VIEW v_momentum_summary AS
SELECT
    symbol,
    direction,
    timeframe,
    COUNT(*) as event_count,
    AVG(max_move_percentage) as avg_move_pct,
    AVG(continuation_duration_seconds) as avg_continuation_sec,
    AVG(reversal_percentage) as avg_reversal_pct,
    AVG(reversal_time_seconds) as avg_reversal_time_sec,
    STDDEV(continuation_duration_seconds) as stddev_continuation_sec
FROM momentum_events
WHERE continuation_duration_seconds IS NOT NULL
GROUP BY symbol, direction, timeframe;

-- Add comments for documentation
COMMENT ON TABLE stock_prices IS 'Time-series storage for OHLCV stock price data';
COMMENT ON TABLE momentum_events IS 'Detected momentum events with continuation and reversal metrics';
COMMENT ON TABLE pattern_statistics IS 'Aggregated statistical patterns for momentum events';
COMMENT ON TABLE computed_features IS 'Cached technical indicators and computed features';
