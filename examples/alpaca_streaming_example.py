"""
Example usage of Alpaca real-time streaming.

This script demonstrates how to use both WebSocket and SSE streaming
from Alpaca Markets to receive real-time market data and trade events.
"""

import os
import time
from datetime import datetime

from gambler_ai.data_ingestion import AlpacaSSEStreamer, AlpacaWebSocketStreamer
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


def example_websocket_streaming():
    """
    Example: Real-time market data streaming via WebSocket.

    This is the primary method for streaming real-time market data
    including trades, quotes, and bars.
    """
    logger.info("=== WebSocket Streaming Example ===")

    # Get credentials from environment
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Please set ALPACA_API_KEY and ALPACA_API_SECRET environment variables")
        return

    # Initialize streamer
    streamer = AlpacaWebSocketStreamer(
        api_key=api_key,
        api_secret=api_secret,
        feed="iex",  # Use 'iex' for free tier, 'sip' for unlimited
        paper=True,
    )

    # Define custom handlers
    def on_trade(trade):
        """Handle incoming trade."""
        symbol = trade["S"]
        price = trade["p"]
        size = trade["s"]
        timestamp = trade["t"]

        logger.info(f"Trade: {symbol} @ ${price:.2f} x {size} shares at {timestamp}")

    def on_quote(quote):
        """Handle incoming quote."""
        symbol = quote["S"]
        bid = quote.get("bp", 0)
        ask = quote.get("ap", 0)
        spread = ask - bid if ask > 0 and bid > 0 else 0

        logger.info(f"Quote: {symbol} - Bid: ${bid:.2f} Ask: ${ask:.2f} Spread: ${spread:.2f}")

    def on_bar(bar):
        """Handle incoming bar (1-minute OHLCV)."""
        symbol = bar["S"]
        open_price = bar["o"]
        high = bar["h"]
        low = bar["l"]
        close = bar["c"]
        volume = bar["v"]

        logger.info(
            f"Bar: {symbol} - O: ${open_price:.2f} H: ${high:.2f} "
            f"L: ${low:.2f} C: ${close:.2f} V: {volume}"
        )

    # Register handlers
    streamer.add_trade_handler(on_trade)
    streamer.add_quote_handler(on_quote)
    streamer.add_bar_handler(on_bar)

    try:
        # Connect to WebSocket
        streamer.connect()
        streamer.start_processing()

        # Subscribe to data streams
        symbols = ["AAPL", "MSFT", "SPY"]

        logger.info(f"Subscribing to trades for: {symbols}")
        streamer.subscribe_trades(symbols)

        logger.info(f"Subscribing to quotes for: {symbols}")
        streamer.subscribe_quotes(symbols)

        logger.info(f"Subscribing to bars for: {symbols}")
        streamer.subscribe_bars(symbols)

        # Stream for 60 seconds
        logger.info("Streaming data for 60 seconds...")
        time.sleep(60)

        # Unsubscribe from quotes (example)
        logger.info("Unsubscribing from quotes...")
        streamer.unsubscribe_quotes(symbols)

        # Continue streaming trades and bars
        time.sleep(30)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Clean up
        logger.info("Disconnecting...")
        streamer.disconnect()


def example_sse_streaming():
    """
    Example: Trade events and account status via SSE.

    SSE is used for broker API events including trade updates,
    account status changes, and transfer updates.
    """
    logger.info("=== SSE Streaming Example ===")

    # Get credentials from environment
    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Please set ALPACA_API_KEY and ALPACA_API_SECRET environment variables")
        return

    # Initialize SSE streamer
    streamer = AlpacaSSEStreamer(
        api_key=api_key,
        api_secret=api_secret,
        base_url="https://paper-api.alpaca.markets",
        paper=True,
    )

    # Define event handlers
    def on_trade_event(event):
        """Handle trade event from broker."""
        logger.info(f"Trade Event: {event}")

        # Process trade update
        if "order" in event:
            order = event["order"]
            logger.info(
                f"Order Update: {order.get('symbol')} - "
                f"Status: {order.get('status')} - "
                f"Filled: {order.get('filled_qty', 0)}/{order.get('qty', 0)}"
            )

    def on_account_event(event):
        """Handle account status event."""
        logger.info(f"Account Event: {event}")

        # Process account update
        status = event.get("status", "unknown")
        logger.info(f"Account Status: {status}")

    # Register handlers
    streamer.add_trade_handler(on_trade_event)
    streamer.add_account_handler(on_account_event)

    try:
        # Start streaming
        streamer.start()

        # Subscribe to trade events
        logger.info("Subscribing to trade events...")
        streamer.subscribe_trade_events(
            symbols=["AAPL", "MSFT"],
            since=datetime.now().isoformat(),
        )

        # Subscribe to account events
        logger.info("Subscribing to account status events...")
        streamer.subscribe_account_events(
            since=datetime.now().isoformat(),
        )

        # Stream for 60 seconds
        logger.info("Streaming events for 60 seconds...")
        time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Clean up
        logger.info("Stopping streamer...")
        streamer.stop()


def example_context_manager():
    """
    Example: Using streamers as context managers.

    This ensures proper cleanup even if errors occur.
    """
    logger.info("=== Context Manager Example ===")

    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Please set ALPACA_API_KEY and ALPACA_API_SECRET environment variables")
        return

    # WebSocket with context manager
    logger.info("Using WebSocket streamer as context manager...")

    with AlpacaWebSocketStreamer(
        api_key=api_key,
        api_secret=api_secret,
        feed="iex",
    ) as ws_streamer:
        ws_streamer.subscribe_trades(["SPY"])

        # Add simple handler
        ws_streamer.add_trade_handler(
            lambda t: logger.info(f"Trade: {t['S']} @ ${t['p']}")
        )

        logger.info("Streaming for 30 seconds...")
        time.sleep(30)

    # Automatically disconnected when exiting context

    logger.info("WebSocket disconnected")

    # SSE with context manager
    logger.info("Using SSE streamer as context manager...")

    with AlpacaSSEStreamer(
        api_key=api_key,
        api_secret=api_secret,
        paper=True,
    ) as sse_streamer:
        sse_streamer.add_account_handler(
            lambda e: logger.info(f"Account event: {e.get('status')}")
        )

        sse_streamer.subscribe_account_events()

        logger.info("Streaming for 30 seconds...")
        time.sleep(30)

    # Automatically stopped when exiting context

    logger.info("SSE streamer stopped")


def example_custom_processing():
    """
    Example: Custom processing of streaming data.

    This shows how to implement custom logic for handling
    streaming data, such as calculating indicators or
    triggering alerts.
    """
    logger.info("=== Custom Processing Example ===")

    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Please set ALPACA_API_KEY and ALPACA_API_SECRET environment variables")
        return

    # Track prices for momentum detection
    price_history = {}

    def detect_momentum(trade):
        """Detect price momentum from trades."""
        symbol = trade["S"]
        price = trade["p"]

        if symbol not in price_history:
            price_history[symbol] = []

        # Keep last 20 prices
        price_history[symbol].append(price)
        if len(price_history[symbol]) > 20:
            price_history[symbol].pop(0)

        # Calculate momentum (simple % change)
        if len(price_history[symbol]) >= 2:
            old_price = price_history[symbol][0]
            change_pct = ((price - old_price) / old_price) * 100

            if abs(change_pct) > 1.0:  # Significant move
                logger.warning(
                    f"MOMENTUM DETECTED: {symbol} moved {change_pct:.2f}% "
                    f"(from ${old_price:.2f} to ${price:.2f})"
                )

    with AlpacaWebSocketStreamer(
        api_key=api_key,
        api_secret=api_secret,
        feed="iex",
    ) as streamer:
        # Add momentum detector
        streamer.add_trade_handler(detect_momentum)

        # Subscribe to high-volume stocks
        symbols = ["AAPL", "MSFT", "TSLA", "SPY", "QQQ"]
        streamer.subscribe_trades(symbols)

        logger.info(f"Monitoring momentum for: {symbols}")
        logger.info("Streaming for 120 seconds...")

        try:
            time.sleep(120)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")

    logger.info("Done")


if __name__ == "__main__":
    # Choose which example to run
    import sys

    if len(sys.argv) < 2:
        print("Usage: python alpaca_streaming_example.py [websocket|sse|context|custom]")
        print("\nExamples:")
        print("  websocket - Real-time market data via WebSocket")
        print("  sse       - Trade events via SSE")
        print("  context   - Using context managers")
        print("  custom    - Custom processing example")
        sys.exit(1)

    example = sys.argv[1].lower()

    if example == "websocket":
        example_websocket_streaming()
    elif example == "sse":
        example_sse_streaming()
    elif example == "context":
        example_context_manager()
    elif example == "custom":
        example_custom_processing()
    else:
        print(f"Unknown example: {example}")
        sys.exit(1)
