"""
Order synchronization module for keeping OrderJournal in sync with Alpaca API.

Handles:
- Tracking all order states (pending, filled, partial, canceled, expired, rejected)
- Logging terminal state details (cancellation timestamps, rejection reasons)
- Periodic sync of all orders, not just pending ones
- Recovery of manually-placed orders not created by the local system
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal

import requests

from gambler_ai.storage.models import OrderJournal
from gambler_ai.trading.state_manager import StateManager
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class OrderSynchronizer:
    """Synchronizes OrderJournal with Alpaca API order status."""

    def __init__(self, state_manager: StateManager, headers: Dict, base_url: str):
        """
        Initialize order synchronizer.

        Args:
            state_manager: StateManager instance for database updates
            headers: HTTP headers for Alpaca API (with auth)
            base_url: Alpaca API base URL
        """
        self.state_manager = state_manager
        self.headers = headers
        self.base_url = base_url
        self.log_prefix = "[ORDER_SYNC]"

    def sync_order_status(
        self,
        alpaca_order_id: str,
        order_info: Dict
    ) -> bool:
        """
        Synchronize a single order's status with the database.

        Args:
            alpaca_order_id: Order ID from Alpaca
            order_info: Order details from Alpaca API

        Returns:
            True if updated, False if no update needed
        """
        order_status = order_info.get('status')
        
        # Determine if this is a terminal state that needs logging
        if order_status in ['filled', 'partial', 'canceled', 'expired', 'rejected']:
            # Update order status in database
            self.state_manager.update_order_status(
                alpaca_order_id=alpaca_order_id,
                status=order_status,
                filled_qty=order_info.get('filled_qty'),
                filled_avg_price=order_info.get('filled_avg_price'),
                filled_at=order_info.get('filled_at'),
                rejection_reason=order_info.get('cancel_reason')
                    or order_info.get('legs')
                    or (order_info.get('rejected_reason') if order_status == 'rejected' else None)
            )
            return True
        
        return False

    def sync_pending_orders(self, pending_orders: Dict) -> Dict:
        """
        Sync all pending orders with latest status from Alpaca.

        Args:
            pending_orders: Dictionary of pending orders from trading system

        Returns:
            Updated pending_orders dict with terminal states removed
        """
        updated_pending = {}
        
        for symbol, order_data in pending_orders.items():
            order_id = order_data.get('order_id')
            if not order_id:
                updated_pending[symbol] = order_data
                continue

            # Get latest order info from Alpaca
            order_info = self._get_order(order_id)
            if not order_info:
                updated_pending[symbol] = order_data
                continue

            order_status = order_info.get('status')

            if order_status == 'filled':
                # Order filled - will be handled by check_positions()
                updated_pending[symbol] = order_data
                # Sync to database
                self.sync_order_status(order_id, order_info)

            elif order_status == 'pending':
                # Still pending - keep tracking
                updated_pending[symbol] = order_data

            elif order_status in ['canceled', 'expired', 'rejected']:
                # Terminal state - log and remove from pending
                logger.info(
                    f"{self.log_prefix} Order {order_status.upper()}: {symbol} "
                    f"(ID: {order_id[:8]})"
                )
                
                # IMPORTANT: Update database BEFORE removing from pending
                self.sync_order_status(order_id, order_info)
                
                # Remove from pending - don't keep tracking
                # Note: order was logged in sync_order_status()

            elif order_status == 'partial':
                # Partial fill - keep tracking, update database
                updated_pending[symbol] = order_data
                self.sync_order_status(order_id, order_info)
                logger.info(
                    f"{self.log_prefix} Order PARTIAL FILL: {symbol} "
                    f"({order_info.get('filled_qty')} of {order_data['qty']} shares)"
                )

        return updated_pending

    def sync_closed_positions(
        self,
        position_data: Dict,
        order_info: Dict
    ):
        """
        Sync details when a position is closed.

        Args:
            position_data: Position that was closed
            order_info: Order information from Alpaca
        """
        if not order_info:
            return

        # Update order journal with exit details
        self.state_manager.update_order_status(
            alpaca_order_id=position_data.get('order_id'),
            status=order_info.get('status'),
            filled_qty=order_info.get('filled_qty'),
            filled_avg_price=order_info.get('filled_avg_price'),
            filled_at=order_info.get('filled_at')
        )

        # If bracket order, check exit legs
        legs = order_info.get('legs', [])
        for leg_id in legs:
            leg_info = self._get_order(leg_id)
            if leg_info and leg_info.get('status') == 'filled':
                # This leg filled - log it
                self.state_manager.update_order_status(
                    alpaca_order_id=leg_id,
                    status='filled',
                    filled_qty=leg_info.get('filled_qty'),
                    filled_avg_price=leg_info.get('filled_avg_price'),
                    filled_at=leg_info.get('filled_at')
                )

    def recover_manual_orders(self, limit: int = 100) -> List[Dict]:
        """
        Recover orders placed manually in Alpaca UI (not via local system).

        Gets recent orders from Alpaca that:
        1. Are not already in OrderJournal
        2. Have a status other than 'pending'
        3. Were placed by the user account

        Args:
            limit: Maximum number of recent orders to check

        Returns:
            List of recovered orders
        """
        # Get recent orders from Alpaca
        alpaca_orders = self._get_all_orders(limit=limit)
        if not alpaca_orders:
            return []

        # Get orders already in our journal
        if not self.state_manager.db:
            return []

        existing_order_ids = set()
        try:
            existing = self.state_manager.db.query(OrderJournal).all()
            existing_order_ids = {o.alpaca_order_id for o in existing}
        except Exception as e:
            logger.warning(f"{self.log_prefix} Could not query existing orders: {e}")
            return []

        recovered = []

        for order in alpaca_orders:
            order_id = order.get('id')
            status = order.get('status')

            # Skip if already tracked
            if order_id in existing_order_ids:
                continue

            # Only recover terminal state orders
            if status not in ['filled', 'partial', 'canceled', 'expired', 'rejected']:
                continue

            recovered.append(order)

            # Log the recovered order
            try:
                self.state_manager.log_order(
                    alpaca_order_id=order_id,
                    symbol=order.get('symbol'),
                    order_type=order.get('order_type', 'unknown'),
                    side=order.get('side'),
                    quantity=float(order.get('qty', 0)),
                    status=status,
                    limit_price=float(order.get('limit_price')) if order.get('limit_price') else None,
                    stop_price=float(order.get('stop_price')) if order.get('stop_price') else None,
                    order_class=order.get('order_class'),
                    time_in_force=order.get('time_in_force')
                )

                logger.info(
                    f"{self.log_prefix} Recovered manual order: "
                    f"{order.get('symbol')} {order.get('side')} {order.get('qty')} "
                    f"(Status: {status})"
                )

            except Exception as e:
                logger.warning(
                    f"{self.log_prefix} Failed to log recovered order {order_id}: {e}"
                )

        return recovered

    def _get_order(self, order_id: str) -> Optional[Dict]:
        """Get single order from Alpaca API."""
        try:
            response = requests.get(
                f"{self.base_url}/v2/orders/{order_id}",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error getting order {order_id}: {e}")
            return None

    def _get_all_orders(
        self,
        status: str = None,
        limit: int = 100,
        nested: bool = True
    ) -> List[Dict]:
        """
        Get all orders from Alpaca API.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of orders
            nested: Include nested/bracket order details

        Returns:
            List of order dicts from Alpaca
        """
        try:
            params = {
                'limit': limit,
                'nested': nested
            }
            if status:
                params['status'] = status

            response = requests.get(
                f"{self.base_url}/v2/orders",
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            logger.warning(f"{self.log_prefix} Error getting all orders: {e}")
            return []
