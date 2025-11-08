#!/usr/bin/env python3
"""
Live Paper Trading with Alpaca API - WITH RECOVERY SUPPORT.

This script connects to Alpaca's Paper Trading environment and executes
the momentum strategy with real market data and paper money.

Features:
- Automatic state persistence to database
- Recovery from crashes/restarts
- Position reconciliation with Alpaca API
- Transaction journal for audit trail
- Graceful shutdown handling

Setup:
1. Sign up for free Alpaca Paper Trading: https://alpaca.markets
2. Get API keys from dashboard
3. Set environment variables or pass as arguments
4. Ensure database is initialized (run init_databases())
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import json

import pandas as pd
import requests

from gambler_ai.storage.database import get_analytics_db, init_databases
from gambler_ai.trading.state_manager import StateManager
from gambler_ai.trading.position_reconciler import PositionReconciler


class AlpacaPaperTraderWithRecovery:
    """Paper trading with Alpaca API and recovery support."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        db_session=None,
        base_url: str = None,
        resume_session_id: str = None
    ):
        """
        Initialize Alpaca paper trader with recovery.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            db_session: Database session for state persistence
            base_url: API base URL (defaults to paper trading)
            resume_session_id: Optional session ID to resume
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

        # State management
        self.db_session = db_session
        self.state_manager = StateManager(db_session) if db_session else None
        self.reconciler = PositionReconciler(self.state_manager) if self.state_manager else None

        # In-memory state (synced with DB)
        self.active_positions = {}
        self.closed_trades = []
        self.scanning_symbols = []

        # Checkpoint tracking
        self.last_checkpoint_time = None
        self.checkpoint_interval = 30  # Create checkpoint every 30 seconds

        # Graceful shutdown
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Resume session if requested
        if resume_session_id and self.state_manager:
            self.resume_from_session(resume_session_id)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n⚠ Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True

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
        """Get current positions from Alpaca."""
        response = requests.get(
            f"{self.base_url}/v2/positions",
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []

    def reconcile_positions(self):
        """Reconcile positions with Alpaca API."""
        if not self.reconciler:
            print("⚠ No reconciler available, skipping reconciliation")
            return

        print("\n⟳ Reconciling positions with Alpaca API...")

        # Get positions from Alpaca
        alpaca_positions = self.get_positions()

        # Perform full recovery
        summary = self.reconciler.full_recovery(
            alpaca_positions=alpaca_positions,
            import_new=True,
            close_orphaned=True
        )

        # Reload in-memory state from DB
        self.load_positions_from_db()

    def load_positions_from_db(self):
        """Load active positions from database into memory."""
        if not self.state_manager:
            return

        self.active_positions = {}
        active_positions = self.state_manager.get_open_positions()

        for pos in active_positions:
            self.active_positions[pos.symbol] = {
                'symbol': pos.symbol,
                'entry_time': pos.entry_time,
                'entry_price': float(pos.entry_price),
                'qty': int(pos.qty),  # Main's model uses Integer qty
                'direction': pos.direction,  # 'UP' or 'DOWN'
                'side': pos.side,
                'stop_loss': float(pos.stop_loss) if pos.stop_loss else None,
                'take_profit': float(pos.take_profit) if pos.take_profit else None,
                'order_id': pos.order_id,  # Main's model uses order_id not entry_order_id
                'position_id': pos.id
            }

        print(f"✓ Loaded {len(self.active_positions)} positions from database")

    def resume_from_session(self, session_id: str):
        """Resume from a previous session."""
        session = self.state_manager.resume_session(session_id)
        if session:
            # Load positions
            self.load_positions_from_db()
            print(f"✓ Resumed with {len(self.active_positions)} active positions")

            # Try to restore from latest checkpoint
            checkpoint_state = self.state_manager.restore_from_latest_checkpoint()
            if checkpoint_state:
                print(f"  Checkpoint: {checkpoint_state['checkpoint_time']}")
                if checkpoint_state.get('account_info'):
                    print(f"  Last known portfolio value: ${checkpoint_state['account_info'].get('portfolio_value', 'N/A')}")

    def create_checkpoint(self):
        """Create a checkpoint of the current state."""
        if not self.state_manager:
            return

        try:
            # Get current account info
            account = self.get_account()
            account_info = {
                'portfolio_value': float(account['portfolio_value']),
                'buying_power': float(account['buying_power']),
                'cash': float(account['cash']),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Strategy parameters
            strategy_params = {
                'min_price_change_pct': self.min_price_change_pct,
                'min_volume_ratio': self.min_volume_ratio,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'position_size': self.position_size
            }

            # Create checkpoint
            checkpoint_id = self.state_manager.create_checkpoint(
                account_info=account_info,
                strategy_params=strategy_params
            )

            self.last_checkpoint_time = datetime.now()

            # Optionally print checkpoint info (only every 10th checkpoint to reduce noise)
            stats = self.state_manager.get_checkpoint_stats()
            if stats.get('total_checkpoints', 0) % 10 == 0:
                print(f"   💾 Checkpoint #{stats['total_checkpoints']} created")

        except Exception as e:
            print(f"⚠ Failed to create checkpoint: {e}")

    def get_latest_bars(self, symbols: List[str], timeframe: str = "5Min", limit: int = 100):
        """Get latest bars for symbols."""
        symbols_str = ','.join(symbols)

        url = f"{self.data_url}/v2/stocks/bars"
        params = {
            'symbols': symbols_str,
            'timeframe': timeframe,
            'limit': limit,
            'feed': 'iex',
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
        """Detect momentum event in bars."""
        if len(bars) < 20:
            return None

        df = pd.DataFrame(bars)
        df['t'] = pd.to_datetime(df['t'])
        df = df.sort_values('t')

        df['avg_volume'] = df['v'].rolling(window=20).mean()
        df['volume_ratio'] = df['v'] / df['avg_volume']

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
        """Place an order with Alpaca."""
        order_data = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': order_type,
            'time_in_force': time_in_force,
        }

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

                # Log order to journal
                if self.state_manager:
                    self.state_manager.log_order(
                        alpaca_order_id=order['id'],
                        symbol=symbol,
                        order_type=order_type,
                        side=side,
                        quantity=qty,
                        status='submitted',
                        order_class=order_data.get('order_class'),
                        time_in_force=time_in_force
                    )

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

        if symbol in self.active_positions:
            print(f"⚠ Already in position for {symbol}, skipping")
            return

        qty = int(self.position_size / entry_price)

        if qty < 1:
            print(f"⚠ Position size too small for {symbol}")
            return

        if direction == "UP":
            side = "buy"
            stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
            take_profit = entry_price * (1 + self.take_profit_pct / 100)
        else:
            side = "sell"
            stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
            take_profit = entry_price * (1 - self.take_profit_pct / 100)

        print(f"\n🔔 MOMENTUM SIGNAL: {symbol} {direction}")
        print(f"   Entry: ${entry_price:.2f}")
        print(f"   Size: {qty} shares (${qty * entry_price:,.0f})")

        order = self.place_order(
            symbol=symbol,
            qty=qty,
            side=side,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
        )

        if order:
            entry_time = datetime.now(timezone.utc)

            # Save to database
            position_id = None
            if self.state_manager:
                position_id = self.state_manager.save_position(
                    symbol=symbol,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    quantity=qty,
                    direction=direction,  # Should be 'UP' or 'DOWN'
                    side=side,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    order_id=order['id']  # Main's model uses order_id
                )

            # Track in memory
            self.active_positions[symbol] = {
                'symbol': symbol,
                'entry_time': entry_time,
                'entry_price': entry_price,
                'qty': qty,
                'direction': direction,
                'side': side,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'order_id': order['id'],
                'position_id': position_id
            }

    def check_positions(self):
        """Check status of active positions."""
        if not self.active_positions:
            return

        positions = self.get_positions()
        position_symbols = {p['symbol'] for p in positions}

        for symbol in list(self.active_positions.keys()):
            if symbol not in position_symbols:
                pos = self.active_positions.pop(symbol)

                print(f"\n✓ Position CLOSED: {symbol}")
                print(f"   Entry: ${pos['entry_price']:.2f}")
                print(f"   Direction: {pos['direction']}")
                duration = (datetime.now(timezone.utc) - pos['entry_time']).seconds // 60
                print(f"   Duration: {duration} minutes")

                # Update database
                if self.state_manager:
                    self.state_manager.update_position(
                        symbol=symbol,
                        exit_time=datetime.now(timezone.utc),
                        exit_reason='bracket_closed',
                        status='closed'
                    )

                self.closed_trades.append({
                    'symbol': symbol,
                    'entry_time': pos['entry_time'],
                    'exit_time': datetime.now(timezone.utc),
                    'entry_price': pos['entry_price'],
                    'direction': pos['direction'],
                    'qty': pos['qty'],
                })

    def should_create_checkpoint(self) -> bool:
        """Check if it's time to create a checkpoint."""
        if not self.last_checkpoint_time:
            return True

        elapsed = (datetime.now() - self.last_checkpoint_time).seconds
        return elapsed >= self.checkpoint_interval

    def scan_for_signals(self, symbols: List[str]):
        """Scan symbols for momentum signals."""
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Scanning {len(symbols)} symbols...")

        bars_data = self.get_latest_bars(symbols, timeframe='5Min', limit=100)

        signals_found = 0

        for symbol in symbols:
            if symbol not in bars_data:
                continue

            bars = bars_data[symbol]

            if not bars:
                continue

            event = self.detect_momentum(symbol, bars)

            if event:
                signals_found += 1
                print(f"   📊 {symbol}: {event['direction']} {event['price_change_pct']:.2f}% move, {event['volume_ratio']:.1f}x volume")
                self.enter_position(event)

        if signals_found == 0:
            print("   No signals detected")

    def run_paper_trading(
        self,
        symbols: List[str],
        duration_minutes: int = 60,
        scan_interval_seconds: int = 60,
        resume: bool = False
    ):
        """Run paper trading session with recovery support."""
        self.scanning_symbols = symbols

        print("\n" + "=" * 80)
        print("ALPACA PAPER TRADING - LIVE SESSION (WITH RECOVERY)")
        print("=" * 80)
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Scan Interval: {scan_interval_seconds} seconds")
        print(f"Checkpoint Interval: {self.checkpoint_interval} seconds")
        print(f"Strategy: {self.stop_loss_pct}% stop loss, {self.take_profit_pct}% take profit")
        print(f"Recovery: {'ENABLED' if self.state_manager else 'DISABLED'}")
        print("=" * 80 + "\n")

        # Get initial account status
        account = self.get_account()
        initial_value = float(account['portfolio_value'])
        print(f"Starting Portfolio Value: ${initial_value:,.2f}\n")

        # Create or resume session
        if self.state_manager:
            if not self.state_manager.session_id:
                self.state_manager.create_session(
                    symbols=symbols,
                    initial_capital=initial_value,
                    duration_minutes=duration_minutes,
                    scan_interval_seconds=scan_interval_seconds
                )

            # Reconcile positions
            if resume:
                self.reconcile_positions()

        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)

        try:
            while datetime.now() < end_time and not self.shutdown_requested:
                self.scan_for_signals(symbols)
                self.check_positions()

                # Create periodic checkpoints
                if self.should_create_checkpoint():
                    self.create_checkpoint()

                remaining = int((end_time - datetime.now()).seconds / 60)
                print(f"   Active: {len(self.active_positions)}, Closed: {len(self.closed_trades)}, Time remaining: {remaining} min")

                time.sleep(scan_interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user")
        except Exception as e:
            print(f"\n\n✗ Error during trading: {e}")
            import traceback
            traceback.print_exc()

        # Graceful shutdown
        print("\n⟳ Shutting down gracefully...")

        # Create final checkpoint before shutdown
        if self.state_manager:
            print("   Creating final checkpoint...")
            self.create_checkpoint()

        account = self.get_account()
        final_value = float(account['portfolio_value'])

        if self.state_manager:
            # Get checkpoint stats
            checkpoint_stats = self.state_manager.get_checkpoint_stats()
            if checkpoint_stats.get('total_checkpoints', 0) > 0:
                print(f"   Total checkpoints created: {checkpoint_stats['total_checkpoints']}")

            self.state_manager.end_session(
                final_capital=final_value,
                status='completed' if not self.shutdown_requested else 'crashed'
            )

            # Clean up old checkpoints (keep last 100)
            deleted = self.state_manager.cleanup_old_checkpoints(keep_count=100)
            if deleted > 0:
                print(f"   Cleaned up {deleted} old checkpoints")

        # Final report
        print("\n" + "=" * 80)
        print("SESSION COMPLETE")
        print("=" * 80)

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
    parser = argparse.ArgumentParser(description="Alpaca Paper Trading with Recovery")
    parser.add_argument("--api-key", help="Alpaca API Key")
    parser.add_argument("--api-secret", help="Alpaca API Secret")
    parser.add_argument("--symbols", default="AAPL,MSFT,GOOGL,TSLA,NVDA", help="Symbols to trade")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes")
    parser.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    parser.add_argument("--resume", action="store_true", help="Resume last active session")
    parser.add_argument("--resume-session", help="Resume specific session ID")
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables")
    parser.add_argument("--reconcile-only", action="store_true", help="Only reconcile positions and exit")
    parser.add_argument("--checkpoint-interval", type=int, default=30, help="Checkpoint interval in seconds (default: 30)")

    args = parser.parse_args()

    # Initialize database if requested
    if args.init_db:
        print("Initializing database...")
        init_databases()
        print("✓ Database initialized\n")

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
        return

    # Parse symbols
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    # Get database session
    db_manager = get_analytics_db()
    db_manager.create_tables()  # Ensure tables exist
    db_session = db_manager.get_session_direct()

    try:
        # Create trader
        trader = AlpacaPaperTraderWithRecovery(
            api_key,
            api_secret,
            db_session=db_session,
            resume_session_id=args.resume_session
        )

        # Set checkpoint interval
        trader.checkpoint_interval = args.checkpoint_interval

        # Test connection
        if not trader.check_connection():
            print("\nFailed to connect to Alpaca. Please check your API credentials.")
            return

        # Reconcile only mode
        if args.reconcile_only:
            trader.reconcile_positions()
            return

        print("\n✓ Ready to start paper trading!\n")
        if not args.resume and not args.resume_session:
            input("Press ENTER to begin...")

        # Run paper trading
        trader.run_paper_trading(
            symbols=symbols,
            duration_minutes=args.duration,
            scan_interval_seconds=args.interval,
            resume=args.resume or args.resume_session is not None
        )

    finally:
        db_session.close()


if __name__ == "__main__":
    main()
