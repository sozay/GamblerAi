"""
Alpaca WebSocket real-time market data streamer.

This module provides real-time streaming of market data from Alpaca Markets
using WebSocket protocol. This is the primary method for streaming market data.
"""

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Thread, Event
from queue import Queue

import websocket

from gambler_ai.storage import StockPrice, get_timeseries_db
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class AlpacaWebSocketStreamer:
    """
    Alpaca WebSocket streamer for real-time market data.

    Supports:
    - Real-time trades
    - Real-time quotes (bid/ask)
    - Real-time bars (minute/daily aggregates)
    - Automatic reconnection on failures
    - Multiple symbol subscriptions
    """

    # WebSocket URLs
    MARKET_DATA_URL = "wss://stream.data.alpaca.markets/v2/{feed}"
    TRADING_URL = "wss://paper-api.alpaca.markets/stream"

    def __init__(
        self,
        api_key: str = "PKJUPGKDCCIMZKPDXUFXHM3E4D",
        api_secret: str = "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H",
        feed: str = "iex",  # 'iex' or 'sip'
        paper: bool = True,
    ):
        """
        Initialize Alpaca WebSocket streamer.

        Args:
            api_key: Alpaca API key (default: hardcoded test key)
            api_secret: Alpaca API secret (default: hardcoded test secret)
            feed: Data feed ('iex' for free tier, 'sip' for unlimited)
            paper: Whether to use paper trading (default: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.feed = feed
        self.paper = paper

        # WebSocket connection
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[Thread] = None

        # Event handlers
        self.trade_handlers: List[Callable] = []
        self.quote_handlers: List[Callable] = []
        self.bar_handlers: List[Callable] = []

        # Control flags
        self._running = Event()
        self._authenticated = Event()

        # Subscriptions
        self.subscribed_trades: Set[str] = set()
        self.subscribed_quotes: Set[str] = set()
        self.subscribed_bars: Set[str] = set()

        # Database connection
        self.db = get_timeseries_db()

        # Message queue
        self.message_queue = Queue(maxsize=10000)
        self.processor_thread: Optional[Thread] = None

        logger.info(f"Initialized Alpaca WebSocket streamer (feed={feed}, paper={paper})")

    def connect(self):
        """Establish WebSocket connection."""
        if self.ws is not None:
            logger.warning("WebSocket already connected")
            return

        url = self.MARKET_DATA_URL.format(feed=self.feed)
        logger.info(f"Connecting to WebSocket: {url}")

        self.ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        # Start WebSocket in a separate thread
        self._running.set()
        self.ws_thread = Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()

        # Wait for authentication
        if not self._authenticated.wait(timeout=10):
            raise TimeoutError("WebSocket authentication timeout")

        logger.info("WebSocket connected and authenticated")

    def _run_websocket(self):
        """Run WebSocket connection with auto-reconnect."""
        retry_delay = 1
        max_retry_delay = 60

        while self._running.is_set():
            try:
                self.ws.run_forever(
                    ping_interval=30,
                    ping_timeout=10,
                )

                # If we get here, connection was closed
                if self._running.is_set():
                    logger.warning(f"WebSocket disconnected, reconnecting in {retry_delay}s...")
                    time.sleep(retry_delay)

                    # Exponential backoff
                    retry_delay = min(retry_delay * 2, max_retry_delay)

                    # Reset connection
                    self._authenticated.clear()
                    self.ws = None

            except Exception as e:
                if self._running.is_set():
                    logger.error(f"WebSocket error: {e}", exc_info=True)
                    time.sleep(retry_delay)

    def _on_open(self, ws):
        """Handle WebSocket connection opened."""
        logger.info("WebSocket connection opened")

        # Send authentication
        auth_msg = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.api_secret,
        }

        ws.send(json.dumps(auth_msg))
        logger.debug("Sent authentication message")

    def _on_message(self, ws, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)

            # Handle different message types
            for msg in data if isinstance(data, list) else [data]:
                msg_type = msg.get("T")

                if msg_type == "success":
                    if msg.get("msg") == "authenticated":
                        logger.info("WebSocket authenticated successfully")
                        self._authenticated.set()

                        # Resubscribe to channels if reconnecting
                        self._resubscribe()

                elif msg_type == "error":
                    logger.error(f"WebSocket error message: {msg}")

                elif msg_type == "subscription":
                    logger.info(f"Subscription confirmed: {msg}")

                elif msg_type == "t":
                    # Trade update
                    self._handle_trade(msg)

                elif msg_type == "q":
                    # Quote update
                    self._handle_quote(msg)

                elif msg_type == "b":
                    # Bar update
                    self._handle_bar(msg)

                else:
                    logger.debug(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}", exc_info=True)

    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed."""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self._authenticated.clear()

    def _resubscribe(self):
        """Resubscribe to all channels after reconnection."""
        if self.subscribed_trades:
            self._subscribe("trades", list(self.subscribed_trades))

        if self.subscribed_quotes:
            self._subscribe("quotes", list(self.subscribed_quotes))

        if self.subscribed_bars:
            self._subscribe("bars", list(self.subscribed_bars))

    def _subscribe(self, channel: str, symbols: List[str]):
        """
        Subscribe to a channel for specific symbols.

        Args:
            channel: Channel name ('trades', 'quotes', 'bars')
            symbols: List of symbols to subscribe to
        """
        if not self.ws or not self._authenticated.is_set():
            logger.warning("Cannot subscribe: WebSocket not authenticated")
            return

        msg = {
            "action": "subscribe",
            channel: symbols,
        }

        self.ws.send(json.dumps(msg))
        logger.info(f"Subscribed to {channel}: {symbols}")

    def subscribe_trades(self, symbols: List[str]):
        """
        Subscribe to real-time trades for symbols.

        Args:
            symbols: List of stock symbols
        """
        self.subscribed_trades.update(symbols)
        self._subscribe("trades", symbols)

    def subscribe_quotes(self, symbols: List[str]):
        """
        Subscribe to real-time quotes (bid/ask) for symbols.

        Args:
            symbols: List of stock symbols
        """
        self.subscribed_quotes.update(symbols)
        self._subscribe("quotes", symbols)

    def subscribe_bars(self, symbols: List[str]):
        """
        Subscribe to real-time bars (minute aggregates) for symbols.

        Args:
            symbols: List of stock symbols
        """
        self.subscribed_bars.update(symbols)
        self._subscribe("bars", symbols)

    def unsubscribe_trades(self, symbols: List[str]):
        """Unsubscribe from trades."""
        self.subscribed_trades.difference_update(symbols)
        if self.ws:
            msg = {"action": "unsubscribe", "trades": symbols}
            self.ws.send(json.dumps(msg))

    def unsubscribe_quotes(self, symbols: List[str]):
        """Unsubscribe from quotes."""
        self.subscribed_quotes.difference_update(symbols)
        if self.ws:
            msg = {"action": "unsubscribe", "quotes": symbols}
            self.ws.send(json.dumps(msg))

    def unsubscribe_bars(self, symbols: List[str]):
        """Unsubscribe from bars."""
        self.subscribed_bars.difference_update(symbols)
        if self.ws:
            msg = {"action": "unsubscribe", "bars": symbols}
            self.ws.send(json.dumps(msg))

    def _handle_trade(self, trade: Dict[str, Any]):
        """Handle trade update."""
        try:
            symbol = trade["S"]

            # Add to queue
            self.message_queue.put(("trade", trade))

            # Call custom handlers
            for handler in self.trade_handlers:
                try:
                    handler(trade)
                except Exception as e:
                    logger.error(f"Error in trade handler: {e}", exc_info=True)

            # Save to database
            self._save_trade_to_db(trade)

        except Exception as e:
            logger.error(f"Error handling trade: {e}", exc_info=True)

    def _handle_quote(self, quote: Dict[str, Any]):
        """Handle quote update."""
        try:
            # Add to queue
            self.message_queue.put(("quote", quote))

            # Call custom handlers
            for handler in self.quote_handlers:
                try:
                    handler(quote)
                except Exception as e:
                    logger.error(f"Error in quote handler: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling quote: {e}", exc_info=True)

    def _handle_bar(self, bar: Dict[str, Any]):
        """Handle bar update."""
        try:
            # Add to queue
            self.message_queue.put(("bar", bar))

            # Call custom handlers
            for handler in self.bar_handlers:
                try:
                    handler(bar)
                except Exception as e:
                    logger.error(f"Error in bar handler: {e}", exc_info=True)

            # Save to database
            self._save_bar_to_db(bar)

        except Exception as e:
            logger.error(f"Error handling bar: {e}", exc_info=True)

    def _save_trade_to_db(self, trade: Dict[str, Any]):
        """Save trade to database."""
        try:
            symbol = trade["S"]
            price = float(trade["p"])
            size = int(trade["s"])
            timestamp = datetime.fromisoformat(trade["t"].replace("Z", "+00:00"))

            record = {
                "symbol": symbol,
                "timestamp": timestamp,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
                "timeframe": "tick",
            }

            with self.db.get_session() as session:
                from sqlalchemy.dialects.postgresql import insert

                stmt = insert(StockPrice).values([record])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "timestamp", "timeframe"],
                    set_={
                        "close": stmt.excluded.close,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "volume": stmt.excluded.volume,
                    },
                )
                session.execute(stmt)

        except Exception as e:
            logger.error(f"Error saving trade to DB: {e}", exc_info=True)

    def _save_bar_to_db(self, bar: Dict[str, Any]):
        """Save bar (OHLCV) to database."""
        try:
            symbol = bar["S"]
            timestamp = datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))

            record = {
                "symbol": symbol,
                "timestamp": timestamp,
                "open": float(bar["o"]),
                "high": float(bar["h"]),
                "low": float(bar["l"]),
                "close": float(bar["c"]),
                "volume": int(bar["v"]),
                "timeframe": "1min",
            }

            with self.db.get_session() as session:
                from sqlalchemy.dialects.postgresql import insert

                stmt = insert(StockPrice).values([record])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "timestamp", "timeframe"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                    },
                )
                session.execute(stmt)

            logger.debug(f"Saved bar: {symbol} @ {timestamp}")

        except Exception as e:
            logger.error(f"Error saving bar to DB: {e}", exc_info=True)

    def add_trade_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add custom trade handler."""
        self.trade_handlers.append(handler)

    def add_quote_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add custom quote handler."""
        self.quote_handlers.append(handler)

    def add_bar_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add custom bar handler."""
        self.bar_handlers.append(handler)

    def start_processing(self):
        """Start message processing thread."""
        if self.processor_thread is not None:
            logger.warning("Processor already running")
            return

        self.processor_thread = Thread(target=self._process_messages, daemon=True)
        self.processor_thread.start()
        logger.info("Message processor started")

    def _process_messages(self):
        """Process messages from queue."""
        while self._running.is_set():
            try:
                msg_type, data = self.message_queue.get(timeout=1)
                # Additional processing can be done here
                self.message_queue.task_done()
            except:
                continue

    def disconnect(self):
        """Disconnect WebSocket."""
        logger.info("Disconnecting WebSocket...")
        self._running.clear()

        if self.ws:
            self.ws.close()

        if self.ws_thread:
            self.ws_thread.join(timeout=5)

        if self.processor_thread:
            self.processor_thread.join(timeout=5)

        logger.info("WebSocket disconnected")

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._authenticated.is_set()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.start_processing()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
