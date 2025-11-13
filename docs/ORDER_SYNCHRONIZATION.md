# Order Synchronization with Alpaca

## Overview

This document describes how the trading system synchronizes order status and positions with Alpaca, and how expired/canceled exit orders are automatically handled.

## Automatic Order Synchronization

The trading system automatically syncs order status in real-time during normal operation.

### How It Works

**Location:** `scripts/alpaca_paper_trading.py`

The `check_positions()` method runs every scan cycle and performs three key checks:

#### 1. Check Pending Orders (Lines 682-749)
Monitors orders that haven't filled yet and updates their status:
- **Filled** → Move to active positions, save to database
- **Canceled/Expired/Rejected** → Log to database, remove from tracking

#### 2. Check Active Positions for Closure (Lines 751-847)
Detects when positions close in Alpaca:
- Compares local active positions with Alpaca's position list
- If position missing from Alpaca → Position was closed
- Retrieves exit details from bracket order legs
- Updates database with exit price, P&L, and reason

#### 3. Check for Expired Exit Orders (Lines 849-869) **NEW**
Automatically recreates exit orders when they expire:
```python
# Check if position has active exit orders
has_exit_orders, exit_details = self.check_exit_orders_status(order_id)

if not has_exit_orders and exit_details.get('expired'):
    # Position has expired/canceled exit orders - needs protection
    # Recreate exit orders automatically
    if self.recreate_exit_orders(symbol, pos):
        print("✓ Position is now protected")
```

## Order Synchronization Module

**Location:** `gambler_ai/trading/order_synchronizer.py`

### Key Methods

#### `sync_order_status(order_id, order_info)`
Updates order journal with latest status from Alpaca:
- Detects terminal states: filled, partial, canceled, expired, rejected
- Records filled quantity and price
- Logs rejection reasons

#### `sync_pending_orders(pending_orders)`
Processes all pending orders and updates database:
- Keeps filled/partial orders in tracking
- Removes expired/canceled/rejected orders after logging

#### `sync_closed_positions(position_data, order_info)`
Records exit details when positions close:
- Updates order journal with exit order status
- Logs bracket order leg details

## Exit Order Recreation

When exit orders expire or are canceled, the system automatically creates new ones.

### Auto-Recreation Logic

**Location:** `scripts/alpaca_paper_trading.py` (Lines 599-667)

```python
def recreate_exit_orders(symbol, position_data):
    """
    Create new exit orders for a position that lost its exit protection.

    - Uses current market price to calculate new exit levels
    - Take Profit: current_price + (2 × stop_loss_pct)
    - Stop Loss: current_price - stop_loss_pct
    - Time in Force: GTC (Good Till Canceled) - won't expire
    """
```

### Why Exit Orders Expire

Common reasons:
1. **Day orders** - Orders with `time_in_force='day'` expire at market close (10:00 PM ET)
2. **Manual cancellation** - User or system cancels orders
3. **Rejected orders** - Order parameters invalid (price limits, etc.)

### Prevention

**Use GTC (Good Till Canceled):**
```python
order_data = {
    'time_in_force': 'gtc',  # ← Won't expire until filled or manually canceled
    'order_class': 'oco',
    'take_profit': {'limit_price': tp_price},
    'stop_loss': {'stop_price': sl_price}
}
```

## Real-Time Monitoring with WebSocket (Optional)

For instant notifications instead of polling, use Alpaca's WebSocket API.

### Benefits
- ⚡ Instant notification when orders expire (<1 second vs 30+ second delay)
- 💰 No API calls (Alpaca pushes updates to you)
- 📈 Scales to unlimited positions

### Implementation

**Location:** `gambler_ai/trading/order_stream_monitor.py`

```python
from gambler_ai.trading.order_stream_monitor import OrderStreamMonitor, OrderEventHandler

# Create event handler
event_handler = OrderEventHandler(trader)

# Start WebSocket monitor
monitor = OrderStreamMonitor(
    api_key=api_key,
    api_secret=api_secret,
    on_order_update=event_handler.handle_order_update
)

# Run alongside polling
await monitor.start()
```

### WebSocket Events
- `new` - Order placed
- `fill` - Order filled
- `partial_fill` - Partial fill
- `canceled` - Order canceled
- `expired` - Order expired
- `rejected` - Order rejected

### Hybrid Approach (Recommended)
Use **both** WebSocket (for instant updates) and polling (as backup):
- WebSocket handles 99% of updates instantly
- Polling runs every 5-10 minutes as safety net
- Best reliability and performance

## Database Schema

### OrderJournal Table
Tracks all orders placed through the system:
- `alpaca_order_id` - Alpaca's order ID
- `status` - Current status (filled, canceled, expired, etc.)
- `filled_qty` - Quantity filled
- `filled_avg_price` - Average fill price
- `submitted_at` - When order was placed
- `filled_at` - When order was filled
- `cancelled_at` - When order was canceled

### Position Table
Tracks all positions (open and closed):
- `status` - 'active' or 'closed'
- `entry_price` - Entry price
- `exit_price` - Exit price (NULL if still open)
- `pnl` - Profit/loss in dollars
- `pnl_pct` - Profit/loss percentage
- `exit_reason` - Why position closed (take_profit, stop_loss, expired_orders, etc.)

## Troubleshooting

### Position Showing Active but Not in Alpaca

**Symptoms:**
- Database shows position as 'active'
- Position not in Alpaca's position list
- Exit orders expired/canceled

**Cause:**
- Exit orders expired while position was open
- Position never actually closed, just lost protection

**Auto-Fix:**
The system will automatically detect this and recreate exit orders on next check cycle.

**Manual Fix (if needed):**
```python
# Use state_manager to update position
from gambler_ai.trading.state_manager import StateManager

state_manager.update_position(
    symbol='AAPL',
    exit_time=datetime.now(),
    exit_price=current_price,
    exit_reason='expired_orders',
    status='closed'
)
```

### Exit Orders Keep Expiring

**Cause:** Using `time_in_force='day'` instead of `'gtc'`

**Fix:** The system now uses GTC by default in `recreate_exit_orders()`. Verify in code:
```python
# Line 649 in alpaca_paper_trading.py
'time_in_force': 'gtc',  # ← Should be 'gtc' not 'day'
```

### Database P&L Doesn't Match Alpaca

**Causes:**
1. Positions closed externally (in Alpaca UI) not synced to database
2. Old positions from before tracking system was implemented
3. Incomplete order history

**Fix:**
Check positions and manually update if needed:
```python
# Check Alpaca account P&L
account = get_account()
alpaca_pnl = float(account['equity']) - 100000  # Assuming $100k start

# Check database P&L
db_pnl = session.query(func.sum(Position.pnl)).filter_by(status='closed').scalar()

# If mismatch, review order history and update database
```

## Best Practices

### 1. Always Use GTC for Exit Orders
```python
# Good
'time_in_force': 'gtc'

# Bad - will expire
'time_in_force': 'day'
```

### 2. Monitor Logs for Expired Orders
Watch for these messages:
```
⚠ Position AAPL has NO active exit orders!
✓ Created new exit orders for AAPL
```

### 3. Run Regular Reconciliation
Periodically verify database matches Alpaca (built into the system, happens automatically).

### 4. Enable WebSocket for Production
For live trading with real money, use WebSocket monitoring for instant reaction to expired orders.

### 5. Review Order History
Check Alpaca's order history weekly to catch any discrepancies:
- https://app.alpaca.markets/paper/dashboard/orders (Paper Trading)
- https://app.alpaca.markets/brokerage/dashboard/orders (Live Trading)

## Code References

### Key Files
- `scripts/alpaca_paper_trading.py` - Main trading loop with sync logic
- `gambler_ai/trading/order_synchronizer.py` - Order sync module
- `gambler_ai/trading/state_manager.py` - Database operations
- `gambler_ai/trading/position_reconciler.py` - Position reconciliation
- `gambler_ai/trading/order_stream_monitor.py` - WebSocket monitoring

### Key Methods
- `check_positions()` - Main sync loop (Line 669)
- `check_exit_orders_status()` - Check if position has active exit orders (Line 563)
- `recreate_exit_orders()` - Create new GTC exit orders (Line 599)
- `sync_order_status()` - Update order in database (order_synchronizer.py:41)

## Summary

The trading system now includes:
1. ✅ **Automatic detection** of expired exit orders
2. ✅ **Automatic recreation** of exit orders with GTC
3. ✅ **Real-time sync** of order status to database
4. ✅ **Position reconciliation** with Alpaca
5. ✅ **WebSocket support** for instant notifications (optional)

**Your positions are always protected** - even if exit orders expire, the system automatically creates new ones within one scan cycle (typically <60 seconds).
