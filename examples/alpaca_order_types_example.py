#!/usr/bin/env python3
"""
Alpaca Order Types Examples - Including Stop Loss and Stop Limit

This script demonstrates how to place different order types on Alpaca paper trading:
- Market orders
- Limit orders
- Stop loss orders
- Stop limit orders
- Trailing stop orders
"""

import os
import json
import requests
from datetime import datetime


class AlpacaTradingClient:
    """Simple client for placing orders on Alpaca paper trading."""

    def __init__(
        self,
        api_key: str = "PKJUPGKDCCIMZKPDXUFXHM3E4D",
        api_secret: str = "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H",
        base_url: str = "https://paper-api.alpaca.markets",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = self._create_session()

    def _create_session(self):
        """Create requests session with auth headers."""
        session = requests.Session()
        session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        })
        return session

    def get_account(self):
        """Get account information."""
        response = self.session.get(f"{self.base_url}/v2/account")
        response.raise_for_status()
        return response.json()

    def get_positions(self):
        """Get all open positions."""
        response = self.session.get(f"{self.base_url}/v2/positions")
        response.raise_for_status()
        return response.json()

    def get_orders(self, status="all"):
        """Get orders."""
        response = self.session.get(
            f"{self.base_url}/v2/orders",
            params={"status": status}
        )
        response.raise_for_status()
        return response.json()

    def place_market_order(self, symbol: str, qty: int, side: str = "buy"):
        """
        Place a market order.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Number of shares
            side: 'buy' or 'sell'
        """
        order = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }

        response = self.session.post(
            f"{self.base_url}/v2/orders",
            json=order
        )
        response.raise_for_status()
        return response.json()

    def place_limit_order(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        side: str = "buy",
    ):
        """
        Place a limit order.

        Args:
            symbol: Stock symbol
            qty: Number of shares
            limit_price: Limit price
            side: 'buy' or 'sell'
        """
        order = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "limit",
            "limit_price": limit_price,
            "time_in_force": "day",
        }

        response = self.session.post(
            f"{self.base_url}/v2/orders",
            json=order
        )
        response.raise_for_status()
        return response.json()

    def place_stop_loss_order(
        self,
        symbol: str,
        qty: int,
        stop_price: float,
        side: str = "sell",
    ):
        """
        Place a stop loss order.

        This triggers a market order when the stock reaches the stop price.

        Args:
            symbol: Stock symbol
            qty: Number of shares
            stop_price: Price at which to trigger the stop loss
            side: Usually 'sell' for stop loss
        """
        order = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "stop",
            "stop_price": stop_price,
            "time_in_force": "gtc",  # Good till canceled
        }

        response = self.session.post(
            f"{self.base_url}/v2/orders",
            json=order
        )
        response.raise_for_status()
        return response.json()

    def place_stop_limit_order(
        self,
        symbol: str,
        qty: int,
        stop_price: float,
        limit_price: float,
        side: str = "sell",
    ):
        """
        Place a stop limit order.

        This triggers a limit order when the stock reaches the stop price.

        Args:
            symbol: Stock symbol
            qty: Number of shares
            stop_price: Price at which to trigger the order
            limit_price: Limit price for the triggered order
            side: Usually 'sell' for stop limit
        """
        order = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "stop_limit",
            "stop_price": stop_price,
            "limit_price": limit_price,
            "time_in_force": "gtc",
        }

        response = self.session.post(
            f"{self.base_url}/v2/orders",
            json=order
        )
        response.raise_for_status()
        return response.json()

    def place_trailing_stop_order(
        self,
        symbol: str,
        qty: int,
        trail_percent: float,
        side: str = "sell",
    ):
        """
        Place a trailing stop order.

        The stop price trails the market price by a percentage.

        Args:
            symbol: Stock symbol
            qty: Number of shares
            trail_percent: Trailing percentage (e.g., 5.0 for 5%)
            side: Usually 'sell' for trailing stop
        """
        order = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "trailing_stop",
            "trail_percent": trail_percent,
            "time_in_force": "gtc",
        }

        response = self.session.post(
            f"{self.base_url}/v2/orders",
            json=order
        )
        response.raise_for_status()
        return response.json()

    def cancel_order(self, order_id: str):
        """Cancel an order."""
        response = self.session.delete(f"{self.base_url}/v2/orders/{order_id}")
        response.raise_for_status()
        return True

    def get_order(self, order_id: str):
        """Get order details."""
        response = self.session.get(f"{self.base_url}/v2/orders/{order_id}")
        response.raise_for_status()
        return response.json()


# ============================================================================
# EXAMPLES
# ============================================================================

def example_market_order():
    """Example: Place a simple market order."""
    print("\n" + "=" * 60)
    print("Example 1: Market Order")
    print("=" * 60)

    client = AlpacaTradingClient()

    try:
        # Get account info first
        account = client.get_account()
        print(f"Account cash: ${float(account['cash']):.2f}")
        print(f"Buying power: ${float(account['buying_power']):.2f}")

        # Place market order
        print("\nPlacing market order: BUY 1 AAPL")
        order = client.place_market_order("AAPL", 1, "buy")

        print(f"✓ Order placed!")
        print(f"  Order ID: {order['id']}")
        print(f"  Status: {order['status']}")
        print(f"  Symbol: {order['symbol']}")
        print(f"  Quantity: {order['qty']}")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_limit_order():
    """Example: Place a limit order."""
    print("\n" + "=" * 60)
    print("Example 2: Limit Order")
    print("=" * 60)

    client = AlpacaTradingClient()

    try:
        # Place limit order to buy AAPL at $150
        print("\nPlacing limit order: BUY 1 AAPL @ $150.00")
        order = client.place_limit_order("AAPL", 1, 150.00, "buy")

        print(f"✓ Order placed!")
        print(f"  Order ID: {order['id']}")
        print(f"  Status: {order['status']}")
        print(f"  Limit Price: ${order['limit_price']}")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_stop_loss_order():
    """Example: Place a stop loss order."""
    print("\n" + "=" * 60)
    print("Example 3: Stop Loss Order")
    print("=" * 60)
    print("Use case: Protect profits or limit losses on existing position")

    client = AlpacaTradingClient()

    try:
        # First, buy a stock
        print("\nStep 1: Buy 1 share of AAPL (market order)")
        buy_order = client.place_market_order("AAPL", 1, "buy")
        print(f"✓ Bought 1 AAPL (Order ID: {buy_order['id']})")

        # Then place stop loss at $145
        print("\nStep 2: Place stop loss at $145.00")
        print("(If AAPL drops to $145, sell at market)")
        stop_order = client.place_stop_loss_order("AAPL", 1, 145.00, "sell")

        print(f"✓ Stop loss placed!")
        print(f"  Order ID: {stop_order['id']}")
        print(f"  Status: {stop_order['status']}")
        print(f"  Stop Price: ${stop_order['stop_price']}")
        print(f"  Time in Force: {stop_order['time_in_force']}")
        print("\n  → Will sell AAPL if price drops to $145")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_stop_limit_order():
    """Example: Place a stop limit order."""
    print("\n" + "=" * 60)
    print("Example 4: Stop Limit Order")
    print("=" * 60)
    print("Use case: More control than stop loss, but may not fill")

    client = AlpacaTradingClient()

    try:
        # First, buy a stock
        print("\nStep 1: Buy 1 share of SPY (market order)")
        buy_order = client.place_market_order("SPY", 1, "buy")
        print(f"✓ Bought 1 SPY (Order ID: {buy_order['id']})")

        # Then place stop limit
        print("\nStep 2: Place stop limit")
        print("  Stop Price: $450.00 (trigger)")
        print("  Limit Price: $449.00 (minimum sell price)")
        stop_limit = client.place_stop_limit_order(
            "SPY", 1, 450.00, 449.00, "sell"
        )

        print(f"✓ Stop limit placed!")
        print(f"  Order ID: {stop_limit['id']}")
        print(f"  Status: {stop_limit['status']}")
        print(f"  Stop Price: ${stop_limit['stop_price']}")
        print(f"  Limit Price: ${stop_limit['limit_price']}")
        print("\n  → If SPY drops to $450, try to sell at $449 or better")
        print("  → May not fill if price drops too fast")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_trailing_stop_order():
    """Example: Place a trailing stop order."""
    print("\n" + "=" * 60)
    print("Example 5: Trailing Stop Order")
    print("=" * 60)
    print("Use case: Lock in profits as stock rises")

    client = AlpacaTradingClient()

    try:
        # First, buy a stock
        print("\nStep 1: Buy 1 share of TSLA (market order)")
        buy_order = client.place_market_order("TSLA", 1, "buy")
        print(f"✓ Bought 1 TSLA (Order ID: {buy_order['id']})")

        # Then place trailing stop
        print("\nStep 2: Place trailing stop at 5%")
        trailing = client.place_trailing_stop_order("TSLA", 1, 5.0, "sell")

        print(f"✓ Trailing stop placed!")
        print(f"  Order ID: {trailing['id']}")
        print(f"  Status: {trailing['status']}")
        print(f"  Trail Percent: {trailing['trail_percent']}%")
        print("\n  → Stop price trails the market by 5%")
        print("  → If TSLA goes up, stop price rises with it")
        print("  → If TSLA drops 5% from highest, sell at market")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_bracket_order():
    """Example: Bracket order with take profit and stop loss."""
    print("\n" + "=" * 60)
    print("Example 6: Bracket Order (Take Profit + Stop Loss)")
    print("=" * 60)
    print("Use case: Set both profit target and loss limit")

    client = AlpacaTradingClient()

    try:
        # Bracket orders are supported via order nesting
        print("\nPlacing bracket order for AAPL:")
        print("  Entry: Market buy 1 share")
        print("  Take Profit: Sell at $160")
        print("  Stop Loss: Sell at $145")

        order = {
            "symbol": "AAPL",
            "qty": 1,
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit": {
                "limit_price": 160.00
            },
            "stop_loss": {
                "stop_price": 145.00
            }
        }

        response = client.session.post(
            f"{client.base_url}/v2/orders",
            json=order
        )
        response.raise_for_status()
        result = response.json()

        print(f"✓ Bracket order placed!")
        print(f"  Entry Order ID: {result['id']}")
        print(f"  Status: {result['status']}")
        print("\n  → Will sell at $160 (profit) OR $145 (loss)")
        print("  → Whichever happens first cancels the other")

    except Exception as e:
        print(f"✗ Error: {e}")


def example_view_orders():
    """Example: View and manage orders."""
    print("\n" + "=" * 60)
    print("Example 7: View and Manage Orders")
    print("=" * 60)

    client = AlpacaTradingClient()

    try:
        # Get all open orders
        print("\nFetching all open orders...")
        orders = client.get_orders(status="open")

        if orders:
            print(f"\n✓ Found {len(orders)} open orders:")
            for order in orders[:5]:  # Show first 5
                print(f"\n  Order ID: {order['id']}")
                print(f"  Symbol: {order['symbol']}")
                print(f"  Side: {order['side']}")
                print(f"  Type: {order['type']}")
                print(f"  Qty: {order['qty']}")
                print(f"  Status: {order['status']}")

                if order['type'] == 'stop':
                    print(f"  Stop Price: ${order['stop_price']}")
                elif order['type'] == 'stop_limit':
                    print(f"  Stop Price: ${order['stop_price']}")
                    print(f"  Limit Price: ${order['limit_price']}")
                elif order['type'] == 'limit':
                    print(f"  Limit Price: ${order['limit_price']}")

            # Example: Cancel first order
            if orders and input("\nCancel first order? (y/n): ").lower() == 'y':
                client.cancel_order(orders[0]['id'])
                print(f"✓ Cancelled order {orders[0]['id']}")
        else:
            print("\n  No open orders")

    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Alpaca Order Types Demo")
    print("=" * 60)
    print("\nSupported Order Types:")
    print("  1. Market Order - Execute immediately at market price")
    print("  2. Limit Order - Execute at specified price or better")
    print("  3. Stop Loss - Sell when price drops to stop price")
    print("  4. Stop Limit - Limit order triggered at stop price")
    print("  5. Trailing Stop - Stop price trails market by percentage")
    print("  6. Bracket Order - Entry + take profit + stop loss")
    print("\n⚠️  Note: Requires valid Alpaca API credentials")
    print("=" * 60)

    # Run examples (will fail with invalid credentials)
    examples = [
        ("Market Order", example_market_order),
        ("Limit Order", example_limit_order),
        ("Stop Loss Order", example_stop_loss_order),
        ("Stop Limit Order", example_stop_limit_order),
        ("Trailing Stop Order", example_trailing_stop_order),
        ("Bracket Order", example_bracket_order),
        ("View Orders", example_view_orders),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")

        input("\nPress Enter to continue to next example...")
