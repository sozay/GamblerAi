# Backtesting Automatic Stock Screening

## Overview

This document describes how to backtest the automatic stock screening system against historical data.

## Two Backtest Scripts

### 1. `backtest_screening.py` - Real Data Backtest

Uses real historical data from Alpaca Markets API.

**Requirements:**
- Valid Alpaca API credentials
- Historical data access

**Usage:**
```bash
python backtest_screening.py
```

**Configuration:**
```python
backtest = ScreeningBacktest(
    start_date=datetime(2024, 11, 6),
    end_date=datetime.now(),
    initial_capital=100_000.0,
    screening_interval_hours=24,  # Daily screening
    max_positions=5,
    position_size_pct=0.20,  # 20% per position
    stop_loss_pct=0.02,  # 2% stop loss
    take_profit_pct=0.04,  # 4% take profit
)
```

### 2. `backtest_screening_demo.py` - Simulated Data Demo

Uses simulated historical data for testing without API access.

**Requirements:**
- None (uses simulated data)

**Usage:**
```bash
python backtest_screening_demo.py
```

**Perfect for:**
- Testing the backtest logic
- Understanding the workflow
- Development and debugging
- Demo purposes

---

## Backtest Workflow

```
1. LOAD HISTORICAL DATA
   ├─ Fetch or generate price data for universe
   └─ Cache data for fast access

2. RUN SIMULATION
   ├─ Day-by-day iteration
   └─ For each day:
       ├─ Run screening (at specified interval)
       │   ├─ Screen momentum stocks
       │   ├─ Screen mean reversion
       │   ├─ Screen breakouts
       │   ├─ Screen volume surges
       │   ├─ Detect market regime
       │   └─ Rank and select top stocks
       │
       ├─ Generate signals for selected stocks
       │   └─ Use adaptive strategy selector
       │
       ├─ Execute trades
       │   ├─ Enter new positions (BUY)
       │   └─ Exit positions (SELL)
       │
       ├─ Check stops
       │   ├─ Stop loss (2%)
       │   └─ Take profit (4%)
       │
       └─ Update equity curve

3. GENERATE RESULTS
   ├─ Calculate returns
   ├─ Analyze trades
   ├─ Compute risk metrics
   └─ Compare to benchmark
```

---

## Backtest Parameters

### Capital Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| `initial_capital` | $100,000 | Starting capital |
| `max_positions` | 5 | Maximum concurrent positions |
| `position_size_pct` | 0.20 | 20% of capital per position |

### Risk Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| `stop_loss_pct` | 0.02 | 2% stop loss |
| `take_profit_pct` | 0.04 | 4% take profit |

### Screening

| Parameter | Default | Description |
|-----------|---------|-------------|
| `screening_interval_hours` | 24 | Rescan every 24 hours (daily) |
| `screening_interval_days` | 7 | (Demo) Rescan weekly |

---

## Output Files

### 1. Equity Curve CSV

**File:** `backtest_equity_curve.csv` or `backtest_demo_equity_curve.csv`

**Columns:**
- `timestamp` - Date/time
- `equity` - Total portfolio value

**Example:**
```csv
timestamp,equity
2024-11-06,100000.00
2024-11-07,101250.00
2024-11-08,102100.00
```

**Usage:**
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('backtest_equity_curve.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['equity'])
plt.title('Equity Curve')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
plt.grid(True)
plt.show()
```

### 2. Trades CSV

**File:** `backtest_trades.csv` or `backtest_demo_trades.csv`

**Columns:**
- `timestamp` - Trade date/time
- `symbol` - Stock symbol
- `action` - BUY or SELL
- `shares` - Number of shares
- `price` - Execution price
- `value` - Total transaction value
- `pnl` - Profit/Loss (SELL only)
- `pnl_pct` - P&L percentage (SELL only)
- `hold_days` - Holding period (SELL only)

**Example:**
```csv
timestamp,symbol,action,shares,price,value,pnl,pnl_pct,hold_days
2024-11-06,AAPL,BUY,100,150.00,15000.00,,,
2024-11-10,AAPL,SELL,100,156.00,15600.00,600.00,4.0,4
```

### 3. Screenings CSV

**File:** `backtest_screenings.csv`

**Columns:**
- `timestamp` - Screening date
- `regime` - Market regime (BULL/BEAR/RANGE)
- `confidence` - Regime confidence (0-1)
- `candidates` - Total candidates found
- `selected` - List of selected symbols

---

## Performance Metrics

The backtest reports the following metrics:

### Returns
- **Initial Capital** - Starting amount
- **Final Equity** - Ending portfolio value
- **Total Return** - Dollar and percentage return
- **Outperformance** - Return vs SPY benchmark

### Trade Statistics
- **Total Trades** - Number of completed trades
- **Winning Trades** - Number and percentage of winners
- **Losing Trades** - Number and percentage of losers
- **Average Win** - Average profit per winning trade
- **Average Loss** - Average loss per losing trade
- **Profit Factor** - Avg Win / Avg Loss ratio

### Risk Metrics
- **Sharpe Ratio** - Risk-adjusted returns
  - Formula: `(Mean Return / Std Return) × √252`
  - > 1.0 = Good
  - > 2.0 = Very Good
  - > 3.0 = Excellent
- **Max Drawdown** - Maximum peak-to-trough decline
  - Lower is better
  - < 10% = Excellent
  - < 20% = Good
  - > 30% = High risk

---

## Example Results

```
================================================================================
BACKTEST RESULTS
================================================================================

Initial Capital:  $     100,000.00
Final Equity:     $     127,917.75
Total Return:     $      27,917.75 (+27.92%)

Trade Statistics:
  Total Trades:     25
  Winning Trades:   20 (80.0%)
  Losing Trades:    5 (20.0%)
  Average Win:      $    1,500.00
  Average Loss:     $     -250.00
  Total P&L:        $   27,917.75
  Profit Factor:         6.00

Screening Statistics:
  Total Screenings: 53

Risk Metrics:
  Sharpe Ratio:                2.95
  Max Drawdown:              -8.50%

Benchmark (SPY Buy & Hold):
  SPY Return:               +15.20%
  Outperformance:           +12.72%

================================================================================
```

---

## Customization

### Change Screening Strategies

Edit `backtest_screening.py`:

```python
# Run specific strategies only
results = {
    "momentum": self.screener.screen_momentum(top_n=5),
    "breakout": self.screener.screen_breakout(top_n=5),
    # Exclude mean_reversion and volume_surge
}
```

### Adjust Risk Parameters

```python
backtest = ScreeningBacktest(
    stop_loss_pct=0.01,  # Tighter 1% stop loss
    take_profit_pct=0.05,  # Wider 5% take profit
)
```

### Change Screening Frequency

```python
backtest = ScreeningBacktest(
    screening_interval_hours=168,  # Weekly (7 days × 24 hours)
)
```

### Modify Position Sizing

```python
backtest = ScreeningBacktest(
    max_positions=10,  # More concurrent positions
    position_size_pct=0.10,  # Smaller 10% per position
)
```

---

## Understanding the Results

### Good Backtest Results

✅ **Positive Returns**
- Higher than buy-and-hold benchmark
- Consistent across different time periods

✅ **High Win Rate**
- > 50% is good
- > 60% is excellent
- Balance with risk/reward ratio

✅ **Good Profit Factor**
- > 1.5 = Profitable system
- > 2.0 = Strong system
- > 3.0 = Excellent system

✅ **Manageable Drawdown**
- < 15% is good
- < 25% is acceptable
- > 30% may be too risky

✅ **High Sharpe Ratio**
- > 1.0 = Good risk-adjusted returns
- > 2.0 = Very good
- > 3.0 = Excellent

### Warning Signs

⚠️ **Overfitting**
- 100% win rate
- Perfect equity curve
- Too good to be true results

⚠️ **High Drawdown**
- > 30% max drawdown
- Long underwater periods
- Volatile equity curve

⚠️ **Poor Risk/Reward**
- Average loss > Average win
- Low profit factor < 1.5
- Low win rate < 40%

---

## Best Practices

### 1. Test Different Periods
```bash
# Test bull market
python backtest_screening.py --start 2020-01-01 --end 2021-12-31

# Test bear market
python backtest_screening.py --start 2022-01-01 --end 2022-12-31

# Test full cycle
python backtest_screening.py --start 2020-01-01 --end 2023-12-31
```

### 2. Walk-Forward Analysis
- Train on first 60% of data
- Test on last 40%
- Verify strategy generalizes

### 3. Parameter Sensitivity
- Test different stop loss levels
- Vary position sizes
- Try different screening intervals

### 4. Transaction Costs
Add slippage and commissions:
```python
cost = shares * current_price * (1 + slippage)  # Add 0.1% slippage
commission = 0.0  # Alpaca has no commissions
```

### 5. Realistic Assumptions
- Account for market impact
- Consider liquidity constraints
- Factor in execution delays

---

## Limitations

### Current Backtest Limitations

1. **No Slippage** - Assumes perfect execution at close price
2. **No Market Impact** - Assumes orders don't move price
3. **Perfect Data** - Uses adjusted close prices
4. **No Gaps** - Doesn't handle overnight gaps
5. **No Liquidity** - Assumes all stocks liquid

### Future Improvements

- Add realistic slippage model
- Implement market impact calculations
- Handle corporate actions (splits, dividends)
- Add intraday execution simulation
- Include bid-ask spread costs

---

## Interpreting Screening Results

### What the Backtest Tests

✅ **Stock Selection**
- Quality of screened candidates
- Regime-based ranking effectiveness
- Symbol rotation strategy

✅ **Entry Timing**
- Signal generation accuracy
- Adaptive strategy selection
- Entry price effectiveness

✅ **Exit Management**
- Stop loss effectiveness
- Take profit levels
- Signal-based exits

✅ **Risk Management**
- Position sizing
- Maximum drawdown control
- Capital preservation

### What It Doesn't Test

❌ Real-time execution latency
❌ API reliability and downtime
❌ Extreme market conditions
❌ Black swan events
❌ Broker limitations

---

## Next Steps

After running backtests:

1. **Analyze Results**
   - Review trade distribution
   - Identify best/worst trades
   - Check for patterns

2. **Optimize Parameters**
   - Adjust stop loss/take profit
   - Tune screening frequency
   - Modify position sizing

3. **Paper Trading**
   - Test live with paper account
   - Monitor real-time performance
   - Validate backtest results

4. **Live Trading**
   - Start with small capital
   - Monitor closely
   - Scale gradually

---

## Troubleshooting

### "Failed to load historical data"

**Issue:** Alpaca API credentials invalid

**Solution:**
```bash
# Use demo version
python backtest_screening_demo.py

# Or update credentials
export ALPACA_API_KEY="your_key"
export ALPACA_API_SECRET="your_secret"
```

### "No trades executed"

**Issue:** Signal logic too conservative

**Solution:**
- Adjust signal thresholds
- Check screening parameters
- Verify data quality

### "Unrealistic results"

**Issue:** Simulated data is too perfect

**Solution:**
- Use real historical data
- Add transaction costs
- Test across different periods

---

## Summary

The backtest system provides:

✅ Complete workflow testing
✅ Realistic trade simulation
✅ Comprehensive metrics
✅ Screening validation
✅ Performance analysis

Use it to:
- Validate your strategies
- Optimize parameters
- Build confidence
- Identify weaknesses
- Improve system design

**Remember:** Past performance doesn't guarantee future results. Always paper trade before going live!
