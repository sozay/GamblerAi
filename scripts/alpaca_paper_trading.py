#!/usr/bin/env python3
"""
Live Paper Trading with Alpaca API.

This script connects to Alpaca's Paper Trading environment and executes
the momentum strategy with real market data and paper money.

Setup:
1. Sign up for free Alpaca Paper Trading: https://alpaca.markets
2. Get API keys from dashboard
3. Set environment variables or pass as arguments
"""

import argparse
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

import pandas as pd
import requests


class AlpacaPaperTrader:
    """Paper trading with Alpaca API."""

    def __init__(self, api_key: str, api_secret: str, base_url: str = None):
        """
        Initialize Alpaca paper trader.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: API base URL (defaults to paper trading)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or "https://paper-api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"

        self.headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret,
            'accept': 'application/json',
        }

        # Strategy parameters
        self.min_price_change_pct = 2.0
        self.min_volume_ratio = 2.0
        self.stop_loss_pct = 2.0
        self.take_profit_pct = 4.0
        self.position_size = 10000  # $10k per trade

        # State
        self.active_positions = {}
        self.closed_trades = []
        self.scanning_symbols = []

    def check_connection(self):
        """Test API connection."""
        print("Testing Alpaca Paper Trading connection...")

        try:
            response = requests.get(
                f"{self.base_url}/v2/account",
                headers=self.headers
            )

            if response.status_code == 200:
                account = response.json()
                print("✓ Connected to Alpaca Paper Trading")
                print(f"  Account Status: {account['status']}")
                print(f"  Buying Power: ${float(account['buying_power']):,.2f}")
                print(f"  Cash: ${float(account['cash']):,.2f}")
                print(f"  Portfolio Value: ${float(account['portfolio_value']):,.2f}")
                return True
            else:
                print(f"✗ Connection failed: {response.status_code}")
                print(f"  {response.text}")
                return False

        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False

    def get_account(self):
        """Get account information."""
        response = requests.get(
            f"{self.base_url}/v2/account",
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get account: {response.text}")

    def get_positions(self):
        """Get current positions."""
        response = requests.get(
            f"{self.base_url}/v2/positions",
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []

    def get_latest_bars(self, symbols: List[str], timeframe: str = "5Min", limit: int = 100):
        """
        Get latest bars for symbols.

        Args:
            symbols: List of symbols
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            limit: Number of bars
        """
        # Alpaca requires symbols as comma-separated
        symbols_str = ','.join(symbols)

        url = f"{self.data_url}/v2/stocks/bars"
        params = {
            'symbols': symbols_str,
            'timeframe': timeframe,
            'limit': limit,
            'feed': 'iex',  # Free IEX feed
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                data = response.json()
                return data.get('bars', {})
            else:
                print(f"Failed to get bars: {response.status_code} - {response.text}")
                return {}

        except Exception as e:
            print(f"Error getting bars: {e}")
            return {}

    def detect_momentum(self, symbol: str, bars: List[Dict]) -> Optional[Dict]:
        """
        Detect momentum event in bars.

        Returns:
            Dict with event details if momentum detected, None otherwise
        """
        if len(bars) < 20:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(bars)
        df['t'] = pd.to_datetime(df['t'])
        df = df.sort_values('t')

        # Calculate volume ratio
        df['avg_volume'] = df['v'].rolling(window=20).mean()
        df['volume_ratio'] = df['v'] / df['avg_volume']

        # Check last 5 bars for momentum
        if len(df) < 5:
            return None

        window = df.tail(5)

        price_change_pct = (
            (window.iloc[-1]['c'] - window.iloc[0]['o']) / window.iloc[0]['o'] * 100
        )

        avg_vol_ratio = window['volume_ratio'].mean()

        if pd.isna(avg_vol_ratio):
            return None

        if (
            abs(price_change_pct) >= self.min_price_change_pct
            and avg_vol_ratio >= self.min_volume_ratio
        ):
            direction = "UP" if price_change_pct > 0 else "DOWN"

            return {
                'symbol': symbol,
                'timestamp': window.iloc[-1]['t'],
                'direction': direction,
                'price_change_pct': abs(price_change_pct),
                'volume_ratio': avg_vol_ratio,
                'entry_price': float(window.iloc[-1]['c']),
            }

        return None

    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
        stop_loss: float = None,
        take_profit: float = None,
    ):
        """
        Place an order with Alpaca.

        Args:
            symbol: Stock symbol
            qty: Quantity of shares
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', etc.
            time_in_force: 'day', 'gtc', etc.
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        order_data = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': order_type,
            'time_in_force': time_in_force,
        }

        # Add bracket orders for stop loss and take profit
        if stop_loss or take_profit:
            order_data['order_class'] = 'bracket'

            if stop_loss:
                order_data['stop_loss'] = {
                    'stop_price': stop_loss,
                }

            if take_profit:
                order_data['take_profit'] = {
                    'limit_price': take_profit,
                }

        try:
            response = requests.post(
                f"{self.base_url}/v2/orders",
                headers=self.headers,
                json=order_data
            )

            if response.status_code in [200, 201]:
                order = response.json()
                print(f"✓ Order placed: {side.upper()} {qty} {symbol} @ market")
                if stop_loss:
                    print(f"  Stop Loss: ${stop_loss:.2f}")
                if take_profit:
                    print(f"  Take Profit: ${take_profit:.2f}")
                return order
            else:
                print(f"✗ Order failed: {response.status_code}")
                print(f"  {response.text}")
                return None

        except Exception as e:
            print(f"✗ Order error: {e}")
            return None

    def enter_position(self, event: Dict):
        """Enter a position based on momentum event."""
        symbol = event['symbol']
        direction = event['direction']
        entry_price = event['entry_price']

        # Skip if already in position
        if symbol in self.active_positions:
            print(f"⚠ Already in position for {symbol}, skipping")
            return

        # Calculate position size (number of shares)
        qty = int(self.position_size / entry_price)

        if qty < 1:
            print(f"⚠ Position size too small for {symbol}")
            return

        # Calculate stop loss and take profit
        if direction == "UP":
            side = "buy"
            stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
            take_profit = entry_price * (1 + self.take_profit_pct / 100)
        else:
            side = "sell"  # Short position
            stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
            take_profit = entry_price * (1 - self.take_profit_pct / 100)

        print(f"\n🔔 MOMENTUM SIGNAL: {symbol} {direction}")
        print(f"   Entry: ${entry_price:.2f}")
        print(f"   Size: {qty} shares (${qty * entry_price:,.0f})")

        # Place order
        order = self.place_order(
            symbol=symbol,
            qty=qty,
            side=side,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
        )

        if order:
            # Track position
            self.active_positions[symbol] = {
                'symbol': symbol,
                'entry_time': datetime.now(),
                'entry_price': entry_price,
                'qty': qty,
                'direction': direction,
                'side': side,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'order_id': order['id'],
            }

    def check_positions(self):
        """Check status of active positions."""
        if not self.active_positions:
            return

        # Get current positions from Alpaca
        positions = self.get_positions()
        position_symbols = {p['symbol'] for p in positions}

        # Check if any of our tracked positions are closed
        for symbol in list(self.active_positions.keys()):
            if symbol not in position_symbols:
                # Position closed
                pos = self.active_positions.pop(symbol)

                # Get order details to determine exit reason
                # (would need to query orders endpoint for full details)

                print(f"\n✓ Position CLOSED: {symbol}")
                print(f"   Entry: ${pos['entry_price']:.2f}")
                print(f"   Direction: {pos['direction']}")
                print(f"   Duration: {(datetime.now() - pos['entry_time']).seconds // 60} minutes")

                self.closed_trades.append({
                    'symbol': symbol,
                    'entry_time': pos['entry_time'],
                    'exit_time': datetime.now(),
                    'entry_price': pos['entry_price'],
                    'direction': pos['direction'],
                    'qty': pos['qty'],
                })

    def scan_for_signals(self, symbols: List[str]):
        """Scan symbols for momentum signals."""
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Scanning {len(symbols)} symbols...")

        # Get latest bars for all symbols
        bars_data = self.get_latest_bars(symbols, timeframe='5Min', limit=100)

        signals_found = 0

        for symbol in symbols:
            if symbol not in bars_data:
                continue

            bars = bars_data[symbol]

            if not bars:
                continue

            # Check for momentum
            event = self.detect_momentum(symbol, bars)

            if event:
                signals_found += 1
                print(f"   📊 {symbol}: {event['direction']} {event['price_change_pct']:.2f}% move, {event['volume_ratio']:.1f}x volume")

                # Enter position
                self.enter_position(event)

        if signals_found == 0:
            print("   No signals detected")

    def run_paper_trading(
        self,
        symbols: List[str],
        duration_minutes: int = 60,
        scan_interval_seconds: int = 60,
    ):
        """
        Run paper trading session.

        Args:
            symbols: List of symbols to monitor
            duration_minutes: How long to run (minutes)
            scan_interval_seconds: How often to scan (seconds)
        """
        self.scanning_symbols = symbols

        print("\n" + "=" * 80)
        print("ALPACA PAPER TRADING - LIVE SESSION")
        print("=" * 80)
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Scan Interval: {scan_interval_seconds} seconds")
        print(f"Strategy: {self.stop_loss_pct}% stop loss, {self.take_profit_pct}% take profit")
        print("=" * 80 + "\n")

        # Check initial account status
        account = self.get_account()
        initial_value = float(account['portfolio_value'])
        print(f"Starting Portfolio Value: ${initial_value:,.2f}\n")

        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        try:
            while datetime.now() < end_time:
                # Scan for signals
                self.scan_for_signals(symbols)

                # Check existing positions
                self.check_positions()

                # Status update
                remaining = int((end_time - datetime.now()).seconds / 60)
                print(f"   Active positions: {len(self.active_positions)}, Closed trades: {len(self.closed_trades)}, Time remaining: {remaining} min")

                # Wait before next scan
                time.sleep(scan_interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user")

        # Final report
        print("\n" + "=" * 80)
        print("SESSION COMPLETE")
        print("=" * 80)

        account = self.get_account()
        final_value = float(account['portfolio_value'])
        pnl = final_value - initial_value

        print(f"\nInitial Portfolio Value: ${initial_value:,.2f}")
        print(f"Final Portfolio Value:   ${final_value:,.2f}")
        print(f"P&L:                     ${pnl:,.2f} ({pnl/initial_value*100:+.2f}%)")
        print(f"\nTotal Closed Trades: {len(self.closed_trades)}")
        print(f"Active Positions:    {len(self.active_positions)}")

        if self.closed_trades:
            print("\nClosed Trades:")
            for trade in self.closed_trades:
                duration = (trade['exit_time'] - trade['entry_time']).seconds // 60
                print(f"  {trade['symbol']}: {trade['direction']}, {duration} min")

        print("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Alpaca Paper Trading")
    parser.add_argument("--api-key", help="Alpaca API Key (or set ALPACA_API_KEY env var)")
    parser.add_argument("--api-secret", help="Alpaca API Secret (or set ALPACA_API_SECRET env var)")
    parser.add_argument("--symbols", default="AAPL,MSFT,GOOGL,TSLA,NVDA", help="Symbols to trade")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")

    args = parser.parse_args()

    # Get API credentials
    api_key = args.api_key or os.environ.get('ALPACA_API_KEY')
    api_secret = args.api_secret or os.environ.get('ALPACA_API_SECRET')

    if not api_key or not api_secret:
        print("ERROR: Alpaca API credentials required!")
        print("\nOptions:")
        print("1. Set environment variables:")
        print("   export ALPACA_API_KEY='your_key'")
        print("   export ALPACA_API_SECRET='your_secret'")
        print("\n2. Pass as arguments:")
        print("   --api-key YOUR_KEY --api-secret YOUR_SECRET")
        print("\n3. Get free paper trading account:")
        print("   https://alpaca.markets (sign up for paper trading)")
        return

    # Parse symbols
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    # Create trader
    trader = AlpacaPaperTrader(api_key, api_secret)

    # Test connection
    if not trader.check_connection():
        print("\nFailed to connect to Alpaca. Please check your API credentials.")
        return

    print("\n✓ Ready to start paper trading!\n")
    input("Press ENTER to begin...")

    # Run paper trading
    trader.run_paper_trading(
        symbols=symbols,
        duration_minutes=args.duration,
        scan_interval_seconds=args.interval,
    )


if __name__ == "__main__":
    main()
