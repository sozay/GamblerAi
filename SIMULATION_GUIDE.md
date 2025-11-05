# GamblerAI Simulation Guide

This guide explains how to run various backtesting simulations to compare trading strategies across different conditions.

## Overview

GamblerAI includes three types of comprehensive simulations:

1. **Monthly Comparison** - Compare strategies month-by-month throughout 2024
2. **Timeframe Comparison** - Test strategies across different bar sizes (1-min to daily)
3. **Combined Analysis** - Run both monthly and timeframe analyses together

## Quick Start

### Option 1: Interactive Menu

```bash
python run_comprehensive_analysis.py
```

This launches an interactive menu where you can select:
- 1: Monthly Comparison
- 2: Timeframe Comparison
- 3: Combined Analysis
- 4: Quick Summary
- 5: Exit

### Option 2: Command-Line Arguments

```bash
# Run monthly comparison
python run_comprehensive_analysis.py --monthly

# Run timeframe comparison
python run_comprehensive_analysis.py --timeframe

# Run combined analysis
python run_comprehensive_analysis.py --combined

# Run quick summary
python run_comprehensive_analysis.py --quick
```

### Option 3: Direct Script Execution

```bash
# Month-by-month analysis
python backtest_monthly_comparison.py

# Multi-timeframe analysis
python backtest_timeframe_comparison.py
```

## Monthly Comparison Analysis

Tests all 5 strategies across each month of 2024 to identify seasonal patterns and market regime preferences.

### What It Does

- Generates realistic market data for each month with different characteristics:
  - **January**: Rally (0.02% drift, 1.2% vol)
  - **February**: Consolidation (0.01% drift, 1.1% vol)
  - **March**: Volatility (-0.01% drift, 1.3% vol)
  - **April**: Bounce (0.03% drift, 1.0% vol)
  - **May**: Rally (0.05% drift, 0.9% vol)
  - **June**: Momentum (0.07% drift, 0.8% vol)
  - **July**: Pause (0.04% drift, 1.0% vol)
  - **August**: Correction (-0.02% drift, 1.4% vol)
  - **September**: Weakness (-0.03% drift, 1.5% vol)
  - **October**: Recovery (0.06% drift, 1.1% vol)
  - **November**: Rally (0.09% drift, 0.9% vol)
  - **December**: Strength (0.10% drift, 0.8% vol)

- Runs all 5 strategies on each month's data
- Generates comprehensive comparison tables

### Output

1. **Strategy-by-Strategy Monthly Breakdown**
   - Monthly returns for each strategy
   - Win rates, trade counts, profit factors
   - Best/worst months identified
   - Annual cumulative returns

2. **Cross-Strategy Monthly Winners**
   - Which strategy performed best each month
   - Runner-up for each month

3. **Dollar-Based Tracking**
   - Starting with $10,000
   - Shows running balance month-by-month
   - Final capital and total gain percentage

### Example Output

```
STRATEGY: Multi-Timeframe
================================================================================
Month         Return %      Win Rate     Trades    Profit Factor  Sharpe    Score
--------------------------------------------------------------------------------
January       🟢 +8.45%     65.2         142       2.34           1.82      78.3
February      ⚪ +2.11%     58.1         98        1.45           0.92      62.5
March         🔴 -1.23%     45.3         87        0.89          -0.34      42.1
...
December      🟢 +12.34%    72.1         189       3.12           2.45      85.7
--------------------------------------------------------------------------------
ANNUAL SUMMARY: +85.67% cumulative | Avg: +7.14% | Std: 4.23% | Total Trades: 1456
Best Month:  December (+12.34%)
Worst Month: March (-1.23%)
```

### Running Time

Approximately 2-3 minutes for full year analysis across all 5 strategies.

## Timeframe Comparison Analysis

Tests all 5 strategies across 6 different bar sizes to identify optimal trading timeframes.

### Timeframes Tested

1. **1-Minute Bars** - Ultra-short-term (60 days, ~23,400 bars)
2. **2-Minute Bars** - Very short-term (60 days, ~11,700 bars)
3. **5-Minute Bars** - Short-term (60 days, ~4,680 bars)
4. **15-Minute Bars** - Medium-term (120 days, ~3,120 bars)
5. **1-Hour Bars** - Longer-term (252 days, ~1,638 bars)
6. **Daily Bars** - Long-term (252 days, 252 bars)

### What It Does

- Generates realistic intraday data with appropriate volatility for each timeframe
- Runs all 5 strategies on each timeframe
- Creates performance comparison tables
- Generates a heatmap showing which strategies work best on which timeframes

### Output

1. **Strategy-by-Strategy Timeframe Breakdown**
   - Returns, win rates, trade counts for each timeframe
   - Best performing timeframe identified
   - Performance scores (0-100)

2. **Timeframe Winners Table**
   - Best strategy for each timeframe
   - Return percentages and trade counts

3. **Performance Heatmap**
   - Visual grid of all strategies × all timeframes
   - Color coding:
     - 🟢 Excellent (70+ score)
     - 🟡 Good (50-70 score)
     - 🔴 Poor (<50 score)

4. **Key Insights**
   - Best and worst timeframe for each strategy
   - Average performance scores

### Example Output

```
STRATEGY-TIMEFRAME PERFORMANCE HEATMAP
Color coding: 🟢 Excellent (70+) | 🟡 Good (50-70) | 🔴 Poor (<50)
================================================================================

Strategy                  1-Min        2-Min        5-Min        15-Min       1-Hour       Daily
--------------------------------------------------------------------------------
Momentum                  🔴 42.3      🔴 45.8      🟡 58.2      🟡 62.5      🟢 71.3      🟢 75.8
Mean Reversion            🟢 72.1      🟢 71.5      🟡 65.3      🟡 58.7      🔴 48.2      🔴 42.9
Volatility Breakout       🔴 38.5      🔴 41.2      🟡 52.8      🟡 61.4      🟢 70.2      🟢 73.5
Multi-Timeframe           🟡 65.8      🟢 70.2      🟢 76.5      🟢 78.9      🟢 75.3      🟡 68.2
Smart Money               🟢 71.2      🟢 73.5      🟢 76.8      🟢 79.2      🟢 77.5      🟡 69.8

KEY INSIGHTS:
---------------------------------------------------------------------------
Momentum:
  Best on: Daily (75.8)
  Worst on: 1-Min (42.3)
  Average Score: 59.3

Multi-Timeframe:
  Best on: 15-Min (78.9)
  Worst on: 1-Min (65.8)
  Average Score: 72.5
```

### Running Time

Approximately 3-4 minutes for all 6 timeframes across all 5 strategies.

## Combined Analysis

Runs both monthly and timeframe analyses sequentially, providing a comprehensive view of strategy performance.

### Running Time

Approximately 5-7 minutes total.

## Understanding the Output

### Performance Metrics

- **Return %**: Percentage gain/loss over the period
- **Win Rate**: Percentage of profitable trades (0-100%)
- **Trades**: Number of trades executed
- **Profit Factor**: Gross profit ÷ Gross loss (>1 is profitable)
- **Sharpe Ratio**: Risk-adjusted returns (>1 is good, >2 is excellent)
- **Max DD %**: Maximum drawdown percentage
- **Score**: Overall performance score (0-100, weighted composite)

### Performance Score Calculation

The 0-100 score is calculated as:
- **Win Rate**: 20 points
- **Profit Factor**: 25 points
- **Sharpe Ratio**: 25 points
- **Drawdown**: 20 points (inverted - lower is better)
- **Return**: 10 points

### Interpreting Results

**Excellent Performance (70-100)**
- Strategy is well-suited to this timeframe/regime
- Consider prioritizing this strategy in similar conditions
- May allocate more capital

**Good Performance (50-70)**
- Strategy works reasonably well
- Can be used as secondary strategy
- Monitor closely

**Poor Performance (<50)**
- Strategy struggles in these conditions
- Avoid using or reduce allocation
- May need parameter optimization

## Strategy Characteristics

### Momentum
- **Best in**: Trending markets, longer timeframes
- **Worst in**: Choppy markets, very short timeframes
- **Trades**: Low frequency (10-50/month)

### Mean Reversion
- **Best in**: Ranging markets, shorter timeframes
- **Worst in**: Strong trends, daily timeframes
- **Trades**: Medium frequency (50-100/month)

### Volatility Breakout
- **Best in**: Volatility expansion periods
- **Worst in**: Tight consolidation
- **Trades**: Low frequency (0-30/month, regime dependent)

### Multi-Timeframe
- **Best in**: All conditions (most consistent)
- **Worst in**: Very short timeframes (1-2 min)
- **Trades**: High frequency (100-200/month)

### Smart Money
- **Best in**: Institutional activity periods
- **Worst in**: Low volume periods
- **Trades**: Low-Medium frequency (30-80/month)

## Customization

### Modifying Monthly Data

Edit `backtest_monthly_comparison.py`:

```python
month_regimes = {
    1: {'drift': 0.0002, 'vol': 0.012, 'name': 'January Rally'},
    # Adjust drift (daily return) and vol (volatility)
}
```

### Modifying Timeframes

Edit `backtest_timeframe_comparison.py`:

```python
timeframes = [
    ('1-Minute', 1, 60),      # (name, minutes, days)
    ('30-Minute', 30, 180),   # Add new timeframe
    # ...
]
```

### Modifying Strategy Parameters

Edit individual detector files:
- `gambler_ai/analysis/momentum_detector.py`
- `gambler_ai/analysis/mean_reversion_detector.py`
- `gambler_ai/analysis/volatility_breakout_detector.py`
- `gambler_ai/analysis/multi_timeframe_analyzer.py`
- `gambler_ai/analysis/smart_money_detector.py`

See `STRATEGY_PARAMETERS.md` for full parameter documentation.

### Modifying Risk Management

Edit backtest calls:

```python
engine = BacktestEngine(
    initial_capital=100000,       # Starting capital
    risk_per_trade=0.01,          # 1% risk per trade
    max_concurrent_trades=3,      # Max 3 positions
)
```

## Troubleshooting

### "No trades detected"

- Strategy found no valid setups in the data
- Try: Adjust strategy parameters to be less restrictive
- Or: Generate data with more volatility/volume spikes

### "ImportError: cannot import name..."

- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python path includes project root

### "Process takes too long"

- Each month/timeframe processes ~20-400 bars per day
- Reduce number of days in data generation
- Run single strategy first to test

### "Results seem unrealistic"

- Synthetic data is being used (no slippage, perfect fills)
- Real trading will have:
  - Slippage (1-5 cents per share)
  - Commissions ($0-$1 per trade)
  - Partial fills
  - Wider spreads
- Multiply returns by 0.7-0.8 for realistic expectations

## Next Steps

After reviewing simulation results:

1. **Identify Best Strategies**
   - Note which strategies performed best overall
   - Note which excel in specific conditions

2. **Optimize Parameters**
   - Focus on promising strategies
   - Test parameter variations
   - See STRATEGY_PARAMETERS.md

3. **Portfolio Allocation**
   - Allocate more capital to high-scoring strategies
   - Use low-correlation strategies together
   - Example: Multi-Timeframe (60%) + Smart Money (40%)

4. **Live Testing**
   - Start with paper trading
   - Use reduced position sizes
   - Monitor for 1-2 months before scaling

5. **Continuous Monitoring**
   - Run monthly simulations regularly
   - Adjust allocations based on recent performance
   - Watch for regime changes

## Files

- `run_comprehensive_analysis.py` - Main entry point with menu
- `backtest_monthly_comparison.py` - Monthly analysis
- `backtest_timeframe_comparison.py` - Timeframe analysis
- `SIMULATION_GUIDE.md` - This guide
- `STRATEGY_PARAMETERS.md` - Parameter documentation
- `ALTERNATIVE_STRATEGIES.md` - Strategy design docs

## Support

For issues or questions:
- Check existing documentation in project root
- Review code comments in detector files
- Examine example output from demo scripts
