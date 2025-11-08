# Session Checkpointing - Quick Start

## Overview

Session checkpointing automatically saves your trading state every 30 seconds, enabling seamless recovery from crashes or restarts.

## Quick Start

### 1. Basic Usage

Start trading with automatic checkpointing (enabled by default):

```bash
python scripts/alpaca_paper_trading_recovery.py \
    --symbols AAPL,MSFT,GOOGL \
    --duration 60
```

Checkpoints are created automatically every 30 seconds.

### 2. Resume After Crash

If your trading session crashes or stops, simply restart with the `--resume` flag:

```bash
python scripts/alpaca_paper_trading_recovery.py --resume
```

This will:
- Find your last active session
- Restore positions from the latest checkpoint
- Reconcile with Alpaca API
- Continue trading seamlessly

### 3. Resume Specific Session

If you have multiple sessions, resume a specific one:

```bash
python scripts/alpaca_paper_trading_recovery.py \
    --resume-session YOUR_SESSION_ID
```

### 4. Custom Checkpoint Interval

Change how often checkpoints are created:

```bash
# Create checkpoint every 60 seconds (less frequent)
python scripts/alpaca_paper_trading_recovery.py \
    --checkpoint-interval 60 \
    --symbols AAPL,MSFT

# Create checkpoint every 10 seconds (more frequent, better recovery)
python scripts/alpaca_paper_trading_recovery.py \
    --checkpoint-interval 10 \
    --symbols AAPL,MSFT
```

## What Gets Saved in a Checkpoint?

Each checkpoint saves:
- ✓ All active positions (symbol, entry price, quantity, stop loss, take profit)
- ✓ Account state (portfolio value, buying power, cash)
- ✓ Strategy parameters (stop loss %, take profit %, position size)
- ✓ Closed trades count
- ✓ Timestamp

## Recovery Scenarios

### Scenario 1: Application Crashes

**Before:** Trading AAPL, MSFT, GOOGL with 3 active positions
**Crash:** Application crashes unexpectedly
**After:** Run `--resume` flag
**Result:** All 3 positions restored, trading continues

### Scenario 2: Intentional Restart

**Before:** Running trading session
**Action:** Press Ctrl+C to stop gracefully
**After:** Restart with same command
**Result:** Can resume from exact point where you stopped

### Scenario 3: Server Reboot

**Before:** Server reboots unexpectedly
**After:** Restart application with `--resume`
**Result:** Session restored from last checkpoint (max 30 seconds of data loss with default settings)

## Configuration Options

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--resume` | False | Resume last active session |
| `--resume-session ID` | None | Resume specific session by ID |
| `--checkpoint-interval N` | 30 | Create checkpoint every N seconds |

### Programmatic Usage

```python
from gambler_ai.trading.state_manager import StateManager

# Create checkpoint manually
state_manager.create_checkpoint(
    account_info={'portfolio_value': 100000.00},
    strategy_params={'stop_loss_pct': 2.0}
)

# Restore from checkpoint
restored_state = state_manager.restore_from_latest_checkpoint()

# Get checkpoint statistics
stats = state_manager.get_checkpoint_stats()
print(f"Total checkpoints: {stats['total_checkpoints']}")
```

## Monitoring

### View Checkpoint Information

During trading, you'll see:

```
💾 Checkpoint #10 created
💾 Checkpoint #20 created
```

Every 10th checkpoint is logged to confirm the system is working.

### On Shutdown

```
⟳ Shutting down gracefully...
   Creating final checkpoint...
   Total checkpoints created: 127
   Cleaned up 27 old checkpoints
```

### On Resume

```
✓ Resumed session: abc-123-def-456
  Started: 2025-11-08 10:00:00
  Symbols: AAPL,MSFT,GOOGL
✓ Loaded 3 positions from database
✓ Restored from checkpoint created at 2025-11-08 10:45:23
  Active positions: 3
  Closed trades: 5
  Checkpoint: 2025-11-08 10:45:23
  Last known portfolio value: $102,345.67
```

## Best Practices

### 1. Checkpoint Frequency

- **Day trading (high frequency):** 10-15 seconds
- **Swing trading (normal):** 30 seconds (default)
- **Position trading (low frequency):** 60-120 seconds

### 2. Always Use Resume After Restart

```bash
# DON'T: Start new session after crash
python scripts/alpaca_paper_trading_recovery.py

# DO: Resume previous session
python scripts/alpaca_paper_trading_recovery.py --resume
```

### 3. Monitor Checkpoint Creation

Check logs to ensure checkpoints are being created regularly. If you don't see checkpoint messages, something may be wrong.

### 4. Clean Database Periodically

Old checkpoints are automatically cleaned up (keeps last 100 by default), but you can also manually clean:

```python
deleted = state_manager.cleanup_old_checkpoints(keep_count=50)
```

## Troubleshooting

### No checkpoints being created

**Check:** Is the session active?

```python
if state_manager.session_id:
    print("Session is active")
else:
    print("No active session - checkpoints won't be created")
```

### Can't resume session

**Try:** Verify session exists in database

```bash
# Reconcile positions first
python scripts/alpaca_paper_trading_recovery.py --reconcile-only

# Then resume
python scripts/alpaca_paper_trading_recovery.py --resume
```

### Too many checkpoints in database

**Solution:** Adjust cleanup settings

```python
# Keep only last 20 checkpoints
state_manager.cleanup_old_checkpoints(keep_count=20)

# Delete checkpoints older than 1 hour
state_manager.cleanup_old_checkpoints(
    keep_count=50,
    older_than_hours=1
)
```

## Testing

Test the checkpointing system:

```bash
python tests/test_session_checkpointing.py
```

Expected output:
```
✓ TEST 1: Checkpoint Creation - PASSED
✓ TEST 2: Checkpoint Restoration - PASSED
✓ TEST 3: Checkpoint Cleanup - PASSED
✓ TEST 4: Session Resume with Checkpoint - PASSED

ALL TESTS PASSED ✓
```

## Complete Example

Here's a complete workflow:

```bash
# Day 1: Start trading
python scripts/alpaca_paper_trading_recovery.py \
    --symbols AAPL,MSFT,GOOGL,TSLA,NVDA \
    --duration 360 \
    --interval 60 \
    --checkpoint-interval 30

# ... trading happens, checkpoints created every 30 seconds ...

# Application crashes!

# Day 1: Resume immediately
python scripts/alpaca_paper_trading_recovery.py --resume

# ... trading resumes from last checkpoint ...

# End of day: Stop gracefully
# Press Ctrl+C

# Day 2: Resume next day
python scripts/alpaca_paper_trading_recovery.py --resume

# All positions and state restored!
```

## Next Steps

- Read the [full documentation](docs/SESSION_CHECKPOINTING.md) for advanced usage
- Review the [Recovery Guide](docs/RECOVERY_GUIDE.md) for complete recovery system
- Check out the [API Reference](docs/SESSION_CHECKPOINTING.md#api-reference) for programmatic access

## Need Help?

- Check logs for error messages
- Verify database connection
- Ensure Alpaca API credentials are valid
- Review checkpoint statistics with `get_checkpoint_stats()`
