#!/usr/bin/env python3
"""
Quick test script to verify Alpaca API credentials and streaming functionality.
"""

import time
import sys
from datetime import datetime

from gambler_ai.data_ingestion import AlpacaWebSocketStreamer, AlpacaSSEStreamer
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


def test_websocket_connection():
    """Test WebSocket connection and authentication."""
    logger.info("=" * 60)
    logger.info("Testing Alpaca WebSocket Connection")
    logger.info("=" * 60)

    try:
        # Initialize with default credentials
        streamer = AlpacaWebSocketStreamer()

        logger.info(f"Using API Key: {streamer.api_key[:10]}...")
        logger.info(f"Using Feed: {streamer.feed}")
        logger.info(f"Paper Trading: {streamer.paper}")

        # Track received messages
        received_messages = {
            "trades": [],
            "quotes": [],
            "bars": [],
        }

        def on_trade(trade):
            received_messages["trades"].append(trade)
            logger.info(f"✓ TRADE: {trade['S']} @ ${trade['p']:.2f} x {trade['s']} shares")

        def on_quote(quote):
            received_messages["quotes"].append(quote)
            logger.info(f"✓ QUOTE: {quote['S']} - Bid: ${quote.get('bp', 0):.2f} Ask: ${quote.get('ap', 0):.2f}")

        def on_bar(bar):
            received_messages["bars"].append(bar)
            logger.info(f"✓ BAR: {bar['S']} - Close: ${bar['c']:.2f} Volume: {bar['v']}")

        # Add handlers
        streamer.add_trade_handler(on_trade)
        streamer.add_quote_handler(on_quote)
        streamer.add_bar_handler(on_bar)

        # Connect
        logger.info("\nConnecting to WebSocket...")
        streamer.connect()

        if streamer.is_connected():
            logger.info("✓ Successfully connected and authenticated!")
        else:
            logger.error("✗ Failed to authenticate")
            return False

        # Subscribe to test symbols
        test_symbols = ["SPY", "AAPL"]
        logger.info(f"\nSubscribing to: {test_symbols}")

        streamer.subscribe_trades(test_symbols)
        streamer.subscribe_quotes(test_symbols)
        streamer.subscribe_bars(test_symbols)

        logger.info("✓ Subscriptions sent")

        # Stream for 30 seconds
        logger.info("\nStreaming data for 30 seconds...")
        logger.info("(Note: May not receive data if market is closed)")

        for i in range(30):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                logger.info(f"  {i + 1}s elapsed... (Trades: {len(received_messages['trades'])}, "
                          f"Quotes: {len(received_messages['quotes'])}, "
                          f"Bars: {len(received_messages['bars'])})")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary:")
        logger.info(f"  Trades received: {len(received_messages['trades'])}")
        logger.info(f"  Quotes received: {len(received_messages['quotes'])}")
        logger.info(f"  Bars received: {len(received_messages['bars'])}")

        total_messages = sum(len(v) for v in received_messages.values())

        if total_messages > 0:
            logger.info(f"\n✓ SUCCESS: Received {total_messages} total messages")
            success = True
        else:
            logger.warning("\n⚠ WARNING: No messages received (market may be closed)")
            success = True  # Still a success if connected

        # Disconnect
        logger.info("\nDisconnecting...")
        streamer.disconnect()
        logger.info("✓ Disconnected cleanly")

        return success

    except Exception as e:
        logger.error(f"\n✗ ERROR: {e}", exc_info=True)
        return False


def test_sse_connection():
    """Test SSE connection for account events."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Alpaca SSE Connection")
    logger.info("=" * 60)

    try:
        # Initialize with default credentials
        streamer = AlpacaSSEStreamer()

        logger.info(f"Using API Key: {streamer.api_key[:10]}...")
        logger.info(f"Base URL: {streamer.base_url}")

        # Track received events
        received_events = {
            "account": [],
            "trade": [],
        }

        def on_account_event(event):
            received_events["account"].append(event)
            logger.info(f"✓ ACCOUNT EVENT: {event}")

        def on_trade_event(event):
            received_events["trade"].append(event)
            logger.info(f"✓ TRADE EVENT: {event}")

        # Add handlers
        streamer.add_account_handler(on_account_event)
        streamer.add_trade_handler(on_trade_event)

        # Start streaming
        logger.info("\nStarting SSE streamer...")
        streamer.start()

        if streamer.is_running():
            logger.info("✓ SSE streamer started")
        else:
            logger.error("✗ Failed to start SSE streamer")
            return False

        # Subscribe to account events
        logger.info("\nSubscribing to account events...")
        streamer.subscribe_account_events(since=datetime.now().isoformat())
        logger.info("✓ Subscription sent")

        # Stream for 20 seconds
        logger.info("\nStreaming events for 20 seconds...")

        for i in range(20):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                logger.info(f"  {i + 1}s elapsed... (Account: {len(received_events['account'])}, "
                          f"Trade: {len(received_events['trade'])})")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary:")
        logger.info(f"  Account events: {len(received_events['account'])}")
        logger.info(f"  Trade events: {len(received_events['trade'])}")

        total_events = sum(len(v) for v in received_events.values())

        if total_events > 0:
            logger.info(f"\n✓ SUCCESS: Received {total_events} total events")
        else:
            logger.warning("\n⚠ WARNING: No events received (may be normal if no activity)")

        # Stop
        logger.info("\nStopping streamer...")
        streamer.stop()
        logger.info("✓ Stopped cleanly")

        return True

    except Exception as e:
        logger.error(f"\n✗ ERROR: {e}", exc_info=True)
        return False


def test_basic_api_access():
    """Test basic API access using requests."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Basic Alpaca API Access")
    logger.info("=" * 60)

    try:
        import requests

        api_key = "PKJUPGKDCCIMZKPDXUFXHM3E4D"
        api_secret = "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"
        base_url = "https://paper-api.alpaca.markets"

        # Test account endpoint
        logger.info("\nTesting account endpoint...")

        response = requests.get(
            f"{base_url}/v2/account",
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            }
        )

        logger.info(f"Response Status: {response.status_code}")

        if response.status_code == 200:
            account = response.json()
            logger.info("✓ Successfully authenticated!")
            logger.info(f"  Account ID: {account.get('id', 'N/A')}")
            logger.info(f"  Account Status: {account.get('status', 'N/A')}")
            logger.info(f"  Cash: ${float(account.get('cash', 0)):.2f}")
            logger.info(f"  Buying Power: ${float(account.get('buying_power', 0)):.2f}")
            logger.info(f"  Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")
            return True
        else:
            logger.error(f"✗ Authentication failed: {response.text}")
            return False

    except Exception as e:
        logger.error(f"\n✗ ERROR: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("Alpaca Streaming Test Suite")
    logger.info(f"Started at: {datetime.now()}")

    results = {}

    # Test 1: Basic API Access
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Basic API Access")
    logger.info("=" * 60)
    results["basic_api"] = test_basic_api_access()

    if not results["basic_api"]:
        logger.error("\n✗ Basic API test failed. Cannot proceed with streaming tests.")
        logger.error("Please verify your credentials are correct.")
        sys.exit(1)

    # Test 2: WebSocket Streaming
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: WebSocket Streaming")
    logger.info("=" * 60)
    results["websocket"] = test_websocket_connection()

    # Test 3: SSE Streaming
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: SSE Streaming")
    logger.info("=" * 60)
    results["sse"] = test_sse_connection()

    # Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL TEST RESULTS")
    logger.info("=" * 60)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {test_name:20s}: {status}")

    all_passed = all(results.values())

    if all_passed:
        logger.info("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.warning("\n⚠ Some tests failed")
        sys.exit(1)
