# State Persistence & Crash Recovery

## Overview

The paper trading system now includes comprehensive state persistence and crash recovery features. All trading sessions, positions, and state checkpoints are automatically saved to the database every 30 seconds.

## Features

### 1. Trading Session Tracking

Every trading session is tracked with a unique UUID and stored in the `trading_sessions` table:

- **Session ID**: Unique identifier for recovery
- **Start/End Time**: Session duration tracking
- **Status**: `active`, `completed`, or `crashed`
- **Symbols**: List of symbols being traded
- **Portfolio Metrics**: Initial/final values, P&L, P&L %
- **Configuration**: Duration, scan interval

### 2. Position Tracking

All positions (active and closed) are tracked in the `positions` table:

- **Entry Details**: Time, price, quantity, direction (UP/DOWN), side (buy/sell)
- **Exit Details**: Time, price, reason (stop_loss_hit, take_profit_hit, etc.)
- **Risk Management**: Stop loss and take profit levels
- **Order ID**: Links to Alpaca order for verification
- **P&L Tracking**: Actual profit/loss and percentage

### 3. Periodic Checkpoints

State checkpoints are saved every 30 seconds to the `position_checkpoints` table:

- **Positions Snapshot**: Complete state of all active positions (JSON)
- **Account Snapshot**: Portfolio value, buying power, cash (JSON)
- **Counts**: Number of active positions and closed trades
- **Timestamp**: When checkpoint was created

### 4. Crash Detection

On startup, the system:
- Checks for sessions with status = 'active'
- Marks old active sessions as 'crashed'
- Displays information about crashed sessions
- Continues with new session

## Database Schema

### trading_sessions

```sql
CREATE TABLE trading_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    symbols TEXT,
    duration_minutes INTEGER,
    scan_interval_seconds INTEGER,
    initial_portfolio_value DECIMAL(12,2),
    final_portfolio_value DECIMAL(12,2),
    pnl DECIMAL(12,2),
    pnl_pct DECIMAL(5,2),
    total_trades INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### positions

```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_time TIMESTAMP WITH TIME ZONE,
    entry_price DECIMAL(10,2) NOT NULL,
    exit_price DECIMAL(10,2),
    qty INTEGER NOT NULL,
    direction VARCHAR(10) NOT NULL,
    side VARCHAR(10) NOT NULL,
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    order_id VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    exit_reason VARCHAR(50),
    pnl DECIMAL(12,2),
    pnl_pct DECIMAL(5,2),
    duration_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
);
```

### position_checkpoints

```sql
CREATE TABLE position_checkpoints (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    checkpoint_time TIMESTAMP WITH TIME ZONE NOT NULL,
    positions_snapshot JSON,
    account_snapshot JSON,
    active_positions_count INTEGER DEFAULT 0,
    closed_trades_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
);
```

## Usage

### Enable State Persistence (Default)

```python
from scripts.alpaca_paper_trading import AlpacaPaperTrader

trader = AlpacaPaperTrader(api_key, api_secret, enable_persistence=True)
trader.run_paper_trading(symbols=['AAPL', 'MSFT'], duration_minutes=60)
```

### Disable State Persistence

```python
trader = AlpacaPaperTrader(api_key, api_secret, enable_persistence=False)
```

### Command Line

```bash
# State persistence is enabled by default
python scripts/alpaca_paper_trading.py \
  --api-secret YOUR_SECRET \
  --symbols "AAPL,MSFT,TSLA" \
  --duration 60 \
  --interval 60
```

## Crash Recovery Process

### What Happens During a Crash

1. **Session Status**: Remains as 'active' in database
2. **Positions**: Last checkpoint preserved with all active positions
3. **Checkpoints**: Available for analysis up to last save (max 30s ago)

### What Happens on Restart

1. **Detection**: System queries for sessions with status='active'
2. **Notification**: Displays crashed session information to user
3. **Cleanup**: Marks crashed sessions as status='crashed'
4. **New Session**: Starts fresh with new session ID

### Recovering Position Data

To recover positions from a crashed session:

```python
from gambler_ai.storage import get_analytics_db, Position, PositionCheckpoint

db = get_analytics_db()

# Get crashed session
with db.get_session() as session:
    # Find crashed session
    crashed = session.query(TradingSession).filter_by(
        status='crashed'
    ).order_by(TradingSession.start_time.desc()).first()

    # Get last checkpoint
    checkpoint = session.query(PositionCheckpoint).filter_by(
        session_id=crashed.session_id
    ).order_by(PositionCheckpoint.checkpoint_time.desc()).first()

    # Recover position state
    positions = checkpoint.positions_snapshot
    account = checkpoint.account_snapshot
```

## Configuration

### Checkpoint Interval

Default is 30 seconds. To change:

```python
trader = AlpacaPaperTrader(api_key, api_secret)
trader.checkpoint_interval = 60  # Change to 60 seconds
```

## Benefits

1. **Crash Safety**: Never lose position tracking even with power loss or crash
2. **Session History**: Complete audit trail of all trading sessions
3. **Performance Analysis**: Detailed P&L tracking per position and session
4. **Recovery**: Ability to recover and reconcile state after crashes
5. **Monitoring**: Real-time visibility into checkpoint status

## Limitations

### Current Implementation

- Checkpoints save state every 30 seconds (max 30s data loss on crash)
- Exit reasons require additional API calls to Alpaca (not yet implemented)
- Recovery is manual (future: automatic recovery and resumption)

### Future Enhancements

1. **Automatic Recovery**: Resume monitoring positions after crash
2. **Reconciliation**: Compare database state with Alpaca API on startup
3. **Exit Reason Detection**: Query Alpaca orders endpoint for exit reasons
4. **Manual Intervention**: UI for manually closing/adjusting positions
5. **Real-time Sync**: Reduce checkpoint interval or use event-driven updates

## Testing

Run the test script to verify state persistence:

```bash
python test_state_persistence.py
```

Expected output:
```
✓ TradingSession model
✓ Position model
✓ PositionCheckpoint model
✅ All model tests passed!
```

## Monitoring

### Check Active Sessions

```sql
SELECT session_id, start_time, status, symbols, pnl
FROM trading_sessions
WHERE status = 'active'
ORDER BY start_time DESC;
```

### View Recent Checkpoints

```sql
SELECT
    session_id,
    checkpoint_time,
    active_positions_count,
    closed_trades_count
FROM position_checkpoints
WHERE session_id = 'YOUR_SESSION_ID'
ORDER BY checkpoint_time DESC
LIMIT 10;
```

### Analyze Session Performance

```sql
SELECT
    session_id,
    start_time,
    end_time,
    status,
    initial_portfolio_value,
    final_portfolio_value,
    pnl,
    pnl_pct,
    total_trades
FROM trading_sessions
WHERE status = 'completed'
ORDER BY pnl DESC
LIMIT 10;
```

## Troubleshooting

### Database Connection Issues

If database connection fails:
- State persistence automatically disables
- Warning message displayed
- Trading continues without persistence

### Checkpoint Failures

Individual checkpoint failures:
- Warning logged but trading continues
- Next checkpoint attempt in 30 seconds

### Manual Recovery

To manually mark all active sessions as crashed:

```sql
UPDATE trading_sessions
SET status = 'crashed', updated_at = NOW()
WHERE status = 'active';
```
