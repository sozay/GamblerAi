# Session Checkpointing Guide

## Overview

Session checkpointing enables the GamblerAi trading system to save its state at regular intervals, allowing it to resume from the last known state after crashes, restarts, or unexpected shutdowns. This feature provides robust fault tolerance and ensures no trading data is lost.

## Features

### Core Capabilities

1. **Automatic State Persistence**
   - Periodic snapshots of active positions
   - Account information (portfolio value, buying power, cash)
   - Strategy parameters
   - Session metadata

2. **Fast Recovery**
   - Resume from last checkpoint
   - Restore positions and account state
   - Continue trading seamlessly

3. **Checkpoint Management**
   - Automatic cleanup of old checkpoints
   - Configurable retention policies
   - Checkpoint statistics and monitoring

4. **Data Integrity**
   - Complete snapshot of all active positions
   - Immutable checkpoint records
   - Audit trail for state changes

## Architecture

### Components

```
gambler_ai/trading/
├── checkpoint_manager.py    # Core checkpoint management
├── state_manager.py          # Enhanced with checkpoint integration
└── position_reconciler.py    # Reconciles with Alpaca API
```

### Database Schema

The `position_checkpoints` table stores checkpoint data:

```sql
CREATE TABLE position_checkpoints (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    checkpoint_time TIMESTAMP WITH TIME ZONE NOT NULL,
    positions_snapshot JSON,              -- Active positions
    account_snapshot JSON,                -- Account state
    active_positions_count INTEGER,
    closed_trades_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Checkpoint Data Structure

Each checkpoint contains:

```json
{
  "positions_snapshot": {
    "AAPL": {
      "id": 123,
      "symbol": "AAPL",
      "entry_time": "2025-11-08T10:00:00Z",
      "entry_price": 150.50,
      "qty": 100,
      "direction": "UP",
      "side": "buy",
      "stop_loss": 147.49,
      "take_profit": 156.52,
      "order_id": "alpaca_order_123",
      "status": "active"
    }
  },
  "account_snapshot": {
    "portfolio_value": 100500.00,
    "buying_power": 50000.00,
    "cash": 45000.00,
    "timestamp": "2025-11-08T10:00:00Z",
    "strategy_params": {
      "stop_loss_pct": 2.0,
      "take_profit_pct": 4.0,
      "position_size": 10000
    }
  },
  "active_positions_count": 1,
  "closed_trades_count": 0
}
```

## Usage

### Basic Usage in Trading Scripts

```python
from gambler_ai.storage.database import get_analytics_db
from gambler_ai.trading.state_manager import StateManager

# Initialize
db_manager = get_analytics_db()
db_session = db_manager.get_session_direct()
state_manager = StateManager(db_session)

# Create session
session_id = state_manager.create_session(
    symbols=['AAPL', 'MSFT'],
    initial_capital=100000.0,
    duration_minutes=60
)

# During trading loop - create periodic checkpoints
account_info = {
    'portfolio_value': 100500.00,
    'buying_power': 50000.00,
    'cash': 45000.00
}

strategy_params = {
    'stop_loss_pct': 2.0,
    'take_profit_pct': 4.0
}

checkpoint_id = state_manager.create_checkpoint(
    account_info=account_info,
    strategy_params=strategy_params
)

# Resume from checkpoint after restart
session = state_manager.resume_session(session_id)
restored_state = state_manager.restore_from_latest_checkpoint()

print(f"Restored {restored_state['active_count']} positions")
print(f"Portfolio value: ${restored_state['account_info']['portfolio_value']}")
```

### Using with Alpaca Paper Trading Script

The `alpaca_paper_trading_recovery.py` script has built-in checkpointing:

```bash
# Start trading with default 30-second checkpoint interval
python scripts/alpaca_paper_trading_recovery.py \
    --symbols AAPL,MSFT,GOOGL \
    --duration 60 \
    --interval 60

# Custom checkpoint interval (every 60 seconds)
python scripts/alpaca_paper_trading_recovery.py \
    --symbols AAPL,MSFT,GOOGL \
    --duration 60 \
    --checkpoint-interval 60

# Resume from last active session
python scripts/alpaca_paper_trading_recovery.py \
    --resume

# Resume specific session
python scripts/alpaca_paper_trading_recovery.py \
    --resume-session abc-123-def-456
```

### Checkpoint Management API

#### Create Checkpoint

```python
checkpoint_id = state_manager.create_checkpoint(
    account_info={'portfolio_value': 100000.00},
    strategy_params={'stop_loss_pct': 2.0}
)
```

#### Restore from Latest Checkpoint

```python
restored_state = state_manager.restore_from_latest_checkpoint()

# Access restored data
positions = restored_state['positions']
account_info = restored_state['account_info']
checkpoint_time = restored_state['checkpoint_time']
```

#### List Checkpoints

```python
# Get last 10 checkpoints
checkpoints = state_manager.list_checkpoints(limit=10)

for cp in checkpoints:
    print(f"Checkpoint at {cp.checkpoint_time}")
    print(f"  Active positions: {cp.active_positions_count}")
    print(f"  Closed trades: {cp.closed_trades_count}")
```

#### Get Checkpoint Statistics

```python
stats = state_manager.get_checkpoint_stats()

print(f"Total checkpoints: {stats['total_checkpoints']}")
print(f"First checkpoint: {stats['first_checkpoint']}")
print(f"Last checkpoint: {stats['last_checkpoint']}")
print(f"Time span: {stats['time_span_minutes']} minutes")
print(f"Avg interval: {stats['avg_interval_seconds']} seconds")
```

#### Cleanup Old Checkpoints

```python
# Keep only last 100 checkpoints
deleted = state_manager.cleanup_old_checkpoints(keep_count=100)
print(f"Deleted {deleted} old checkpoints")

# Delete checkpoints older than 24 hours
deleted = state_manager.cleanup_old_checkpoints(
    keep_count=50,
    older_than_hours=24
)
```

## Recovery Scenarios

### Scenario 1: Application Crash

**What happens:**
1. Trading application crashes unexpectedly
2. Last checkpoint was created 15 seconds ago

**Recovery:**
```bash
# Restart with resume flag
python scripts/alpaca_paper_trading_recovery.py --resume
```

**Result:**
- Resumes last active session
- Restores positions from last checkpoint
- Reconciles with Alpaca API
- Continues trading

### Scenario 2: Planned Restart

**What happens:**
1. User stops application with Ctrl+C
2. Graceful shutdown creates final checkpoint
3. Session marked as 'completed'

**Recovery:**
```bash
# Resume specific session
python scripts/alpaca_paper_trading_recovery.py \
    --resume-session abc-123-def-456
```

**Result:**
- Restores exact state at shutdown
- All positions preserved
- Account state matches

### Scenario 3: Server Restart

**What happens:**
1. Server reboots unexpectedly
2. Multiple active sessions exist

**Recovery:**
```bash
# Reconcile positions only (verify state)
python scripts/alpaca_paper_trading_recovery.py --reconcile-only

# Then resume
python scripts/alpaca_paper_trading_recovery.py --resume
```

**Result:**
- Identifies all active sessions
- Reconciles positions with Alpaca
- Safe to resume trading

## Best Practices

### Checkpoint Frequency

**Recommended intervals:**
- **High-frequency trading**: 10-15 seconds
- **Normal trading**: 30 seconds (default)
- **Long-term positions**: 60-120 seconds

**Trade-offs:**
- Shorter intervals = Better recovery, more database writes
- Longer intervals = Less overhead, potential data loss

```python
# Configure in script
trader.checkpoint_interval = 30  # seconds
```

### Cleanup Strategy

**Retention policies:**
- Keep at least 100 recent checkpoints
- Delete checkpoints older than 24 hours for completed sessions
- Keep all checkpoints for active sessions

```python
# During session end
state_manager.cleanup_old_checkpoints(
    keep_count=100,
    older_than_hours=24
)
```

### Monitoring

**Key metrics to track:**
- Checkpoint success rate
- Average checkpoint creation time
- Storage used by checkpoints
- Time since last checkpoint

```python
# Get stats periodically
stats = state_manager.get_checkpoint_stats()

# Alert if no checkpoint in last 5 minutes
time_since_last = (datetime.now(timezone.utc) -
                   stats['last_checkpoint']).seconds
if time_since_last > 300:
    print("⚠ WARNING: No checkpoint in 5 minutes")
```

## Integration with Recovery System

Checkpointing works alongside the existing recovery infrastructure:

```
Session Start
    ↓
Create/Resume Session
    ↓
Restore from Checkpoint (if exists)
    ↓
Reconcile with Alpaca API
    ↓
Start Trading Loop
    ↓
Create Checkpoints Every N Seconds
    ↓
On Shutdown: Final Checkpoint
    ↓
End Session
```

### Combined Recovery Flow

```python
# Full recovery process
trader = AlpacaPaperTraderWithRecovery(
    api_key=api_key,
    api_secret=api_secret,
    db_session=db_session,
    resume_session_id=session_id
)

# 1. Resume session (loads from DB)
# 2. Restore from checkpoint (gets last known state)
# 3. Reconcile positions (syncs with Alpaca)
# 4. Start trading (continues from exact state)
```

## Performance Considerations

### Database Impact

- Each checkpoint writes JSON data to PostgreSQL
- Typical checkpoint size: 1-10 KB
- At 30-second intervals: ~120 checkpoints/hour
- Storage: ~1-10 MB/hour

### Optimization Tips

1. **Batch checkpoint cleanup**
   ```python
   # Clean up during off-hours
   if hour >= 22 or hour <= 6:
       state_manager.cleanup_old_checkpoints(keep_count=50)
   ```

2. **Adjust frequency based on activity**
   ```python
   # More frequent during active trading
   if len(active_positions) > 0:
       checkpoint_interval = 30
   else:
       checkpoint_interval = 120
   ```

3. **Use connection pooling**
   ```python
   # Database manager handles pooling automatically
   db_manager = get_analytics_db()
   ```

## Troubleshooting

### Issue: Checkpoints not being created

**Check:**
```python
# Verify session exists
if not state_manager.session_id:
    print("No active session")

# Check for errors
try:
    state_manager.create_checkpoint()
except Exception as e:
    print(f"Error: {e}")
```

### Issue: Cannot restore from checkpoint

**Check:**
```python
# Verify checkpoint exists
checkpoint = state_manager.checkpoint_manager.get_latest_checkpoint(session_id)
if not checkpoint:
    print("No checkpoints found")
else:
    print(f"Latest checkpoint: {checkpoint.checkpoint_time}")
```

### Issue: Too many checkpoints

**Solution:**
```python
# Aggressive cleanup
deleted = state_manager.cleanup_old_checkpoints(
    keep_count=20,
    older_than_hours=1
)
print(f"Deleted {deleted} checkpoints")
```

## Testing

Run the test suite to verify checkpoint functionality:

```bash
# Run all tests
python tests/test_session_checkpointing.py

# Expected output:
# ✓ TEST 1: Checkpoint Creation - PASSED
# ✓ TEST 2: Checkpoint Restoration - PASSED
# ✓ TEST 3: Checkpoint Cleanup - PASSED
# ✓ TEST 4: Session Resume with Checkpoint - PASSED
```

## API Reference

### SessionCheckpointManager

#### `create_checkpoint(session_id, account_info, strategy_params)`
Create a new checkpoint for a session.

**Parameters:**
- `session_id` (str): Trading session ID
- `account_info` (dict, optional): Account snapshot data
- `strategy_params` (dict, optional): Strategy parameters

**Returns:** Checkpoint ID (int)

#### `get_latest_checkpoint(session_id)`
Get the most recent checkpoint for a session.

**Parameters:**
- `session_id` (str): Trading session ID

**Returns:** PositionCheckpoint object or None

#### `restore_from_checkpoint(checkpoint)`
Extract state from a checkpoint for restoration.

**Parameters:**
- `checkpoint` (PositionCheckpoint): Checkpoint to restore from

**Returns:** Dictionary with restored state

#### `list_checkpoints(session_id, limit)`
List checkpoints for a session.

**Parameters:**
- `session_id` (str): Trading session ID
- `limit` (int): Maximum number to return

**Returns:** List of PositionCheckpoint objects

#### `cleanup_old_checkpoints(session_id, keep_count, older_than_hours)`
Remove old checkpoints.

**Parameters:**
- `session_id` (str): Trading session ID
- `keep_count` (int): Minimum number to keep
- `older_than_hours` (int, optional): Delete older than N hours

**Returns:** Number deleted (int)

### StateManager Extensions

#### `create_checkpoint(account_info, strategy_params)`
Create checkpoint for current session.

#### `restore_from_latest_checkpoint()`
Restore from latest checkpoint.

#### `list_checkpoints(limit)`
List checkpoints for current session.

#### `get_checkpoint_stats()`
Get checkpoint statistics for current session.

#### `cleanup_old_checkpoints(keep_count, older_than_hours)`
Clean up old checkpoints for current session.

## See Also

- [Recovery Guide](RECOVERY_GUIDE.md) - Complete recovery system documentation
- [State Management](../gambler_ai/trading/state_manager.py) - Core state management
- [Position Reconciler](../gambler_ai/trading/position_reconciler.py) - Alpaca reconciliation
