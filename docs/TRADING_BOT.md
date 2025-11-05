# Automated Trading Bot

## Overview

This trading bot combines adaptive strategy selection with real-time market data to execute trades automatically on Alpaca's paper trading platform.

## Features

✅ **Adaptive Strategy Selection**
- Automatically detects market regime (BULL/BEAR/RANGE)
- Selects optimal strategy based on current conditions
- Switches strategies as market changes

✅ **Real-Time Trading**
- WebSocket streaming for live market data
- 1-minute bar analysis
- Instant signal generation

✅ **Risk Management**
- Automatic stop loss on every trade
- Take profit targets
- Position sizing based on risk
- Maximum exposure limits

✅ **Multiple Strategies**
- **Momentum**: Trend-following in strong markets
- **Mean Reversion**: Profit from pullbacks
- **Volatility Breakout**: Capture explosive moves
- **Multi-Timeframe**: Confirmation across timeframes
- **Smart Money**: Follow institutional activity

✅ **Paper Trading**
- Test strategies risk-free
- $100,000 virtual capital
- Real market data

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Alpaca WebSocket Streamer               │
│         (Real-time market data)                 │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│         Data Buffer (500 bars per symbol)       │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│         Regime Detector                         │
│         (BULL/BEAR/RANGE + Volatility)         │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│         Adaptive Strategy Selector              │
│         (Picks best strategy for regime)        │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│         Strategy Signal Generation              │
│         (BUY/SELL signals)                      │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│         Risk Manager                            │
│         (Position sizing, stop loss)            │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│         Order Execution                         │
│         (Bracket orders with stops)             │
└─────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Credentials

Edit `.env` file:
```bash
ALPACA_API_KEY=your_paper_trading_key
ALPACA_API_SECRET=your_paper_trading_secret
```

Or use the hardcoded defaults (will fail with 403 - need valid credentials).

### 3. Run the Bot

```bash
python trading_bot.py
```

### 4. Monitor

The bot will:
1. Connect to Alpaca WebSocket
2. Subscribe to real-time data for configured symbols
3. Detect market regime every minute
4. Generate trading signals
5. Execute trades with stop loss/take profit
6. Log all activity

## Configuration

Edit `trading_bot_config.yaml`:

```yaml
trading:
  symbols: ["SPY", "QQQ", "AAPL"]
  max_position_size: 10000.0     # Max $ per position
  risk_per_trade: 0.02           # Risk 2% per trade
  stop_loss_pct: 0.03            # 3% stop loss
  take_profit_pct: 0.06          # 6% take profit
```

## Trading Logic

### Regime Detection

The bot uses 200 EMA to detect market regime:

```python
Price > 200 EMA * 1.02  → BULL market
Price < 200 EMA * 0.98  → BEAR market
Otherwise               → RANGE market
```

Plus volatility detection:
```python
Daily volatility > 1.5%  → HIGH VOLATILITY
Otherwise                → LOW VOLATILITY
```

### Strategy Selection

Based on regime and volatility:

| Regime | Volatility | Strategy Selected |
|--------|-----------|------------------|
| BULL   | Low       | Multi-Timeframe  |
| BULL   | High      | Mean Reversion   |
| BEAR   | Any       | Mean Reversion   |
| RANGE  | Any       | Mean Reversion   |

### Signal Generation

Each strategy analyzes market data and generates signals:

**Example: Momentum Strategy**
```python
Signal = BUY when:
  - Price change > 2%
  - Volume > 2x average
  - Trend confirmed
```

**Example: Mean Reversion Strategy**
```python
Signal = BUY when:
  - RSI < 30 (oversold)
  - Price bouncing from support
  - Volume increasing
```

### Risk Management

Every trade includes:

1. **Position Sizing**
   ```python
   Risk Amount = Account Value × Risk Per Trade (2%)
   Position Size = Risk Amount / Stop Loss %
   Max Size = min(Position Size, Max Position Size)
   ```

2. **Stop Loss**
   ```python
   Stop Loss Price = Entry Price × (1 - Stop Loss %)
   Example: Entry $150 → Stop $145.50 (3% loss)
   ```

3. **Take Profit**
   ```python
   Take Profit Price = Entry Price × (1 + Take Profit %)
   Example: Entry $150 → Target $159 (6% profit)
   ```

4. **Bracket Order**
   ```python
   {
     "entry": Market buy,
     "take_profit": Limit sell at +6%,
     "stop_loss": Stop sell at -3%
   }
   ```

## Example Trade Flow

```
1. Bot receives 1-minute bar for SPY
   └─> Current price: $450.00

2. Regime Detection
   └─> SPY > 200 EMA × 1.02 → BULL market
   └─> Volatility: 1.2% → LOW volatility

3. Strategy Selection
   └─> BULL + LOW VOL → Multi-Timeframe Strategy

4. Signal Generation
   └─> Multi-Timeframe detects alignment
   └─> Signal: BUY

5. Risk Calculation
   └─> Account: $100,000
   └─> Risk per trade: 2% = $2,000
   └─> Stop loss: 3%
   └─> Position size: $2,000 / 0.03 = $66,666
   └─> Limited to max: $10,000
   └─> Shares: $10,000 / $450 = 22 shares

6. Order Placement
   └─> Entry: BUY 22 SPY @ market ($450.00)
   └─> Stop Loss: SELL 22 SPY @ $436.50 (-3%)
   └─> Take Profit: SELL 22 SPY @ $477.00 (+6%)

7. Outcome Scenarios
   A) Price → $477 → Take Profit Hit → +$594 (+6%)
   B) Price → $436.50 → Stop Loss Hit → -$297 (-3%)
   C) End of day → Close position
```

## Monitoring

The bot logs:

```
📊 Status Update - 14:30:00
   Active Positions: 3
   Total Trades: 15

   Current Positions:
     SPY: +2.5% | Multi-Timeframe | BULL
     QQQ: +1.2% | Mean Reversion | BULL
     AAPL: -0.8% | Momentum | BULL
```

Key events logged:
- 🔄 Regime changes
- 📊 Strategy switches
- 🎯 BUY signals generated
- ✅ Orders placed
- 📉 Positions closed
- ⚠️  Errors and warnings

## Performance Tracking

The bot tracks:
- Total trades executed
- Wins vs losses
- Win rate %
- Current P&L
- Daily P&L
- Risk exposure

## Safety Features

### Built-in Safeguards

1. **Maximum Position Size**
   - Limits $ amount per trade
   - Prevents over-exposure

2. **Stop Loss on Every Trade**
   - Automatic exit at loss limit
   - Protects capital

3. **Position Limits**
   - Max 5 concurrent positions
   - Max 50% total exposure

4. **Minimum Data Requirement**
   - Needs 200 bars before trading
   - Ensures quality signals

5. **Error Handling**
   - Graceful failure on API errors
   - Continues monitoring other symbols

### Emergency Stop

Press `Ctrl+C` to:
1. Stop accepting new signals
2. Close all open positions
3. Disconnect from data stream
4. Show performance summary

## Advanced Usage

### Custom Strategy

Create your own strategy:

```python
from gambler_ai.analysis.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def detect(self, df):
        # Your logic here
        signals = []
        # Generate BUY/SELL signals
        return pd.DataFrame(signals)

# Add to bot
bot.strategy_selector.strategies['My Strategy'] = MyStrategy()
```

### Multiple Symbols

Trade more symbols:

```python
bot = TradingBot(
    symbols=["SPY", "QQQ", "AAPL", "MSFT", "TSLA",
             "AMD", "NVDA", "GOOGL", "AMZN", "META"],
    max_positions=5  # Limit concurrent trades
)
```

### Aggressive Settings

More risk, more reward:

```python
bot = TradingBot(
    risk_per_trade=0.05,      # 5% risk per trade
    stop_loss_pct=0.05,       # 5% stop loss
    take_profit_pct=0.15,     # 15% take profit (3:1 R:R)
    max_position_size=20000   # Larger positions
)
```

### Conservative Settings

Lower risk:

```python
bot = TradingBot(
    risk_per_trade=0.01,      # 1% risk per trade
    stop_loss_pct=0.02,       # 2% stop loss
    take_profit_pct=0.04,     # 4% take profit (2:1 R:R)
    max_position_size=5000    # Smaller positions
)
```

## Troubleshooting

### Bot Won't Start

**Issue**: 403 Access Denied
**Solution**: Update API credentials in `.env`

```bash
ALPACA_API_KEY=your_real_key
ALPACA_API_SECRET=your_real_secret
```

### No Signals Generated

**Issue**: Bot monitors but doesn't trade
**Possible Causes**:
1. Not enough data yet (need 200 bars = 200 minutes)
2. No clear signals in current market
3. Already at max positions

**Solution**: Wait longer or check logs for regime/strategy info

### Orders Rejected

**Issue**: Orders fail to execute
**Possible Causes**:
1. Insufficient buying power
2. Symbol not tradable
3. Market closed

**Solution**: Check account status and market hours

### High CPU Usage

**Issue**: Bot uses lots of CPU
**Solution**: Reduce number of symbols or increase update interval

## Testing

### Paper Trading (Recommended)

Always test first:

```python
bot = TradingBot(
    paper_trading=True,  # ✅ Safe
    symbols=["SPY"]      # Start with one symbol
)
```

### Dry Run Mode

Test without placing orders:

```yaml
# trading_bot_config.yaml
safety:
  dry_run: true  # Generate signals but don't trade
```

### Backtest First

Before running live, backtest your settings:

```bash
python backtest_adaptive.py
```

## Best Practices

1. **Start Small**
   - Test with 1-2 symbols
   - Use small position sizes
   - Monitor closely

2. **Paper Trade First**
   - Run for at least 1 week
   - Verify performance
   - Understand behavior

3. **Check Daily**
   - Review trades
   - Check P&L
   - Adjust if needed

4. **Risk Management**
   - Never risk more than 2% per trade
   - Keep stop losses tight
   - Don't override safety limits

5. **Market Conditions**
   - Bot performs differently in different regimes
   - Monitor regime changes
   - Some periods may have few trades

## Limitations

- **Paper Trading Only**: This implementation is for paper trading
- **Requires Valid Credentials**: Need working Alpaca API keys
- **Market Hours**: Only works during market hours (9:30 AM - 4:00 PM ET)
- **Data Lag**: WebSocket data has ~1 second latency
- **Execution**: Paper trading fills may differ from live
- **Strategies**: Pre-built strategies may not fit all markets

## FAQ

**Q: Can I run this with real money?**
A: This is designed for paper trading. DO NOT use with live money without extensive testing and modifications.

**Q: What's the expected win rate?**
A: Backtests show 50-60% win rate with 2:1 risk:reward. Live results will vary.

**Q: How many trades per day?**
A: Depends on market conditions. Typically 5-15 trades per day across all symbols.

**Q: Does it work in all market conditions?**
A: No strategy works in all conditions. The adaptive approach helps but isn't perfect.

**Q: Can I leave it running overnight?**
A: Yes, but it only trades during market hours. It will wait for market open.

## Support

- **Documentation**: See `/docs` folder
- **Examples**: See `/examples` folder
- **Issues**: Check logs for detailed error messages

## Disclaimer

⚠️ **IMPORTANT**: This is educational software for paper trading only. Trading involves risk. Past performance doesn't guarantee future results. Use at your own risk.

## Next Steps

1. ✅ Get valid Alpaca paper trading credentials
2. ✅ Test with `./test_trading_capabilities.sh`
3. ✅ Configure `trading_bot_config.yaml`
4. ✅ Run `python trading_bot.py`
5. ✅ Monitor for 1 week
6. ✅ Analyze results
7. ✅ Adjust settings as needed

Happy trading! 🚀
