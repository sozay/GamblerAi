# Session Recording and Replay System

## Overview

The Session Recording and Replay system allows you to capture complete trading sessions with all market data, signals, and decisions, then replay them with different parameters to understand how strategy behavior changes.

This is extremely useful for:
- **Parameter Optimization**: Test different parameter values without waiting for market conditions
- **Debugging**: Understand why a strategy made specific decisions
- **Strategy Analysis**: Compare outcomes with different settings
- **What-If Analysis**: See how small changes affect overall performance

## Architecture

### Core Components

1. **SessionRecorder** (`gambler_ai/trading/session_recorder.py`)
   - Captures market data (OHLCV bars with indicators)
   - Records all events (signals, orders, fills, position changes)
   - Stores decision metadata (why signals were detected)

2. **SessionReplayer** (`gambler_ai/trading/session_replayer.py`)
   - Loads recorded sessions
   - Replays market data in sequence
   - Re-runs strategy with modified parameters
   - Compares outcomes with original

3. **Database Models** (`gambler_ai/storage/models.py`)
   - `RecordedSession`: Recording metadata
   - `RecordedMarketData`: Captured price bars
   - `RecordedEvent`: All events with decision context
   - `ReplaySession`: Replay results and comparison

4. **API Endpoints** (`gambler_ai/api/routes/recordings.py`)
   - List, view, and manage recordings
   - Trigger replays with new parameters
   - Compare original vs replayed results

## Database Schema

### RecordedSession
Stores metadata about a recorded trading session:
- `recording_id`: Unique recording identifier
- `session_id`: Link to original TradingSession
- `instance_id`: Which instance was recorded
- `strategy_name`: Strategy used during recording
- `original_parameters`: All strategy parameters as JSON
- `symbols_recorded`: Symbols tracked during recording
- `total_bars_recorded`: Number of market data bars captured
- `total_events_recorded`: Number of events logged
- `original_trades`, `original_pnl`, `original_win_rate`: Original performance

### RecordedMarketData
Captures every market data bar:
- `recording_id`: Link to RecordedSession
- `symbol`, `timestamp`: Bar identification
- `open`, `high`, `low`, `close`, `volume`: OHLCV data
- `indicators`: Technical indicators calculated at this bar (JSON)
- `sequence`: Order number for replay

### RecordedEvent
Logs all events during trading:
- `event_type`: SIGNAL_DETECTED, ORDER_PLACED, ORDER_FILLED, POSITION_OPENED, POSITION_CLOSED, etc.
- `event_data`: Event-specific data (JSON)
- `decision_metadata`: Indicator values, scores, reasoning for decisions (JSON)
- `market_state`: Snapshot of market conditions (JSON)

### ReplaySession
Stores replay results:
- `replay_id`: Unique replay identifier
- `recording_id`: Link to original RecordedSession
- `modified_parameters`: Parameters changed from original (JSON)
- `total_trades`, `winning_trades`, `losing_trades`: Replay statistics
- `total_pnl`, `win_rate`, `max_drawdown`, `sharpe_ratio`: Performance metrics
- `trades_diff`, `pnl_diff`, `win_rate_diff`: Comparison with original
- `comparison_data`: Detailed comparison (JSON)
- `replay_events`: All events from replay (JSON)

## Usage

### 1. Recording a Session

#### In Python Code:
```python
from gambler_ai.trading.session_recorder import SessionRecorder
from gambler_ai.storage.database import get_db_session

# Initialize recorder
db = next(get_db_session())
recorder = SessionRecorder(
    db_session=db,
    trading_session_id="your-session-id",
    instance_id=1,
    strategy_name="Mean Reversion",
    strategy_parameters={
        'rsi_threshold': 30,
        'bb_std': 2.5,
        'position_size': 10,
    },
    symbols=['AAPL', 'MSFT', 'GOOGL'],
)

# During trading loop, record market data
recorder.record_market_data(
    symbol='AAPL',
    timestamp=datetime.now(),
    open_price=150.0,
    high=151.0,
    low=149.5,
    close=150.5,
    volume=1000000,
    indicators={'rsi': 28.5, 'bb_lower': 148.0, 'bb_upper': 152.0}
)

# Record signal detection
recorder.record_signal_detected(
    symbol='AAPL',
    signal_type='MEAN_REVERSION',
    entry_price=150.5,
    stop_loss=149.0,
    take_profit=151.5,
    indicators={'rsi': 28.5, 'bb_lower': 148.0},
    signal_strength=0.85,
    reasoning='Price below BB lower band with oversold RSI'
)

# Record position events
recorder.record_position_opened(
    symbol='AAPL',
    entry_price=150.5,
    quantity=10,
    direction='LONG',
    stop_loss=149.0,
    take_profit=151.5,
)

# Stop recording when done
recorder.stop_recording(
    description='Morning session with high volatility',
    tags=['high_volatility', 'morning_session']
)
```

#### Via API:
```bash
# Get currently active recording for an instance
curl http://localhost:9090/api/v1/recordings/instances/1/active-recording

# Note: Starting/stopping recording is currently managed within the trading script
# Future versions will support API-triggered recording
```

### 2. Viewing Recordings

#### Via API:
```bash
# List all recordings
curl http://localhost:9090/api/v1/recordings/

# Filter by instance
curl http://localhost:9090/api/v1/recordings/?instance_id=1

# Filter by status
curl http://localhost:9090/api/v1/recordings/?status=completed

# Get recording details
curl http://localhost:9090/api/v1/recordings/{recording_id}

# Get recording events
curl http://localhost:9090/api/v1/recordings/{recording_id}/events

# Filter events by type
curl "http://localhost:9090/api/v1/recordings/{recording_id}/events?event_type=SIGNAL_DETECTED"

# Get market data from recording
curl http://localhost:9090/api/v1/recordings/{recording_id}/market-data

# Filter market data by symbol
curl "http://localhost:9090/api/v1/recordings/{recording_id}/market-data?symbol=AAPL"
```

### 3. Replaying a Session

#### In Python Code:
```python
from gambler_ai.trading.session_replayer import SessionReplayer
from gambler_ai.storage.database import get_db_session
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector

# Load recording
db = next(get_db_session())
replayer = SessionReplayer(db, recording_id='your-recording-id')

# Modify parameters
replayer.set_parameters({
    'rsi_threshold': 25,  # Changed from 30
    'bb_std': 2.0,        # Changed from 2.5
    'position_size': 15,  # Changed from 10
})

# Replay with strategy detector
detector = MeanReversionDetector()
results = replayer.replay(detector)

print(f"Original trades: {results['comparison']['original_trades']}")
print(f"Replay trades: {results['total_trades']}")
print(f"Difference: {results['comparison']['trades_diff']}")

print(f"Original P&L: ${results['comparison']['original_pnl']:.2f}")
print(f"Replay P&L: ${results['total_pnl']:.2f}")
print(f"Difference: ${results['comparison']['pnl_diff']:.2f}")
```

#### Via API:
```bash
# Replay with modified parameters
curl -X POST http://localhost:9090/api/v1/recordings/{recording_id}/replay \
  -H "Content-Type: application/json" \
  -d '{
    "modified_parameters": {
      "rsi_threshold": 25,
      "bb_std": 2.0,
      "position_size": 15
    },
    "description": "Testing lower RSI threshold"
  }'

# Get all replays for a recording
curl http://localhost:9090/api/v1/recordings/{recording_id}/replays

# Get specific replay details
curl http://localhost:9090/api/v1/replays/{replay_id}
```

### 4. Comparing Results

After replaying, you can analyze the differences:

```python
# From replay results
comparison = results['comparison']

print("=== Trade Count Comparison ===")
print(f"Original: {comparison['original_trades']}")
print(f"Replay:   {comparison['replay_trades']}")
print(f"Change:   {comparison['trades_diff']:+d}")

print("\n=== P&L Comparison ===")
print(f"Original: ${comparison['original_pnl']:.2f}")
print(f"Replay:   ${comparison['replay_pnl']:.2f}")
print(f"Change:   ${comparison['pnl_diff']:+.2f}")

print("\n=== Win Rate Comparison ===")
print(f"Original: {comparison['original_win_rate']:.1f}%")
print(f"Replay:   {comparison['replay_win_rate']:.1f}%")
print(f"Change:   {comparison['win_rate_diff']:+.1f}%")

# Detailed position comparison
for position in results['positions']:
    print(f"\n{position['symbol']}:")
    print(f"  Entry:  ${position['entry_price']:.2f}")
    print(f"  Exit:   ${position['exit_price']:.2f}")
    print(f"  P&L:    ${position['pnl']:.2f} ({position['pnl_pct']:.2f}%)")
    print(f"  Reason: {position['exit_reason']}")
```

## Use Cases

### 1. Parameter Optimization

Record a session during specific market conditions, then replay with different parameter sets:

```python
# Record original session with default parameters
recorder = SessionRecorder(...)

# Later, test multiple parameter combinations
test_params = [
    {'rsi_threshold': 25, 'bb_std': 2.0},
    {'rsi_threshold': 30, 'bb_std': 2.5},
    {'rsi_threshold': 35, 'bb_std': 3.0},
]

best_pnl = float('-inf')
best_params = None

for params in test_params:
    replayer = SessionReplayer(db, recording_id)
    replayer.set_parameters(params)
    results = replayer.replay(detector)

    if results['total_pnl'] > best_pnl:
        best_pnl = results['total_pnl']
        best_params = params

print(f"Best parameters: {best_params}")
print(f"Best P&L: ${best_pnl:.2f}")
```

### 2. Debugging Wrong Behavior

When you see unexpected strategy behavior:

```bash
# Get the recording
curl http://localhost:9090/api/v1/recordings/{recording_id}

# Look at all signal detections
curl "http://localhost:9090/api/v1/recordings/{recording_id}/events?event_type=SIGNAL_DETECTED"

# Check the decision metadata to see indicator values
# Each event includes:
# - event_data: What action was taken
# - decision_metadata: Indicator values at decision time
# - market_state: Market conditions when decision was made
```

### 3. What-If Analysis

Test how small changes affect outcomes:

```python
# Original parameters
original = {'stop_loss_pct': 1.0, 'take_profit_pct': 0.5}

# Test tighter stop loss
replayer1 = SessionReplayer(db, recording_id)
replayer1.set_parameter('stop_loss_pct', 0.5)
results1 = replayer1.replay(detector)

# Test wider take profit
replayer2 = SessionReplayer(db, recording_id)
replayer2.set_parameter('take_profit_pct', 1.0)
results2 = replayer2.replay(detector)

# Compare
print(f"Tighter SL: {results1['total_trades']} trades, ${results1['total_pnl']:.2f}")
print(f"Wider TP:   {results2['total_trades']} trades, ${results2['total_pnl']:.2f}")
```

## Database Migration

To set up the recording tables in your database:

```bash
# Run the migration script
psql -h localhost -p 5433 -U gambler_user -d gambler_analytics \
  -f migrations/add_recording_tables.sql
```

The migration creates:
- `recorded_sessions` table with indexes
- `recorded_market_data` table with indexes
- `recorded_events` table with indexes
- `replay_sessions` table with indexes
- Triggers for automatic `updated_at` timestamps

## API Reference

### GET /api/v1/recordings/
List all recordings with optional filters.

**Query Parameters:**
- `instance_id` (optional): Filter by instance
- `status` (optional): Filter by status

**Response:**
```json
{
  "success": true,
  "count": 10,
  "recordings": [
    {
      "recording_id": "uuid",
      "instance_id": 1,
      "strategy_name": "Mean Reversion",
      "status": "completed",
      "recording_start_time": "2025-11-10T10:00:00Z",
      "recording_end_time": "2025-11-10T11:00:00Z",
      "total_bars_recorded": 120,
      "total_events_recorded": 45,
      "original_trades": 5,
      "original_pnl": 125.50,
      "original_win_rate": 80.0
    }
  ]
}
```

### GET /api/v1/recordings/{recording_id}
Get detailed information about a recording.

**Response:**
```json
{
  "success": true,
  "recording": {
    "recording_id": "uuid",
    "session_id": "session-uuid",
    "instance_id": 1,
    "strategy_name": "Mean Reversion",
    "original_parameters": {
      "rsi_threshold": 30,
      "bb_std": 2.5
    },
    "event_counts": {
      "SIGNAL_DETECTED": 12,
      "ORDER_PLACED": 10,
      "POSITION_OPENED": 5,
      "POSITION_CLOSED": 5
    },
    "replays": [...]
  }
}
```

### POST /api/v1/recordings/{recording_id}/replay
Replay a recording with modified parameters.

**Request Body:**
```json
{
  "modified_parameters": {
    "rsi_threshold": 25,
    "bb_std": 2.0
  },
  "description": "Testing lower RSI threshold"
}
```

**Response:**
```json
{
  "success": true,
  "replay_id": "replay-uuid",
  "recording_id": "recording-uuid",
  "total_trades": 7,
  "total_pnl": 145.75,
  "win_rate": 85.7,
  "comparison": {
    "trades_diff": 2,
    "pnl_diff": 20.25,
    "win_rate_diff": 5.7
  }
}
```

## Best Practices

1. **Record During Interesting Market Conditions**
   - High volatility periods
   - Unusual price movements
   - When strategies behave unexpectedly

2. **Tag Your Recordings**
   - Use descriptive tags for easy searching
   - Include market condition tags (high_vol, trending, ranging)
   - Add strategy-specific tags

3. **Test Multiple Parameters**
   - Create a parameter grid and test all combinations
   - Track which parameters improve which metrics
   - Document findings for future reference

4. **Compare Systematically**
   - Always compare replay results with original
   - Look at both aggregate metrics and individual trades
   - Analyze why differences occurred

5. **Clean Up Old Recordings**
   - Recordings can consume significant storage
   - Delete recordings you no longer need
   - Keep recordings from important market events

## Future Enhancements

Planned improvements:
- [ ] API endpoints to start/stop recording on running instances
- [ ] Automatic recording triggers (e.g., record when drawdown > X%)
- [ ] Multi-strategy replay comparison
- [ ] Visualization dashboard for replay comparisons
- [ ] Export recordings to files for sharing
- [ ] Import recordings from files
- [ ] Parallel replay execution for faster parameter sweeps
- [ ] Machine learning-based parameter optimization using recordings

## Troubleshooting

### Recording Not Capturing Data

Check:
1. Recording status: `SELECT status FROM recorded_sessions WHERE recording_id = 'xxx'`
2. Recorder initialization in trading script
3. Database connection is active
4. Sufficient disk space for market data

### Replay Results Don't Match Original

Possible causes:
1. Strategy detector not properly instantiated
2. Parameters not correctly applied
3. Market data missing or incomplete
4. Random elements in strategy (ensure deterministic replay)

### High Storage Usage

Solutions:
1. Delete old recordings: `DELETE FROM recorded_sessions WHERE recording_end_time < NOW() - INTERVAL '30 days'`
2. Record selectively (not every session)
3. Store only signals, not all market data (modify recorder)

## Support

For issues or questions:
- Check logs: `/logs/trading-{instance_id}.log`
- Review API docs: `http://localhost:9090/docs`
- Check database: Query `recorded_sessions` table for recording status
