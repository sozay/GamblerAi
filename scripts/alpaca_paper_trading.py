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
from dotenv import load_dotenv
import yaml

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gambler_ai.storage import (
    get_analytics_db,
    TradingSession,
    Position,
    PositionCheckpoint,
)
from gambler_ai.utils.transaction_logger import TransactionLogger
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.trading.order_synchronizer import OrderSynchronizer
from gambler_ai.analysis.indicators import calculate_bollinger_bands, calculate_rsi
from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType


class AlpacaPaperTrader:
    """Paper trading with Alpaca API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = None,
        enable_persistence: bool = True,
        transaction_logger: Optional[TransactionLogger] = None,
        instance_id: int = 1,
        config_dict: Optional[Dict] = None,
    ):
        """
        Initialize Alpaca paper trader.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: API base URL (defaults to paper trading)
            enable_persistence: Enable state persistence to database
            transaction_logger: TransactionLogger instance for logging trades
            instance_id: Instance ID for multi-instance tracking
            config_dict: Configuration dictionary from config.yaml
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or "https://paper-api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"

        self.instance_id = instance_id
        self.log_prefix = f"[INST-{instance_id}]"

        self.headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret,
            'accept': 'application/json',
        }

        # Load configuration or use defaults
        if config_dict:
            self._load_config(config_dict)
        else:
            self._load_default_config()

        # Initialize detector based on config
        self._initialize_detector()

        # Initialize scanner if configured
        self._initialize_scanner()

        # State
        self.active_positions = {}
        self.pending_orders = {}  # Track orders that haven't filled yet
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
                print(f"{self.log_prefix} ✓ Database connection established for state persistence")
                # Initialize state manager and order synchronizer
                from gambler_ai.trading.state_manager import StateManager
                self.state_manager = StateManager(self.db.get_session_direct())
                self.order_sync = OrderSynchronizer(self.state_manager, self.headers, self.base_url)
                print(f"{self.log_prefix} ✓ Order synchronizer initialized")
            except Exception as e:
                print(f"{self.log_prefix} ⚠ Warning: Could not connect to database: {e}")
                print(f"{self.log_prefix}   State persistence disabled")
                self.enable_persistence = False

    def _load_config(self, config_dict: Dict):
        """Load configuration from config dict."""
        # Strategy configuration
        self.strategy_name = config_dict.get('name', 'Unknown Strategy')
        self.primary_detector = config_dict.get('primary_detector', 'MeanReversionDetector')
        self.scanner_type = config_dict.get('scanner_type')
        self.strategy_parameters = config_dict.get('parameters', {})

        # Position sizing and risk management
        self.position_size = config_dict.get('position_size', 10000)
        self.stop_loss_pct = config_dict.get('stop_loss_pct', 1.0)
        self.target_bb_middle = config_dict.get('target_bb_middle', True)
        self.max_holding_minutes = config_dict.get('max_holding_minutes', 30)

        # Extract detector-specific parameters
        if self.primary_detector == 'MeanReversionDetector':
            self.bb_period = self.strategy_parameters.get('bb_period', 20)
            self.bb_std = self.strategy_parameters.get('bb_std', 2.5)
            self.rsi_oversold = self.strategy_parameters.get('rsi_oversold', 30)
            self.rsi_overbought = self.strategy_parameters.get('rsi_overbought', 70)
            self.volume_multiplier = self.strategy_parameters.get('volume_multiplier', 3.0)
            self.relative_strength_period = self.strategy_parameters.get('relative_strength_period', 20)
            self.use_relative_strength = self.strategy_parameters.get('use_relative_strength', False)
            self.profit_target_pct = self.strategy_parameters.get('profit_target_pct', 2.0)  # Fixed profit target
        elif self.primary_detector == 'VolatilityBreakoutDetector':
            self.atr_period = self.strategy_parameters.get('atr_period', 14)
            self.atr_compression_ratio = self.strategy_parameters.get('atr_compression_ratio', 0.5)
            self.consolidation_min_bars = self.strategy_parameters.get('consolidation_min_bars', 20)
            self.breakout_threshold = self.strategy_parameters.get('breakout_threshold', 0.5)
            self.volume_multiplier = self.strategy_parameters.get('volume_multiplier', 2.0)
            self.relative_strength_period = self.strategy_parameters.get('relative_strength_period', 20)

    def _load_default_config(self):
        """Load default configuration (backward compatibility)."""
        self.strategy_name = "Mean Reversion + Relative Strength"
        self.primary_detector = "MeanReversionDetector"
        self.scanner_type = None
        self.strategy_parameters = {}

        self.bb_period = 20
        self.bb_std = 2.5
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.stop_loss_pct = 1.0
        self.profit_target_pct = 2.0  # Fixed 2% profit target
        self.target_bb_middle = True
        self.position_size = 10000
        self.max_holding_minutes = 30

        self.relative_strength_period = 20
        self.use_relative_strength = True
        self.volume_multiplier = 3.0

    def _initialize_detector(self):
        """Initialize the primary detector based on configuration."""
        if self.primary_detector == 'MeanReversionDetector':
            self.detector = MeanReversionDetector(
                bb_period=self.bb_period,
                bb_std=self.bb_std,
                rsi_oversold=self.rsi_oversold,
                rsi_overbought=self.rsi_overbought,
                volume_multiplier=self.volume_multiplier,
                profit_target_pct=self.profit_target_pct,
                stop_loss_pct=self.stop_loss_pct,
            )
            print(f"{self.log_prefix} ✓ Initialized MeanReversionDetector (BB={self.bb_period}, σ={self.bb_std}, RSI<{self.rsi_oversold}, Target={self.profit_target_pct}%)")
        elif self.primary_detector == 'VolatilityBreakoutDetector':
            self.detector = VolatilityBreakoutDetector(
                atr_period=self.atr_period,
                atr_compression_ratio=self.atr_compression_ratio,
                consolidation_min_bars=self.consolidation_min_bars,
                breakout_threshold_pct=self.breakout_threshold,
                volume_multiplier=self.volume_multiplier,
            )
            print(f"{self.log_prefix} ✓ Initialized VolatilityBreakoutDetector (ATR={self.atr_period}, compression={self.atr_compression_ratio})")
        else:
            raise ValueError(f"Unknown detector type: {self.primary_detector}")

    def _initialize_scanner(self):
        """Initialize stock scanner if configured."""
        self.scanner = None
        if self.scanner_type:
            try:
                # Map string scanner_type to ScannerType enum
                scanner_type_map = {
                    'relative_strength': ScannerType.RELATIVE_STRENGTH,
                    'gap_scanner': ScannerType.GAP_SCANNER,
                    'best_setups': ScannerType.BEST_SETUPS,
                    'top_movers': ScannerType.TOP_MOVERS,
                    'high_volume': ScannerType.HIGH_VOLUME,
                    'volatility_range': ScannerType.VOLATILITY_RANGE,
                }

                scanner_enum = scanner_type_map.get(self.scanner_type)
                if scanner_enum:
                    self.scanner = StockScanner(scanner_type=scanner_enum)
                    print(f"{self.log_prefix} ✓ Initialized StockScanner: {self.scanner_type}")
                else:
                    print(f"{self.log_prefix} ⚠ Warning: Unknown scanner_type '{self.scanner_type}', skipping scanner")
            except Exception as e:
                print(f"{self.log_prefix} ⚠ Warning: Failed to initialize scanner: {e}")

    def check_connection(self):
        """Test API connection."""
        print(f"{self.log_prefix} Testing Alpaca Paper Trading connection...")

        try:
            response = requests.get(
                f"{self.base_url}/v2/account",
                headers=self.headers
            )

            if response.status_code == 200:
                account = response.json()
                print(f"{self.log_prefix} ✓ Connected to Alpaca Paper Trading")
                print(f"{self.log_prefix}   Account Status: {account['status']}")
                print(f"{self.log_prefix}   Buying Power: ${float(account['buying_power']):,.2f}")
                print(f"{self.log_prefix}   Cash: ${float(account['cash']):,.2f}")
                print(f"{self.log_prefix}   Portfolio Value: ${float(account['portfolio_value']):,.2f}")
                return True
            else:
                print(f"{self.log_prefix} ✗ Connection failed: {response.status_code}")
                print(f"{self.log_prefix}   {response.text}")
                return False

        except Exception as e:
            print(f"{self.log_prefix} ✗ Connection error: {e}")
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

    def get_order(self, order_id: str):
        """Get order details by order ID."""
        try:
            response = requests.get(
                f"{self.base_url}/v2/orders/{order_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"{self.log_prefix} ⚠ Failed to get order {order_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"{self.log_prefix} ⚠ Error getting order {order_id}: {e}")
            return None

    def get_current_price(self, symbol: str):
        """Get current price for a symbol."""
        try:
            response = requests.get(
                f"{self.data_url}/v2/stocks/{symbol}/quotes/latest",
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                # Use ask price for current price
                return float(data.get('quote', {}).get('ap', 0))
            return None
        except Exception as e:
            print(f"{self.log_prefix} ⚠ Error getting price for {symbol}: {e}")
            return None

    def is_market_open(self):
        """Check if market is currently open."""
        try:
            response = requests.get(
                f"{self.base_url}/v2/clock",
                headers=self.headers
            )
            if response.status_code == 200:
                clock = response.json()
                return clock.get('is_open', False)
            else:
                print(f"{self.log_prefix} ⚠ Failed to get market clock: {response.status_code}")
                return False
        except Exception as e:
            print(f"{self.log_prefix} ⚠ Error checking market hours: {e}")
            return False

    def cancel_order(self, order_id: str):
        """Cancel a specific order."""
        try:
            response = requests.delete(
                f"{self.base_url}/v2/orders/{order_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                return True
            else:
                print(f"{self.log_prefix} ⚠ Failed to cancel order {order_id}: {response.status_code}")
                return False
        except Exception as e:
            print(f"{self.log_prefix} ⚠ Error cancelling order {order_id}: {e}")
            return False

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

    def detect_signal(self, symbol: str, bars: List[Dict]) -> Optional[Dict]:
        """
        Detect trading opportunities using configured detector.

        Returns:
            Dict with setup details if opportunity detected, None otherwise
        """
        # Need enough data for indicators (use safe minimum)
        min_bars = 50
        if len(bars) < min_bars:
            return None

        # Convert to DataFrame
        df = pd.DataFrame(bars)
        df['t'] = pd.to_datetime(df['t'])
        df = df.sort_values('t')

        # Rename columns to match expected format
        df = df.rename(columns={
            't': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume'
        })

        # Detect setups using configured detector
        try:
            setups = self.detector.detect_setups(df)
        except Exception as e:
            print(f"{self.log_prefix}   Error detecting signal for {symbol}: {e}")
            return None

        if not setups:
            return None

        # Get most recent setup
        latest_setup = setups[-1]

        # Only trade LONG positions for now
        if latest_setup['direction'] != 'LONG':
            return None

        # Build result dict with common fields
        result = {
            'symbol': symbol,
            'timestamp': latest_setup['timestamp'],
            'direction': 'LONG',
            'entry_price': latest_setup['entry_price'],
            'target_price': latest_setup['target'],
            'stop_loss': latest_setup['stop_loss'],
            'volume_ratio': latest_setup.get('volume_ratio', 0),
            'strategy': self.strategy_name
        }

        # Add detector-specific fields
        if self.primary_detector == 'MeanReversionDetector':
            result['rsi'] = latest_setup.get('rsi', 0)
            result['bb_distance_pct'] = latest_setup.get('bb_distance_pct', 0)
        elif self.primary_detector == 'VolatilityBreakoutDetector':
            result['range_size_pct'] = latest_setup.get('range_size_pct', 0)
            result['consolidation_duration'] = latest_setup.get('consolidation_duration', 0)

        return result

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
        """Enter a position based on trading signal."""
        symbol = event['symbol']
        direction = event['direction']
        entry_price = event['entry_price']

        # Skip if already in position or have pending order
        if symbol in self.active_positions:
            print(f"{self.log_prefix} ⚠ Already in position for {symbol}, skipping")
            return

        if symbol in self.pending_orders:
            print(f"{self.log_prefix} ⚠ Pending order exists for {symbol}, skipping")
            return

        # Check if market is open before placing order
        if not self.is_market_open():
            print(f"{self.log_prefix} ⚠ Market is CLOSED - skipping order for {symbol}")
            print(f"{self.log_prefix}    (Order would be placed outside market hours)")
            return

        # Calculate position size (number of shares)
        qty = int(self.position_size / entry_price)

        if qty < 1:
            print(f"{self.log_prefix} ⚠ Position size too small for {symbol}")
            return

        # Calculate stop loss and take profit
        side = "buy"  # LONG only for now
        stop_loss = event.get('stop_loss', entry_price * (1 - self.stop_loss_pct / 100))
        take_profit = event.get('target_price', entry_price * (1 + self.stop_loss_pct * 2 / 100))

        print(f"\n{self.log_prefix} 🔔 {self.strategy_name} SIGNAL: {symbol} {direction}")
        print(f"{self.log_prefix}    Entry: ${entry_price:.2f}")
        print(f"{self.log_prefix}    Size: {qty} shares (${qty * entry_price:,.0f})")

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

            # Track pending order (not in position yet until filled)
            order_data = {
                'symbol': symbol,
                'entry_time': entry_time,
                'expected_entry_price': entry_price,
                'qty': qty,
                'direction': direction,
                'side': side,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'order_id': order['id'],
                'transaction_id': None,  # Will be set if logging enabled
            }
            self.pending_orders[symbol] = order_data
            print(f"{self.log_prefix}    Order placed, waiting for fill...")

    def check_exit_orders_status(self, order_id: str):
        """
        Check if a position has active exit orders.

        Args:
            order_id: The entry order ID (bracket order parent)

        Returns:
            Tuple of (has_active_exit_orders: bool, exit_order_details: list)
        """
        order_info = self.get_order(order_id)

        if not order_info:
            return False, []

        order_class = order_info.get('order_class', 'simple')

        if order_class not in ['bracket', 'oco', 'oto']:
            return False, []

        # Check bracket order legs
        legs = order_info.get('legs', [])
        active_legs = []
        expired_or_canceled = []

        for leg_id in legs:
            leg_info = self.get_order(leg_id)
            if leg_info:
                leg_status = leg_info.get('status')
                if leg_status in ['pending', 'new', 'accepted', 'partially_filled']:
                    active_legs.append(leg_info)
                elif leg_status in ['expired', 'canceled', 'rejected']:
                    expired_or_canceled.append(leg_info)

        return len(active_legs) > 0, {'active': active_legs, 'expired': expired_or_canceled}

    def recreate_exit_orders(self, symbol: str, position_data: dict):
        """
        Create new exit orders for a position that lost its exit protection.

        Args:
            symbol: Stock symbol
            position_data: Position data dictionary

        Returns:
            True if exit orders were successfully created
        """
        try:
            current_price = self.get_current_price(symbol)
            if not current_price:
                print(f"{self.log_prefix} ⚠ Could not get current price for {symbol}")
                return False

            # Calculate new exit prices based on current price
            if position_data['side'] == 'buy':
                take_profit = current_price * (1 + (self.stop_loss_pct / 100) * 2)  # 2x stop loss for TP
                stop_loss = current_price * (1 - self.stop_loss_pct / 100)
            else:
                take_profit = current_price * (1 - (self.stop_loss_pct / 100) * 2)
                stop_loss = current_price * (1 + self.stop_loss_pct / 100)

            # Determine exit side
            exit_side = 'sell' if position_data['side'] == 'buy' else 'buy'

            # Create OCO order (one-cancels-other) with take profit and stop loss
            order_data = {
                'symbol': symbol,
                'qty': position_data['qty'],
                'side': exit_side,
                'type': 'limit',
                'time_in_force': 'gtc',  # Good till canceled
                'order_class': 'oco',
                'take_profit': {
                    'limit_price': round(take_profit, 2)
                },
                'stop_loss': {
                    'stop_price': round(stop_loss, 2),
                    'limit_price': round(stop_loss * 0.99 if exit_side == 'sell' else stop_loss * 1.01, 2)
                }
            }

            response = requests.post(
                f"{self.base_url}/v2/orders",
                headers=self.headers,
                json=order_data
            )

            if response.status_code in [200, 201]:
                order_response = response.json()
                print(f"{self.log_prefix} ✓ Created new exit orders for {symbol}")
                print(f"{self.log_prefix}    Current: ${current_price:.2f}")
                print(f"{self.log_prefix}    Take Profit: ${take_profit:.2f}")
                print(f"{self.log_prefix}    Stop Loss: ${stop_loss:.2f}")

                # Update position data with new exit prices
                position_data['take_profit'] = take_profit
                position_data['stop_loss'] = stop_loss

                return True
            else:
                print(f"{self.log_prefix} ✗ Failed to create exit orders for {symbol}: {response.status_code}")
                print(f"{self.log_prefix}    {response.text}")
                return False

        except Exception as e:
            print(f"{self.log_prefix} ✗ Error creating exit orders for {symbol}: {e}")
            return False

    def check_positions(self):
        """Check status of pending orders and active positions."""

        # 0. Auto-cancel stale pending orders (older than 10 minutes)
        stale_timeout_minutes = 10
        for symbol in list(self.pending_orders.keys()):
            order_data = self.pending_orders[symbol]
            order_age_minutes = (datetime.now() - order_data['entry_time']).total_seconds() / 60

            if order_age_minutes > stale_timeout_minutes:
                print(f"\n{self.log_prefix} ⚠ Auto-cancelling stale order for {symbol}")
                print(f"{self.log_prefix}    Order age: {order_age_minutes:.1f} minutes (timeout: {stale_timeout_minutes} min)")

                if self.cancel_order(order_data['order_id']):
                    print(f"{self.log_prefix}    ✓ Order cancelled successfully")
                    del self.pending_orders[symbol]
                else:
                    print(f"{self.log_prefix}    ✗ Failed to cancel order, will retry next check")

        # 1. Check pending orders to see if they've filled
        for symbol in list(self.pending_orders.keys()):
            order_data = self.pending_orders[symbol]
            order_id = order_data['order_id']

            # Get order status from Alpaca
            order_info = self.get_order(order_id)
            if not order_info:
                continue

            order_status = order_info.get('status')

            if order_status == 'filled':
                # Order filled! Move to active positions
                filled_qty = int(order_info.get('filled_qty', order_data['qty']))
                filled_avg_price = float(order_info.get('filled_avg_price', order_data['expected_entry_price']))

                print(f"\n{self.log_prefix} ✓ Order FILLED: {symbol}")
                print(f"{self.log_prefix}    Filled Price: ${filled_avg_price:.2f}")
                print(f"{self.log_prefix}    Quantity: {filled_qty}")

                # Create position entry
                position_data = {
                    'symbol': symbol,
                    'entry_time': order_data['entry_time'],
                    'entry_price': filled_avg_price,
                    'qty': filled_qty,
                    'direction': order_data['direction'],
                    'side': order_data['side'],
                    'stop_loss': order_data['stop_loss'],
                    'take_profit': order_data['take_profit'],
                    'order_id': order_id,
                    'transaction_id': None,
                }

                self.active_positions[symbol] = position_data
                del self.pending_orders[symbol]

                # Save to database
                if self.enable_persistence:
                    self._save_position(symbol, position_data)

                # Log trade entry
                if self.transaction_logger:
                    try:
                        transaction_id = self.transaction_logger.log_trade_entry(
                            symbol=symbol,
                            direction="LONG" if position_data['side'] == "buy" else "SHORT",
                            entry_time=position_data['entry_time'],
                            entry_price=filled_avg_price,
                            position_size=filled_qty,
                            stop_loss=position_data['stop_loss'],
                            target=position_data['take_profit'],
                            strategy_name=self.strategy_name,
                            trade_id=order_id,
                        )
                        self.active_positions[symbol]['transaction_id'] = transaction_id
                    except Exception as e:
                        print(f"{self.log_prefix} ⚠ Warning: Failed to log trade entry: {e}")

            elif order_status in ['canceled', 'expired', 'rejected']:
                # Order not filled, remove from pending
                print(f"\n{self.log_prefix} ⚠ Order {order_status.upper()}: {symbol}")
                # CRITICAL FIX: Update database BEFORE removing from pending
                if self.enable_persistence and hasattr(self, 'order_sync'):
                    self.order_sync.sync_order_status(order_id, order_info)
                    print(f"{self.log_prefix}    Logged to OrderJournal with status: {order_status}")
                del self.pending_orders[symbol]

        # 2. Check active positions to see if they've closed
        if not self.active_positions:
            return

        # Get current positions from Alpaca
        positions = self.get_positions()
        position_symbols = {p['symbol'] for p in positions}

        # Check if any of our tracked positions are closed
        for symbol in list(self.active_positions.keys()):
            if symbol not in position_symbols:
                # Position closed - get actual exit details from order
                pos = self.active_positions.pop(symbol)
                exit_time = datetime.now()

                # Get exit order details (stop loss or take profit leg of bracket order)
                order_info = self.get_order(pos['order_id'])

                exit_price = pos['entry_price']  # Default fallback
                exit_reason = "unknown"

                if order_info:
                    # Check bracket order legs for exit details
                    # SYNC EXIT ORDER DETAILS TO DATABASE
                    if self.enable_persistence and hasattr(self, 'order_sync'):
                        self.order_sync.sync_closed_positions(pos, order_info)
                    legs = order_info.get('legs', [])
                    for leg_id in legs:
                        leg_info = self.get_order(leg_id)
                        if leg_info and leg_info.get('status') == 'filled':
                            exit_price = float(leg_info.get('filled_avg_price', exit_price))
                            leg_type = leg_info.get('order_class', '')
                            if 'stop' in leg_type.lower():
                                exit_reason = "stop_loss"
                            elif 'limit' in leg_type.lower():
                                exit_reason = "take_profit"
                            else:
                                exit_reason = "bracket_filled"
                            break

                # Calculate P&L
                if pos['side'] == 'buy':
                    pnl = (exit_price - pos['entry_price']) * pos['qty']
                else:  # sell/short
                    pnl = (pos['entry_price'] - exit_price) * pos['qty']

                pnl_pct = (pnl / (pos['entry_price'] * pos['qty'])) * 100 if pos['entry_price'] > 0 else 0

                duration_minutes = int((exit_time - pos['entry_time']).seconds / 60)

                print(f"\n{self.log_prefix} ✓ Position CLOSED: {symbol}")
                print(f"{self.log_prefix}    Entry: ${pos['entry_price']:.2f} → Exit: ${exit_price:.2f}")
                print(f"{self.log_prefix}    P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
                print(f"{self.log_prefix}    Reason: {exit_reason}")
                print(f"{self.log_prefix}    Duration: {duration_minutes} minutes")

                trade_data = {
                    'symbol': symbol,
                    'entry_time': pos['entry_time'],
                    'exit_time': exit_time,
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'direction': pos['direction'],
                    'qty': pos['qty'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                }
                self.closed_trades.append(trade_data)

                # Update position in database
                if self.enable_persistence:
                    self._update_position_closed(symbol, pos)

                # Log trade exit with actual P&L
                if self.transaction_logger and pos.get('transaction_id'):
                    try:
                        self.transaction_logger.log_trade_exit(
                            transaction_id=pos['transaction_id'],
                            exit_time=exit_time,
                            exit_price=exit_price,
                            exit_reason=exit_reason,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            return_pct=pnl_pct,
                            max_adverse_excursion=0.0,
                            max_favorable_excursion=0.0,
                            trade_id=pos['order_id'],
                        )
                    except Exception as e:
                        print(f"{self.log_prefix} ⚠ Warning: Failed to log trade exit: {e}")

        # 3. Check active positions for expired/canceled exit orders
        for symbol in list(self.active_positions.keys()):
            pos = self.active_positions[symbol]
            order_id = pos.get('order_id')

            if not order_id:
                continue

            # Check if position has active exit orders
            has_exit_orders, exit_details = self.check_exit_orders_status(order_id)

            if not has_exit_orders and exit_details.get('expired'):
                # Position has expired/canceled exit orders - needs protection
                print(f"\n{self.log_prefix} ⚠ Position {symbol} has NO active exit orders!")
                print(f"{self.log_prefix}    {len(exit_details['expired'])} exit order(s) expired/canceled")

                # Try to recreate exit orders
                if self.recreate_exit_orders(symbol, pos):
                    print(f"{self.log_prefix}    ✓ Position {symbol} is now protected")
                else:
                    print(f"{self.log_prefix}    ✗ WARNING: Could not protect {symbol} - position at risk!")

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
                    instance_id=self.instance_id,
                    strategy_name=self.strategy_name if hasattr(self, 'strategy_name') else None,
                )
                session.add(trading_session)
                session.commit()
                print(f"{self.log_prefix} ✓ Session {self.session_id[:8]} created in database")
        except Exception as e:
            print(f"{self.log_prefix} ⚠ Warning: Failed to create session record: {e}")

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
            print(f"{self.log_prefix} ⚠ Warning: Failed to save position {symbol}: {e}")

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
            print(f"{self.log_prefix} ⚠ Warning: Failed to update position {symbol}: {e}")

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
            print(f"{self.log_prefix}    💾 Checkpoint saved: {len(self.active_positions)} active positions")

        except Exception as e:
            print(f"{self.log_prefix} ⚠ Warning: Failed to save checkpoint: {e}")

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
                    print(f"{self.log_prefix} ✓ Session {self.session_id[:8]} finalized in database")
        except Exception as e:
            print(f"{self.log_prefix} ⚠ Warning: Failed to finalize session: {e}")

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
        """Scan symbols for trading signals with optional scanner filtering."""
        print(f"\n{self.log_prefix} ⏰ {datetime.now().strftime('%H:%M:%S')} - Scanning {len(symbols)} symbols...")

        # Get latest bars for all symbols
        all_symbols = symbols.copy()

        # Add SPY as benchmark if not already in list (for relative strength)
        if 'SPY' not in all_symbols:
            all_symbols.append('SPY')

        bars_data = self.get_latest_bars(all_symbols, timeframe='5Min', limit=100)

        # Apply scanner filtering if configured
        filtered_symbols = symbols.copy()

        if self.scanner and self.scanner_type == 'relative_strength':
            # Use relative strength scanner logic
            filtered_symbols = self._filter_by_relative_strength(symbols, bars_data)
        elif hasattr(self, 'use_relative_strength') and self.use_relative_strength:
            # Legacy relative strength filtering
            filtered_symbols = self._filter_by_relative_strength(symbols, bars_data)

        # If no scanner configured, use all symbols
        if not filtered_symbols:
            filtered_symbols = symbols

        signals_found = 0

        for symbol in filtered_symbols:
            if symbol not in bars_data:
                continue

            bars = bars_data[symbol]

            if not bars:
                continue

            # Check for trading signal using configured detector
            event = self.detect_signal(symbol, bars)

            if event:
                signals_found += 1
                self._print_signal(event)

                # Enter position
                self.enter_position(event)

        if signals_found == 0:
            print(f"{self.log_prefix}    No signals detected")

    def _filter_by_relative_strength(self, symbols: List[str], bars_data: Dict) -> List[str]:
        """Filter symbols by relative strength vs SPY."""
        if 'SPY' not in bars_data:
            return symbols

        spy_bars = bars_data['SPY']
        if not spy_bars or len(spy_bars) < self.relative_strength_period:
            return symbols

        # Calculate SPY return
        spy_return = (spy_bars[-1]['c'] - spy_bars[-self.relative_strength_period]['c']) / spy_bars[-self.relative_strength_period]['c']

        # Calculate relative strength for each stock
        rs_results = []
        for symbol in symbols:
            if symbol == 'SPY' or symbol not in bars_data:
                continue

            bars = bars_data[symbol]
            if not bars or len(bars) < self.relative_strength_period:
                continue

            # Calculate stock return
            stock_return = (bars[-1]['c'] - bars[-self.relative_strength_period]['c']) / bars[-self.relative_strength_period]['c']

            # Relative strength = stock outperformance vs SPY
            relative_strength = stock_return - spy_return

            rs_results.append({
                'symbol': symbol,
                'relative_strength': relative_strength,
                'stock_return': stock_return,
                'spy_return': spy_return
            })

        # Filter to only stocks with positive relative strength (outperforming SPY)
        strong_stocks = [r for r in rs_results if r['relative_strength'] > 0]
        filtered_symbols = [r['symbol'] for r in strong_stocks]

        # Sort by relative strength
        strong_stocks.sort(key=lambda x: x['relative_strength'], reverse=True)

        # Show filtering results
        if strong_stocks:
            print(f"{self.log_prefix}    ✓ Relative Strength Filter: {len(filtered_symbols)}/{len(symbols)} stocks outperforming SPY")
            top_performers = ', '.join(["{symbol}({rs:+.1f}%)".format(symbol=r['symbol'], rs=r['relative_strength']*100) for r in strong_stocks[:5]])
            print(f"{self.log_prefix}       Top performers: {top_performers}")
        else:
            print(f"{self.log_prefix}    ⚠ Relative Strength Filter: No stocks outperforming SPY")

        return filtered_symbols

    def _print_signal(self, event: Dict):
        """Print signal details based on detector type."""
        symbol = event['symbol']
        direction = event['direction']
        volume_ratio = event.get('volume_ratio', 0)

        if self.primary_detector == 'MeanReversionDetector':
            rsi = event.get('rsi', 0)
            bb_dist = event.get('bb_distance_pct', 0)
            print(f"{self.log_prefix}    📊 {symbol}: {direction} RSI={rsi:.1f}, BB Distance={bb_dist:.1f}%, Vol={volume_ratio:.1f}x")
        elif self.primary_detector == 'VolatilityBreakoutDetector':
            range_size = event.get('range_size_pct', 0)
            consolidation = event.get('consolidation_duration', 0)
            print(f"{self.log_prefix}    📊 {symbol}: {direction} Range={range_size:.1f}%, Consolidation={consolidation} bars, Vol={volume_ratio:.1f}x")
        else:
            print(f"{self.log_prefix}    📊 {symbol}: {direction} Vol={volume_ratio:.1f}x")

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
        print(f"{self.log_prefix} ALPACA PAPER TRADING - LIVE SESSION")
        print("=" * 80)
        print(f"{self.log_prefix} Session ID: {self.session_id[:8]}")
        print(f"{self.log_prefix} Instance ID: {self.instance_id}")
        print(f"{self.log_prefix} Symbols: {', '.join(symbols)}")
        print(f"{self.log_prefix} Duration: {'Continuous' if duration_minutes == 0 else f'{duration_minutes} minutes'}")
        print(f"{self.log_prefix} Scan Interval: {scan_interval_seconds} seconds")
        print(f"{self.log_prefix} Strategy: {self.strategy_name}")
        print(f"{self.log_prefix} Detector: {self.primary_detector}")
        if self.scanner_type:
            print(f"{self.log_prefix} Scanner: {self.scanner_type}")
        print(f"{self.log_prefix} Position Size: ${self.position_size:,}")
        print(f"{self.log_prefix} Stop Loss: {self.stop_loss_pct}%")
        if self.enable_persistence:
            print(f"{self.log_prefix} State Persistence: ✓ Enabled (checkpoints every {self.checkpoint_interval}s)")
        else:
            print(f"{self.log_prefix} State Persistence: ✗ Disabled")
        print("=" * 80 + "\n")

        # Check initial account status
        account = self.get_account()
        initial_value = float(account['portfolio_value'])
        print(f"{self.log_prefix} Starting Portfolio Value: ${initial_value:,.2f}\n")

        # Create session record
        if self.enable_persistence:
            self._create_session_record(symbols, duration_minutes, scan_interval_seconds, initial_value)

        start_time = datetime.now()
        # If duration is 0, run indefinitely
        end_time = start_time + timedelta(minutes=duration_minutes) if duration_minutes > 0 else None

        try:
            while True:
                # Check if we should stop (only if not continuous mode)
                if end_time and datetime.now() >= end_time:
                    break

                # Scan for signals
                self.scan_for_signals(symbols)

                # Check existing positions
                self.check_positions()

                # Save checkpoint periodically
                if self.enable_persistence:
                    self._save_checkpoint()

                # Status update
                if end_time:
                    remaining = int((end_time - datetime.now()).seconds / 60)
                    print(f"{self.log_prefix}    Pending orders: {len(self.pending_orders)}, Active positions: {len(self.active_positions)}, Closed trades: {len(self.closed_trades)}, Time remaining: {remaining} min")
                else:
                    runtime = int((datetime.now() - start_time).total_seconds() / 60)
                    print(f"{self.log_prefix}    Pending orders: {len(self.pending_orders)}, Active positions: {len(self.active_positions)}, Closed trades: {len(self.closed_trades)}, Runtime: {runtime} min")

                # Wait before next scan
                time.sleep(scan_interval_seconds)

        except KeyboardInterrupt:
            print(f"\n\n{self.log_prefix} ⚠ Interrupted by user")

        # Final report
        print("\n" + "=" * 80)
        print(f"{self.log_prefix} SESSION COMPLETE")
        print("=" * 80)

        account = self.get_account()
        final_value = float(account['portfolio_value'])
        pnl = final_value - initial_value

        print(f"\n{self.log_prefix} Initial Portfolio Value: ${initial_value:,.2f}")
        print(f"{self.log_prefix} Final Portfolio Value:   ${final_value:,.2f}")
        print(f"{self.log_prefix} P&L:                     ${pnl:,.2f} ({pnl/initial_value*100:+.2f}%)")
        print(f"\n{self.log_prefix} Pending Orders:      {len(self.pending_orders)}")
        print(f"{self.log_prefix} Total Closed Trades: {len(self.closed_trades)}")
        print(f"{self.log_prefix} Active Positions:    {len(self.active_positions)}")

        if self.closed_trades:
            print(f"\n{self.log_prefix} Closed Trades:")
            for trade in self.closed_trades:
                duration = (trade['exit_time'] - trade['entry_time']).seconds // 60
                print(f"{self.log_prefix}   {trade['symbol']}: {trade['direction']}, {duration} min")

        # Finalize session in database
        if self.enable_persistence:
            self._finalize_session(final_value, pnl)

        print("\n" + "=" * 80 + "\n")


def load_config_file(config_path: str) -> Dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"ERROR: Failed to load config file: {e}")
        sys.exit(1)


def main():
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Alpaca Paper Trading - Multi-Instance Support")
    parser.add_argument("--api-key", help="Alpaca API Key (or set ALPACA_API_KEY env var)")
    parser.add_argument("--api-secret", help="Alpaca API Secret (or set ALPACA_API_SECRET env var)")
    parser.add_argument("--instance-id", type=int, default=1, help="Instance ID (1-5) for multi-instance tracking")
    parser.add_argument("--strategy", type=str, help="Strategy name from config.yaml (e.g., 'mean-reversion-rs')")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml file")
    parser.add_argument("--symbols", help="Symbols to trade (comma-separated, overrides config)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in minutes (0 for continuous)")
    parser.add_argument("--interval", type=int, help="Scan interval in seconds (overrides config)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously (same as --duration 0)")
    parser.add_argument("--no-persistence", action="store_true", help="Disable database persistence (faster startup, no crash recovery)")

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

    # Load configuration if strategy or instance_id specified
    config_dict = None
    symbols = None
    scan_interval = args.interval or 60

    if args.config or args.strategy or args.instance_id >= 1:
        # Load config.yaml
        full_config = load_config_file(args.config)

        # Determine which strategy to use
        if args.strategy:
            # Use specified strategy
            strategy_name = args.strategy
            if strategy_name not in full_config.get('trading_strategies', {}):
                print(f"ERROR: Strategy '{strategy_name}' not found in config.yaml")
                print(f"Available strategies: {', '.join(full_config.get('trading_strategies', {}).keys())}")
                return
            config_dict = full_config['trading_strategies'][strategy_name]
        else:
            # Use instance configuration
            instance_id = args.instance_id
            if instance_id not in full_config.get('trading_instances', {}):
                print(f"ERROR: Instance ID {instance_id} not found in config.yaml")
                print(f"Available instances: {', '.join(map(str, full_config.get('trading_instances', {}).keys()))}")
                return

            instance_config = full_config['trading_instances'][instance_id]
            strategy_name = instance_config['strategy']

            if strategy_name not in full_config.get('trading_strategies', {}):
                print(f"ERROR: Strategy '{strategy_name}' not found in config.yaml")
                return

            config_dict = full_config['trading_strategies'][strategy_name]

            # Get symbols and interval from instance config
            if not args.symbols:
                symbols = instance_config.get('symbols', [])
            if not args.interval:
                scan_interval = instance_config.get('interval_seconds', 60)

            print(f"[INST-{instance_id}] Loading instance configuration:")
            print(f"[INST-{instance_id}]   Name: {instance_config.get('name')}")
            print(f"[INST-{instance_id}]   Strategy: {strategy_name}")
            print(f"[INST-{instance_id}]   Description: {instance_config.get('description')}")

    # Parse symbols (command line overrides config)
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    elif symbols is None:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

    # Determine duration (0 or --continuous means run indefinitely)
    duration_minutes = 0 if args.continuous else args.duration

    # Create trader
    trader = AlpacaPaperTrader(
        api_key=api_key,
        api_secret=api_secret,
        instance_id=args.instance_id,
        config_dict=config_dict,
        enable_persistence=not args.no_persistence,
    )

    # Test connection
    if not trader.check_connection():
        print(f"\n[INST-{args.instance_id}] Failed to connect to Alpaca. Please check your API credentials.")
        return

    print(f"\n[INST-{args.instance_id}] ✓ Ready to start paper trading!\n")
    # input("Press ENTER to begin...")  # Commented out for automated runs

    # Run paper trading
    trader.run_paper_trading(
        symbols=symbols,
        duration_minutes=duration_minutes,
        scan_interval_seconds=scan_interval,
    )


if __name__ == "__main__":
    main()
