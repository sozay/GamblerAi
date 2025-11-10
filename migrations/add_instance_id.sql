-- Migration: Add multi-instance support to trading_sessions table
-- Date: 2025-11-10
-- Description: Adds instance_id, strategy_name, and allocated_capital columns

-- Add instance_id column (defaults to 1 for existing sessions)
ALTER TABLE trading_sessions
ADD COLUMN IF NOT EXISTS instance_id INTEGER NOT NULL DEFAULT 1;

-- Add strategy_name column
ALTER TABLE trading_sessions
ADD COLUMN IF NOT EXISTS strategy_name VARCHAR(100);

-- Add allocated_capital column
ALTER TABLE trading_sessions
ADD COLUMN IF NOT EXISTS allocated_capital DECIMAL(12,2);

-- Create index on instance_id for better query performance
CREATE INDEX IF NOT EXISTS idx_sessions_instance_id ON trading_sessions(instance_id);

-- Create index on strategy_name for filtering
CREATE INDEX IF NOT EXISTS idx_sessions_strategy ON trading_sessions(strategy_name);

-- Update existing sessions with default strategy name
UPDATE trading_sessions
SET strategy_name = 'Mean Reversion + Relative Strength'
WHERE strategy_name IS NULL;

-- Verify migration
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'trading_sessions'
  AND column_name IN ('instance_id', 'strategy_name', 'allocated_capital');
