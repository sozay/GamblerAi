# 🤖 Automated Trading Bot with Adaptive Strategy Selection

## What This Does

This trading bot automatically:
1. **Monitors** real-time market data via Alpaca WebSocket
2. **Detects** market regime (BULL/BEAR/RANGE) and volatility
3. **Selects** optimal strategy for current conditions
4. **Generates** trading signals
5. **Executes** trades with stop loss and take profit
6. **Manages** positions and risk

## Quick Start

### 1. Get Alpaca Paper Trading Account

1. Sign up at https://alpaca.markets/
2. Generate **Paper Trading** API keys
3. Copy your API Key and Secret

### 2. Set Credentials

```bash
export ALPACA_API_KEY="your_paper_trading_key"
export ALPACA_API_SECRET="your_paper_trading_secret"
```

Or create `.env` file:
```
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
```

### 3. Run the Bot

```bash
./run_trading_bot.sh
```

Or directly:
```bash
python trading_bot.py
```

## What You'll See

```
==========================================
Starting Automated Trading Bot
==========================================
Symbols: ['SPY', 'QQQ', 'AAPL', 'MSFT']
Max Position Size: $10,000.00
Risk Per Trade: 2.0%
Stop Loss: 3.0%
Take Profit: 6.0%
Paper Trading: True
==========================================

Account Status: ACTIVE
Buying Power: $100,000.00
Portfolio Value: $100,000.00

Connecting to real-time data stream...
Subscribing to ['SPY', 'QQQ', 'AAPL', 'MSFT']...

✓ Trading bot is LIVE!
Monitoring market and generating signals...
Press Ctrl+C to stop

🔄 SPY: Regime changed to BULL (confidence: 0.87)
📊 SPY: Switched to Multi-Timeframe strategy

🎯 SPY: Multi-Timeframe BUY Signal (Regime: BULL)
   Price: $450.25
   Quantity: 22 shares
   Position Value: $9,905.50
   Stop Loss: $436.74 (-3.0%)
   Take Profit: $477.27 (+6.0%)
✅ SPY: Order placed! (ID: order-123abc)
```

## Components

### 1. Real-Time Data Streaming

```python
from gambler_ai.data_ingestion import AlpacaWebSocketStreamer

streamer = AlpacaWebSocketStreamer()
streamer.connect()
streamer.subscribe_bars(["SPY", "QQQ"])
```

### 2. Market Regime Detection

```python
from gambler_ai.analysis.regime_detector import RegimeDetector

detector = RegimeDetector()
regime, confidence = detector.detect_regime_with_confidence(df)
# Returns: ('BULL', 0.87)
```

### 3. Adaptive Strategy Selection

```python
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector

selector = AdaptiveStrategySelector()
strategy_name, strategy = selector.select_strategy(df)
# Returns: ('Multi-Timeframe', <strategy_object>)
```

### 4. Order Execution with Risk Management

```python
from examples.alpaca_order_types_example import AlpacaTradingClient

client = AlpacaTradingClient()

# Place bracket order (entry + take profit + stop loss)
order = client.session.post(
    f"{client.base_url}/v2/orders",
    json={
        "symbol": "SPY",
        "qty": 22,
        "side": "buy",
        "type": "market",
        "order_class": "bracket",
        "take_profit": {"limit_price": "477.27"},
        "stop_loss": {"stop_price": "436.74"}
    }
)
```

## Strategy Selection Logic

The bot automatically picks the best strategy:

| Market Regime | Volatility | Strategy Selected | Why? |
|--------------|-----------|------------------|------|
| **BULL** | Low | Multi-Timeframe | Best smooth bull performer (+98.7%) |
| **BULL** | High | Mean Reversion | Choppy bulls favor mean reversion |
| **BEAR** | Any | Mean Reversion | Best bear performer (+74.4%) |
| **RANGE** | Any | Mean Reversion | Works well in sideways markets |

## Available Strategies

1. **Momentum** - Follows strong trends
   - Best in: Strong directional moves
   - Indicators: Price change, volume, trend

2. **Mean Reversion** - Profits from pullbacks
   - Best in: Choppy markets, bear markets
   - Indicators: RSI, support/resistance

3. **Volatility Breakout** - Captures explosive moves
   - Best in: High volatility periods
   - Indicators: ATR, price channels

4. **Multi-Timeframe** - Confirms across timeframes
   - Best in: Smooth bull markets
   - Indicators: Alignment across 5m, 15m, 1h

5. **Smart Money** - Follows institutional activity
   - Best in: All conditions
   - Indicators: Volume analysis, order flow

## Risk Management

Every trade includes:

### Position Sizing
```python
risk_amount = account_value * 0.02  # Risk 2%
position_size = risk_amount / stop_loss_pct
max_size = min(position_size, max_position_size)
```

### Stop Loss (Automatic)
```python
stop_loss_price = entry_price * (1 - 0.03)  # 3% stop
# If SPY bought at $450 → Stop at $436.50
```

### Take Profit (Automatic)
```python
take_profit_price = entry_price * (1 + 0.06)  # 6% profit
# If SPY bought at $450 → Target at $477
```

### Risk:Reward Ratio
```
Stop Loss: -3%
Take Profit: +6%
R:R = 1:2 (risk $1 to make $2)
```

## Configuration

Edit `trading_bot_config.yaml`:

```yaml
trading:
  symbols: ["SPY", "QQQ", "AAPL", "MSFT"]
  max_position_size: 10000.0
  risk_per_trade: 0.02
  stop_loss_pct: 0.03
  take_profit_pct: 0.06
```

## Files Created

### Core Bot
- `trading_bot.py` - Main trading bot
- `trading_bot_config.yaml` - Configuration
- `run_trading_bot.sh` - Quick start script

### Integration
- `gambler_ai/data_ingestion/alpaca_websocket_streamer.py` - Real-time data
- `gambler_ai/data_ingestion/alpaca_sse_streamer.py` - Event streaming
- `gambler_ai/analysis/adaptive_strategy.py` - Strategy selector
- `gambler_ai/analysis/regime_detector.py` - Market regime detection

### Examples
- `examples/alpaca_order_types_example.py` - Order types
- `examples/alpaca_streaming_example.py` - Streaming examples

### Documentation
- `docs/TRADING_BOT.md` - Full documentation
- `docs/ALPACA_STREAMING.md` - Streaming guide
- `docs/ORDER_TYPES.md` - Order types guide

### Testing
- `test_trading_capabilities.sh` - Test credentials
- `test_order_types.sh` - Test order placement
- `simple_test.py` - Basic API test

## Architecture

```
User
  │
  ├─> run_trading_bot.sh
  │     │
  │     └─> trading_bot.py
  │           │
  │           ├─> AlpacaWebSocketStreamer (real-time data)
  │           │     └─> Receives 1-min bars for SPY, QQQ, AAPL, MSFT
  │           │
  │           ├─> RegimeDetector (market analysis)
  │           │     └─> Determines BULL/BEAR/RANGE + volatility
  │           │
  │           ├─> AdaptiveStrategySelector (strategy picker)
  │           │     ├─> Momentum Strategy
  │           │     ├─> Mean Reversion Strategy
  │           │     ├─> Volatility Breakout Strategy
  │           │     ├─> Multi-Timeframe Strategy
  │           │     └─> Smart Money Strategy
  │           │
  │           └─> AlpacaTradingClient (order execution)
  │                 └─> Places bracket orders with stop loss/take profit
  │
  └─> Alpaca Paper Trading Account
        ├─> $100,000 virtual capital
        ├─> Real-time market data
        └─> Order execution simulation
```

## Example Trade Flow

```
14:30:00 - SPY bar received: $450.25
14:30:01 - Regime detected: BULL (confidence: 0.87)
14:30:02 - Strategy selected: Multi-Timeframe
14:30:03 - Signal generated: BUY
14:30:04 - Position calculated: 22 shares ($9,905)
14:30:05 - Order placed:
           • Entry: BUY 22 SPY @ market
           • Stop Loss: SELL 22 SPY @ $436.74
           • Take Profit: SELL 22 SPY @ $477.27
14:30:06 - Order filled: Entry @ $450.30
14:30:07 - Position active: Waiting for stop or target

... 2 hours later ...

16:45:00 - SPY price: $477.50
16:45:01 - Take profit triggered
16:45:02 - Position closed: SELL 22 SPY @ $477.27
16:45:03 - Profit: +$593.34 (+6.0%)
```

## Monitoring

The bot logs real-time updates:

```
📊 Status Update - 14:30:00
   Active Positions: 3
   Total Trades: 15

   Current Positions:
     SPY: +2.5% | Multi-Timeframe | BULL
     QQQ: +1.2% | Mean Reversion | BULL
     AAPL: -0.8% | Momentum | BULL
```

## Safety Features

✅ **Automatic Stop Loss** - Every trade protected
✅ **Position Limits** - Max 5 positions, $10k each
✅ **Risk Limits** - Max 2% risk per trade
✅ **Data Validation** - Needs 200 bars before trading
✅ **Error Handling** - Graceful failure, continues monitoring
✅ **Emergency Stop** - Ctrl+C closes all positions

## Performance Expectations

Based on backtests:
- **Win Rate**: 50-60%
- **Risk:Reward**: 1:2
- **Trades/Day**: 5-15 (depending on conditions)
- **Monthly Return**: Variable (market dependent)

## Important Notes

⚠️ **Paper Trading Only**
- This is for educational/testing purposes
- Uses $100,000 virtual capital
- No real money at risk

⚠️ **Requires Valid Credentials**
- Need working Alpaca API keys
- Default credentials in code don't work
- Get free paper trading account

⚠️ **Market Hours**
- Only trades 9:30 AM - 4:00 PM ET
- Bot can run 24/7, waits for market open

⚠️ **Not Investment Advice**
- For educational purposes only
- Past performance ≠ future results
- Use at your own risk

## Troubleshooting

**Bot won't start?**
- Check API credentials
- Run `./test_trading_capabilities.sh`

**No signals generated?**
- Wait for 200+ bars (200 minutes)
- Check if market is open
- Review logs for regime/strategy info

**Orders rejected?**
- Check buying power
- Verify symbol is tradable
- Confirm market hours

## Next Steps

1. ✅ Get Alpaca paper trading account
2. ✅ Generate API keys
3. ✅ Test credentials: `./test_trading_capabilities.sh`
4. ✅ Configure settings: `trading_bot_config.yaml`
5. ✅ Run bot: `./run_trading_bot.sh`
6. ✅ Monitor for 1 week
7. ✅ Review performance
8. ✅ Adjust parameters

## Support

- Full documentation: `docs/TRADING_BOT.md`
- Streaming guide: `docs/ALPACA_STREAMING.md`
- Order types: `docs/ORDER_TYPES.md`
- Examples: `examples/` directory

## Disclaimer

⚠️ **IMPORTANT**: This software is for educational and paper trading purposes only. Real trading involves significant risk. This is not investment advice. Use at your own risk.

---

Happy automated trading! 🚀📈
