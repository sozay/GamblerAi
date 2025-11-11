# Simulation Features Guide

## Overview

GamblerAI now includes advanced simulation features that provide more realistic backtesting:

1. **Execution Slippage**: Simulates real-world order execution delays
2. **Configurable Profit/Loss Targets**: User-defined stop loss and take profit percentages

## Features

### 1. Execution Slippage

In real-world trading, not all orders execute at the expected price. This feature simulates that reality.

#### How It Works

- **Slippage Probability**: Percentage of orders that experience delayed execution (e.g., 30%)
- **Delay Bars**: Number of bars to delay execution (e.g., 1 bar = next bar price)

#### Example

With 30% slippage and 1 bar delay:
- 70% of orders execute at the current bar price (no slippage)
- 30% of orders execute at the next bar's price (with slippage)

This means some orders will execute at better or worse prices than expected, just like in real trading.

### 2. Configurable Profit/Loss Targets

Set custom stop loss and take profit percentages for your trading strategy.

#### Parameters

- **Stop Loss %**: Maximum loss before closing the position (e.g., 1.0 = 1% loss)
- **Take Profit %**: Target profit before closing the position (e.g., 2.0 = 2% gain)
- **Use Percentage Targets**: Enable/disable percentage-based targets

#### Examples

**Example 1: Conservative Setup**
- Entry Price: $100
- Stop Loss: 1% → Exit at $99 (loss)
- Take Profit: 2% → Exit at $102 (gain)
- Risk/Reward Ratio: 1:2

**Example 2: Aggressive Setup**
- Entry Price: $100
- Stop Loss: 2% → Exit at $98 (loss)
- Take Profit: 6% → Exit at $106 (gain)
- Risk/Reward Ratio: 1:3

## Usage

### Method 1: Using the Configurator UI (Recommended)

```bash
streamlit run scripts/simulation_configurator_ui.py
```

This provides an interactive interface where you can:
- Set slippage parameters
- Configure profit/loss targets
- Run simulations with custom settings
- View results in real-time

### Method 2: Programmatic Usage

```python
from scripts.simulation_race_engine import SimulationRaceEngine

# Create engine with custom parameters
engine = SimulationRaceEngine(
    initial_capital=100000,
    lookback_days=365,
    # Slippage configuration
    slippage_enabled=True,
    slippage_probability=0.3,  # 30% of orders
    slippage_delay_bars=1,      # 1 bar delay
    # Profit/Loss targets
    stop_loss_pct=1.0,          # 1% stop loss
    take_profit_pct=2.0,        # 2% take profit
    use_percentage_targets=True,
)

# Run simulation
results = engine.run_simulation()
```

### Method 3: Using BacktestEngine Directly

```python
from gambler_ai.backtesting.backtest_engine import BacktestEngine

# Create backtest engine with custom parameters
engine = BacktestEngine(
    initial_capital=100000.0,
    slippage_enabled=True,
    slippage_probability=0.3,
    slippage_delay_bars=1,
    stop_loss_pct=1.0,
    take_profit_pct=2.0,
    use_percentage_targets=True,
)

# Run backtest on your data
trades = engine.run_backtest(df, detector)
```

### Method 4: Configuration File

Edit `config.yaml`:

```yaml
backtest:
  # Execution slippage simulation
  execution_slippage:
    enabled: true
    probability: 0.3    # 30% slippage rate
    delay_bars: 1       # 1 bar delay

  # Profit/loss targets
  profit_loss_targets:
    use_percentage_targets: true
    stop_loss_pct: 1.0   # 1% stop loss
    take_profit_pct: 2.0 # 2% take profit
```

## Viewing Results

### Simulation Race UI

```bash
streamlit run scripts/simulation_race_ui.py
```

The UI now displays simulation parameters in the sidebar:
- Slippage configuration (if enabled)
- Stop loss and take profit percentages
- All other simulation settings

## Parameter Recommendations

### Conservative (Low Risk)
```python
stop_loss_pct=0.5        # 0.5% stop loss
take_profit_pct=1.0      # 1.0% take profit
slippage_probability=0.2 # 20% slippage
```
**Use for**: Stable markets, frequent trading, risk-averse strategies

### Balanced (Medium Risk)
```python
stop_loss_pct=1.0        # 1% stop loss
take_profit_pct=2.0      # 2% take profit
slippage_probability=0.3 # 30% slippage
```
**Use for**: Normal market conditions, balanced risk/reward

### Aggressive (High Risk)
```python
stop_loss_pct=2.0        # 2% stop loss
take_profit_pct=6.0      # 6% take profit
slippage_probability=0.5 # 50% slippage
```
**Use for**: Volatile markets, high risk tolerance, momentum strategies

### Worst-Case Testing
```python
stop_loss_pct=1.0        # 1% stop loss
take_profit_pct=2.0      # 2% take profit
slippage_probability=1.0 # 100% slippage
```
**Use for**: Stress testing, worst-case scenarios

## Understanding Risk/Reward Ratios

The **Risk/Reward Ratio** is calculated as:
```
Risk/Reward = Take Profit % ÷ Stop Loss %
```

**Examples:**
- 2% TP / 1% SL = **1:2 ratio** (risk $1 to make $2)
- 6% TP / 2% SL = **1:3 ratio** (risk $1 to make $3)
- 1% TP / 0.5% SL = **1:2 ratio** (risk $0.50 to make $1)

**Professional traders** typically target ratios of **1:2 or higher**.

## Slippage Impact Analysis

### No Slippage (0%)
All orders execute at expected price - **unrealistic** but useful for establishing a baseline.

### Low Slippage (10-20%)
Minimal impact - simulates good market conditions with high liquidity.

### Medium Slippage (30-40%)
Moderate impact - simulates normal market conditions.

### High Slippage (50-70%)
Significant impact - simulates volatile markets or low liquidity.

### Extreme Slippage (80-100%)
Maximum impact - simulates worst-case scenarios or highly volatile markets.

## Technical Details

### Slippage Implementation

When an order is placed:
1. Generate random number between 0 and 1
2. If random < slippage_probability:
   - Delay execution by `slippage_delay_bars`
   - Use price from delayed bar instead of current bar
3. Otherwise:
   - Execute at current bar price (no slippage)

### Profit/Loss Target Implementation

For **LONG** positions:
```python
entry_price = 100.0
stop_loss = entry_price * (1 - stop_loss_pct / 100)  # e.g., $99 for 1%
target = entry_price * (1 + take_profit_pct / 100)   # e.g., $102 for 2%
```

For **SHORT** positions:
```python
entry_price = 100.0
stop_loss = entry_price * (1 + stop_loss_pct / 100)  # e.g., $101 for 1%
target = entry_price * (1 - take_profit_pct / 100)   # e.g., $98 for 2%
```

## Demo Script

Run the demonstration script to see examples:

```bash
python scripts/demo_slippage_and_targets.py
```

This shows:
- How to configure slippage
- How to set profit/loss targets
- Comparison of aggressive vs conservative settings
- How to load configuration from YAML

## Files Modified

1. **config.yaml**: Added slippage and profit/loss target configuration
2. **gambler_ai/backtesting/backtest_engine.py**: Implemented slippage and target features
3. **scripts/simulation_race_engine.py**: Added parameter support
4. **scripts/simulation_race_ui.py**: Display simulation parameters
5. **scripts/simulation_configurator_ui.py**: New interactive configurator UI
6. **scripts/demo_slippage_and_targets.py**: Demonstration script

## Best Practices

1. **Start Conservative**: Begin with low risk parameters and gradually increase
2. **Test Multiple Scenarios**: Run simulations with different slippage levels
3. **Compare Results**: Use the same strategy with different parameters to see impact
4. **Document Settings**: Always note which parameters produced which results
5. **Realistic Slippage**: Use 20-40% slippage for realistic backtests
6. **Risk Management**: Never risk more than 1-2% per trade in real trading

## Troubleshooting

**Q: My results are worse with slippage enabled**
A: This is expected! Slippage simulates real-world conditions where not all orders execute perfectly.

**Q: Should I always use percentage targets?**
A: Yes, for most cases. Percentage targets scale with stock price, making them more flexible.

**Q: What slippage percentage should I use?**
A: Start with 30% for balanced testing. Use 50%+ for stress testing.

**Q: How do I disable slippage?**
A: Set `slippage_enabled=False` or `slippage_probability=0.0`

## Future Enhancements

Potential future additions:
- Variable slippage based on volatility
- Bid-ask spread simulation
- Partial fills
- Order rejection simulation
- Time-of-day slippage variation
- Trailing stop loss
- Dynamic position sizing based on volatility

## Support

For questions or issues:
1. Check the demo script: `scripts/demo_slippage_and_targets.py`
2. Review the configurator UI: `scripts/simulation_configurator_ui.py`
3. Check the configuration: `config.yaml`
4. Read the code comments in `gambler_ai/backtesting/backtest_engine.py`
