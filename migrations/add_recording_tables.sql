-- Migration: Add session recording and replay tables
-- Date: 2025-11-10
-- Description: Adds tables for recording trading sessions and replaying them with different parameters

-- Create recorded_sessions table
CREATE TABLE IF NOT EXISTS recorded_sessions (
    id SERIAL PRIMARY KEY,
    recording_id VARCHAR(36) UNIQUE NOT NULL,
    session_id VARCHAR(36) NOT NULL REFERENCES trading_sessions(session_id),
    instance_id INTEGER NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,

    recording_start_time TIMESTAMPTZ NOT NULL,
    recording_end_time TIMESTAMPTZ,

    status VARCHAR(20) NOT NULL DEFAULT 'recording',

    original_parameters JSONB,

    symbols_recorded TEXT,
    total_bars_recorded INTEGER DEFAULT 0,
    total_events_recorded INTEGER DEFAULT 0,

    original_trades INTEGER DEFAULT 0,
    original_pnl DECIMAL(12, 2),
    original_win_rate DECIMAL(5, 2),

    description TEXT,
    tags TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for recorded_sessions
CREATE INDEX IF NOT EXISTS idx_recorded_sessions_recording_id ON recorded_sessions(recording_id);
CREATE INDEX IF NOT EXISTS idx_recorded_sessions_session_id ON recorded_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_recorded_sessions_instance_id ON recorded_sessions(instance_id);
CREATE INDEX IF NOT EXISTS idx_recorded_sessions_strategy ON recorded_sessions(strategy_name);
CREATE INDEX IF NOT EXISTS idx_recorded_sessions_status ON recorded_sessions(status);
CREATE INDEX IF NOT EXISTS idx_recorded_sessions_start_time ON recorded_sessions(recording_start_time);

-- Create recorded_market_data table
CREATE TABLE IF NOT EXISTS recorded_market_data (
    id SERIAL PRIMARY KEY,
    recording_id VARCHAR(36) NOT NULL REFERENCES recorded_sessions(recording_id) ON DELETE CASCADE,

    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10, 4) NOT NULL,
    high DECIMAL(10, 4) NOT NULL,
    low DECIMAL(10, 4) NOT NULL,
    close DECIMAL(10, 4) NOT NULL,
    volume BIGINT NOT NULL,

    indicators JSONB,

    sequence INTEGER NOT NULL,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uix_recording_symbol_time UNIQUE (recording_id, symbol, timestamp)
);

-- Create indexes for recorded_market_data
CREATE INDEX IF NOT EXISTS idx_recorded_market_data_recording_id ON recorded_market_data(recording_id);
CREATE INDEX IF NOT EXISTS idx_recorded_market_data_symbol ON recorded_market_data(symbol);
CREATE INDEX IF NOT EXISTS idx_recorded_market_data_timestamp ON recorded_market_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_recorded_market_data_sequence ON recorded_market_data(sequence);

-- Create recorded_events table
CREATE TABLE IF NOT EXISTS recorded_events (
    id SERIAL PRIMARY KEY,
    recording_id VARCHAR(36) NOT NULL REFERENCES recorded_sessions(recording_id) ON DELETE CASCADE,

    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    sequence INTEGER NOT NULL,

    symbol VARCHAR(10),

    event_data JSONB NOT NULL,
    decision_metadata JSONB,
    market_state JSONB,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for recorded_events
CREATE INDEX IF NOT EXISTS idx_recorded_events_recording_id ON recorded_events(recording_id);
CREATE INDEX IF NOT EXISTS idx_recorded_events_event_type ON recorded_events(event_type);
CREATE INDEX IF NOT EXISTS idx_recorded_events_timestamp ON recorded_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_recorded_events_sequence ON recorded_events(sequence);
CREATE INDEX IF NOT EXISTS idx_recorded_events_symbol ON recorded_events(symbol);

-- Create replay_sessions table
CREATE TABLE IF NOT EXISTS replay_sessions (
    id SERIAL PRIMARY KEY,
    replay_id VARCHAR(36) UNIQUE NOT NULL,
    recording_id VARCHAR(36) NOT NULL REFERENCES recorded_sessions(recording_id) ON DELETE CASCADE,

    replay_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',

    modified_parameters JSONB NOT NULL,

    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(12, 2),
    win_rate DECIMAL(5, 2),
    max_drawdown DECIMAL(12, 2),
    sharpe_ratio DECIMAL(5, 2),

    trades_diff INTEGER,
    pnl_diff DECIMAL(12, 2),
    win_rate_diff DECIMAL(5, 2),

    comparison_data JSONB,
    replay_events JSONB,

    description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for replay_sessions
CREATE INDEX IF NOT EXISTS idx_replay_sessions_replay_id ON replay_sessions(replay_id);
CREATE INDEX IF NOT EXISTS idx_replay_sessions_recording_id ON replay_sessions(recording_id);
CREATE INDEX IF NOT EXISTS idx_replay_sessions_replay_time ON replay_sessions(replay_time);
CREATE INDEX IF NOT EXISTS idx_replay_sessions_status ON replay_sessions(status);

-- Create updated_at trigger function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_recorded_sessions_updated_at ON recorded_sessions;
CREATE TRIGGER update_recorded_sessions_updated_at
    BEFORE UPDATE ON recorded_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_replay_sessions_updated_at ON replay_sessions;
CREATE TRIGGER update_replay_sessions_updated_at
    BEFORE UPDATE ON replay_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Verify migration
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('recorded_sessions', 'recorded_market_data', 'recorded_events', 'replay_sessions')
ORDER BY table_name;
