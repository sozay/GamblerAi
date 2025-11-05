# Alpaca Real-Time Streaming

This document describes the real-time streaming capabilities for GamblerAI using Alpaca Markets API.

## Overview

GamblerAI now supports real-time market data streaming from Alpaca Markets using two protocols:

1. **WebSocket** - Primary method for real-time market data (trades, quotes, bars)
2. **SSE (Server-Sent Events)** - For broker API events (trade updates, account status)

## Features

### WebSocket Streaming
- Real-time trade data
- Real-time quotes (bid/ask spreads)
- Real-time bars (minute-level OHLCV)
- Automatic reconnection on failure
- Multiple symbol subscriptions
- Custom event handlers
- Direct database integration

### SSE Streaming
- Trade event updates (with ULID support)
- Account status events
- Transfer status events
- Historical event replay
- Automatic reconnection
- Event queuing and async processing

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `alpaca-trade-api>=3.0.0`
- `websocket-client>=1.7.0`
- `requests>=2.31.0`

### 2. Configure API Credentials

Set environment variables:

```bash
export ALPACA_API_KEY="your_api_key"
export ALPACA_API_SECRET="your_api_secret"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"  # For paper trading
export ALPACA_DATA_FEED="iex"  # 'iex' for free tier, 'sip' for unlimited
```

Or update `config.yaml`:

```yaml
data_sources:
  alpaca:
    enabled: true
    api_key: ${ALPACA_API_KEY:}
    api_secret: ${ALPACA_API_SECRET:}
    base_url: ${ALPACA_BASE_URL:https://paper-api.alpaca.markets}
    data_feed: ${ALPACA_DATA_FEED:iex}
    paper_trading: true
```

### 3. Create `.env` file

```bash
# .env
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_FEED=iex
ALPACA_PAPER_TRADING=true
```

## Usage

### WebSocket Streaming

#### Basic Usage

```python
from gambler_ai.data_ingestion import AlpacaWebSocketStreamer

# Initialize streamer
streamer = AlpacaWebSocketStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
    feed="iex",  # 'iex' or 'sip'
    paper=True,
)

# Connect
streamer.connect()
streamer.start_processing()

# Subscribe to trades
streamer.subscribe_trades(["AAPL", "MSFT", "SPY"])

# Subscribe to quotes
streamer.subscribe_quotes(["AAPL", "MSFT"])

# Subscribe to bars (1-minute OHLCV)
streamer.subscribe_bars(["SPY"])

# Stream for a while
import time
time.sleep(60)

# Disconnect
streamer.disconnect()
```

#### With Custom Handlers

```python
from gambler_ai.data_ingestion import AlpacaWebSocketStreamer

def on_trade(trade):
    symbol = trade["S"]
    price = trade["p"]
    size = trade["s"]
    print(f"Trade: {symbol} @ ${price} x {size} shares")

def on_quote(quote):
    symbol = quote["S"]
    bid = quote["bp"]
    ask = quote["ap"]
    print(f"Quote: {symbol} - Bid: ${bid} Ask: ${ask}")

def on_bar(bar):
    symbol = bar["S"]
    close = bar["c"]
    volume = bar["v"]
    print(f"Bar: {symbol} - Close: ${close} Volume: {volume}")

# Initialize with handlers
streamer = AlpacaWebSocketStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
)

streamer.add_trade_handler(on_trade)
streamer.add_quote_handler(on_quote)
streamer.add_bar_handler(on_bar)

streamer.connect()
streamer.subscribe_trades(["AAPL"])
```

#### Using Context Manager

```python
from gambler_ai.data_ingestion import AlpacaWebSocketStreamer

with AlpacaWebSocketStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
    feed="iex",
) as streamer:
    streamer.subscribe_trades(["SPY", "QQQ"])

    # Add handlers
    streamer.add_trade_handler(lambda t: print(f"Trade: {t['S']} @ ${t['p']}"))

    # Stream for 60 seconds
    import time
    time.sleep(60)

# Automatically disconnected
```

### SSE Streaming

#### Basic Usage

```python
from gambler_ai.data_ingestion import AlpacaSSEStreamer
from datetime import datetime

# Initialize streamer
streamer = AlpacaSSEStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
    base_url="https://paper-api.alpaca.markets",
    paper=True,
)

# Start streaming
streamer.start()

# Subscribe to trade events
streamer.subscribe_trade_events(
    symbols=["AAPL", "MSFT"],
    since=datetime.now().isoformat(),
)

# Subscribe to account events
streamer.subscribe_account_events(
    since=datetime.now().isoformat(),
)

# Stream for a while
import time
time.sleep(60)

# Stop
streamer.stop()
```

#### With Custom Handlers

```python
from gambler_ai.data_ingestion import AlpacaSSEStreamer

def on_trade_event(event):
    print(f"Trade Event: {event}")

    if "order" in event:
        order = event["order"]
        print(f"Order Update: {order['symbol']} - Status: {order['status']}")

def on_account_event(event):
    print(f"Account Event: {event}")
    status = event.get("status", "unknown")
    print(f"Account Status: {status}")

streamer = AlpacaSSEStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
)

streamer.add_trade_handler(on_trade_event)
streamer.add_account_handler(on_account_event)

streamer.start()
streamer.subscribe_trade_events()
streamer.subscribe_account_events()
```

#### Using Context Manager

```python
from gambler_ai.data_ingestion import AlpacaSSEStreamer

with AlpacaSSEStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
) as streamer:
    streamer.subscribe_account_events()

    # Add handler
    streamer.add_account_handler(
        lambda e: print(f"Account: {e.get('status')}")
    )

    # Stream for 60 seconds
    import time
    time.sleep(60)

# Automatically stopped
```

## Data Storage

Both streamers automatically save received data to TimescaleDB:

- **Trades** → Saved as individual ticks with timeframe='tick'
- **Bars** → Saved as 1-minute OHLCV with timeframe='1min'
- **Real-time updates** → Upserted to avoid duplicates

Database schema:

```python
class StockPrice:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: str  # 'tick', '1min', '5min', etc.
```

## Event Formats

### WebSocket Trade Event

```json
{
  "T": "t",
  "S": "AAPL",
  "p": 150.50,
  "s": 100,
  "t": "2025-01-01T12:00:00Z",
  "x": "V",
  "i": 12345,
  "z": "C"
}
```

Fields:
- `T`: Message type ('t' for trade)
- `S`: Symbol
- `p`: Price
- `s`: Size (shares)
- `t`: Timestamp
- `x`: Exchange
- `i`: Trade ID
- `z`: Tape

### WebSocket Quote Event

```json
{
  "T": "q",
  "S": "AAPL",
  "bp": 150.45,
  "bs": 200,
  "ap": 150.55,
  "as": 100,
  "t": "2025-01-01T12:00:00Z"
}
```

Fields:
- `T`: Message type ('q' for quote)
- `S`: Symbol
- `bp`: Bid price
- `bs`: Bid size
- `ap`: Ask price
- `as`: Ask size
- `t`: Timestamp

### WebSocket Bar Event

```json
{
  "T": "b",
  "S": "AAPL",
  "o": 150.00,
  "h": 150.75,
  "l": 149.90,
  "c": 150.50,
  "v": 10000,
  "t": "2025-01-01T12:00:00Z"
}
```

Fields:
- `T`: Message type ('b' for bar)
- `S`: Symbol
- `o`: Open price
- `h`: High price
- `l`: Low price
- `c`: Close price
- `v`: Volume
- `t`: Timestamp

### SSE Trade Event

```json
{
  "id": "01JCXYZ123ABC",
  "event_type": "fill",
  "order": {
    "id": "order-123",
    "symbol": "AAPL",
    "qty": 10,
    "filled_qty": 10,
    "status": "filled",
    "filled_avg_price": 150.50
  },
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### SSE Account Event

```json
{
  "id": "01JCXYZ456DEF",
  "account_id": "account-123",
  "status": "ACTIVE",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## Error Handling

Both streamers implement automatic reconnection:

- **Exponential backoff**: Starts at 1s, doubles on each failure, max 60s
- **Connection monitoring**: Ping/pong to detect dead connections
- **Automatic resubscription**: Resubscribes to all channels after reconnect

Example with error handling:

```python
from gambler_ai.data_ingestion import AlpacaWebSocketStreamer
import time

streamer = AlpacaWebSocketStreamer(
    api_key="your_api_key",
    api_secret="your_api_secret",
)

try:
    streamer.connect()
    streamer.subscribe_trades(["AAPL"])

    # Stream indefinitely
    while True:
        time.sleep(1)

        # Check connection status
        if not streamer.is_connected():
            print("Connection lost, reconnecting...")

except KeyboardInterrupt:
    print("Interrupted by user")
finally:
    streamer.disconnect()
```

## Performance Considerations

### WebSocket
- **Throughput**: Can handle thousands of messages per second
- **Latency**: Sub-second latency for most events
- **Memory**: Message queue capped at 10,000 items
- **CPU**: Minimal overhead, runs in background threads

### SSE
- **Throughput**: Lower than WebSocket but sufficient for broker events
- **Latency**: 1-2 seconds typical
- **Memory**: Message queue capped at 10,000 items
- **Reconnection**: Automatic with exponential backoff

## Testing

Run integration tests:

```bash
# Set credentials
export ALPACA_API_KEY="your_key"
export ALPACA_API_SECRET="your_secret"

# Run tests
pytest tests/integration/test_alpaca_streaming.py -v

# Run only WebSocket tests
pytest tests/integration/test_alpaca_streaming.py::TestAlpacaWebSocketStreamer -v

# Run only SSE tests
pytest tests/integration/test_alpaca_streaming.py::TestAlpacaSSEStreamer -v
```

Note: Integration tests require valid Alpaca credentials and will be skipped if not provided.

## Examples

See `examples/alpaca_streaming_example.py` for complete examples:

```bash
# WebSocket example
python examples/alpaca_streaming_example.py websocket

# SSE example
python examples/alpaca_streaming_example.py sse

# Context manager example
python examples/alpaca_streaming_example.py context

# Custom processing example
python examples/alpaca_streaming_example.py custom
```

## Troubleshooting

### Connection Issues

**Problem**: WebSocket fails to authenticate

**Solution**: Verify your API credentials and base URL:
```python
# For paper trading
base_url = "https://paper-api.alpaca.markets"

# For live trading
base_url = "https://api.alpaca.markets"
```

**Problem**: No data received

**Solution**:
1. Check if market is open (9:30 AM - 4:00 PM ET)
2. Verify symbol subscriptions
3. Check data feed (IEX vs SIP)

### Performance Issues

**Problem**: High memory usage

**Solution**: Reduce queue size or process messages faster:
```python
streamer.message_queue = Queue(maxsize=1000)  # Reduce from 10000
```

**Problem**: Delayed messages

**Solution**: Check network latency and processing time in handlers

### Data Quality

**Problem**: Missing data points

**Solution**:
1. Check database write errors in logs
2. Verify TimescaleDB is running
3. Check disk space

**Problem**: Duplicate data

**Solution**: The streamers use upsert logic to handle duplicates automatically

## API Limits

### Free Tier (IEX)
- Market data from IEX exchange only
- No historical data via streaming
- No SIP data

### Unlimited Plan (SIP)
- Full market data (all exchanges)
- Consolidated tape
- Higher rate limits

### Rate Limits
- WebSocket: No explicit limits, but throttled if excessive
- SSE: No explicit limits
- API: 200 requests/minute for REST endpoints

## Security

### Best Practices
1. Never commit API keys to version control
2. Use environment variables or secure vaults
3. Rotate API keys regularly
4. Use paper trading for development
5. Implement proper error handling

### API Key Permissions
Ensure your API key has the following permissions:
- Market data streaming
- Account information (for SSE)
- Trading (if using trade events)

## References

- [Alpaca SSE Events Documentation](https://docs.alpaca.markets/docs/sse-events)
- [Alpaca WebSocket Streaming](https://docs.alpaca.markets/docs/streaming-market-data)
- [Alpaca API Documentation](https://docs.alpaca.markets/)

## License

This implementation is part of GamblerAI and follows the project's license.
