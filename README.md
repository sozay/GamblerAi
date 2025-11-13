# GamblerAI - AI-Powered Trading System

An intelligent trading system that combines real-time trading with comprehensive strategy simulation and backtesting capabilities.

## 🎯 Core Functionalities

### 1. **Live Trading System**
Real-time paper/live trading integrated with Alpaca API
- Automated trading with multiple momentum-based strategies
- Real-time market data analysis and signal detection
- Position management with stop-loss and take-profit orders
- State persistence and crash recovery
- Multi-symbol concurrent trading

### 2. **Simulation & Backtesting Engine**
Comprehensive strategy testing and optimization platform
- Test multiple trading strategies against historical data
- Scanner strategy comparison (40+ combinations)
- Interactive race visualization showing strategy performance
- Week-by-week performance tracking
- Realistic market simulation with slippage and fees

### 3. **Interactive Web UI**
Streamlit-based dashboards for both systems
- Real-time trading dashboard with live P&L tracking
- Simulation race interface with animated comparisons
- Strategy configurator for parameter tuning
- Performance analytics and visualizations

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set up Alpaca API credentials (free paper trading account)
export ALPACA_API_KEY='your_key'
export ALPACA_API_SECRET='your_secret'
```

### Running Live Trading

```bash
# Start paper trading (recommended for testing)
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL \
  --duration 60 \
  --interval 30
```

### Running Simulations

```bash
# Run simulation race (tests 40+ strategy combinations)
python3 scripts/simulation_race_engine.py

# Launch interactive simulation UI
streamlit run scripts/simulation_race_ui.py
```

### Launching Dashboards

```bash
# Trading dashboard (monitor live trading)
streamlit run scripts/simulation_live_dashboard.py

# Strategy configurator (tune parameters)
streamlit run scripts/simulation_configurator_ui.py

# Interactive simulator
streamlit run scripts/interactive_simulator_ui.py
```

---

## 📁 Project Structure

```
GamblerAi/
├── gambler_ai/                      # Core package
│   ├── analysis/                    # Trading strategies & detectors
│   ├── backtesting/                 # Backtest engine
│   ├── trading/                     # Live trading logic
│   ├── api/                         # API integrations
│   ├── dashboard/                   # UI components
│   ├── data_ingestion/              # Market data fetching
│   ├── storage/                     # Database & persistence
│   └── utils/                       # Configuration & logging
├── scripts/                         # Production scripts
│   ├── alpaca_paper_trading.py      # Main live trading script
│   ├── alpaca_paper_trading_recovery.py  # Trading recovery system
│   ├── simulation_race_engine.py    # Simulation engine
│   ├── simulation_race_ui.py        # Simulation race UI
│   ├── simulation_live_dashboard.py # Live trading dashboard
│   ├── interactive_simulator_ui.py  # Interactive simulator
│   ├── simulation_configurator_ui.py # Strategy configurator
│   ├── fetch_alpaca_data.py         # Data fetching utilities
│   ├── data_downloader.py           # Historical data downloader
│   └── enhanced_data_downloader.py  # Advanced data fetching
├── docs/                            # Documentation
│   ├── guides/                      # User guides
│   ├── reference/                   # Technical documentation
│   └── archive/                     # Historical docs & notes
├── archive/                         # Archived experiments
│   └── old-scripts/                 # Deprecated scripts
├── tests/                           # Test suite
├── config.yaml                      # Strategy configuration
├── docker-compose.yml               # Docker setup
└── requirements.txt                 # Dependencies
```

---

## 🎮 Usage Examples

### Live Trading

```bash
# Quick 5-minute test
python3 scripts/alpaca_paper_trading.py --duration 5 --symbols AAPL,MSFT

# Full trading session with multiple symbols
python3 scripts/alpaca_paper_trading.py \
  --symbols AAPL,MSFT,GOOGL,TSLA,NVDA \
  --duration 120 \
  --interval 60
```

### Simulation & Backtesting

```bash
# Run full simulation race (52 weeks, 40+ combinations)
python3 scripts/simulation_race_engine.py

# View results interactively
streamlit run scripts/simulation_race_ui.py
```

### Data Management

```bash
# Fetch historical data from Alpaca
python3 scripts/fetch_alpaca_data.py --symbol AAPL --start 2024-01-01

# Download extended historical data
python3 scripts/data_downloader.py
```

---

## ⚙️ Configuration

Edit `config.yaml` to customize trading strategies:

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
  api_key: ${ALPACA_API_KEY}
  api_secret: ${ALPACA_API_SECRET}
  paper_trading: true
```

---

## 📊 Trading Strategies

The system implements multiple momentum-based strategies:

1. **Mean Reversion** - Trades overbought/oversold conditions
2. **Smart Money** - Follows institutional money flows
3. **Volatility Breakout** - Captures volatility expansion
4. **Multi-Timeframe** - Analyzes multiple timeframes
5. **Momentum** - Follows strong directional moves

### Stock Scanners

- Top Movers (volume + price action)
- High Volume spikes
- Volatility Range filtering
- Relative Strength vs benchmark
- Gap Scanner (pre-market/intraday gaps)
- Best Setups (risk/reward optimization)
- Sector Leaders
- Market Cap weighted selection

---

## 🐳 Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- **gambler-api**: REST API for trading operations
- **gambler-trading**: Main trading service
- **postgres**: Database for persistence

---

## 📚 Documentation

- **[Setup Guide](docs/guides/PAPER_TRADING_SETUP.md)** - Complete setup instructions
- **[Running Instructions](docs/guides/RUNNING_INSTRUCTIONS.md)** - How to run the system
- **[Troubleshooting](docs/guides/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Architecture](docs/reference/ARCHITECTURE.md)** - System design details
- **[Simulation Guide](scripts/README_SIMULATION_RACE.md)** - Simulation system guide

---

## 🧪 Development

### Running Tests

```bash
pytest tests/
```

### Adding New Strategies

1. Create detector in `gambler_ai/analysis/`
2. Inherit from `MomentumDetector` base class
3. Implement `detect_pattern()` method
4. Register in `stock_scanner.py`
5. Test with simulation engine

---

## 🔧 Service Management

The project includes systemd service files for production deployment:

```bash
# Install services
sudo ./install-services.sh

# Check status
sudo systemctl status gambler-trading
sudo systemctl status gambler-api

# View logs
sudo journalctl -u gambler-trading -f
```

---

## 📈 Current Status

✅ **Implemented:**
- Real-time Alpaca paper/live trading integration
- 5+ momentum-based trading strategies
- 8 stock scanner types
- Comprehensive simulation and backtesting engine
- Interactive web dashboards (Streamlit)
- State persistence and crash recovery
- Multi-symbol concurrent trading
- Performance analytics and visualization

---

## 🛠️ Built With

- **Python 3.11+** - Core language
- **Alpaca API** - Market data & trading execution
- **Streamlit** - Interactive web dashboards
- **PostgreSQL** - State persistence
- **Docker** - Containerized deployment
- **Pandas/NumPy** - Data analysis

---

## ⚠️ Disclaimer

This system is for educational and research purposes. Trading involves substantial risk. Always test thoroughly with paper trading before considering live trading. Past performance does not guarantee future results.

---

## 📞 Support

For questions or issues:
- Review documentation in `docs/guides/`
- Check `docs/guides/TROUBLESHOOTING.md`
- Open an issue on GitHub

---

## 📝 License

See LICENSE file for details.
