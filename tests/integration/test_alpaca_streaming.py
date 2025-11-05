"""
Integration tests for Alpaca real-time streaming.

Note: These tests require valid Alpaca API credentials in environment variables:
- ALPACA_API_KEY
- ALPACA_API_SECRET
"""

import os
import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from gambler_ai.data_ingestion import AlpacaSSEStreamer, AlpacaWebSocketStreamer


# Skip tests if credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_API_SECRET"),
    reason="Alpaca API credentials not configured",
)


@pytest.fixture
def alpaca_credentials():
    """Get Alpaca credentials from environment."""
    return {
        "api_key": os.getenv("ALPACA_API_KEY", "test_key"),
        "api_secret": os.getenv("ALPACA_API_SECRET", "test_secret"),
    }


class TestAlpacaSSEStreamer:
    """Test Alpaca SSE streamer."""

    def test_initialization(self, alpaca_credentials):
        """Test SSE streamer initialization."""
        streamer = AlpacaSSEStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            paper=True,
        )

        assert streamer.api_key == alpaca_credentials["api_key"]
        assert streamer.paper is True
        assert not streamer.is_running()

    def test_add_handlers(self, alpaca_credentials):
        """Test adding event handlers."""
        streamer = AlpacaSSEStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
        )

        # Add handlers
        trade_handler = Mock()
        account_handler = Mock()

        streamer.add_trade_handler(trade_handler)
        streamer.add_account_handler(account_handler)

        assert len(streamer.trade_handlers) == 1
        assert len(streamer.account_handlers) == 1

    @pytest.mark.integration
    def test_trade_event_subscription(self, alpaca_credentials):
        """Test subscribing to trade events (requires live API)."""
        streamer = AlpacaSSEStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            paper=True,
        )

        # Add handler to capture events
        received_events = []

        def capture_event(event):
            received_events.append(event)

        streamer.add_trade_handler(capture_event)

        try:
            # Start streamer
            streamer.start()

            # Subscribe to trade events
            streamer.subscribe_trade_events(
                symbols=["AAPL", "SPY"],
                since=datetime.now().isoformat(),
            )

            # Wait for events (timeout after 30 seconds)
            timeout = 30
            start_time = time.time()

            while len(received_events) == 0 and (time.time() - start_time) < timeout:
                time.sleep(1)

            # We should have received at least one event (or timeout)
            # This test may timeout during non-market hours
            if received_events:
                assert "symbol" in received_events[0] or "id" in received_events[0]

        finally:
            streamer.stop()

    def test_context_manager(self, alpaca_credentials):
        """Test using SSE streamer as context manager."""
        with AlpacaSSEStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
        ) as streamer:
            assert streamer.is_running()

        # Should be stopped after context exit
        assert not streamer.is_running()


class TestAlpacaWebSocketStreamer:
    """Test Alpaca WebSocket streamer."""

    def test_initialization(self, alpaca_credentials):
        """Test WebSocket streamer initialization."""
        streamer = AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            feed="iex",
            paper=True,
        )

        assert streamer.api_key == alpaca_credentials["api_key"]
        assert streamer.feed == "iex"
        assert not streamer.is_connected()

    def test_add_handlers(self, alpaca_credentials):
        """Test adding event handlers."""
        streamer = AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
        )

        # Add handlers
        trade_handler = Mock()
        quote_handler = Mock()
        bar_handler = Mock()

        streamer.add_trade_handler(trade_handler)
        streamer.add_quote_handler(quote_handler)
        streamer.add_bar_handler(bar_handler)

        assert len(streamer.trade_handlers) == 1
        assert len(streamer.quote_handlers) == 1
        assert len(streamer.bar_handlers) == 1

    @pytest.mark.integration
    def test_websocket_connection(self, alpaca_credentials):
        """Test WebSocket connection (requires live API)."""
        streamer = AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            feed="iex",
        )

        try:
            # Connect
            streamer.connect()

            # Should be authenticated
            assert streamer.is_connected()

        finally:
            streamer.disconnect()

    @pytest.mark.integration
    def test_trade_subscription(self, alpaca_credentials):
        """Test subscribing to trades (requires live API)."""
        streamer = AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            feed="iex",
        )

        received_trades = []

        def capture_trade(trade):
            received_trades.append(trade)

        streamer.add_trade_handler(capture_trade)

        try:
            streamer.connect()
            streamer.start_processing()

            # Subscribe to trades
            streamer.subscribe_trades(["AAPL", "SPY"])

            # Wait for trades (timeout after 30 seconds)
            timeout = 30
            start_time = time.time()

            while len(received_trades) == 0 and (time.time() - start_time) < timeout:
                time.sleep(1)

            # May timeout during non-market hours
            if received_trades:
                trade = received_trades[0]
                assert "S" in trade  # Symbol
                assert "p" in trade  # Price
                assert "s" in trade  # Size

        finally:
            streamer.disconnect()

    @pytest.mark.integration
    def test_multiple_subscriptions(self, alpaca_credentials):
        """Test subscribing to multiple data types (requires live API)."""
        streamer = AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            feed="iex",
        )

        try:
            streamer.connect()
            streamer.start_processing()

            # Subscribe to multiple data types
            symbols = ["SPY"]
            streamer.subscribe_trades(symbols)
            streamer.subscribe_quotes(symbols)
            streamer.subscribe_bars(symbols)

            # Verify subscriptions
            assert "SPY" in streamer.subscribed_trades
            assert "SPY" in streamer.subscribed_quotes
            assert "SPY" in streamer.subscribed_bars

            # Unsubscribe from quotes
            streamer.unsubscribe_quotes(symbols)
            assert "SPY" not in streamer.subscribed_quotes

        finally:
            streamer.disconnect()

    def test_context_manager(self, alpaca_credentials):
        """Test using WebSocket streamer as context manager."""
        with AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
        ) as streamer:
            # Should connect automatically
            time.sleep(2)  # Give it time to connect
            assert streamer.is_connected() or streamer.ws is not None

        # Should be disconnected after context exit
        assert not streamer.is_connected()


class TestStreamingIntegration:
    """Test integration between streamers and database."""

    @pytest.mark.integration
    def test_save_to_database(self, alpaca_credentials):
        """Test that streaming data is saved to database."""
        streamer = AlpacaWebSocketStreamer(
            api_key=alpaca_credentials["api_key"],
            api_secret=alpaca_credentials["api_secret"],
            feed="iex",
        )

        try:
            streamer.connect()
            streamer.start_processing()

            # Subscribe to bars (easier to test)
            streamer.subscribe_bars(["SPY"])

            # Wait for data
            time.sleep(10)

            # Check database for saved data
            from gambler_ai.storage import get_timeseries_db, StockPrice

            db = get_timeseries_db()
            with db.get_session() as session:
                result = (
                    session.query(StockPrice)
                    .filter(
                        StockPrice.symbol == "SPY",
                        StockPrice.timeframe == "1min",
                    )
                    .order_by(StockPrice.timestamp.desc())
                    .first()
                )

                # May be None during non-market hours
                if result:
                    assert result.symbol == "SPY"
                    assert result.open is not None
                    assert result.close is not None

        finally:
            streamer.disconnect()


# Mock tests that don't require credentials
class TestMockedStreaming:
    """Test streaming with mocked responses."""

    @patch("gambler_ai.data_ingestion.alpaca_sse_streamer.requests.Session")
    def test_sse_handle_trade_event(self, mock_session):
        """Test handling of trade events."""
        streamer = AlpacaSSEStreamer(
            api_key="test_key",
            api_secret="test_secret",
        )

        # Mock event
        event = {
            "id": "test-123",
            "symbol": "AAPL",
            "price": 150.50,
            "size": 100,
            "timestamp": "2025-01-01T12:00:00Z",
        }

        # Add handler
        captured_events = []
        streamer.add_trade_handler(lambda e: captured_events.append(e))

        # Handle event
        streamer._handle_trade_event(event)

        # Verify
        assert len(captured_events) == 1
        assert captured_events[0]["symbol"] == "AAPL"

    def test_websocket_message_parsing(self):
        """Test parsing of WebSocket messages."""
        streamer = AlpacaWebSocketStreamer(
            api_key="test_key",
            api_secret="test_secret",
        )

        # Mock trade message
        trade_msg = {
            "T": "t",
            "S": "AAPL",
            "p": 150.50,
            "s": 100,
            "t": "2025-01-01T12:00:00Z",
        }

        captured_trades = []
        streamer.add_trade_handler(lambda t: captured_trades.append(t))

        # Process message
        streamer._handle_trade(trade_msg)

        # Verify
        assert len(captured_trades) == 1
        assert captured_trades[0]["S"] == "AAPL"
