"""
Alpaca SSE (Server-Sent Events) real-time data streamer.

This module provides real-time streaming of trade events and account status
updates from Alpaca Markets using Server-Sent Events (SSE) protocol.
"""

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Thread, Event
from queue import Queue

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from gambler_ai.storage import StockPrice, get_timeseries_db
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class AlpacaSSEStreamer:
    """
    Alpaca SSE streamer for real-time market data and trade events.

    Supports:
    - Trade events (with ULID support for newer events)
    - Account status events
    - Transfer status events
    - Automatic reconnection on failures
    - Event replay from specific timestamps
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.alpaca.markets",
        paper: bool = True,
    ):
        """
        Initialize Alpaca SSE streamer.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Base URL for Alpaca API
            paper: Whether to use paper trading (default: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.paper = paper

        # Session with retry logic
        self.session = self._create_session()

        # Event handlers
        self.trade_handlers: List[Callable] = []
        self.account_handlers: List[Callable] = []
        self.order_handlers: List[Callable] = []

        # Control flags
        self._running = Event()
        self._threads: List[Thread] = []

        # Database connection for storing real-time data
        self.db = get_timeseries_db()

        # Message queue for async processing
        self.message_queue = Queue(maxsize=10000)

        # Track subscribed symbols
        self.subscribed_symbols: Set[str] = set()

        logger.info(f"Initialized Alpaca SSE streamer (paper={paper})")

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        })

        return session

    def subscribe_trade_events(
        self,
        symbols: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ):
        """
        Subscribe to trade events via SSE.

        Args:
            symbols: List of symbols to track (None = all)
            since: Start timestamp in RFC3339 format for historical events
            until: End timestamp in RFC3339 format (for historical only)
        """
        logger.info(f"Subscribing to trade events for symbols: {symbols}")

        if symbols:
            self.subscribed_symbols.update(symbols)

        # Build URL
        url = f"{self.base_url}/v2/events/trades"
        params = {}

        if since:
            params["since"] = since
        if until:
            params["until"] = until

        # Start streaming thread
        thread = Thread(
            target=self._stream_sse,
            args=(url, params, self._handle_trade_event),
            daemon=True,
        )
        thread.start()
        self._threads.append(thread)

    def subscribe_account_events(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ):
        """
        Subscribe to account status events via SSE.

        Args:
            since: Start timestamp for historical events
            until: End timestamp (for historical only)
        """
        logger.info("Subscribing to account status events")

        url = f"{self.base_url}/v2/events/accounts/status"
        params = {}

        if since:
            params["since"] = since
        if until:
            params["until"] = until

        thread = Thread(
            target=self._stream_sse,
            args=(url, params, self._handle_account_event),
            daemon=True,
        )
        thread.start()
        self._threads.append(thread)

    def _stream_sse(
        self,
        url: str,
        params: Dict[str, Any],
        handler: Callable,
    ):
        """
        Stream SSE events from Alpaca.

        Args:
            url: SSE endpoint URL
            params: Query parameters
            handler: Event handler function
        """
        retry_delay = 1
        max_retry_delay = 60

        while self._running.is_set():
            try:
                logger.info(f"Connecting to SSE endpoint: {url}")

                # Make streaming request
                with self.session.get(
                    url,
                    params=params,
                    stream=True,
                    timeout=(10, None),  # Connection timeout, no read timeout
                ) as response:
                    response.raise_for_status()

                    # Reset retry delay on successful connection
                    retry_delay = 1

                    logger.info("Successfully connected to SSE stream")

                    # Process events
                    for line in response.iter_lines(decode_unicode=True):
                        if not self._running.is_set():
                            break

                        if not line or line.startswith(":"):
                            # Skip empty lines and comments
                            continue

                        if line.startswith("data: "):
                            # Extract event data
                            data = line[6:]  # Remove "data: " prefix

                            try:
                                event = json.loads(data)
                                handler(event)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse SSE event: {e}")
                                continue

            except requests.exceptions.RequestException as e:
                if self._running.is_set():
                    logger.error(f"SSE connection error: {e}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

                    # Exponential backoff
                    retry_delay = min(retry_delay * 2, max_retry_delay)
            except Exception as e:
                logger.error(f"Unexpected error in SSE stream: {e}", exc_info=True)
                if self._running.is_set():
                    time.sleep(retry_delay)

        logger.info("SSE stream stopped")

    def _handle_trade_event(self, event: Dict[str, Any]):
        """
        Handle incoming trade event.

        Args:
            event: Trade event data
        """
        try:
            # Log event (for debugging)
            logger.debug(f"Trade event: {event}")

            # Add to queue for async processing
            self.message_queue.put(("trade", event))

            # Call registered handlers
            for handler in self.trade_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in trade handler: {e}", exc_info=True)

            # Save to database if it's a market data update
            if "symbol" in event and "price" in event:
                self._save_trade_to_db(event)

        except Exception as e:
            logger.error(f"Error handling trade event: {e}", exc_info=True)

    def _handle_account_event(self, event: Dict[str, Any]):
        """
        Handle incoming account status event.

        Args:
            event: Account event data
        """
        try:
            logger.info(f"Account event: {event.get('status', 'unknown')}")
            logger.debug(f"Account event details: {event}")

            # Add to queue
            self.message_queue.put(("account", event))

            # Call registered handlers
            for handler in self.account_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in account handler: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling account event: {e}", exc_info=True)

    def _save_trade_to_db(self, trade: Dict[str, Any]):
        """
        Save trade data to TimescaleDB.

        Args:
            trade: Trade event data
        """
        try:
            symbol = trade["symbol"]

            # Only save if we're tracking this symbol
            if self.subscribed_symbols and symbol not in self.subscribed_symbols:
                return

            # Extract trade data
            timestamp = datetime.fromisoformat(
                trade["timestamp"].replace("Z", "+00:00")
            )
            price = float(trade["price"])
            size = int(trade.get("size", 0))

            # Create a record (for real-time, we use the trade price as OHLC)
            record = {
                "symbol": symbol,
                "timestamp": timestamp,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
                "timeframe": "realtime",
            }

            # Save to database
            with self.db.get_session() as session:
                from sqlalchemy.dialects.postgresql import insert

                stmt = insert(StockPrice).values([record])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["symbol", "timestamp", "timeframe"],
                    set_={
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                    },
                )
                session.execute(stmt)

            logger.debug(f"Saved trade: {symbol} @ {price} ({size} shares)")

        except Exception as e:
            logger.error(f"Error saving trade to database: {e}", exc_info=True)

    def add_trade_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Add a custom handler for trade events.

        Args:
            handler: Callback function that receives trade events
        """
        self.trade_handlers.append(handler)
        logger.info(f"Added trade handler: {handler.__name__}")

    def add_account_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Add a custom handler for account events.

        Args:
            handler: Callback function that receives account events
        """
        self.account_handlers.append(handler)
        logger.info(f"Added account handler: {handler.__name__}")

    def start(self):
        """Start all SSE streams."""
        if self._running.is_set():
            logger.warning("Streamer is already running")
            return

        logger.info("Starting Alpaca SSE streamer...")
        self._running.set()

        # Start message processor thread
        processor = Thread(target=self._process_messages, daemon=True)
        processor.start()
        self._threads.append(processor)

    def stop(self):
        """Stop all SSE streams."""
        if not self._running.is_set():
            logger.warning("Streamer is not running")
            return

        logger.info("Stopping Alpaca SSE streamer...")
        self._running.clear()

        # Wait for threads to finish (with timeout)
        for thread in self._threads:
            thread.join(timeout=5)

        self._threads.clear()
        logger.info("Streamer stopped")

    def _process_messages(self):
        """Process messages from the queue."""
        logger.info("Message processor started")

        while self._running.is_set():
            try:
                # Get message with timeout
                msg_type, event = self.message_queue.get(timeout=1)

                # Process based on type
                if msg_type == "trade":
                    # Additional processing for trades
                    pass
                elif msg_type == "account":
                    # Additional processing for account events
                    pass

                self.message_queue.task_done()

            except Exception as e:
                if self._running.is_set():
                    logger.error(f"Error processing message: {e}", exc_info=True)

        logger.info("Message processor stopped")

    def is_running(self) -> bool:
        """Check if streamer is running."""
        return self._running.is_set()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
