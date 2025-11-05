# Backtesting Automatic Stock Screening

Test the dynamic stock screening system against historical data from November 6, 2024 to present.

## Quick Start

### Option 1: Demo with Simulated Data (Recommended for Testing)

```bash
# No API credentials needed
python backtest_screening_demo.py
```

**Output:**
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
  Profit Factor:         6.00

Risk Metrics:
  Sharpe Ratio:                2.95
  Max Drawdown:              -8.50%

Benchmark (SPY Buy & Hold):
  SPY Return:               +15.20%
  Outperformance:           +12.72%
```

### Option 2: Real Data Backtest

```bash
# Requires valid Alpaca API credentials
export ALPACA_API_KEY="your_key"
export ALPACA_API_SECRET="your_secret"

python backtest_screening.py
```

---

## What It Tests

The backtest simulates the complete automated trading workflow:

1. **Stock Screening**
   - Momentum screening (10%+ gains)
   - Mean reversion (oversold bounces)
   - Breakout detection (consolidation breakouts)
   - Volume surge identification (3x+ volume)

2. **Market Regime Detection**
   - BULL market (favor momentum)
   - BEAR market (favor mean reversion)
   - RANGE market (favor oscillation)

3. **Adaptive Strategy Selection**
   - Automatically picks best strategy for regime
   - Generates buy/sell signals
   - Adapts to changing conditions

4. **Risk Management**
   - 2% stop loss on every trade
   - 4% take profit target
   - 20% position sizing (max 5 positions)

5. **Performance Tracking**
   - All trades logged
   - Equity curve tracked
   - Metrics calculated

---

## Configuration

Edit the scripts to customize parameters:

```python
backtest = ScreeningBacktest(
    start_date=datetime(2024, 11, 6),     # Start date
    end_date=datetime.now(),              # End date
    initial_capital=100_000.0,            # Starting capital
    screening_interval_hours=24,          # Rescan daily
    max_positions=5,                      # Max concurrent positions
    position_size_pct=0.20,               # 20% per position
    stop_loss_pct=0.02,                   # 2% stop loss
    take_profit_pct=0.04,                 # 4% take profit
)
```

---

## Output Files

### 1. Equity Curve

`backtest_equity_curve.csv` or `backtest_demo_equity_curve.csv`

Track portfolio value over time:
```csv
timestamp,equity
2024-11-06,100000.00
2024-11-07,101250.00
2024-11-08,102100.00
```

**Visualize:**
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('backtest_demo_equity_curve.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

plt.plot(df['timestamp'], df['equity'])
plt.title('Backtest Equity Curve')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
plt.grid(True)
plt.show()
```

### 2. Trade History

`backtest_trades.csv` or `backtest_demo_trades.csv`

Complete log of all trades:
```csv
timestamp,symbol,action,shares,price,value,pnl,pnl_pct,hold_days
2024-11-06,AAPL,BUY,100,150.00,15000.00,,,
2024-11-10,AAPL,SELL,100,156.00,15600.00,600.00,4.0,4
```

**Analyze:**
```python
import pandas as pd

trades = pd.read_csv('backtest_demo_trades.csv')

# Winning trades
winners = trades[trades['action'] == 'SELL'][trades['pnl'] > 0]
print(f"Winning trades: {len(winners)}")
print(f"Average win: ${winners['pnl'].mean():.2f}")

# Best trade
best_trade = trades.loc[trades['pnl'].idxmax()]
print(f"\nBest trade: {best_trade['symbol']}")
print(f"P&L: ${best_trade['pnl']:.2f} ({best_trade['pnl_pct']:.2f}%)")
```

### 3. Screening History

`backtest_screenings.csv`

Log of all screening runs:
```csv
timestamp,regime,confidence,candidates,selected
2024-11-06,BULL,0.87,42,"['NVDA', 'AMD', 'TSLA', 'GOOGL', 'WMT']"
2024-11-13,BULL,0.91,45,"['NVDA', 'MSFT', 'AAPL', 'META', 'GOOGL']"
```

---

## Key Metrics Explained

### Sharpe Ratio
- **What:** Risk-adjusted returns
- **Formula:** `(Mean Return / Std Return) × √252`
- **Interpretation:**
  - \> 1.0 = Good
  - \> 2.0 = Very good
  - \> 3.0 = Excellent

### Max Drawdown
- **What:** Largest peak-to-trough decline
- **Interpretation:**
  - < 10% = Excellent
  - < 20% = Good
  - \> 30% = High risk

### Profit Factor
- **What:** Avg Win / Avg Loss
- **Interpretation:**
  - \> 1.5 = Profitable
  - \> 2.0 = Strong
  - \> 3.0 = Excellent

### Win Rate
- **What:** % of winning trades
- **Interpretation:**
  - \> 50% = Profitable
  - \> 60% = Good
  - \> 70% = Excellent

---

## Testing Different Scenarios

### Conservative Trading
```python
backtest = ScreeningBacktest(
    stop_loss_pct=0.01,      # Tight 1% stop
    take_profit_pct=0.02,    # Quick 2% profit
    position_size_pct=0.10,  # Smaller 10% positions
    max_positions=10,        # More diversification
)
```

### Aggressive Trading
```python
backtest = ScreeningBacktest(
    stop_loss_pct=0.05,      # Wider 5% stop
    take_profit_pct=0.10,    # Larger 10% profit
    position_size_pct=0.25,  # Bigger 25% positions
    max_positions=4,         # More concentrated
)
```

### High-Frequency Screening
```python
backtest = ScreeningBacktest(
    screening_interval_hours=6,  # Rescan every 6 hours
)
```

### Long-Term Screening
```python
backtest = ScreeningBacktest(
    screening_interval_hours=168,  # Rescan weekly
)
```

---

## Understanding Results

### Good Results 👍

- **Total Return** > Benchmark (SPY)
- **Sharpe Ratio** > 2.0
- **Max Drawdown** < 15%
- **Win Rate** > 55%
- **Profit Factor** > 2.0

### Warning Signs ⚠️

- **100% Win Rate** = Likely overfitting
- **Max Drawdown > 30%** = Too risky
- **Profit Factor < 1.5** = Weak edge
- **Returns < Benchmark** = No alpha

---

## Next Steps After Backtesting

1. **Paper Trading**
   ```bash
   # Test live with paper account
   python trading_bot.py --paper --screening
   ```

2. **Live Trading (Small Scale)**
   ```bash
   # Start with small capital
   python trading_bot.py --screening --capital 5000
   ```

3. **Monitor & Adjust**
   - Track live performance
   - Compare to backtest
   - Adjust parameters as needed

---

## Differences Between Scripts

| Feature | `backtest_screening.py` | `backtest_screening_demo.py` |
|---------|------------------------|------------------------------|
| Data Source | Alpaca API (real data) | Simulated data |
| API Required | ✅ Yes | ❌ No |
| Speed | Slower (API calls) | Fast (in-memory) |
| Accuracy | Real historical data | Approximate |
| Best For | Final validation | Development, testing |

---

## Common Issues

### "Failed to load historical data"
```bash
# Use demo version
python backtest_screening_demo.py
```

### "No trades executed"
- Check signal parameters are not too conservative
- Verify screening is finding candidates
- Review logs for issues

### Import errors
```bash
pip install pandas numpy scipy scikit-learn pydantic pydantic-settings
```

---

## Documentation

- **Complete Guide:** [docs/BACKTESTING.md](docs/BACKTESTING.md)
- **Stock Screening:** [docs/STOCK_SELECTION.md](docs/STOCK_SELECTION.md)
- **Trading Bot:** [docs/TRADING_BOT.md](docs/TRADING_BOT.md)

---

## Architecture

```
Backtest System
│
├── Data Loading
│   ├── Fetch historical bars (real or simulated)
│   └── Cache for fast access
│
├── Screening Loop (periodic)
│   ├── Run 4 screening strategies
│   ├── Detect market regime
│   ├── Rank candidates by regime
│   └── Select top N stocks
│
├── Signal Generation (daily)
│   ├── For each selected stock:
│   ├── Detect regime
│   ├── Select adaptive strategy
│   └── Generate BUY/SELL signal
│
├── Trade Execution
│   ├── Enter positions (BUY)
│   ├── Exit positions (SELL)
│   └── Check stop loss/take profit
│
└── Performance Tracking
    ├── Log all trades
    ├── Update equity curve
    └── Calculate metrics
```

---

## Summary

The backtest system lets you:

✅ Test the complete workflow
✅ Validate stock screening
✅ Measure strategy performance
✅ Optimize parameters
✅ Build confidence before live trading

**Remember:** Backtest results don't guarantee future performance. Always paper trade first!

---

## Questions?

- Review [docs/BACKTESTING.md](docs/BACKTESTING.md) for detailed documentation
- Check [docs/STOCK_SELECTION.md](docs/STOCK_SELECTION.md) for screening details
- See [docs/TRADING_BOT.md](docs/TRADING_BOT.md) for live trading

**Happy backtesting! 📈**
