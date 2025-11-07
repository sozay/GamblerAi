# Experimental Backtest Files

This directory contains historical experimental and research backtest scripts that were used during development and testing phases. These files are archived for reference but are not part of the active production system.

## Archived Files

### Scenario Testing
- **backtest_2019_2020_covid.py** - COVID crash regime detection analysis
- **backtest_2021_2022_transition.py** - Bull-to-bear market transition analysis
- **backtest_2024_2025_forward.py** - 2024-2025 forward projection analysis
- **backtest_bear_market.py** - Bear market specific strategy analysis

### Strategy Variants
- **backtest_adaptive.py** - Adaptive regime-based strategy selection
- **backtest_volatility_adjusted.py** - Volatility-adjusted adaptive strategy
- **backtest_2024_all_strategies.py** - All strategies comparison for 2024
- **backtest_2024_realistic.py** - Realistic market conditions simulation

### Comparison Studies
- **backtest_monthly_comparison.py** - Monthly performance comparison
- **backtest_timeframe_comparison.py** - Timeframe comparison analysis
- **backtest_10k_detailed.py** - Detailed $10k portfolio simulation
- **backtest_multi_stock_scanner.py** - Multi-stock scanner system testing

## Current Active System

For the current production backtest system, see:
- `/scripts/backtest_screening.py` - Main backtest engine
- `/scripts/alpaca_paper_trading.py` - Live paper trading
- `/gambler_ai/backtesting/` - Core backtesting package

## Notes

These files contain valuable research and testing code but:
- May use outdated strategy parameters
- May have dependencies on older data structures
- Are kept for reference and potential future research
- Should not be modified without understanding the current production system first
