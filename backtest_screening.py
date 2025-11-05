#!/usr/bin/env python3
"""
Backtest Automatic Stock Screening

Tests the dynamic screening system against historical data from November 6, 2024 to present.
Simulates the complete workflow: screening → ranking → signal generation → trading.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

from gambler_ai.screening import StockScreener, StockRanker
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class ScreeningBacktest:
    """
    Backtest the automatic screening system.

    Workflow:
    1. Load historical data for universe
    2. Run screening periodically (daily or custom interval)
    3. Generate signals using adaptive strategies
    4. Simulate trades with risk management
    5. Track performance and generate report
    """

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100_000.0,
        screening_interval_hours: int = 24,  # Daily screening
        max_positions: int = 5,
        position_size_pct: float = 0.20,  # 20% per position
        stop_loss_pct: float = 0.02,  # 2% stop loss
        take_profit_pct: float = 0.04,  # 4% take profit
        api_key: str = None,
        api_secret: str = None,
    ):
        """
        Initialize backtest.

        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Starting capital
            screening_interval_hours: How often to rescan (hours)
            max_positions: Maximum concurrent positions
            position_size_pct: Position size as % of capital
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            api_key: Alpaca API key
            api_secret: Alpaca API secret
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.screening_interval = timedelta(hours=screening_interval_hours)
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        # Initialize components
        self.screener = StockScreener(api_key=api_key, api_secret=api_secret)
        self.ranker = StockRanker()
        self.strategy_selector = AdaptiveStrategySelector()
        self.regime_detector = RegimeDetector()

        # Portfolio state
        self.capital = initial_capital
        self.positions: Dict[str, Dict] = {}  # symbol -> position info
        self.watchlist: List[str] = []

        # Historical data cache
        self.historical_data: Dict[str, pd.DataFrame] = {}

        # Performance tracking
        self.trades: List[Dict] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.screenings: List[Dict] = []

    def load_historical_data(self, symbols: List[str]) -> bool:
        """
        Load historical data for all symbols.

        Args:
            symbols: List of symbols to load

        Returns:
            Success status
        """
        logger.info(f"Loading historical data for {len(symbols)} symbols...")

        for symbol in symbols:
            try:
                # Get data with some buffer before start date
                buffer_start = self.start_date - timedelta(days=100)

                bars = self.screener._get_bars(
                    symbol,
                    days=(self.end_date - buffer_start).days + 10
                )

                if bars is not None and len(bars) > 0:
                    self.historical_data[symbol] = bars
                    logger.debug(f"Loaded {len(bars)} bars for {symbol}")
                else:
                    logger.warning(f"No data for {symbol}")

            except Exception as e:
                logger.error(f"Error loading {symbol}: {e}")
                continue

        logger.info(f"✓ Loaded data for {len(self.historical_data)} symbols")
        return len(self.historical_data) > 0

    def get_data_at_time(self, symbol: str, current_time: datetime, lookback_bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Get historical data up to a specific time.

        Args:
            symbol: Stock symbol
            current_time: Current simulation time
            lookback_bars: Number of bars to include

        Returns:
            DataFrame with data up to current_time
        """
        if symbol not in self.historical_data:
            return None

        df = self.historical_data[symbol]

        # Filter data up to current time
        mask = df['timestamp'] <= current_time
        filtered = df[mask].tail(lookback_bars)

        return filtered if len(filtered) > 0 else None

    def run_screening(self, current_time: datetime) -> List[str]:
        """
        Run screening at current time.

        Args:
            current_time: Current simulation time

        Returns:
            List of selected symbols
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Running screening at {current_time.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"{'='*60}")

        # Get SPY data for regime detection
        spy_data = self.get_data_at_time('SPY', current_time, lookback_bars=200)

        if spy_data is None or len(spy_data) < 50:
            logger.warning("Insufficient SPY data for regime detection")
            return self.watchlist  # Keep current watchlist

        # Detect market regime
        regime, confidence = self.regime_detector.detect_regime_with_confidence(spy_data)
        logger.info(f"Market Regime: {regime} (confidence: {confidence:.2f})")

        # Temporarily replace screener's _get_bars to use historical data
        original_get_bars = self.screener._get_bars

        def get_bars_at_time(symbol: str, days: int) -> Optional[pd.DataFrame]:
            return self.get_data_at_time(symbol, current_time, lookback_bars=days)

        self.screener._get_bars = get_bars_at_time

        try:
            # Run all screening strategies
            results = self.screener.screen_all(top_n_per_strategy=3)

            # Count total candidates
            total_candidates = sum(len(candidates) for candidates in results.values())
            logger.info(f"Found {total_candidates} candidates across 4 strategies")

            # Rank by regime
            ranked = self.ranker.rank_by_regime(results, spy_data)

            # Select top picks
            top_picks = ranked[:self.max_positions * 2]  # Get extra for rotation
            selected_symbols = [pick.symbol for pick in top_picks]

            logger.info(f"\nTop {len(selected_symbols)} picks:")
            for i, pick in enumerate(top_picks, 1):
                logger.info(f"  {i}. {pick.symbol:6s} - Score: {pick.score:6.1f} - {pick.reason}")

            # Store screening info
            self.screenings.append({
                'timestamp': current_time,
                'regime': regime,
                'confidence': confidence,
                'candidates': total_candidates,
                'selected': selected_symbols[:self.max_positions],
            })

            return selected_symbols[:self.max_positions]

        except Exception as e:
            logger.error(f"Error during screening: {e}")
            return self.watchlist  # Keep current watchlist

        finally:
            # Restore original method
            self.screener._get_bars = original_get_bars

    def generate_signals(self, symbol: str, current_time: datetime) -> Optional[str]:
        """
        Generate trading signal for a symbol.

        Args:
            symbol: Stock symbol
            current_time: Current simulation time

        Returns:
            Signal: 'BUY', 'SELL', or None
        """
        # Get data
        data = self.get_data_at_time(symbol, current_time, lookback_bars=200)

        if data is None or len(data) < 50:
            return None

        # Detect regime
        regime, _ = self.regime_detector.detect_regime_with_confidence(data)

        # Select strategy
        strategy = self.strategy_selector.select_strategy(data)

        if strategy is None:
            return None

        # Generate signal
        signal_data = strategy.generate_signals(data)

        if signal_data is None or len(signal_data) == 0:
            return None

        # Get latest signal
        latest_signal = signal_data['signal'].iloc[-1]

        return 'BUY' if latest_signal == 1 else ('SELL' if latest_signal == -1 else None)

    def execute_trade(
        self,
        symbol: str,
        signal: str,
        current_time: datetime,
        current_price: float
    ):
        """
        Execute a trade.

        Args:
            symbol: Stock symbol
            signal: 'BUY' or 'SELL'
            current_time: Current time
            current_price: Current price
        """
        if signal == 'BUY' and symbol not in self.positions:
            # Check if we have room for new position
            if len(self.positions) >= self.max_positions:
                logger.debug(f"Max positions reached, skipping {symbol}")
                return

            # Calculate position size
            position_value = self.capital * self.position_size_pct
            shares = int(position_value / current_price)

            if shares < 1:
                logger.debug(f"Insufficient capital for {symbol}")
                return

            cost = shares * current_price

            if cost > self.capital:
                logger.debug(f"Insufficient capital for {symbol}")
                return

            # Open position
            self.capital -= cost

            self.positions[symbol] = {
                'shares': shares,
                'entry_price': current_price,
                'entry_time': current_time,
                'stop_loss': current_price * (1 - self.stop_loss_pct),
                'take_profit': current_price * (1 + self.take_profit_pct),
            }

            logger.info(f"✓ BUY {shares} {symbol} @ ${current_price:.2f} (Total: ${cost:.2f})")

            # Record trade
            self.trades.append({
                'timestamp': current_time,
                'symbol': symbol,
                'action': 'BUY',
                'shares': shares,
                'price': current_price,
                'value': cost,
            })

        elif signal == 'SELL' and symbol in self.positions:
            # Close position
            position = self.positions[symbol]
            proceeds = position['shares'] * current_price
            self.capital += proceeds

            # Calculate P&L
            cost = position['shares'] * position['entry_price']
            pnl = proceeds - cost
            pnl_pct = (pnl / cost) * 100

            hold_time = (current_time - position['entry_time']).days

            logger.info(f"✓ SELL {position['shares']} {symbol} @ ${current_price:.2f} "
                       f"(P&L: ${pnl:+.2f} / {pnl_pct:+.2f}%, Hold: {hold_time}d)")

            # Record trade
            self.trades.append({
                'timestamp': current_time,
                'symbol': symbol,
                'action': 'SELL',
                'shares': position['shares'],
                'price': current_price,
                'value': proceeds,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'hold_days': hold_time,
            })

            # Remove position
            del self.positions[symbol]

    def check_stops(self, current_time: datetime):
        """
        Check stop loss and take profit for all positions.

        Args:
            current_time: Current simulation time
        """
        symbols_to_close = []

        for symbol, position in self.positions.items():
            # Get current price
            data = self.get_data_at_time(symbol, current_time, lookback_bars=1)

            if data is None or len(data) == 0:
                continue

            current_price = data['close'].iloc[-1]

            # Check stop loss
            if current_price <= position['stop_loss']:
                logger.info(f"⚠️  Stop loss triggered for {symbol}")
                self.execute_trade(symbol, 'SELL', current_time, current_price)
                symbols_to_close.append(symbol)

            # Check take profit
            elif current_price >= position['take_profit']:
                logger.info(f"🎯 Take profit hit for {symbol}")
                self.execute_trade(symbol, 'SELL', current_time, current_price)
                symbols_to_close.append(symbol)

    def update_equity(self, current_time: datetime):
        """
        Update equity curve.

        Args:
            current_time: Current time
        """
        # Calculate total equity (cash + positions)
        total_equity = self.capital

        for symbol, position in self.positions.items():
            data = self.get_data_at_time(symbol, current_time, lookback_bars=1)

            if data is not None and len(data) > 0:
                current_price = data['close'].iloc[-1]
                position_value = position['shares'] * current_price
                total_equity += position_value

        self.equity_curve.append((current_time, total_equity))

    def run(self) -> Dict:
        """
        Run the backtest.

        Returns:
            Dictionary with results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"STARTING BACKTEST: {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"{'='*70}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Screening Interval: {self.screening_interval.total_seconds() / 3600:.0f} hours")
        logger.info(f"Max Positions: {self.max_positions}")
        logger.info(f"Position Size: {self.position_size_pct * 100:.0f}%")
        logger.info(f"Stop Loss: {self.stop_loss_pct * 100:.1f}%")
        logger.info(f"Take Profit: {self.take_profit_pct * 100:.1f}%")

        # Load historical data
        logger.info(f"\n{'='*70}")
        logger.info("LOADING HISTORICAL DATA")
        logger.info(f"{'='*70}")

        if not self.load_historical_data(self.screener.universe):
            logger.error("Failed to load historical data")
            return {}

        # Run backtest
        logger.info(f"\n{'='*70}")
        logger.info("RUNNING SIMULATION")
        logger.info(f"{'='*70}\n")

        current_time = self.start_date
        next_screening = current_time

        # Initial screening
        self.watchlist = self.run_screening(current_time)
        self.update_equity(current_time)

        # Simulate day by day
        while current_time <= self.end_date:
            # Check if it's time to rescan
            if current_time >= next_screening:
                self.watchlist = self.run_screening(current_time)
                next_screening = current_time + self.screening_interval

            # Generate signals for watchlist
            for symbol in self.watchlist:
                signal = self.generate_signals(symbol, current_time)

                if signal:
                    # Get current price
                    data = self.get_data_at_time(symbol, current_time, lookback_bars=1)

                    if data is not None and len(data) > 0:
                        current_price = data['close'].iloc[-1]
                        self.execute_trade(symbol, signal, current_time, current_price)

            # Check stops
            self.check_stops(current_time)

            # Update equity
            self.update_equity(current_time)

            # Move to next day
            current_time += timedelta(days=1)

        # Close all remaining positions
        logger.info(f"\n{'='*70}")
        logger.info("CLOSING REMAINING POSITIONS")
        logger.info(f"{'='*70}")

        for symbol in list(self.positions.keys()):
            data = self.get_data_at_time(symbol, self.end_date, lookback_bars=1)

            if data is not None and len(data) > 0:
                current_price = data['close'].iloc[-1]
                self.execute_trade(symbol, 'SELL', self.end_date, current_price)

        # Generate results
        return self.generate_results()

    def generate_results(self) -> Dict:
        """
        Generate backtest results and statistics.

        Returns:
            Dictionary with all results
        """
        logger.info(f"\n{'='*70}")
        logger.info("BACKTEST RESULTS")
        logger.info(f"{'='*70}\n")

        # Calculate returns
        final_equity = self.equity_curve[-1][1] if self.equity_curve else self.initial_capital
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        logger.info(f"Initial Capital:  ${self.initial_capital:>12,.2f}")
        logger.info(f"Final Equity:     ${final_equity:>12,.2f}")
        logger.info(f"Total Return:     ${total_return:>12,.2f} ({total_return_pct:+.2f}%)")

        # Trade statistics
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']

        if sell_trades:
            winning_trades = [t for t in sell_trades if t['pnl'] > 0]
            losing_trades = [t for t in sell_trades if t['pnl'] <= 0]

            win_rate = (len(winning_trades) / len(sell_trades)) * 100
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

            logger.info(f"\nTrade Statistics:")
            logger.info(f"  Total Trades:     {len(sell_trades)}")
            logger.info(f"  Winning Trades:   {len(winning_trades)} ({win_rate:.1f}%)")
            logger.info(f"  Losing Trades:    {len(losing_trades)}")
            logger.info(f"  Average Win:      ${avg_win:>10,.2f}")
            logger.info(f"  Average Loss:     ${avg_loss:>10,.2f}")

            if avg_loss != 0:
                profit_factor = abs(avg_win / avg_loss)
                logger.info(f"  Profit Factor:    {profit_factor:.2f}")

        # Screening statistics
        logger.info(f"\nScreening Statistics:")
        logger.info(f"  Total Screenings: {len(self.screenings)}")

        if self.screenings:
            avg_candidates = np.mean([s['candidates'] for s in self.screenings])
            logger.info(f"  Avg Candidates:   {avg_candidates:.1f}")

        # Calculate benchmark (SPY buy and hold)
        spy_data = self.historical_data.get('SPY')

        if spy_data is not None:
            spy_start_mask = spy_data['timestamp'] >= self.start_date
            spy_end_mask = spy_data['timestamp'] <= self.end_date
            spy_period = spy_data[spy_start_mask & spy_end_mask]

            if len(spy_period) > 1:
                spy_start_price = spy_period['close'].iloc[0]
                spy_end_price = spy_period['close'].iloc[-1]
                spy_return_pct = ((spy_end_price - spy_start_price) / spy_start_price) * 100

                logger.info(f"\nBenchmark (SPY Buy & Hold):")
                logger.info(f"  SPY Return:       {spy_return_pct:+.2f}%")
                logger.info(f"  Outperformance:   {total_return_pct - spy_return_pct:+.2f}%")

        # Equity curve statistics
        if len(self.equity_curve) > 1:
            equity_df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
            equity_df['returns'] = equity_df['equity'].pct_change()

            # Calculate Sharpe ratio (annualized)
            if equity_df['returns'].std() > 0:
                sharpe = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252)
                logger.info(f"\nRisk Metrics:")
                logger.info(f"  Sharpe Ratio:     {sharpe:.2f}")

            # Max drawdown
            cummax = equity_df['equity'].cummax()
            drawdown = (equity_df['equity'] - cummax) / cummax
            max_drawdown = drawdown.min() * 100
            logger.info(f"  Max Drawdown:     {max_drawdown:.2f}%")

        logger.info(f"\n{'='*70}\n")

        # Return results dictionary
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'screenings': self.screenings,
            'sell_trades': sell_trades if sell_trades else [],
            'win_rate': win_rate if sell_trades else 0,
        }


def main():
    """Run the backtest."""

    # Define backtest period
    start_date = datetime(2024, 11, 6)
    end_date = datetime.now()

    print("\n" + "="*70)
    print("AUTOMATIC SCREENING BACKTEST")
    print("="*70)
    print(f"\nTesting period: {start_date.date()} to {end_date.date()}")
    print(f"Duration: {(end_date - start_date).days} days")
    print()

    # Create backtest
    backtest = ScreeningBacktest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000.0,
        screening_interval_hours=24,  # Daily screening
        max_positions=5,
        position_size_pct=0.20,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
    )

    # Run backtest
    try:
        results = backtest.run()

        # Save results
        if results:
            # Save equity curve
            if results.get('equity_curve'):
                equity_df = pd.DataFrame(
                    results['equity_curve'],
                    columns=['timestamp', 'equity']
                )
                equity_df.to_csv('backtest_equity_curve.csv', index=False)
                print("✓ Saved equity curve to: backtest_equity_curve.csv")

            # Save trades
            if results.get('trades'):
                trades_df = pd.DataFrame(results['trades'])
                trades_df.to_csv('backtest_trades.csv', index=False)
                print("✓ Saved trade history to: backtest_trades.csv")

            # Save screenings
            if results.get('screenings'):
                screenings_df = pd.DataFrame(results['screenings'])
                screenings_df.to_csv('backtest_screenings.csv', index=False)
                print("✓ Saved screening history to: backtest_screenings.csv")

            print("\n✓ Backtest complete!")

    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user")
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")


if __name__ == "__main__":
    main()
