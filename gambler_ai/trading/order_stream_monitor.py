"""
Real-time order monitoring using Alpaca WebSocket streaming.

This module listens to Alpaca trade updates in real-time and automatically
handles order status changes (filled, canceled, expired) without polling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, Optional

from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL

logger = logging.getLogger(__name__)


class OrderStreamMonitor:
    """
    Real-time order monitoring via Alpaca WebSocket.

    Receives instant notifications when orders change status:
    - filled
    - canceled
    - expired
    - rejected
    - partially_filled
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = 'https://paper-api.alpaca.markets',
        on_order_update: Optional[Callable] = None,
        on_trade_update: Optional[Callable] = None
    ):
        """
        Initialize order stream monitor.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: API base URL
            on_order_update: Callback function(order_data) when order updates
            on_trade_update: Callback function(trade_data) when trade executes
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

        # Callbacks
        self.on_order_update = on_order_update
        self.on_trade_update = on_trade_update

        # Stream instance
        self.stream = None
        self._running = False

    def _create_stream(self):
        """Create Alpaca stream instance."""
        # Determine base URL type
        if 'paper' in self.base_url:
            base_url_enum = URL('https://paper-api.alpaca.markets')
        else:
            base_url_enum = URL('https://api.alpaca.markets')

        self.stream = Stream(
            self.api_key,
            self.api_secret,
            base_url=base_url_enum,
            data_feed='iex'  # or 'sip' for full feed
        )

    async def _handle_trade_update(self, data):
        """
        Handle trade update from WebSocket.

        Trade updates include:
        - new: Order placed
        - fill: Order filled
        - partial_fill: Order partially filled
        - canceled: Order canceled
        - expired: Order expired
        - rejected: Order rejected
        - replaced: Order replaced
        - pending_new: Order pending
        - stopped: Order stopped
        - pending_cancel: Cancel pending
        - pending_replace: Replace pending
        - calculated: Calculated (for bracket orders)
        """
        event = data.event
        order = data.order

        logger.info(f"Trade Update: {event} - {order.get('symbol')} - Status: {order.get('status')}")

        # Extract relevant order info
        order_info = {
            'event': event,
            'order_id': order.get('id'),
            'client_order_id': order.get('client_order_id'),
            'symbol': order.get('symbol'),
            'side': order.get('side'),
            'order_type': order.get('order_type'),
            'qty': order.get('qty'),
            'filled_qty': order.get('filled_qty'),
            'filled_avg_price': order.get('filled_avg_price'),
            'status': order.get('status'),
            'submitted_at': order.get('submitted_at'),
            'filled_at': order.get('filled_at'),
            'canceled_at': order.get('canceled_at'),
            'expired_at': order.get('expired_at'),
            'order_class': order.get('order_class'),
            'legs': order.get('legs', []),
            'timestamp': datetime.now()
        }

        # Handle specific events
        if event == 'fill':
            logger.info(f"✓ ORDER FILLED: {order_info['symbol']} - {order_info['filled_qty']} @ ${order_info['filled_avg_price']}")
            if self.on_order_update:
                await self._safe_callback(self.on_order_update, order_info)

        elif event == 'partial_fill':
            logger.info(f"◐ ORDER PARTIALLY FILLED: {order_info['symbol']} - {order_info['filled_qty']}/{order_info['qty']}")
            if self.on_order_update:
                await self._safe_callback(self.on_order_update, order_info)

        elif event == 'canceled':
            logger.warning(f"✗ ORDER CANCELED: {order_info['symbol']}")
            if self.on_order_update:
                await self._safe_callback(self.on_order_update, order_info)

        elif event == 'expired':
            logger.warning(f"⏰ ORDER EXPIRED: {order_info['symbol']}")
            if self.on_order_update:
                await self._safe_callback(self.on_order_update, order_info)

        elif event == 'rejected':
            logger.error(f"✗ ORDER REJECTED: {order_info['symbol']} - Reason: {order.get('reject_reason')}")
            if self.on_order_update:
                await self._safe_callback(self.on_order_update, order_info)

        elif event == 'new':
            logger.info(f"➜ NEW ORDER: {order_info['symbol']} - {order_info['side']} {order_info['qty']}")
            if self.on_order_update:
                await self._safe_callback(self.on_order_update, order_info)

    async def _safe_callback(self, callback, data):
        """Safely execute callback with error handling."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Error in callback: {e}", exc_info=True)

    async def start(self):
        """Start listening to trade updates."""
        if self._running:
            logger.warning("Stream already running")
            return

        logger.info("Starting Alpaca trade update stream...")

        # Create stream
        self._create_stream()

        # Subscribe to trade updates
        self.stream.subscribe_trade_updates(self._handle_trade_update)

        self._running = True

        try:
            # Run the stream
            await self.stream._run_forever()
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            self._running = False
            raise

    async def stop(self):
        """Stop listening to trade updates."""
        if not self._running:
            return

        logger.info("Stopping Alpaca trade update stream...")

        if self.stream:
            await self.stream.stop_ws()

        self._running = False
        logger.info("Stream stopped")

    def is_running(self):
        """Check if stream is running."""
        return self._running


class OrderEventHandler:
    """
    Handler for order events that integrates with trading system.

    This class receives real-time order updates and automatically:
    - Updates database
    - Recreates expired exit orders
    - Logs to order journal
    - Updates position tracking
    """

    def __init__(self, trader):
        """
        Initialize event handler.

        Args:
            trader: AlpacaPaperTrader instance
        """
        self.trader = trader
        self.log_prefix = trader.log_prefix if hasattr(trader, 'log_prefix') else "[STREAM]"

    def handle_order_update(self, order_info: Dict):
        """
        Handle order update event.

        Args:
            order_info: Order information from WebSocket
        """
        event = order_info['event']
        symbol = order_info['symbol']
        status = order_info['status']
        order_id = order_info['order_id']

        # Handle filled orders
        if event == 'fill' and symbol in self.trader.pending_orders:
            self._handle_order_filled(order_info)

        # Handle canceled/expired orders
        elif event in ['canceled', 'expired'] and symbol in self.trader.pending_orders:
            self._handle_order_canceled_or_expired(order_info)

        # Handle expired exit orders for active positions
        elif event in ['canceled', 'expired']:
            self._handle_exit_order_expired(order_info)

    def _handle_order_filled(self, order_info: Dict):
        """Handle order fill event."""
        symbol = order_info['symbol']

        if symbol not in self.trader.pending_orders:
            return

        order_data = self.trader.pending_orders[symbol]

        print(f"\n{self.log_prefix} 🔔 REAL-TIME: Order FILLED - {symbol}")
        print(f"{self.log_prefix}    Price: ${order_info['filled_avg_price']}")
        print(f"{self.log_prefix}    Quantity: {order_info['filled_qty']}")

        # Move to active positions
        position_data = {
            'symbol': symbol,
            'entry_time': order_data['entry_time'],
            'entry_price': float(order_info['filled_avg_price']),
            'qty': int(order_info['filled_qty']),
            'direction': order_data['direction'],
            'side': order_data['side'],
            'stop_loss': order_data['stop_loss'],
            'take_profit': order_data['take_profit'],
            'order_id': order_info['order_id'],
            'transaction_id': None,
        }

        self.trader.active_positions[symbol] = position_data
        del self.trader.pending_orders[symbol]

        # Save to database
        if self.trader.enable_persistence:
            self.trader._save_position(symbol, position_data)

    def _handle_order_canceled_or_expired(self, order_info: Dict):
        """Handle order canceled or expired event."""
        symbol = order_info['symbol']
        event = order_info['event']

        print(f"\n{self.log_prefix} 🔔 REAL-TIME: Order {event.upper()} - {symbol}")

        # Remove from pending
        if symbol in self.trader.pending_orders:
            # Sync to database
            if self.trader.enable_persistence and hasattr(self.trader, 'order_sync'):
                self.trader.order_sync.sync_order_status(
                    order_info['order_id'],
                    order_info
                )

            del self.trader.pending_orders[symbol]

    def _handle_exit_order_expired(self, order_info: Dict):
        """Handle expired exit order for active position."""
        symbol = order_info['symbol']

        # Check if this is an exit order for an active position
        if symbol not in self.trader.active_positions:
            return

        pos = self.trader.active_positions[symbol]

        # Check if this order is part of the position's bracket
        if not pos.get('order_id'):
            return

        print(f"\n{self.log_prefix} 🔔 REAL-TIME: Exit order {order_info['event'].upper()} - {symbol}")
        print(f"{self.log_prefix}    Checking if position needs new exit orders...")

        # Check if position still has active exit orders
        has_exit_orders, exit_details = self.trader.check_exit_orders_status(pos['order_id'])

        if not has_exit_orders:
            print(f"{self.log_prefix}    ⚠ Position has NO active exit orders!")

            # Recreate exit orders
            if self.trader.recreate_exit_orders(symbol, pos):
                print(f"{self.log_prefix}    ✓ New exit orders created")
            else:
                print(f"{self.log_prefix}    ✗ Failed to create exit orders - POSITION AT RISK!")


# Example usage
async def example_usage():
    """Example of how to use the order stream monitor."""
    import os

    # Your API credentials
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')

    # Callback function
    def on_order_update(order_info):
        print(f"Order Update: {order_info['event']} - {order_info['symbol']} - {order_info['status']}")

    # Create monitor
    monitor = OrderStreamMonitor(
        api_key=api_key,
        api_secret=api_secret,
        on_order_update=on_order_update
    )

    try:
        # Start monitoring (runs forever)
        await monitor.start()
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        await monitor.stop()


if __name__ == '__main__':
    # Run example
    asyncio.run(example_usage())
