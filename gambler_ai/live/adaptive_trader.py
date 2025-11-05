"""
Adaptive Trader

Combines stock scanner with adaptive strategy selection for live trading.
"""

import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.live.scanner_runner import LiveScannerRunner


class AdaptiveTrader:
    """
    Live trading with adaptive strategy selection and stock scanning.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        scanner: LiveScannerRunner = None,
        use_volatility_filter: bool = True,
        risk_per_trade: float = 0.01,
        stop_loss_pct: float = 1.0,
        take_profit_pct: float = 3.0,
    ):
        """
        Initialize adaptive trader.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            scanner: LiveScannerRunner instance (optional)
            use_volatility_filter: Use volatility-adjusted strategy selection
            risk_per_trade: Risk per trade as % of capital (0.01 = 1%)
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.scanner = scanner
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        # Alpaca endpoints
        self.base_url = "https://paper-api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"

        self.headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret,
            'accept': 'application/json',
        }

        # Create adaptive selector
        regime_detector = RegimeDetector(high_volatility_threshold=0.012)
        self.adaptive_selector = AdaptiveStrategySelector(
            regime_detector=regime_detector,
            use_volatility_filter=use_volatility_filter,
        )

        # Trading state
        self.active_positions = {}
        self.closed_trades = []
        self.selected_symbols = []

        print(f"✓ AdaptiveTrader initialized")
        print(f"  Volatility filter: {use_volatility_filter}")
        print(f"  Risk per trade: {risk_per_trade*100}%")
        print(f"  Stop loss: {stop_loss_pct}% | Take profit: {take_profit_pct}%")

    def get_account(self) -> Dict:
        """Get account information."""
        url = f"{self.base_url}/v2/account"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_latest_bars(self, symbol: str, timeframe: str = "5Min", limit: int = 200) -> pd.DataFrame:
        """Get latest bars for a symbol."""
        url = f"{self.data_url}/v2/stocks/{symbol}/bars"
        params = {
            'timeframe': timeframe,
            'limit': limit,
            'feed': 'iex',
        }

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        data = response.json()
        bars = data['bars']

        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['t'])
        df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        return df

    def detect_setups(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """
        Detect trading setups using adaptive strategy.

        Args:
            symbol: Stock symbol
            df: Market data DataFrame

        Returns:
            List of detected setups
        """
        # Get regime info
        regime_info = self.adaptive_selector.get_regime_info(df)

        # Detect setups using selected strategy
        setups = self.adaptive_selector.detect_setups(df)

        # Add symbol and regime info
        for setup in setups:
            setup['symbol'] = symbol
            setup['regime'] = regime_info['regime']
            setup['confidence'] = regime_info['confidence']
            setup['is_high_volatility'] = regime_info['is_high_volatility']

        return setups

    def place_order(self, symbol: str, side: str, qty: int, stop_loss: float, take_profit: float) -> bool:
        """Place a bracket order with stop loss and take profit."""
        try:
            url = f"{self.base_url}/v2/orders"

            order_data = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': 'market',
                'time_in_force': 'gtc',
                'order_class': 'bracket',
                'stop_loss': {'stop_price': stop_loss},
                'take_profit': {'limit_price': take_profit},
            }

            response = requests.post(url, headers=self.headers, json=order_data)
            response.raise_for_status()

            print(f"✓ Order placed: {side.upper()} {qty} {symbol} @ market")
            print(f"  Stop loss: ${stop_loss:.2f} | Take profit: ${take_profit:.2f}")

            return True

        except Exception as e:
            print(f"⚠ Order failed for {symbol}: {e}")
            return False

    def scan_for_signals(self) -> None:
        """Scan selected symbols for trading signals."""
        for symbol in self.selected_symbols:
            if symbol in self.active_positions:
                continue

            try:
                # Get market data
                df = self.get_latest_bars(symbol)

                if len(df) < 200:
                    continue

                # Detect setups
                setups = self.detect_setups(symbol, df)

                if not setups:
                    continue

                # Take first setup
                setup = setups[0]

                # Get current price
                current_price = df['close'].iloc[-1]

                # Calculate position size
                account = self.get_account()
                capital = float(account['portfolio_value'])
                position_value = capital * self.risk_per_trade
                qty = int(position_value / current_price)

                if qty < 1:
                    continue

                # Calculate stop loss and take profit
                direction = setup['direction']

                if direction == 'LONG':
                    stop_loss = current_price * (1 - self.stop_loss_pct / 100)
                    take_profit = current_price * (1 + self.take_profit_pct / 100)
                    side = 'buy'
                else:
                    stop_loss = current_price * (1 + self.stop_loss_pct / 100)
                    take_profit = current_price * (1 - self.take_profit_pct / 100)
                    side = 'sell'

                # Print signal
                print(f"\n🔔 ADAPTIVE SIGNAL: {symbol} {direction}")
                print(f"  Strategy: {setup.get('strategy_used', 'N/A')}")
                print(f"  Regime: {setup['regime']} ({setup['confidence']:.1%} confidence)")
                if setup.get('is_high_volatility'):
                    print(f"  Volatility: 🔴 HIGH")
                else:
                    print(f"  Volatility: 🟢 LOW")
                print(f"  Price: ${current_price:.2f}")
                print(f"  Qty: {qty}")

                # Place order
                if self.place_order(symbol, side, qty, stop_loss, take_profit):
                    self.active_positions[symbol] = {
                        'entry_price': current_price,
                        'qty': qty,
                        'direction': direction,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'entry_time': datetime.now(),
                        'strategy': setup.get('strategy_used', 'N/A'),
                        'regime': setup['regime'],
                    }

            except Exception as e:
                print(f"⚠ Error scanning {symbol}: {e}")

    def check_positions(self) -> None:
        """Check status of active positions."""
        try:
            url = f"{self.base_url}/v2/positions"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            positions = response.json()
            current_symbols = {p['symbol'] for p in positions}

            # Check for closed positions
            for symbol in list(self.active_positions.keys()):
                if symbol not in current_symbols:
                    # Position closed
                    pos_info = self.active_positions[symbol]
                    self.closed_trades.append(pos_info)
                    del self.active_positions[symbol]
                    print(f"✓ Position closed: {symbol}")

        except Exception as e:
            print(f"⚠ Error checking positions: {e}")

    def run_trading_session(
        self,
        duration_minutes: int = 60,
        scan_interval_seconds: int = 60,
        rescan_stocks_minutes: int = 0,
    ) -> None:
        """
        Run live trading session.

        Args:
            duration_minutes: How long to run (minutes)
            scan_interval_seconds: How often to scan for signals (seconds)
            rescan_stocks_minutes: How often to re-run stock scanner (0 = once at start)
        """
        print("\n" + "=" * 80)
        print("ADAPTIVE TRADING SESSION")
        print("=" * 80)
        print(f"Duration: {duration_minutes} minutes")
        print(f"Scan Interval: {scan_interval_seconds} seconds")

        if rescan_stocks_minutes > 0:
            print(f"Stock Re-scan: Every {rescan_stocks_minutes} minutes")
        else:
            print("Stock Re-scan: Once at start only")

        print("=" * 80 + "\n")

        # Initial stock scan
        if self.scanner:
            print("Running initial stock scanner...")
            self.selected_symbols = self.scanner.get_selected_symbols()
            print(f"\n✓ Selected {len(self.selected_symbols)} stocks: {', '.join(self.selected_symbols)}\n")
        else:
            print("⚠ No scanner configured - using default symbols")
            self.selected_symbols = ["AAPL", "NVDA", "TSLA"]

        # Check initial account status
        account = self.get_account()
        initial_value = float(account['portfolio_value'])
        print(f"Starting Portfolio Value: ${initial_value:,.2f}\n")

        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        last_stock_scan = start_time

        try:
            while datetime.now() < end_time:
                # Re-scan stocks if needed
                if rescan_stocks_minutes > 0:
                    if (datetime.now() - last_stock_scan).seconds / 60 >= rescan_stocks_minutes:
                        print("\n🔄 Re-scanning stocks...")
                        self.selected_symbols = self.scanner.get_selected_symbols()
                        print(f"✓ Selected stocks: {', '.join(self.selected_symbols)}\n")
                        last_stock_scan = datetime.now()

                # Scan for signals
                self.scan_for_signals()

                # Check existing positions
                self.check_positions()

                # Status update
                remaining = int((end_time - datetime.now()).seconds / 60)
                print(f"   Active: {len(self.active_positions)}, Closed: {len(self.closed_trades)}, Time: {remaining} min")

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
            for i, trade in enumerate(self.closed_trades, 1):
                symbol = list(trade.keys())[0] if isinstance(trade, dict) else "N/A"
                print(f"  {i}. {symbol}")

        print("\n✓ Trading session complete!\n")
