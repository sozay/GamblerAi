# Recovery System Implementation

## Summary

Implemented a comprehensive recovery system for the GamblerAI trading platform that ensures positions are never lost due to crashes or restarts. The system automatically persists all trading state to the database and reconciles with the Alpaca API on startup.

## What Was Implemented

### 1. Database Models (`gambler_ai/storage/models.py`)

Added three new SQLAlchemy models:

- **TradingSession**: Tracks trading session metadata, status, and parameters
- **Position**: Persists individual positions with entry/exit details, P&L, and status
- **OrderJournal**: Immutable transaction log for all orders placed

### 2. State Manager (`gambler_ai/trading/state_manager.py`)

Core component for state persistence:
- Create and resume trading sessions
- Save and update positions in real-time
- Log orders to transaction journal
- Retrieve session statistics
- Handle graceful shutdown

### 3. Position Reconciler (`gambler_ai/trading/position_reconciler.py`)

Handles startup recovery:
- Compare Alpaca API positions vs local database
- Import positions opened externally
- Close orphaned positions (closed in Alpaca but not locally)
- Full recovery workflow with detailed reporting

### 4. Recovery-Aware Trading Script (`scripts/alpaca_paper_trading_recovery.py`)

Enhanced version of the original trading script:
- Automatic state persistence to database
- Position reconciliation on startup
- Resume from previous session support
- Graceful shutdown handling (SIGINT, SIGTERM)
- Database-backed position tracking
- Transaction journal for all orders

### 5. Test Suite (`scripts/test_recovery_system.py`)

Comprehensive test script:
- Test state manager functionality
- Test position reconciler
- Test full recovery workflow
- Simulate crash scenarios
- Cleanup utilities

### 6. Documentation (`docs/RECOVERY_GUIDE.md`)

Complete user guide covering:
- Architecture overview
- Usage instructions
- Recovery scenarios
- Best practices
- Troubleshooting
- Technical details

## Key Features

### Automatic State Persistence
- All positions saved to PostgreSQL in real-time
- Every order logged to immutable transaction journal
- Session metadata tracked

### Crash Recovery
- Detect unexpected shutdowns
- Reconcile with Alpaca API on startup
- Resume monitoring from last known state

### Position Reconciliation
- Compare local DB vs Alpaca API
- Handle three scenarios:
  1. Matched positions (both systems agree)
  2. Orphaned local positions (closed in Alpaca)
  3. New Alpaca positions (opened externally)

### Graceful Shutdown
- Handle SIGINT (Ctrl+C) and SIGTERM
- Save final checkpoint
- Mark session properly stopped

### Transaction Journal
- Immutable audit trail
- Track order lifecycle
- Debugging and compliance

## Usage Examples

### Start New Session
```bash
python scripts/alpaca_paper_trading_recovery.py \
    --symbols "AAPL,MSFT,GOOGL" \
    --duration 120
```

### Resume After Crash
```bash
python scripts/alpaca_paper_trading_recovery.py --resume
```

### Reconcile Positions Only
```bash
python scripts/alpaca_paper_trading_recovery.py --reconcile-only
```

### Initialize Database
```bash
python scripts/alpaca_paper_trading_recovery.py --init-db
```

### Run Tests
```bash
python scripts/test_recovery_system.py
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         AlpacaPaperTraderWithRecovery               │
│                                                      │
│  ┌──────────────┐        ┌──────────────┐          │
│  │ Trading Loop │───────▶│ Alpaca API   │          │
│  └──────────────┘        └──────────────┘          │
│         │                        │                  │
│         │                        │                  │
│         ▼                        ▼                  │
│  ┌──────────────┐        ┌──────────────┐          │
│  │ State        │◀──────▶│ Position     │          │
│  │ Manager      │        │ Reconciler   │          │
│  └──────────────┘        └──────────────┘          │
│         │                        │                  │
└─────────┼────────────────────────┼──────────────────┘
          │                        │
          ▼                        ▼
   ┌─────────────────────────────────────┐
   │     PostgreSQL Database             │
   │                                     │
   │  ┌────────────────────────────┐    │
   │  │ trading_sessions           │    │
   │  ├────────────────────────────┤    │
   │  │ positions                  │    │
   │  ├────────────────────────────┤    │
   │  │ order_journal              │    │
   │  └────────────────────────────┘    │
   └─────────────────────────────────────┘
```

## Recovery Flow

```
┌──────────────┐
│   Startup    │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Resume Last Session? │
└──────┬───────────────┘
       │ Yes
       ▼
┌──────────────────────┐
│ Load from Database   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Query Alpaca API     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Reconcile Positions  │
│                      │
│ • Match existing     │
│ • Import new         │
│ • Close orphaned     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Resume Monitoring    │
└──────────────────────┘
```

## Files Changed/Added

### New Files
- `gambler_ai/trading/__init__.py`
- `gambler_ai/trading/state_manager.py`
- `gambler_ai/trading/position_reconciler.py`
- `scripts/alpaca_paper_trading_recovery.py`
- `scripts/test_recovery_system.py`
- `docs/RECOVERY_GUIDE.md`
- `RECOVERY_IMPLEMENTATION.md`

### Modified Files
- `gambler_ai/storage/models.py` - Added TradingSession, Position, OrderJournal models

## Database Schema

### trading_sessions
- session_id (unique)
- start_time, end_time
- status (active/stopped/crashed)
- initial_capital, final_capital
- symbols (JSON)
- parameters (JSON)

### positions
- session_id (FK)
- symbol, direction, side
- entry_time, entry_price, quantity
- stop_loss, take_profit
- exit_time, exit_price, exit_reason
- pnl, pnl_pct
- status (open/closed/error)
- order IDs

### order_journal
- session_id (FK)
- position_id (FK)
- alpaca_order_id, client_order_id
- symbol, order_type, side, quantity
- status, filled details
- timestamps
- error tracking

## Testing

The test suite validates:
1. State manager can create sessions and persist positions
2. Orders are logged to transaction journal
3. Positions can be retrieved and updated
4. Position reconciler can detect differences
5. New Alpaca positions are imported
6. Orphaned positions are closed
7. Full recovery workflow works end-to-end

Run tests with:
```bash
python scripts/test_recovery_system.py
```

## Next Steps

Potential enhancements:
- [ ] Redis caching for faster state access
- [ ] WebSocket streaming for real-time updates
- [ ] Automatic recovery on exceptions (retry logic)
- [ ] Multi-session management UI
- [ ] Performance analytics dashboard
- [ ] Automated testing with mock Alpaca API

## Benefits

1. **Reliability**: Never lose positions due to crashes
2. **Auditability**: Complete transaction history
3. **Debugging**: Full state history for troubleshooting
4. **Compliance**: Immutable order journal
5. **Flexibility**: Resume from any point
6. **Safety**: Automatic reconciliation prevents drift

## Migration Path

For existing users:
1. Update code with new recovery implementation
2. Run `--init-db` to create new tables
3. Start using recovery-enabled script
4. Old positions won't be tracked (start fresh or manually import)
5. All new sessions will have full recovery support
