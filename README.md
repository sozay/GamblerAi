# GamblerAI - Stock Momentum Trading System

A Python-based momentum trading system with adaptive strategies, backtesting capabilities, and live paper trading integration.

## Overview

GamblerAI is a momentum trading system that:
- Detects momentum patterns across multiple strategies (Mean Reversion, Smart Money, Adaptive)
- Backtests strategies on historical data
- Runs live paper trading via Alpaca API
- Scans multiple stocks for trading opportunities

## Key Features

- **6 Trading Strategies**: Mean Reversion, Smart Money, Volatility Breakout, News Event, Adaptive, Multi-Stock Scanner
- **Backtesting Engine**: Test strategies on historical data with realistic market conditions
- **Live Paper Trading**: Alpaca API integration for real-time paper trading
- **Multi-Stock Scanner**: Scan and trade multiple stocks simultaneously
- **Regime Detection**: Adapt strategies based on market conditions
- **Performance Analytics**: Detailed metrics, Sharpe ratio, max drawdown analysis

## Quick Start

See [docs/guides/PAPER_TRADING_SETUP.md](docs/guides/PAPER_TRADING_SETUP.md) for complete setup instructions.

### Prerequisites

```bash
# Required
pip install pandas numpy requests pyyaml

# Sign up for free Alpaca Paper Trading account
# https://alpaca.markets (get $100k paper money)
```

### Run Paper Trading

```bash
# Set API credentials
export ALPACA_API_KEY='your_key'
export ALPACA_API_SECRET='your_secret'

# Start paper trading (5-minute test)
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL \
  --duration 5 \
  --interval 30
```

That's it! The system will scan for momentum signals and place paper trades automatically.

## Usage

### Paper Trading

```bash
# Quick test (5 minutes)
python3 scripts/alpaca_paper_trading.py --duration 5 --symbols AAPL,MSFT

# Full session (1 hour)
python3 scripts/alpaca_paper_trading.py --duration 60

# Multiple stocks with custom interval
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL,TSLA,NVDA \
  --duration 30 \
  --interval 60
```

### Backtesting

```bash
# Run backtest on historical data
python3 scripts/backtest_screening.py

# Backtest specific scanner strategies
python3 backtest_stock_scanners_multi_year.py

# Debug scanner issues
python3 debug_scanner_issues.py
```

### Utilities

```bash
# Fetch historical data
python3 scripts/fetch_alpaca_data.py --symbol AAPL --start 2024-01-01

# Optimize strategy parameters
python3 scripts/optimize_parameters.py

# Visualize backtest results
python3 scripts/visualize_backtest.py
```

## Project Structure

```
GamblerAi/
├── gambler_ai/                      # Core package
│   ├── analysis/                    # Trading strategies and detectors
│   │   ├── momentum_detector.py     # Base momentum detection
│   │   ├── mean_reversion_detector.py
│   │   ├── smart_money_detector.py
│   │   ├── adaptive_strategy.py     # Regime-based adaptation
│   │   ├── stock_scanner.py         # Multi-stock scanner
│   │   └── regime_detector.py       # Market regime detection
│   ├── backtesting/                 # Backtest engine
│   │   ├── backtest_engine.py       # Main engine
│   │   ├── performance.py           # Metrics calculation
│   │   └── trade.py                 # Trade management
│   ├── data_ingestion/              # Data fetching
│   └── utils/                       # Configuration & logging
├── scripts/                         # Production scripts
│   ├── alpaca_paper_trading.py      # Live paper trading
│   ├── backtest_screening.py        # Main backtest system
│   ├── fetch_alpaca_data.py         # Data fetching
│   ├── optimize_parameters.py       # Parameter optimization
│   └── visualize_backtest.py        # Performance charts
├── docs/                            # Documentation
│   ├── guides/                      # User guides
│   ├── reference/                   # Technical docs
│   ├── results/                     # Backtest reports
│   └── archive/                     # Historical docs
├── archive/                         # Archived experiments
│   └── experimental-backtests/      # Old backtest scripts
├── config.yaml                      # Strategy configuration
└── requirements.txt                 # Dependencies
```

## Configuration

Edit `config.yaml` to customize strategies:

```yaml
strategies:
  mean_reversion:
    min_price_change_pct: 2.0
    stop_loss_pct: 2.0
    take_profit_pct: 4.0

  smart_money:
    volume_threshold: 2.0
    momentum_threshold: 1.5

stocks:
  scanner_symbols:
    - AAPL
    - MSFT
    - GOOGL
    - TSLA
    - NVDA

alpaca:
  # Set via environment variables or .env file
  api_key: ${ALPACA_API_KEY}
  api_secret: ${ALPACA_API_SECRET}
  paper_trading: true
```

## Trading Strategies

### 1. Mean Reversion
Detects overbought/oversold conditions and trades the reversal.

### 2. Smart Money
Follows institutional money flows via volume and price action.

### 3. Volatility Breakout
Captures momentum from volatility expansion.

### 4. News Event
Trades momentum around scheduled events (earnings, Fed announcements).

### 5. Adaptive Strategy
Dynamically selects strategy based on detected market regime (bull/bear/ranging).

### 6. Multi-Stock Scanner
Scans multiple stocks simultaneously for momentum signals across all strategies.

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Strategies

1. Create detector in `gambler_ai/analysis/`
2. Inherit from base `MomentumDetector`
3. Implement `detect_pattern()` method
4. Add to `stock_scanner.py` strategies list
5. Test with `scripts/backtest_screening.py`

## Documentation

- **[Setup Guide](docs/guides/PAPER_TRADING_SETUP.md)** - Complete setup instructions
- **[Running Instructions](docs/guides/RUNNING_INSTRUCTIONS.md)** - How to run paper trading
- **[Troubleshooting](docs/guides/TROUBLESHOOTING.md)** - Common issues and fixes
- **[Architecture](docs/reference/ARCHITECTURE.md)** - System design details
- **[Backtest Results](docs/results/FINAL_BACKTEST_RESULTS.md)** - Performance reports

## Current Status

✅ **Implemented:**
- 6 trading strategies with momentum detection
- Comprehensive backtesting engine
- Live Alpaca paper trading integration
- Multi-stock scanner system
- Regime detection and adaptive strategy selection
- Performance analytics and visualization

📊 **Backtest Performance:**
- Multi-year backtests completed (2019-2024)
- Tested across bull, bear, and ranging markets
- See `docs/results/` for detailed reports

## Support

For questions or issues:
- Review `docs/guides/TROUBLESHOOTING.md`
- Open an issue on GitHub

## Built With

- **Data**: Yahoo Finance, Alpaca Markets API
- **Core**: Python, Pandas, NumPy
- **Analysis**: Custom momentum detection algorithms
- **Trading**: Alpaca Paper Trading API
