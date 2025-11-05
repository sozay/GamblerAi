# Alpaca Order Types Guide

## Overview

Alpaca's paper trading system supports **ALL** major order types including stop loss and stop limit orders. This guide covers how to use them.

## ✅ Supported Order Types

### 1. Market Order
Execute immediately at current market price.

**Use Case:** Quick entry or exit

**Example:**
```python
order = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "market",
    "time_in_force": "day"
}
```

**curl:**
```bash
curl -X POST "https://paper-api.alpaca.markets/v2/orders" \
  -H "APCA-API-KEY-ID: YOUR_KEY" \
  -H "APCA-API-SECRET-KEY: YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","qty":1,"side":"buy","type":"market","time_in_force":"day"}'
```

---

### 2. Limit Order
Execute at specified price or better.

**Use Case:** Control entry/exit price

**Example:**
```python
order = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "limit",
    "limit_price": "150.00",
    "time_in_force": "day"
}
```

---

### 3. Stop Loss Order ✅
**YES - Fully Supported on Paper Trading**

Triggers a **market order** when stock reaches stop price.

**Use Case:** Protect against losses

**How it works:**
- Set stop price below current market price (for sell orders)
- When stock drops to stop price → executes market order
- Guarantees execution (but not price)

**Example:**
```python
# If you own AAPL at $150, protect with stop loss at $145
order = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "stop",
    "stop_price": "145.00",
    "time_in_force": "gtc"  # Good till canceled
}
```

**Real-world scenario:**
```
1. Buy AAPL at $150
2. Place stop loss at $145
3. If AAPL drops to $145 → automatically sells at market
4. Limits your loss to ~$5 per share
```

---

### 4. Stop Limit Order ✅
**YES - Fully Supported on Paper Trading**

Triggers a **limit order** when stock reaches stop price.

**Use Case:** More control than stop loss, but may not fill in fast markets

**How it works:**
- Set stop price (trigger)
- Set limit price (minimum acceptable price)
- When stock hits stop price → places limit order
- May not fill if price drops too fast

**Example:**
```python
# If you own AAPL at $150, set stop limit
order = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "stop_limit",
    "stop_price": "145.00",   # Trigger price
    "limit_price": "144.00",  # Minimum sell price
    "time_in_force": "gtc"
}
```

**Stop Loss vs Stop Limit:**
```
Scenario: You own AAPL at $150

Stop Loss (stop_price=$145):
  - Price drops to $145 → Sells at market (might get $144.50)
  - ✅ Guaranteed to execute
  - ❌ May get worse price in fast drop

Stop Limit (stop_price=$145, limit_price=$144):
  - Price drops to $145 → Places limit order at $144
  - ✅ Won't sell below $144
  - ❌ Might not fill if price drops to $143
```

---

### 5. Trailing Stop Order ✅
**YES - Fully Supported on Paper Trading**

Stop price trails market price by a percentage.

**Use Case:** Lock in profits as stock rises

**How it works:**
- Set trail percentage (e.g., 5%)
- Stop price adjusts upward as stock rises
- If stock drops 5% from peak → sells at market

**Example:**
```python
# Lock in profits with 5% trailing stop
order = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "trailing_stop",
    "trail_percent": "5.0",
    "time_in_force": "gtc"
}
```

**Real-world scenario:**
```
Buy AAPL at $150

Set trailing stop at 5%:
  $150 → Stop price: $142.50 (5% below)
  $155 → Stop price: $147.25 (rises with stock)
  $160 → Stop price: $152.00 (keeps rising)
  $158 → Stop price: $152.00 (doesn't go down)
  $152 → SELL at market (dropped 5% from $160 peak)

Result: Captured most of the gain, exited when trend reversed
```

---

### 6. Bracket Order ✅
**YES - Fully Supported on Paper Trading**

Combines entry + take profit + stop loss in one order.

**Use Case:** Complete risk management

**How it works:**
- Main order: Market/limit entry
- Take profit: Limit order above entry
- Stop loss: Stop order below entry
- First to execute cancels the other

**Example:**
```python
# Buy AAPL with profit target and loss limit
order = {
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "type": "market",
    "time_in_force": "day",
    "order_class": "bracket",
    "take_profit": {
        "limit_price": "160.00"  # Sell at $160 profit
    },
    "stop_loss": {
        "stop_price": "145.00"   # Sell at $145 loss
    }
}
```

**Real-world scenario:**
```
Buy AAPL at $150 (market)

Automatic orders created:
  - Take Profit: SELL at $160 (limit)
  - Stop Loss: SELL at $145 (stop)

If AAPL rises to $160:
  ✅ Sell at $160 (+$10 profit)
  ❌ Cancel stop loss order

If AAPL drops to $145:
  ✅ Sell at $145 (-$5 loss)
  ❌ Cancel take profit order
```

---

## Time in Force Options

- **day** - Active for current trading day only
- **gtc** - Good till canceled (stays active until filled or canceled)
- **ioc** - Immediate or cancel
- **fok** - Fill or kill (entire order must fill immediately)

---

## Order Status Flow

```
Pending → Accepted → Filled
                  → Partially Filled
                  → Canceled
                  → Rejected
```

---

## Complete Example: Trading Strategy with Risk Management

```python
from examples.alpaca_order_types_example import AlpacaTradingClient

client = AlpacaTradingClient(
    api_key="YOUR_KEY",
    api_secret="YOUR_SECRET"
)

# Step 1: Buy stock
print("Buying 10 shares of AAPL...")
buy_order = client.place_market_order("AAPL", 10, "buy")
print(f"Bought at ~${buy_order['filled_avg_price']}")

# Step 2: Set stop loss (protect capital)
print("Setting stop loss at $145...")
stop_loss = client.place_stop_loss_order("AAPL", 10, 145.00, "sell")
print(f"Stop loss order ID: {stop_loss['id']}")

# Step 3: Set take profit (lock in gains)
print("Setting take profit at $160...")
take_profit = client.place_limit_order("AAPL", 10, 160.00, "sell")
print(f"Take profit order ID: {take_profit['id']}")

# Now you have:
# - Position: 10 shares AAPL
# - Protection: Stop loss at $145 (max loss: ~$5/share)
# - Target: Sell at $160 (target gain: ~$10/share)
# - Risk/Reward: 1:2 ratio

# Monitor orders
orders = client.get_orders(status="open")
for order in orders:
    print(f"Order {order['id']}: {order['type']} - {order['status']}")
```

---

## Testing Order Types

### Method 1: Python Script
```bash
python examples/alpaca_order_types_example.py
```

### Method 2: Shell Script
```bash
./test_order_types.sh
```

### Method 3: Manual curl
```bash
# Stop loss example
curl -X POST "https://paper-api.alpaca.markets/v2/orders" \
  -H "APCA-API-KEY-ID: YOUR_KEY" \
  -H "APCA-API-SECRET-KEY: YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "qty": 1,
    "side": "sell",
    "type": "stop",
    "stop_price": "145.00",
    "time_in_force": "gtc"
  }'
```

---

## Common Patterns

### Pattern 1: Protective Stop Loss
```python
# After buying, immediately set stop loss
buy_order = client.place_market_order("AAPL", 10, "buy")
stop_loss = client.place_stop_loss_order("AAPL", 10, 145.00)
```

### Pattern 2: Trailing Stop for Trend Following
```python
# Let profits run with trailing stop
buy_order = client.place_market_order("TSLA", 5, "buy")
trailing = client.place_trailing_stop_order("TSLA", 5, 5.0)  # 5% trail
```

### Pattern 3: Bracket for Defined Risk
```python
# Set both profit target and loss limit
bracket_order = client.session.post(
    f"{client.base_url}/v2/orders",
    json={
        "symbol": "SPY",
        "qty": 10,
        "side": "buy",
        "type": "market",
        "order_class": "bracket",
        "take_profit": {"limit_price": "460.00"},
        "stop_loss": {"stop_price": "450.00"}
    }
)
```

---

## Important Notes

### ✅ All Order Types Work on Paper Trading
- Market ✅
- Limit ✅
- Stop Loss ✅
- Stop Limit ✅
- Trailing Stop ✅
- Bracket ✅

### Paper Trading Limitations
- Executions are simulated
- No real market impact
- Some edge cases may differ from live trading
- Perfect for testing strategies

### Best Practices
1. **Always use stop losses** to protect capital
2. **Use trailing stops** for trending positions
3. **Bracket orders** for defined risk/reward
4. **Test thoroughly** on paper before going live
5. **Monitor orders** regularly

---

## Error Handling

Common errors:
```python
try:
    order = client.place_stop_loss_order("AAPL", 1, 145.00)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 403:
        print("Invalid API credentials")
    elif e.response.status_code == 422:
        print("Invalid order parameters")
        print(e.response.json())
```

---

## Next Steps

1. **Get valid credentials** (see ALPACA_CREDENTIALS_ISSUE.md)
2. **Test order types** with small quantities
3. **Build your strategy** using stop losses and limits
4. **Monitor and adjust** based on results

## References

- [Alpaca Orders API](https://docs.alpaca.markets/reference/postorder)
- [Order Types Guide](https://docs.alpaca.markets/docs/orders)
- [Bracket Orders](https://docs.alpaca.markets/docs/bracket-orders)
