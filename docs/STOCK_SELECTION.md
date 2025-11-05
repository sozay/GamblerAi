# Stock Selection Guide

## Overview

The trading bot supports two methods for choosing which stocks to buy:

1. **Fixed Symbol List** - Trade a predefined list of symbols
2. **Dynamic Screening** - Automatically scan and select the best opportunities

## Method 1: Fixed Symbol List (Default)

### How It Works

You provide a list of symbols, and the bot monitors all of them simultaneously.

```python
bot = TradingBot(
    symbols=["SPY", "QQQ", "AAPL", "MSFT", "TSLA"],
    use_dynamic_screening=False,
)
```

**When to Use:**
- You know exactly which stocks you want to trade
- You're focused on specific sectors or ETFs
- You want predictable behavior
- You prefer manual control

**Pros:**
- ✅ Simple and predictable
- ✅ No additional API calls
- ✅ Full control over what's traded

**Cons:**
- ❌ Miss opportunities in other stocks
- ❌ May trade symbols that aren't performing well
- ❌ Manual updates required

### Example

```bash
# Trade only major ETFs
python trading_bot.py

# Default symbols: SPY, QQQ, AAPL, MSFT
```

---

## Method 2: Dynamic Stock Screening ⭐

### How It Works

The bot automatically:
1. **Scans** a universe of 50+ stocks
2. **Screens** using 4 different strategies
3. **Ranks** based on current market regime
4. **Selects** top 5-10 best opportunities
5. **Rescans** every hour to find new opportunities

```python
bot = TradingBot(
    use_dynamic_screening=True,
    screening_interval=3600,  # Rescan every hour
)
```

**When to Use:**
- You want the bot to find opportunities automatically
- You want to adapt to changing market conditions
- You want to maximize potential returns
- You trust the screening algorithms

**Pros:**
- ✅ Automatically finds best opportunities
- ✅ Adapts to market conditions
- ✅ Scans 50+ stocks continuously
- ✅ Updates watchlist hourly

**Cons:**
- ❌ More complex
- ❌ Requires API calls for screening
- ❌ Less predictable (watchlist changes)

### Example

```bash
# Enable dynamic screening
python trading_bot.py --screening

# or
python trading_bot.py -s
```

---

## Screening Strategies

When dynamic screening is enabled, the bot uses 4 strategies:

### 1. Momentum Screening

**What it finds:**
- Stocks with strong upward momentum (>10% gain)
- Increasing volume
- Breaking to new highs

**Example:**
```
NVDA - Momentum: +15.2%, Vol: 2.3x
```

**Best for:** BULL markets

### 2. Mean Reversion Screening

**What it finds:**
- Oversold stocks (down >10%)
- RSI < 35 (oversold)
- Near support levels

**Example:**
```
AAPL - Pullback: -12.5%, RSI: 28
```

**Best for:** BEAR markets, pullbacks in BULL markets

### 3. Breakout Screening

**What it finds:**
- Stocks consolidating in tight range
- Breaking out with volume
- Near 52-week highs

**Example:**
```
TSLA - Breakout: Range 8.5%, Vol: 3.1x
```

**Best for:** All markets

### 4. Volume Surge Screening

**What it finds:**
- Unusual volume (3x+ average)
- Significant price movement
- Smart money activity

**Example:**
```
AMD - Volume: 4.2x, Price: +5.8%
```

**Best for:** All markets, catching explosive moves

---

## Regime-Based Ranking

The bot ranks stocks differently based on market regime:

### BULL Market

```
Weights:
- Momentum: 40%
- Breakout: 30%
- Volume: 20%
- Mean Reversion: 10%
```

**Logic:** In bull markets, favor trend-following strategies

### BEAR Market

```
Weights:
- Mean Reversion: 50%
- Volume: 25%
- Momentum: 15%
- Breakout: 10%
```

**Logic:** In bear markets, favor counter-trend strategies

### RANGE Market

```
Weights:
- Mean Reversion: 45%
- Volume: 30%
- Breakout: 15%
- Momentum: 10%
```

**Logic:** In sideways markets, play the range

---

## Stock Selection Flow

```
1. SCAN Universe (50+ stocks)
   ↓
2. SCREEN with 4 strategies
   - Momentum (top 3)
   - Mean Reversion (top 3)
   - Breakout (top 3)
   - Volume (top 3)
   ↓
3. DETECT Market Regime
   - BULL / BEAR / RANGE
   ↓
4. RANK by regime weights
   - Adjust scores based on regime
   ↓
5. SELECT Top 5-10
   - Highest combined scores
   ↓
6. SUBSCRIBE to WebSocket
   - Monitor real-time data
   ↓
7. GENERATE Signals
   - Use adaptive strategy
   ↓
8. EXECUTE Trades
   - With risk management
   ↓
9. RESCAN (every hour)
   - Update watchlist
```

---

## Configuration

### Fixed Symbols

```python
# trading_bot.py
bot = TradingBot(
    symbols=["SPY", "QQQ", "IWM", "DIA"],  # Major ETFs
    use_dynamic_screening=False,
)
```

### Dynamic Screening

```python
# trading_bot.py
bot = TradingBot(
    use_dynamic_screening=True,
    screening_interval=3600,  # Rescan every hour
    # screening_interval=1800,  # Or every 30 minutes
)
```

### Config File

```yaml
# trading_bot_config.yaml
trading:
  # Method 1: Fixed list
  symbols:
    - SPY
    - QQQ
    - AAPL

  # Method 2: Dynamic screening
  use_dynamic_screening: true
  screening_interval: 3600
```

---

## Stock Universe

The screener scans this universe:

**ETFs:**
- SPY, QQQ, IWM, DIA

**Technology:**
- AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AMD, NFLX

**Finance:**
- JPM, BAC, WFC, GS, MS

**Healthcare:**
- JNJ, UNH, PFE, ABBV, TMO

**Consumer:**
- WMT, HD, MCD, NKE, SBUX

**Energy:**
- XOM, CVX, COP

**Total:** 50+ liquid stocks

You can customize this in `stock_screener.py:_get_default_universe()`

---

## Example: Dynamic Screening in Action

```
14:00:00 - 🔍 Running periodic stock screening...

Momentum Screening:
  ✓ NVDA - +15.2% with 2.3x volume
  ✓ AMD - +12.1% with 1.8x volume
  ✓ TSLA - +10.5% with 2.1x volume

Mean Reversion Screening:
  ✓ AAPL - -12.5%, RSI: 28
  ✓ MSFT - -8.2%, RSI: 32
  ✓ META - -11.1%, RSI: 30

Breakout Screening:
  ✓ GOOGL - Range 7.5%, Vol: 3.2x
  ✓ JPM - Range 6.1%, Vol: 2.8x

Volume Surge Screening:
  ✓ WMT - 4.2x volume, +5.8%

Market Regime: BULL (confidence: 0.87)

Ranking with BULL weights...

Top 5 Picks:
  1. NVDA - Score: 85.2
  2. AMD - Score: 78.5
  3. GOOGL - Score: 72.1
  4. TSLA - Score: 68.9
  5. WMT - Score: 65.3

✓ Screening complete. Watching 5 symbols

14:01:00 - Subscribing to NVDA, AMD, GOOGL, TSLA, WMT...
14:01:01 - Monitoring for signals...
```

---

## Screening Criteria

### Filters Applied

**Price:**
- Min: $5
- Max: $500

**Volume:**
- Min: 1,000,000 shares/day

**Market Cap:**
- Min: $1 billion

**Quality:**
- Must have data available
- Must be tradable on Alpaca
- Must pass liquidity checks

### Scoring

Each strategy scores stocks 0-100:

```python
Momentum Score = gain_pct * volume_ratio
# Example: 15% gain × 2.3x volume = 34.5

Mean Reversion Score = abs(pullback_pct) * rsi_factor
# Example: 12.5% pullback × 0.9 = 11.25

Breakout Score = volume_surge * (20 - range_pct)
# Example: 3.2x volume × (20 - 7.5) = 40.0

Volume Score = volume_ratio * abs(price_change_pct)
# Example: 4.2x volume × 5.8% = 24.36
```

---

## Which Method Should You Use?

### Use Fixed Symbols If:

- ✅ You're new to algo trading
- ✅ You want full control
- ✅ You focus on specific stocks/ETFs
- ✅ You prefer simplicity
- ✅ You're testing strategies

### Use Dynamic Screening If:

- ✅ You want maximum opportunities
- ✅ You trust the algorithms
- ✅ You want automated discovery
- ✅ You're comfortable with complexity
- ✅ You want to adapt to markets

---

## Monitoring

### Fixed Symbols

```
📊 Status Update - 14:30:00
   Watching: 4 symbols (SPY, QQQ, AAPL, MSFT)
   Active Positions: 2
   Total Trades: 15
```

### Dynamic Screening

```
📊 Status Update - 14:30:00
   Watching: 5 symbols (NVDA, AMD, GOOGL, TSLA, WMT)
   Active Positions: 3
   Total Trades: 22
   Next screening: 42 minutes

   🔍 Last screening found:
     ➕ Added NVDA (momentum)
     ➕ Added GOOGL (breakout)
     ➖ Removed AAPL (no longer top pick)
```

---

## Testing Screening

### Run Screening Manually

```bash
# Test the screener
python examples/stock_screening_example.py
```

### Screen Specific Strategy

```python
from gambler_ai.screening import StockScreener

screener = StockScreener()

# Find momentum stocks
momentum_stocks = screener.screen_momentum(top_n=10)

for stock in momentum_stocks:
    print(f"{stock.symbol}: {stock.reason}")
```

---

## Best Practices

1. **Start with Fixed Symbols**
   - Learn how the bot works
   - Understand behavior

2. **Test Screening Separately**
   - Run `stock_screening_example.py`
   - Verify results make sense

3. **Enable Screening Gradually**
   - Start with longer intervals (2-4 hours)
   - Monitor what it selects

4. **Adjust Universe**
   - Customize the stock universe
   - Add your favorite sectors

5. **Monitor Regularly**
   - Check what's being selected
   - Verify quality of picks

---

## Troubleshooting

**No stocks found?**
- Market may not have good setups
- Adjust screening criteria
- Check if universe is too small

**Too many rescans?**
- Increase screening_interval
- Reduce API usage

**Poor stock selection?**
- Review screening criteria
- Adjust minimum scores
- Verify data quality

---

## Summary

| Feature | Fixed Symbols | Dynamic Screening |
|---------|--------------|-------------------|
| **Simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Control** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Opportunities** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Adaptability** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **API Usage** | Low | Medium |
| **Recommended For** | Beginners | Advanced |

**Bottom Line:**
- Start with fixed symbols to learn
- Move to dynamic screening for maximum performance
- Both methods use the same trading logic (adaptive strategy, risk management, etc.)

The choice is yours! 🎯
