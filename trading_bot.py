"""
Automated Trading Bot with Adaptive Strategy Selection

This bot combines:
1. Real-time market data from Alpaca WebSocket
2. Adaptive strategy selection based on market regime
3. Automated order execution with risk management
4. Stop loss and take profit management
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from gambler_ai.data_ingestion import AlpacaWebSocketStreamer
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from examples.alpaca_order_types_example import AlpacaTradingClient


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingBot:
    """
    Automated trading bot with adaptive strategy selection.

    Features:
    - Real-time market data streaming
    - Automatic regime detection (BULL/BEAR/RANGE)
    - Strategy selection based on regime
    - Risk management with stop loss
    - Position sizing
    - Paper trading support
    """

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        symbols: List[str] = ["SPY", "QQQ", "AAPL"],
        max_position_size: float = 10000.0,  # Max $ per position
        risk_per_trade: float = 0.02,  # Risk 2% per trade
        stop_loss_pct: float = 0.03,  # 3% stop loss
        take_profit_pct: float = 0.06,  # 6% take profit (2:1 R:R)
        paper_trading: bool = True,
    ):
        """
        Initialize trading bot.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            symbols: List of symbols to trade
            max_position_size: Maximum $ per position
            risk_per_trade: Risk % per trade
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            paper_trading: Use paper trading account
        """
        self.symbols = symbols
        self.max_position_size = max_position_size
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.paper_trading = paper_trading

        # Initialize Alpaca clients
        self.trading_client = AlpacaTradingClient(
            api_key=api_key or os.getenv("ALPACA_API_KEY", "PKJUPGKDCCIMZKPDXUFXHM3E4D"),
            api_secret=api_secret or os.getenv("ALPACA_API_SECRET", "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"),
        )

        self.streamer = AlpacaWebSocketStreamer(
            api_key=api_key or os.getenv("ALPACA_API_KEY", "PKJUPGKDCCIMZKPDXUFXHM3E4D"),
            api_secret=api_secret or os.getenv("ALPACA_API_SECRET", "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"),
            feed="iex",
            paper=paper_trading,
        )

        # Initialize strategy selector
        self.strategy_selector = AdaptiveStrategySelector(
            use_volatility_filter=True
        )

        # Data buffers for each symbol
        self.price_data: Dict[str, pd.DataFrame] = {symbol: pd.DataFrame() for symbol in symbols}
        self.bar_data: Dict[str, List[Dict]] = {symbol: [] for symbol in symbols}

        # Track positions and orders
        self.positions: Dict[str, Dict] = {}
        self.active_orders: Dict[str, List[str]] = {}  # symbol -> [order_ids]

        # Current regime and strategy
        self.current_regime: Dict[str, str] = {}
        self.current_strategy: Dict[str, str] = {}

        # Performance tracking
        self.trades_executed = 0
        self.wins = 0
        self.losses = 0

    def start(self):
        """Start the trading bot."""
        logger.info("=" * 60)
        logger.info("Starting Automated Trading Bot")
        logger.info("=" * 60)
        logger.info(f"Symbols: {self.symbols}")
        logger.info(f"Max Position Size: ${self.max_position_size:,.2f}")
        logger.info(f"Risk Per Trade: {self.risk_per_trade * 100:.1f}%")
        logger.info(f"Stop Loss: {self.stop_loss_pct * 100:.1f}%")
        logger.info(f"Take Profit: {self.take_profit_pct * 100:.1f}%")
        logger.info(f"Paper Trading: {self.paper_trading}")
        logger.info("=" * 60)

        # Check account
        try:
            account = self.trading_client.get_account()
            logger.info(f"Account Status: {account['status']}")
            logger.info(f"Buying Power: ${float(account['buying_power']):,.2f}")
            logger.info(f"Portfolio Value: ${float(account['portfolio_value']):,.2f}")
        except Exception as e:
            logger.error(f"Could not connect to Alpaca: {e}")
            logger.error("Please check your API credentials")
            return

        # Connect to WebSocket
        logger.info("\nConnecting to real-time data stream...")
        self.streamer.connect()
        self.streamer.start_processing()

        # Add handlers
        self.streamer.add_bar_handler(self._on_bar)

        # Subscribe to bars (1-minute OHLCV)
        logger.info(f"Subscribing to {self.symbols}...")
        self.streamer.subscribe_bars(self.symbols)

        logger.info("\n✓ Trading bot is LIVE!")
        logger.info("Monitoring market and generating signals...")
        logger.info("Press Ctrl+C to stop\n")

        try:
            # Main loop
            while True:
                time.sleep(60)  # Check every minute
                self._check_positions()
                self._log_status()

        except KeyboardInterrupt:
            logger.info("\n\nStopping trading bot...")
            self.stop()

    def stop(self):
        """Stop the trading bot."""
        logger.info("Closing all positions...")
        self._close_all_positions()

        logger.info("Disconnecting from data stream...")
        self.streamer.disconnect()

        logger.info("\nTrading Bot Summary:")
        logger.info(f"  Total Trades: {self.trades_executed}")
        logger.info(f"  Wins: {self.wins}")
        logger.info(f"  Losses: {self.losses}")
        if self.trades_executed > 0:
            win_rate = (self.wins / self.trades_executed) * 100
            logger.info(f"  Win Rate: {win_rate:.1f}%")

        logger.info("\n✓ Trading bot stopped")

    def _on_bar(self, bar: Dict):
        """Handle incoming bar data."""
        symbol = bar["S"]

        if symbol not in self.symbols:
            return

        # Convert to OHLCV format
        timestamp = pd.to_datetime(bar["t"])

        new_bar = {
            "timestamp": timestamp,
            "open": float(bar["o"]),
            "high": float(bar["h"]),
            "low": float(bar["l"]),
            "close": float(bar["c"]),
            "volume": int(bar["v"]),
        }

        # Add to buffer
        self.bar_data[symbol].append(new_bar)

        # Keep last 500 bars (for strategy calculation)
        if len(self.bar_data[symbol]) > 500:
            self.bar_data[symbol].pop(0)

        # Update DataFrame
        if len(self.bar_data[symbol]) >= 50:  # Need minimum data
            self.price_data[symbol] = pd.DataFrame(self.bar_data[symbol])
            self.price_data[symbol].set_index("timestamp", inplace=True)

            # Generate trading signal
            self._generate_signal(symbol)

    def _generate_signal(self, symbol: str):
        """Generate trading signal using adaptive strategy."""
        df = self.price_data[symbol]

        if len(df) < 200:  # Need enough data for regime detection
            return

        # Detect regime
        regime, confidence = self.strategy_selector.regime_detector.detect_regime_with_confidence(df)

        # Track regime changes
        if self.current_regime.get(symbol) != regime:
            logger.info(f"\n🔄 {symbol}: Regime changed to {regime} (confidence: {confidence:.2f})")
            self.current_regime[symbol] = regime

        # Select strategy
        strategy_name, strategy = self.strategy_selector.select_strategy(df)

        # Track strategy changes
        if self.current_strategy.get(symbol) != strategy_name:
            logger.info(f"📊 {symbol}: Switched to {strategy_name} strategy")
            self.current_strategy[symbol] = strategy_name

        # Check if we already have a position
        if symbol in self.positions:
            return  # Already in position

        # Generate signal based on strategy
        try:
            # Each strategy has a detect() method that returns signals
            if hasattr(strategy, 'detect'):
                signals = strategy.detect(df)

                if signals and len(signals) > 0:
                    latest_signal = signals.iloc[-1]

                    # Check for BUY signal
                    if hasattr(latest_signal, 'action') and latest_signal['action'] == 'BUY':
                        self._execute_buy(symbol, latest_signal, regime, strategy_name)

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")

    def _execute_buy(self, symbol: str, signal: pd.Series, regime: str, strategy: str):
        """Execute buy order with risk management."""
        current_price = float(self.price_data[symbol]['close'].iloc[-1])

        # Calculate position size based on risk
        account = self.trading_client.get_account()
        buying_power = float(account['buying_power'])

        # Position size: min(max_position_size, risk-based size)
        risk_amount = buying_power * self.risk_per_trade
        position_value = min(self.max_position_size, risk_amount / self.stop_loss_pct)

        qty = int(position_value / current_price)

        if qty < 1:
            logger.info(f"⚠️  {symbol}: Position size too small (${position_value:.2f})")
            return

        # Calculate stop loss and take profit prices
        stop_loss_price = current_price * (1 - self.stop_loss_pct)
        take_profit_price = current_price * (1 + self.take_profit_pct)

        logger.info(f"\n🎯 {symbol}: {strategy} BUY Signal (Regime: {regime})")
        logger.info(f"   Price: ${current_price:.2f}")
        logger.info(f"   Quantity: {qty} shares")
        logger.info(f"   Position Value: ${qty * current_price:,.2f}")
        logger.info(f"   Stop Loss: ${stop_loss_price:.2f} (-{self.stop_loss_pct*100:.1f}%)")
        logger.info(f"   Take Profit: ${take_profit_price:.2f} (+{self.take_profit_pct*100:.1f}%)")

        try:
            # Place bracket order (entry + take profit + stop loss)
            order = self.trading_client.session.post(
                f"{self.trading_client.base_url}/v2/orders",
                json={
                    "symbol": symbol,
                    "qty": qty,
                    "side": "buy",
                    "type": "market",
                    "time_in_force": "day",
                    "order_class": "bracket",
                    "take_profit": {
                        "limit_price": f"{take_profit_price:.2f}"
                    },
                    "stop_loss": {
                        "stop_price": f"{stop_loss_price:.2f}"
                    }
                }
            )

            if order.status_code in [200, 201]:
                order_data = order.json()
                order_id = order_data['id']

                # Track position
                self.positions[symbol] = {
                    "qty": qty,
                    "entry_price": current_price,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "order_id": order_id,
                    "strategy": strategy,
                    "regime": regime,
                    "entry_time": datetime.now(),
                }

                self.trades_executed += 1

                logger.info(f"✅ {symbol}: Order placed! (ID: {order_id})")

            else:
                logger.error(f"❌ {symbol}: Order failed - {order.text}")

        except Exception as e:
            logger.error(f"❌ {symbol}: Error placing order - {e}")

    def _check_positions(self):
        """Check and manage open positions."""
        try:
            positions = self.trading_client.get_positions()

            # Update tracked positions
            current_symbols = {pos['symbol'] for pos in positions}

            # Check for closed positions
            for symbol in list(self.positions.keys()):
                if symbol not in current_symbols:
                    # Position was closed
                    pos = self.positions[symbol]
                    entry_price = pos['entry_price']

                    # Estimate if it was win or loss (actual fill price may differ)
                    logger.info(f"\n📉 {symbol}: Position closed")
                    logger.info(f"   Entry: ${entry_price:.2f}")
                    logger.info(f"   Strategy: {pos['strategy']}")
                    logger.info(f"   Regime: {pos['regime']}")

                    # Remove from tracking
                    del self.positions[symbol]

        except Exception as e:
            logger.error(f"Error checking positions: {e}")

    def _close_all_positions(self):
        """Close all open positions."""
        try:
            positions = self.trading_client.get_positions()

            for pos in positions:
                symbol = pos['symbol']
                qty = pos['qty']

                logger.info(f"Closing {symbol} position ({qty} shares)...")

                # Market sell
                self.trading_client.place_market_order(symbol, abs(int(qty)), "sell")

        except Exception as e:
            logger.error(f"Error closing positions: {e}")

    def _log_status(self):
        """Log current bot status."""
        logger.info(f"\n📊 Status Update - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"   Active Positions: {len(self.positions)}")
        logger.info(f"   Total Trades: {self.trades_executed}")

        if self.positions:
            logger.info("\n   Current Positions:")
            for symbol, pos in self.positions.items():
                current_price = self.price_data[symbol]['close'].iloc[-1]
                pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                pnl_sign = "+" if pnl_pct >= 0 else ""

                logger.info(f"     {symbol}: {pnl_sign}{pnl_pct:.2f}% | {pos['strategy']} | {pos['regime']}")


def main():
    """Run the trading bot."""
    bot = TradingBot(
        symbols=["SPY", "QQQ", "AAPL", "MSFT"],
        max_position_size=10000.0,
        risk_per_trade=0.02,
        stop_loss_pct=0.03,
        take_profit_pct=0.06,
        paper_trading=True,
    )

    bot.start()


if __name__ == "__main__":
    main()
