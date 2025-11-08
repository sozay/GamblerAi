# Trading Recovery System Guide

## Overview

The GamblerAI trading system now includes a comprehensive recovery mechanism that ensures positions are never lost due to crashes or restarts. The system automatically persists all trading state to the database and can reconcile with the Alpaca API on startup.

## Features

### 1. **State Persistence**
- All positions are saved to PostgreSQL database in real-time
- Every order is logged to an immutable transaction journal
- Trading sessions are tracked with metadata

### 2. **Crash Recovery**
- Automatically detects when the system was stopped unexpectedly
- Reconciles local database state with Alpaca API positions
- Resumes monitoring from the last known state

### 3. **Position Reconciliation**
- Compares positions between local database and Alpaca API
- Identifies orphaned positions (closed remotely but not locally)
- Imports positions opened outside the system
- Ensures data consistency

### 4. **Graceful Shutdown**
- Handles SIGINT (Ctrl+C) and SIGTERM signals
- Saves final checkpoint before exit
- Marks session as properly stopped

### 5. **Transaction Journal**
- Immutable log of all orders placed
- Tracks order lifecycle (submitted, filled, cancelled, rejected)
- Audit trail for compliance and debugging

## Architecture

### Database Models

#### TradingSession
Tracks trading session metadata:
- `session_id`: Unique session identifier
- `start_time`, `end_time`: Session timestamps
- `status`: 'active', 'stopped', or 'crashed'
- `initial_capital`, `final_capital`: Portfolio values
- `symbols`: List of traded symbols
- `parameters`: Strategy configuration

#### Position
Tracks individual positions:
- Entry details: time, price, quantity, direction
- Risk management: stop loss, take profit
- Order IDs: entry, stop loss, take profit orders
- Exit details: time, price, reason
- Performance: P&L and percentage
- Status: 'open', 'closed', 'error'

#### OrderJournal
Immutable transaction log:
- Order details: symbol, type, side, quantity
- Status tracking: pending, filled, cancelled, rejected
- Execution details: filled quantity, average price
- Timestamps: submitted, filled, cancelled
- Error tracking: rejection reasons

### Components

#### StateManager
`gambler_ai/trading/state_manager.py`

Manages persistent state:
- `create_session()`: Start new trading session
- `resume_session()`: Resume existing session
- `save_position()`: Persist position to database
- `update_position()`: Update position (usually to close)
- `get_open_positions()`: Load open positions from DB
- `log_order()`: Add order to transaction journal
- `update_order_status()`: Update order status

#### PositionReconciler
`gambler_ai/trading/position_reconciler.py`

Reconciles state on startup:
- `reconcile()`: Compare Alpaca vs local positions
- `import_alpaca_positions()`: Import missing positions
- `recover_orphaned_positions()`: Close orphaned positions
- `full_recovery()`: Complete reconciliation workflow

#### AlpacaPaperTraderWithRecovery
`scripts/alpaca_paper_trading_recovery.py`

Enhanced trading script with recovery:
- Automatic state persistence
- Signal handling for graceful shutdown
- Position reconciliation on startup
- Database-backed position tracking

## Usage

### First Time Setup

1. **Initialize the database:**
```bash
python scripts/alpaca_paper_trading_recovery.py --init-db
```

This creates the necessary tables in the analytics database.

### Starting a New Session

```bash
python scripts/alpaca_paper_trading_recovery.py \
    --symbols "AAPL,MSFT,GOOGL,TSLA,NVDA" \
    --duration 120 \
    --interval 60
```

This starts a new trading session that:
- Creates a new session in the database
- Monitors the specified symbols
- Persists all positions and orders
- Can be recovered if interrupted

### Resuming After Crash

If the system crashes or is stopped unexpectedly:

```bash
# Resume the last active session
python scripts/alpaca_paper_trading_recovery.py --resume

# Or resume a specific session
python scripts/alpaca_paper_trading_recovery.py --resume-session SESSION_ID
```

The system will:
1. Load the previous session from database
2. Query Alpaca API for current positions
3. Reconcile differences:
   - Import positions opened in Alpaca
   - Close positions that were closed in Alpaca
   - Verify matched positions
4. Resume monitoring

### Reconcile Positions Only

To just reconcile without starting trading:

```bash
python scripts/alpaca_paper_trading_recovery.py --reconcile-only
```

This is useful for:
- Checking position sync
- Cleaning up orphaned positions
- Importing external positions

### Environment Variables

Set your Alpaca credentials:
```bash
export ALPACA_API_KEY='your_api_key'
export ALPACA_API_SECRET='your_api_secret'
```

Or pass as arguments:
```bash
python scripts/alpaca_paper_trading_recovery.py \
    --api-key YOUR_KEY \
    --api-secret YOUR_SECRET
```

## Recovery Scenarios

### Scenario 1: System Crash During Trading

**What happens:**
- System crashes while monitoring 3 open positions
- Positions remain open in Alpaca
- Local database has positions marked as 'open'

**Recovery:**
```bash
python scripts/alpaca_paper_trading_recovery.py --resume
```

**Result:**
- System loads positions from database
- Queries Alpaca API
- Finds 3 matching positions
- Resumes monitoring all 3 positions

### Scenario 2: Position Closed Externally

**What happens:**
- Position manually closed in Alpaca web interface
- Local database still shows position as 'open'

**Recovery:**
```bash
python scripts/alpaca_paper_trading_recovery.py --resume
```

**Result:**
- System detects position missing in Alpaca
- Marks position as 'closed' in database
- Sets exit_reason to 'recovered_closed'
- Calculates P&L if current price available

### Scenario 3: Position Opened Externally

**What happens:**
- Position opened manually in Alpaca
- Not tracked in local database

**Recovery:**
```bash
python scripts/alpaca_paper_trading_recovery.py --resume
```

**Result:**
- System detects new position in Alpaca
- Imports position to local database
- Begins monitoring the position
- Uses current timestamp as entry_time

### Scenario 4: Database and Alpaca Both Empty

**What happens:**
- Fresh start or all positions closed

**Recovery:**
```bash
python scripts/alpaca_paper_trading_recovery.py
```

**Result:**
- Creates new session
- Starts monitoring for signals
- No reconciliation needed

## Monitoring Recovery

### Check Session Status

Query the database to see session history:

```python
from gambler_ai.storage.database import get_analytics_db

db = get_analytics_db()
with db.get_session() as session:
    from gambler_ai.storage.models import TradingSession

    sessions = session.query(TradingSession).order_by(
        TradingSession.start_time.desc()
    ).limit(10).all()

    for s in sessions:
        print(f"{s.session_id}: {s.status} - {s.start_time} to {s.end_time}")
```

### Check Position History

```python
from gambler_ai.storage.database import get_analytics_db

db = get_analytics_db()
with db.get_session() as session:
    from gambler_ai.storage.models import Position

    positions = session.query(Position).filter_by(
        session_id='YOUR_SESSION_ID'
    ).all()

    for p in positions:
        print(f"{p.symbol}: {p.status} - Entry ${p.entry_price} - P&L ${p.pnl}")
```

### Check Order Journal

```python
from gambler_ai.storage.database import get_analytics_db

db = get_analytics_db()
with db.get_session() as session:
    from gambler_ai.storage.models import OrderJournal

    orders = session.query(OrderJournal).filter_by(
        session_id='YOUR_SESSION_ID'
    ).all()

    for o in orders:
        print(f"{o.symbol} {o.side} {o.quantity} - {o.status}")
```

## Best Practices

1. **Always use the recovery-enabled script** (`alpaca_paper_trading_recovery.py`) for live trading

2. **Resume after any interruption** - Use `--resume` flag to ensure consistency

3. **Reconcile periodically** - Run with `--reconcile-only` to verify state

4. **Monitor logs** - Check database for orphaned positions or failed orders

5. **Handle signals gracefully** - The system catches SIGINT/SIGTERM, let it shutdown properly

6. **Backup the database** - The analytics database contains all trading history

## Troubleshooting

### Issue: "No active session found"

**Solution:** Start a new session without `--resume` flag

### Issue: "Positions mismatch after recovery"

**Solution:** Run with `--reconcile-only` to force reconciliation

### Issue: "Database connection failed"

**Solution:** Check that PostgreSQL is running and `config.yaml` has correct credentials

### Issue: "Orders not logged to journal"

**Solution:** Ensure `db_session` is passed to trader constructor

## Technical Details

### Signal Handling

The system registers handlers for:
- `SIGINT` (Ctrl+C): Graceful shutdown
- `SIGTERM`: Graceful shutdown from system

On signal receipt:
1. Sets `shutdown_requested = True`
2. Completes current scan cycle
3. Updates session status to 'stopped'
4. Saves final checkpoint
5. Exits cleanly

### Database Schema

All recovery tables are in the analytics database (PostgreSQL).

Tables created:
- `trading_sessions`
- `positions`
- `order_journal`

Indexes created on:
- `session_id` (all tables)
- `symbol` (positions, orders)
- `status` (positions, orders, sessions)
- `alpaca_order_id` (orders)

### State Sync Strategy

1. **On position entry:**
   - Place order via Alpaca API
   - Immediately save to database
   - Track in memory

2. **On position check:**
   - Query Alpaca for current positions
   - Compare with in-memory state
   - Update database if closed

3. **On startup/resume:**
   - Load last session from database
   - Query Alpaca for current positions
   - Reconcile differences
   - Reload in-memory state

## Future Enhancements

Potential improvements:
- Redis caching for faster state access
- WebSocket streaming for real-time position updates
- Automatic recovery on exceptions
- Multi-session management
- Performance analytics dashboard
- Order replay for debugging

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `logs/gambler_ai.log`
3. Query database for position/order details
4. File an issue on GitHub
