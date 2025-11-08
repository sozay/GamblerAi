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
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import sys
from decimal import Decimal

import pandas as pd
import requests

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gambler_ai.storage import (
    get_analytics_db,
    TradingSession,
    Position,
    PositionCheckpoint,
)
from gambler_ai.utils.transaction_logger import TransactionLogger


class AlpacaPaperTrader:
    """Paper trading with Alpaca API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = None,
        enable_persistence: bool = True,
        transaction_logger: Optional[TransactionLogger] = None,
    ):
        """
        Initialize Alpaca paper trader.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: API base URL (defaults to paper trading)
            enable_persistence: Enable state persistence to database
            transaction_logger: TransactionLogger instance for logging trades
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

        # Session tracking
        self.session_id = str(uuid.uuid4())
        self.enable_persistence = enable_persistence
        self.db = None
        self.last_checkpoint_time = None
        self.checkpoint_interval = 30  # seconds

        # Transaction logging
        self.transaction_logger = transaction_logger

        # Initialize database if persistence enabled
        if self.enable_persistence:
            try:
                self.db = get_analytics_db()
                print("✓ Database connection established for state persistence")
            except Exception as e:
                print(f"⚠ Warning: Could not connect to database: {e}")
                print("  State persistence disabled")
                self.enable_persistence = False

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
            entry_time = datetime.now()

            # Track position
            position_data = {
                'symbol': symbol,
                'entry_time': entry_time,
                'entry_price': entry_price,
                'qty': qty,
                'direction': direction,
                'side': side,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'order_id': order['id'],
                'transaction_id': None,  # Will be set if logging enabled
            }
            self.active_positions[symbol] = position_data

            # Save to database for crash recovery
            if self.enable_persistence:
                self._save_position(symbol, position_data)

            # Log trade entry for audit trail
            if self.transaction_logger:
                try:
                    transaction_id = self.transaction_logger.log_trade_entry(
                        symbol=symbol,
                        direction="LONG" if side == "buy" else "SHORT",
                        entry_time=entry_time,
                        entry_price=entry_price,
                        position_size=qty,
                        stop_loss=stop_loss,
                        target=take_profit,
                        strategy_name=f"momentum_{direction.lower()}",
                        trade_id=order['id'],
                    )
                    self.active_positions[symbol]['transaction_id'] = transaction_id
                except Exception as e:
                    print(f"Warning: Failed to log trade entry: {e}")

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
                exit_time = datetime.now()

                # Get order details to determine exit reason
                # (would need to query orders endpoint for full details)
                exit_price = None  # Would get from Alpaca API
                exit_reason = "closed"

                duration_minutes = (exit_time - pos['entry_time']).seconds // 60

                print(f"\n✓ Position CLOSED: {symbol}")
                print(f"   Entry: ${pos['entry_price']:.2f}")
                print(f"   Direction: {pos['direction']}")
                print(f"   Duration: {duration_minutes} minutes")

                trade_data = {
                    'symbol': symbol,
                    'entry_time': pos['entry_time'],
                    'exit_time': exit_time,
                    'entry_price': pos['entry_price'],
                    'direction': pos['direction'],
                    'qty': pos['qty'],
                }
                self.closed_trades.append(trade_data)

                # Update position in database for crash recovery
                if self.enable_persistence:
                    self._update_position_closed(symbol, pos)

                # Log trade exit for audit trail
                if self.transaction_logger and pos.get('transaction_id'):
                    try:
                        # Estimate exit price and P&L
                        # In real implementation, would get from Alpaca API
                        estimated_exit = pos['entry_price']  # Placeholder
                        pnl = 0.0  # Would calculate from actual fills
                        pnl_pct = 0.0

                        self.transaction_logger.log_trade_exit(
                            transaction_id=pos['transaction_id'],
                            exit_time=exit_time,
                            exit_price=estimated_exit,
                            exit_reason=exit_reason,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            return_pct=pnl_pct,
                            max_adverse_excursion=0.0,
                            max_favorable_excursion=0.0,
                            trade_id=pos['order_id'],
                        )
                    except Exception as e:
                        print(f"Warning: Failed to log trade exit: {e}")

    def _create_session_record(self, symbols: List[str], duration_minutes: int, scan_interval_seconds: int, initial_value: float):
        """Create initial trading session record in database."""
        if not self.enable_persistence:
            return

        try:
            with self.db.get_session() as session:
                trading_session = TradingSession(
                    session_id=self.session_id,
                    start_time=datetime.now(),
                    status='active',
                    symbols=','.join(symbols),
                    duration_minutes=duration_minutes,
                    scan_interval_seconds=scan_interval_seconds,
                    initial_portfolio_value=Decimal(str(initial_value)),
                )
                session.add(trading_session)
                session.commit()
                print(f"✓ Session {self.session_id[:8]} created in database")
        except Exception as e:
            print(f"⚠ Warning: Failed to create session record: {e}")

    def _save_position(self, symbol: str, position_data: Dict):
        """Save new position to database."""
        if not self.enable_persistence:
            return

        try:
            with self.db.get_session() as session:
                position = Position(
                    session_id=self.session_id,
                    symbol=symbol,
                    entry_time=position_data['entry_time'],
                    entry_price=Decimal(str(position_data['entry_price'])),
                    qty=position_data['qty'],
                    direction=position_data['direction'],
                    side=position_data['side'],
                    stop_loss=Decimal(str(position_data['stop_loss'])),
                    take_profit=Decimal(str(position_data['take_profit'])),
                    order_id=position_data['order_id'],
                    status='active',
                )
                session.add(position)
                session.commit()
        except Exception as e:
            print(f"⚠ Warning: Failed to save position {symbol}: {e}")

    def _update_position_closed(self, symbol: str, position_data: Dict):
        """Update position as closed in database."""
        if not self.enable_persistence:
            return

        try:
            with self.db.get_session() as session:
                position = session.query(Position).filter_by(
                    session_id=self.session_id,
                    symbol=symbol,
                    status='active'
                ).first()

                if position:
                    position.status = 'closed'
                    position.exit_time = datetime.now()
                    position.duration_minutes = int((datetime.now() - position.entry_time).seconds / 60)
                    # Exit reason would need to be determined from Alpaca API
                    position.exit_reason = 'unknown'
                    session.commit()
        except Exception as e:
            print(f"⚠ Warning: Failed to update position {symbol}: {e}")

    def _save_checkpoint(self):
        """Save periodic checkpoint of current state."""
        if not self.enable_persistence:
            return

        # Only checkpoint every 30 seconds
        now = datetime.now()
        if self.last_checkpoint_time and (now - self.last_checkpoint_time).seconds < self.checkpoint_interval:
            return

        try:
            # Get current account state
            account = self.get_account()

            # Prepare positions snapshot
            positions_snapshot = {
                symbol: {
                    'entry_time': pos['entry_time'].isoformat(),
                    'entry_price': float(pos['entry_price']),
                    'qty': pos['qty'],
                    'direction': pos['direction'],
                    'side': pos['side'],
                    'stop_loss': float(pos['stop_loss']),
                    'take_profit': float(pos['take_profit']),
                    'order_id': pos['order_id'],
                }
                for symbol, pos in self.active_positions.items()
            }

            account_snapshot = {
                'portfolio_value': float(account['portfolio_value']),
                'buying_power': float(account['buying_power']),
                'cash': float(account['cash']),
            }

            with self.db.get_session() as session:
                checkpoint = PositionCheckpoint(
                    session_id=self.session_id,
                    checkpoint_time=now,
                    positions_snapshot=positions_snapshot,
                    account_snapshot=account_snapshot,
                    active_positions_count=len(self.active_positions),
                    closed_trades_count=len(self.closed_trades),
                )
                session.add(checkpoint)
                session.commit()

            self.last_checkpoint_time = now
            print(f"   💾 Checkpoint saved: {len(self.active_positions)} active positions")

        except Exception as e:
            print(f"⚠ Warning: Failed to save checkpoint: {e}")

    def _finalize_session(self, final_value: float, pnl: float):
        """Mark session as completed in database."""
        if not self.enable_persistence:
            return

        try:
            with self.db.get_session() as session:
                trading_session = session.query(TradingSession).filter_by(
                    session_id=self.session_id
                ).first()

                if trading_session:
                    trading_session.end_time = datetime.now()
                    trading_session.status = 'completed'
                    trading_session.final_portfolio_value = Decimal(str(final_value))
                    trading_session.pnl = Decimal(str(pnl))
                    if trading_session.initial_portfolio_value:
                        trading_session.pnl_pct = Decimal(str(pnl / float(trading_session.initial_portfolio_value) * 100))
                    trading_session.total_trades = len(self.closed_trades)
                    session.commit()
                    print(f"✓ Session {self.session_id[:8]} finalized in database")
        except Exception as e:
            print(f"⚠ Warning: Failed to finalize session: {e}")

    def _check_for_crashed_sessions(self):
        """Check for crashed sessions and offer recovery."""
        if not self.enable_persistence:
            return None

        try:
            with self.db.get_session() as session:
                crashed_sessions = session.query(TradingSession).filter_by(
                    status='active'
                ).order_by(TradingSession.start_time.desc()).limit(5).all()

                if crashed_sessions:
                    print("\n⚠ Found active sessions (may have crashed):")
                    for idx, sess in enumerate(crashed_sessions, 1):
                        print(f"  {idx}. Session {sess.session_id[:8]} - Started {sess.start_time}")
                        print(f"     Symbols: {sess.symbols}")

                    # For now, just mark them as crashed
                    # Future: could offer recovery option
                    for sess in crashed_sessions:
                        sess.status = 'crashed'
                    session.commit()
                    print("\n  Sessions marked as 'crashed'. Starting new session...\n")

        except Exception as e:
            print(f"⚠ Warning: Failed to check for crashed sessions: {e}")

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

        # Check for crashed sessions
        if self.enable_persistence:
            self._check_for_crashed_sessions()

        print("\n" + "=" * 80)
        print("ALPACA PAPER TRADING - LIVE SESSION")
        print("=" * 80)
        print(f"Session ID: {self.session_id[:8]}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Scan Interval: {scan_interval_seconds} seconds")
        print(f"Strategy: {self.stop_loss_pct}% stop loss, {self.take_profit_pct}% take profit")
        if self.enable_persistence:
            print(f"State Persistence: ✓ Enabled (checkpoints every {self.checkpoint_interval}s)")
        else:
            print(f"State Persistence: ✗ Disabled")
        print("=" * 80 + "\n")

        # Check initial account status
        account = self.get_account()
        initial_value = float(account['portfolio_value'])
        print(f"Starting Portfolio Value: ${initial_value:,.2f}\n")

        # Create session record
        if self.enable_persistence:
            self._create_session_record(symbols, duration_minutes, scan_interval_seconds, initial_value)

        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        try:
            while datetime.now() < end_time:
                # Scan for signals
                self.scan_for_signals(symbols)

                # Check existing positions
                self.check_positions()

                # Save checkpoint periodically
                if self.enable_persistence:
                    self._save_checkpoint()

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

        # Finalize session in database
        if self.enable_persistence:
            self._finalize_session(final_value, pnl)

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
