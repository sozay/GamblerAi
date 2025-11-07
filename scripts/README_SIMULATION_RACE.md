# 🏁 Simulation Race - Scanner & Strategy Performance Comparison

A comprehensive simulation system that tests all combinations of stock selectors and trading strategies over the past year, with an interactive "race" visualization to track performance week by week.

## 📋 Overview

This simulation tests:
- **8 Stock Scanners** (how we select stocks to trade)
- **5 Trading Strategies** (how we trade selected stocks)
- **= 40 Total Combinations**

Each combination is tested on **1 year of minute-level data**, processed week by week (~52 weeks).

## 🎯 Features

### Simulation Engine
- Tests all scanner + strategy combinations
- Week-by-week backtesting over 1 year
- Realistic trade simulation with proper risk management
- Saves progress incrementally
- Comprehensive performance metrics

### Interactive UI
- **Race View**: Animated bar chart showing cumulative P&L over time
- **Leaderboard**: Ranked table of all combinations
- **Performance Charts**: Returns distribution, risk vs return scatter plots
- **Detailed Analysis**: Deep dive into any combination with weekly breakdowns
- **Filters**: Filter by scanner type or strategy
- **Animation Controls**: Adjust speed, pause/play, jump to specific weeks

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install required packages
pip install streamlit plotly pandas numpy
```

### 2. Run the Simulation

```bash
# Run the complete simulation (takes 5-10 minutes)
python scripts/simulation_race_engine.py
```

This will:
- Test all 40 combinations
- Simulate 52 weeks of trading
- Save results to `simulation_results/` directory
- Display top performers when complete

### 3. Launch the Interactive UI

```bash
# Launch the visualization dashboard
streamlit run scripts/simulation_race_ui.py
```

Then open your browser to http://localhost:8501

## 📊 What Gets Tested

### Stock Scanners (8 Types)

1. **TOP_MOVERS** - Stocks with largest price moves + high volume
2. **HIGH_VOLUME** - Stocks with volume spikes
3. **VOLATILITY_RANGE** - Stocks in optimal volatility range (15-35%)
4. **RELATIVE_STRENGTH** - Stocks outperforming benchmark (SPY)
5. **GAP_SCANNER** - Stocks with significant price gaps
6. **BEST_SETUPS** - Stocks with best risk/reward ratios
7. **SECTOR_LEADERS** - Top performers in their sectors
8. **MARKET_CAP_WEIGHTED** - Larger, more liquid stocks

### Trading Strategies (5 Types)

1. **Momentum** - Follows strong directional moves
2. **Mean Reversion** - Trades oversold/overbought conditions
3. **Volatility Breakout** - Captures volatility expansions
4. **Multi-Timeframe** - Analyzes multiple timeframes
5. **Smart Money** - Follows institutional money flows

## 📈 Performance Metrics

For each combination, we track:
- **Total P&L**: Total profit/loss in dollars
- **Return %**: Percentage return on initial capital
- **Total Trades**: Number of trades executed
- **Win Rate**: Percentage of winning trades
- **Sharpe Ratio**: Risk-adjusted return metric
- **Max Drawdown**: Largest peak-to-trough decline

## 🎬 Using the UI

### Race View Tab
- Watch an animated "race" showing how combinations perform over time
- Click **Play** to watch the animation
- Use the slider to jump to specific weeks
- Select top N combinations to display (5-40)
- Adjust animation speed

### Leaderboard Tab
- View final rankings of all combinations
- Sort by different metrics
- See top 3 winners highlighted
- Export data if needed

### Performance Charts Tab
- **Returns Distribution**: Histogram showing spread of returns
- **Risk vs Return**: Scatter plot showing risk/reward profile
- **Weekly Performance**: Line chart tracking top 5 over time

### Detailed Analysis Tab
- Select any combination for deep dive
- View complete weekly breakdown
- See trade-by-trade statistics
- Analyze performance trends

## ⚙️ Configuration

### Customize Simulation Parameters

Edit `scripts/simulation_race_engine.py`:

```python
engine = SimulationRaceEngine(
    symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],  # Stocks to trade
    initial_capital=100000,  # Starting capital
    lookback_days=365,  # Days to simulate (365 = 1 year)
    results_dir="simulation_results",  # Where to save results
)
```

### Filter in UI

Use sidebar to:
- Select specific scanners to compare
- Select specific strategies to compare
- Show top N performers only
- Adjust animation speed

## 📁 Results Structure

After running simulation:

```
simulation_results/
├── all_results.json              # Summary of all combinations
├── top_movers_Momentum.json      # Individual combination results
├── top_movers_Mean_Reversion.json
├── high_volume_Momentum.json
└── ... (40 total combination files)
```

Each file contains:
- Scanner and strategy details
- Total performance metrics
- Week-by-week results
- Trade-level data

## 🔍 Understanding Results

### What Makes a Good Combination?

Look for combinations with:
- **High Return %**: Profitable over the year
- **High Sharpe Ratio** (>1.5): Good risk-adjusted returns
- **Moderate Win Rate** (>45%): Consistent winners
- **Low Max Drawdown** (<20%): Controlled risk
- **Adequate Trades** (>100): Sufficient opportunities

### Common Patterns

Based on historical testing:
- **Mean Reversion** performs well in choppy markets
- **Multi-Timeframe** excels in trending markets
- **Best Setups** scanner often selects quality opportunities
- **High Volume** scanner catches momentum moves

## 🛠️ Advanced Usage

### Run Partial Simulation

```python
from scripts.simulation_race_engine import SimulationRaceEngine

engine = SimulationRaceEngine(lookback_days=90)  # Last 3 months only
results = engine.run_simulation()
```

### Load Previous Results

```python
from scripts.simulation_race_engine import SimulationRaceEngine

results = SimulationRaceEngine.load_results("simulation_results")
print(results)
```

### Custom Analysis

```python
import json

# Load results
with open('simulation_results/all_results.json', 'r') as f:
    data = json.load(f)

# Find best scanner
scanner_performance = {}
for combo_name, combo in data['combinations'].items():
    scanner = combo['scanner_type']
    if scanner not in scanner_performance:
        scanner_performance[scanner] = []
    scanner_performance[scanner].append(combo['return_pct'])

# Average performance by scanner
for scanner, returns in scanner_performance.items():
    avg_return = sum(returns) / len(returns)
    print(f"{scanner}: {avg_return:.2f}%")
```

## 📊 Example Output

### Top 10 Performers

```
Rank  Scanner                  Strategy            Return %    P&L          Trades  Win %   Sharpe
1     best_setups             Multi-Timeframe     18.45%      $18,450      285     54.7%   2.34
2     relative_strength       Mean Reversion      15.23%      $15,230      312     48.4%   2.01
3     top_movers              Multi-Timeframe     14.87%      $14,870      298     52.0%   1.95
4     best_setups             Momentum            13.56%      $13,560      267     46.1%   1.82
5     volatility_range        Mean Reversion      12.98%      $12,980      289     49.3%   1.76
...
```

## 🐛 Troubleshooting

### Simulation Not Running
- Check Python version (3.11+ required)
- Install all dependencies: `pip install -r requirements.txt`
- Check file permissions in results directory

### UI Not Loading
- Make sure simulation ran first
- Check `simulation_results/` directory exists
- Install Streamlit: `pip install streamlit`

### Slow Performance
- Reduce number of combinations shown (use filters)
- Reduce lookback_days (90 instead of 365)
- Increase animation speed in UI

## 📝 Notes

- This simulation uses **simplified trade simulation** for demonstration
- Real trading would require actual minute-level market data
- Results are based on historical simulation and don't guarantee future performance
- Consider transaction costs, slippage, and market impact in real trading

## 🔄 Next Steps

After reviewing results:
1. **Identify top performers**: Note which combinations work best
2. **Understand why**: Analyze what makes them successful
3. **Paper trade**: Test top combinations in paper trading
4. **Refine parameters**: Adjust based on observations
5. **Forward test**: Run on new data not used in backtest

## 📚 Related Documentation

- `docs/guides/RUNNING_INSTRUCTIONS.md` - How to run paper trading
- `docs/guides/PAPER_TRADING_SETUP.md` - Alpaca setup
- `docs/results/FINAL_BACKTEST_RESULTS.md` - Historical backtest results
- `docs/reference/ARCHITECTURE.md` - System architecture

## 💡 Tips

- Run simulations during market hours to test with live data
- Compare results across different time periods
- Pay attention to max drawdown, not just returns
- Best combinations may vary by market regime
- Use filters to compare similar approaches
