# How the Alpaca Paper Trading System Works

## Overview

The system automatically detects momentum signals in real-time and executes paper trades using Alpaca's API with fake money ($100,000 starting capital).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ALPACA PAPER TRADING SYSTEM                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│  Your Computer   │         │  Alpaca Cloud    │
│                  │         │                  │
│  ┌────────────┐  │         │  ┌────────────┐  │
│  │   .env     │  │         │  │  Account   │  │
│  │  API Keys  │◄─┼─────────┼─►│ $100,000   │  │
│  └────────────┘  │         │  └────────────┘  │
│       │          │         │        │         │
│       ▼          │         │        ▼         │
│  ┌────────────┐  │         │  ┌────────────┐  │
│  │ Trading    │  │         │  │   Orders   │  │
│  │ Script     │◄─┼─────────┼─►│ Positions  │  │
│  └────────────┘  │         │  └────────────┘  │
│       │          │         │        │         │
│       ▼          │         │        ▼         │
│  ┌────────────┐  │         │  ┌────────────┐  │
│  │ Momentum   │  │         │  │   Market   │  │
│  │ Detection  │◄─┼─────────┼──┤    Data    │  │
│  └────────────┘  │         │  │  (Real-time)│  │
└──────────────────┘         │  └────────────┘  │
                             └──────────────────┘
```

---

## 1. Which Application?

### Main Script: `scripts/alpaca_paper_trading.py`

This is a **Python command-line application** that runs continuously, monitoring stocks and trading automatically.

**Key Components:**

- **AlpacaPaperTrader Class**: Main trading engine
- **Momentum Detection**: Analyzes price and volume patterns
- **Order Execution**: Places buy/sell orders via API
- **Position Management**: Tracks open positions and P&L

---

## 2. How to Get Data?

### Data Flow

```
Market Data (Real-time) → Alpaca API → Your Script → Analysis
```

### Data Sources

**Alpaca provides TWO APIs:**

1. **Trading API** (`https://paper-api.alpaca.markets`)
   - Account info (cash, buying power, portfolio value)
   - Place orders (buy/sell)
   - Get current positions
   - Check order status

2. **Market Data API** (`https://data.alpaca.markets`)
   - Real-time price bars (5-minute intervals)
   - Volume data
   - Historical data
   - Uses free IEX feed

### Data Request Process (every 60 seconds)

```python
# Script calls Alpaca Data API
get_latest_bars(['AAPL', 'MSFT', 'GOOGL'])

# Returns:
{
  'AAPL': [
    {'t': '2025-11-07T10:00:00Z', 'o': 269.50, 'h': 270.00,
     'l': 269.00, 'c': 269.85, 'v': 125134},
    {'t': '2025-11-07T10:05:00Z', 'o': 269.85, 'h': 271.50,
     'l': 269.50, 'c': 271.20, 'v': 187650},
    # ... last 100 bars (5-min intervals)
  ],
  'MSFT': [...],
  'GOOGL': [...]
}
```

**Script Parameters (line 111-143):**
- Timeframe: `5Min` bars (5-minute candles)
- Limit: Last 100 bars
- Feed: `iex` (free real-time feed)

---

## 3. How to Decide to Trade?

### Trading Strategy: Momentum Detection

The system uses a **simple but effective momentum strategy**:

#### Entry Criteria (lines 145-194)

```
┌─────────────────────────────────────────────────────────┐
│          MOMENTUM DETECTION ALGORITHM                    │
└─────────────────────────────────────────────────────────┘

STEP 1: Get last 100 bars (5-min intervals)

STEP 2: Calculate metrics
        ┌─────────────────────────────────┐
        │ Volume Ratio = Current Volume   │
        │                ───────────────── │
        │                20-bar Average    │
        └─────────────────────────────────┘

STEP 3: Analyze last 5 bars (25-minute window)

        Price Change % = (Latest Close - First Open)
                         ─────────────────────────── × 100
                              First Open

STEP 4: Check conditions

        ✓ Price changed by ≥2.0%  (min_price_change_pct)
        AND
        ✓ Volume is ≥2.0x average (min_volume_ratio)

        → MOMENTUM SIGNAL DETECTED!

STEP 5: Determine direction

        Price Change > 0  →  "UP" (buy long)
        Price Change < 0  →  "DOWN" (sell short)
```

#### Example Signal Detection

```
AAPL bars (5-min):
10:00  Open=$269.50  Close=$269.85  Volume=125k
10:05  Open=$269.85  Close=$270.50  Volume=187k
10:10  Open=$270.50  Close=$271.20  Volume=205k
10:15  Open=$271.20  Close=$272.00  Volume=218k
10:20  Open=$272.00  Close=$274.80  Volume=231k  ← Latest

Analysis:
- Price Change = ($274.80 - $269.50) / $269.50 × 100 = 1.97%
- Average Volume (20 bars) = 95k
- Recent Volume Ratio = (187k + 205k + 218k + 231k) / 4 / 95k = 2.2x

Result: NO SIGNAL (price change 1.97% < 2.0% threshold)

---

AAPL bars (5-min):
10:00  Open=$269.50  Close=$269.85  Volume=125k
10:05  Open=$269.85  Close=$271.50  Volume=197k
10:10  Open=$271.50  Close=$273.20  Volume=215k
10:15  Open=$273.20  Close=$274.50  Volume=228k
10:20  Open=$274.50  Close=$275.20  Volume=241k  ← Latest

Analysis:
- Price Change = ($275.20 - $269.50) / $269.50 × 100 = 2.11% ✓
- Average Volume (20 bars) = 95k
- Recent Volume Ratio = 2.3x ✓

Result: MOMENTUM SIGNAL DETECTED - "UP" direction
        → Execute BUY order
```

---

### Position Entry (lines 264-318)

```
When momentum signal detected:

1. Calculate position size
   Shares = $10,000 / Entry Price

   Example: AAPL @ $275.20
   Shares = $10,000 / $275.20 = 36 shares
   Total Cost = $9,907.20

2. Set stop loss and take profit

   For "UP" (long) position:
   - Stop Loss = Entry × (1 - 2%) = $275.20 × 0.98 = $269.70
   - Take Profit = Entry × (1 + 4%) = $275.20 × 1.04 = $286.21

   For "DOWN" (short) position:
   - Stop Loss = Entry × (1 + 2%)
   - Take Profit = Entry × (1 - 4%)

3. Place bracket order
   {
     "symbol": "AAPL",
     "qty": 36,
     "side": "buy",
     "type": "market",
     "order_class": "bracket",
     "stop_loss": {"stop_price": 269.70},
     "take_profit": {"limit_price": 286.21}
   }
```

### Position Exit

**Automatic exits via bracket orders:**

1. **Stop Loss Hit** (-2%): Close position to limit losses
2. **Take Profit Hit** (+4%): Close position to lock in gains
3. **End of Day**: Alpaca closes all positions at market close

The script checks position status every scan cycle (60 seconds) and reports when positions close.

---

## 4. Complete Trading Cycle Example

```
Time      Event                              Action
────────────────────────────────────────────────────────────
10:00     Script starts                      Connect to Alpaca

10:00     Initial scan                       Get last 100 bars
                                              No signals found

10:01     Wait 60 seconds                    Sleep...

10:01     Scan cycle 2                       Get latest bars
                                              AAPL: 2.3% up, 2.5x vol
                                              → SIGNAL DETECTED!

10:01     Enter position                     BUY 36 AAPL @ $275.20
                                              Stop: $269.70
                                              Target: $286.21

10:02     Wait 60 seconds                    Sleep...

10:02     Scan cycle 3                       No new signals
                                              Check positions
                                              AAPL still open

[... continues scanning every 60 seconds ...]

10:15     Position update                    AAPL position CLOSED
                                              Reason: Take Profit hit
                                              Entry: $275.20
                                              Exit: $286.21
                                              Profit: $396 (+4%)
                                              Duration: 14 minutes

10:15     Continue scanning                  Looking for new signals

[... continues until duration ends ...]

11:00     Session ends                       Final report:
                                              Closed trades: 3
                                              Active positions: 1
                                              P&L: +$847 (+0.85%)
```

---

## 5. Risk Management

### Built-in Safety Features

1. **Position Limits**
   - Max $10,000 per trade
   - One position per symbol (no duplicate entries)
   - Prevents over-concentration

2. **Bracket Orders**
   - Stop loss ALWAYS set (-2%)
   - Take profit ALWAYS set (+4%)
   - No manual intervention needed

3. **Paper Trading Only**
   - Uses fake money ($100,000 virtual)
   - No real financial risk
   - Perfect for testing

4. **Risk-Reward Ratio**
   - Risk: 2% (stop loss)
   - Reward: 4% (take profit)
   - Ratio: 1:2 (good ratio)

---

## 6. Key Configuration Parameters

Located in script (lines 48-53):

```python
self.min_price_change_pct = 2.0    # Entry: Min 2% price move
self.min_volume_ratio = 2.0        # Entry: Min 2x volume
self.stop_loss_pct = 2.0           # Exit: -2% stop loss
self.take_profit_pct = 4.0         # Exit: +4% take profit
self.position_size = 10000         # $10k per trade
```

You can modify these to adjust strategy aggressiveness.

---

## 7. Running the System

### Start Trading

```bash
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL,TSLA,NVDA \
  --duration 60 \
  --interval 60
```

**Parameters:**
- `--symbols`: Comma-separated stock symbols to monitor
- `--duration`: How long to run (minutes)
- `--interval`: How often to scan for signals (seconds)

### Example Output

```
================================================================================
ALPACA PAPER TRADING - LIVE SESSION
================================================================================
Symbols: AAPL, MSFT, GOOGL, TSLA, NVDA
Duration: 60 minutes
Scan Interval: 60 seconds
Strategy: 2.0% stop loss, 4.0% take profit
================================================================================

Starting Portfolio Value: $100,000.00

⏰ 10:00:15 - Scanning 5 symbols...
   No signals detected
   Active positions: 0, Closed trades: 0, Time remaining: 59 min

⏰ 10:01:15 - Scanning 5 symbols...
   📊 AAPL: UP 2.3% move, 2.4x volume

🔔 MOMENTUM SIGNAL: AAPL UP
   Entry: $275.20
   Size: 36 shares ($9,907)

✓ Order placed: BUY 36 AAPL @ market
  Stop Loss: $269.70
  Take Profit: $286.21

   Active positions: 1, Closed trades: 0, Time remaining: 58 min

[... continues ...]

✓ Position CLOSED: AAPL
   Entry: $275.20
   Direction: UP
   Duration: 14 minutes

================================================================================
SESSION COMPLETE
================================================================================

Initial Portfolio Value: $100,000.00
Final Portfolio Value:   $100,396.00
P&L:                     $396.00 (+0.40%)

Total Closed Trades: 1
Active Positions:    0
```

---

## 8. Summary

### The System:
- **Application**: Python script (CLI)
- **Runtime**: Runs continuously for set duration
- **Automation**: Fully automated (no manual intervention)

### Data Acquisition:
- **Source**: Alpaca Market Data API
- **Frequency**: Every 60 seconds
- **Type**: 5-minute bars, last 100 periods
- **Cost**: FREE (IEX feed)

### Trading Decision:
- **Strategy**: Momentum-based
- **Entry**: 2%+ price change + 2x+ volume
- **Exit**: 2% stop loss OR 4% take profit
- **Timeframe**: 5-minute bars, 25-minute window

### Result:
- Real-time paper trading with live market data
- Automatic signal detection and execution
- Risk-managed with bracket orders
- Complete P&L tracking and reporting

**No databases, no complex setup - just Python + Alpaca API!**
