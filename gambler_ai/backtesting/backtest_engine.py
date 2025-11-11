"""
Main backtesting engine for strategy simulation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import random

from gambler_ai.backtesting.trade import Trade, TradeDirection, TradeManager
from gambler_ai.backtesting.performance import PerformanceMetrics
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.storage import get_timeseries_db
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """Main backtesting engine."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        risk_per_trade: float = 0.01,
        max_concurrent_trades: int = 3,
        commission: float = 0.0,  # Commission per trade ($ or %)
        # Execution slippage parameters
        slippage_enabled: bool = True,
        slippage_probability: float = 0.3,  # 30% of time
        slippage_delay_bars: int = 1,
        # Configurable profit/loss targets
        stop_loss_pct: float = 1.0,
        take_profit_pct: float = 2.0,
        use_percentage_targets: bool = True,
    ):
        """
        Initialize backtest engine.

        Args:
            initial_capital: Starting capital
            risk_per_trade: Risk per trade (fraction of capital)
            max_concurrent_trades: Maximum concurrent open trades
            commission: Commission per trade
            slippage_enabled: Enable execution slippage simulation
            slippage_probability: Probability of delayed execution (0.0-1.0)
            slippage_delay_bars: Number of bars to delay execution
            stop_loss_pct: Stop loss percentage (e.g., 1.0 = 1%)
            take_profit_pct: Take profit percentage (e.g., 2.0 = 2%)
            use_percentage_targets: Use percentage-based targets
        """
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_concurrent_trades = max_concurrent_trades
        self.commission = commission

        # Slippage configuration
        self.slippage_enabled = slippage_enabled
        self.slippage_probability = slippage_probability
        self.slippage_delay_bars = slippage_delay_bars

        # Profit/Loss target configuration
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.use_percentage_targets = use_percentage_targets

        self.trade_manager = None
        self.current_capital = initial_capital
        try:
            self.db = get_timeseries_db()
        except:
            self.db = None  # Allow for backtesting without database

    def run_momentum_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
        min_price_change: float = 2.0,
        min_volume_ratio: float = 2.0,
    ) -> Dict:
        """
        Run backtest using Momentum strategy.

        Args:
            symbol: Stock symbol
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Data timeframe
            min_price_change: Min % change to detect momentum
            min_volume_ratio: Min volume ratio

        Returns:
            Dictionary with backtest results
        """
        logger.info(
            f"Starting momentum backtest for {symbol} "
            f"from {start_date} to {end_date}"
        )

        # Initialize trade manager
        self.trade_manager = TradeManager(
            initial_capital=self.initial_capital,
            risk_per_trade=self.risk_per_trade,
        )

        # Initialize momentum detector
        detector = MomentumDetector()

        # Detect momentum events in the historical period
        logger.info("Detecting momentum events...")
        events = detector.detect_events(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            save_to_db=False,  # Don't save during backtest
        )

        logger.info(f"Found {len(events)} momentum events")

        # Simulate trading each event
        logger.info("Simulating trades...")
        for event in events:
            self._simulate_momentum_trade(event, symbol, timeframe)

        # Get price at end for closing open trades
        end_prices = self._get_prices_at_time(symbol, end_date, timeframe)
        self.trade_manager.force_close_all(end_date, end_prices, "end_of_backtest")

        # Calculate performance
        logger.info("Calculating performance metrics...")
        performance = PerformanceMetrics(
            trades=self.trade_manager.closed_trades,
            initial_capital=self.initial_capital,
            final_capital=self.trade_manager.current_capital,
        )

        metrics = performance.calculate_all_metrics()
        report = performance.generate_report()

        logger.info("Backtest complete")

        return {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timeframe": timeframe,
            "strategy": "momentum",
            "metrics": metrics,
            "report": report,
            "trades": [t.to_dict() for t in self.trade_manager.closed_trades],
            "equity_curve": self.trade_manager.equity_curve,
        }

    def _simulate_momentum_trade(self, event: Dict, symbol: str, timeframe: str):
        """
        Simulate a trade based on momentum event.

        Entry Logic:
        - Enter at the END of the momentum event (after initial move detected)
        - With slippage: XX% of time, entry is delayed by N bars

        Exit Logic:
        - Target: Configurable % gain (e.g., 2%)
        - Stop: Configurable % loss (e.g., 1%)
        - Time stop: Exit if no target hit within 60 minutes
        """
        # Check if we can open a trade
        if not self.trade_manager.can_open_trade(self.max_concurrent_trades):
            return

        # Entry parameters
        initial_entry_time = event["end_time"]
        initial_entry_price = event["peak_price"]
        direction = TradeDirection.LONG if event["direction"] == "UP" else TradeDirection.SHORT

        # Simulate execution slippage
        entry_time = initial_entry_time
        entry_price = initial_entry_price
        slippage_applied = False

        if self.slippage_enabled and random.random() < self.slippage_probability:
            # Execution delayed - get price at next bar(s)
            slippage_applied = True
            delayed_time = initial_entry_time + timedelta(minutes=self.slippage_delay_bars * 5)  # Assuming 5min bars
            delayed_prices = self._get_price_data_range(
                symbol, initial_entry_time, delayed_time, timeframe
            )

            if not delayed_prices.empty and len(delayed_prices) >= self.slippage_delay_bars:
                delayed_bar = delayed_prices.iloc[self.slippage_delay_bars - 1]
                entry_time = delayed_bar["timestamp"]
                entry_price = delayed_bar["close"]
                logger.debug(
                    f"Slippage applied: Entry delayed from {initial_entry_time} to {entry_time}, "
                    f"price changed from ${initial_entry_price:.2f} to ${entry_price:.2f}"
                )

        # Calculate stop loss and target using configurable percentages
        if self.use_percentage_targets:
            if direction == TradeDirection.LONG:
                stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                target = entry_price * (1 + self.take_profit_pct / 100)
            else:
                stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                target = entry_price * (1 - self.take_profit_pct / 100)
        else:
            # Fallback to old logic
            if direction == TradeDirection.LONG:
                stop_loss = entry_price * 0.99
                target = entry_price * (1 + (event["max_move_percentage"] * 1.5) / 100)
            else:
                stop_loss = entry_price * 1.01
                target = entry_price * (1 - (event["max_move_percentage"] * 1.5) / 100)

        # Open trade
        trade = self.trade_manager.open_trade(
            symbol=symbol,
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            strategy_name="momentum",
            setup_data=event,
        )

        # Simulate price movement after entry
        # Fetch data after entry for up to 60 minutes
        exit_window_end = entry_time + timedelta(minutes=60)
        price_data = self._get_price_data_range(
            symbol, entry_time, exit_window_end, timeframe
        )

        if price_data.empty:
            # No data available, close at entry price
            trade.close(entry_time, entry_price, "no_data")
            self.trade_manager.close_trade(trade)
            return

        # Iterate through price bars to check for exit conditions
        for idx, row in price_data.iterrows():
            current_time = row["timestamp"]
            current_price = row["close"]
            high = row["high"]
            low = row["low"]

            # Update excursions
            trade.update_excursions(current_price)

            # Check if stop or target was hit during this bar
            if direction == TradeDirection.LONG:
                # Check stop loss
                if low <= stop_loss:
                    trade.close(current_time, stop_loss, "stop_loss")
                    self.trade_manager.close_trade(trade)
                    return

                # Check target
                if high >= target:
                    trade.close(current_time, target, "target")
                    self.trade_manager.close_trade(trade)
                    return

            else:  # SHORT
                # Check stop loss
                if high >= stop_loss:
                    trade.close(current_time, stop_loss, "stop_loss")
                    self.trade_manager.close_trade(trade)
                    return

                # Check target
                if low <= target:
                    trade.close(current_time, target, "target")
                    self.trade_manager.close_trade(trade)
                    return

        # Time stop - close at last available price
        last_row = price_data.iloc[-1]
        trade.close(last_row["timestamp"], last_row["close"], "time_stop")
        self.trade_manager.close_trade(trade)

    def _get_price_data_range(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        timeframe: str,
    ) -> pd.DataFrame:
        """Fetch price data for a specific time range."""
        from gambler_ai.storage import StockPrice
        from sqlalchemy import and_

        try:
            with self.db.get_session() as session:
                query = (
                    session.query(StockPrice)
                    .filter(
                        and_(
                            StockPrice.symbol == symbol,
                            StockPrice.timeframe == timeframe,
                            StockPrice.timestamp > start_time,
                            StockPrice.timestamp <= end_time,
                        )
                    )
                    .order_by(StockPrice.timestamp)
                )

                df = pd.read_sql(query.statement, session.bind)

            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            return df

        except Exception as e:
            logger.error(f"Error fetching price data: {e}")
            return pd.DataFrame()

    def _get_prices_at_time(
        self,
        symbol: str,
        time: datetime,
        timeframe: str,
    ) -> Dict[str, float]:
        """Get price at specific time."""
        from gambler_ai.storage import StockPrice

        try:
            with self.db.get_session() as session:
                price = (
                    session.query(StockPrice)
                    .filter(
                        StockPrice.symbol == symbol,
                        StockPrice.timeframe == timeframe,
                        StockPrice.timestamp <= time,
                    )
                    .order_by(StockPrice.timestamp.desc())
                    .first()
                )

                if price:
                    return {symbol: float(price.close)}

        except Exception as e:
            logger.error(f"Error fetching price: {e}")

        return {}

    def run_multi_symbol_backtest(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
    ) -> Dict:
        """
        Run backtest across multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Backtest start
            end_date: Backtest end
            timeframe: Data timeframe

        Returns:
            Aggregated results across all symbols
        """
        logger.info(f"Running multi-symbol backtest for {len(symbols)} symbols")

        all_results = []

        for symbol in symbols:
            logger.info(f"Backtesting {symbol}...")
            try:
                result = self.run_momentum_backtest(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe,
                )
                all_results.append(result)

            except Exception as e:
                logger.error(f"Error backtesting {symbol}: {e}")
                continue

        # Aggregate results
        aggregated = self._aggregate_results(all_results)

        return aggregated

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results from multiple backtests."""
        if not results:
            return {"error": "No results to aggregate"}

        # Combine all trades
        all_trades = []
        for result in results:
            all_trades.extend(result["trades"])

        # Calculate aggregated metrics
        total_initial_capital = self.initial_capital
        total_final_capital = total_initial_capital

        for result in results:
            # Each symbol gets equal allocation
            pnl = result["metrics"]["total_pnl"]
            total_final_capital += pnl / len(results)

        # Create combined performance
        # Note: This is simplified - in reality you'd need to properly combine trades
        aggregated_metrics = {
            "symbols": [r["symbol"] for r in results],
            "total_symbols": len(results),
            "total_trades": sum(r["metrics"]["total_trades"] for r in results),
            "combined_win_rate": sum(
                r["metrics"]["win_rate"] * r["metrics"]["total_trades"]
                for r in results
            ) / sum(r["metrics"]["total_trades"] for r in results) if sum(r["metrics"]["total_trades"] for r in results) > 0 else 0,
            "combined_return_pct": (total_final_capital - total_initial_capital) / total_initial_capital * 100,
            "individual_results": results,
        }

        return aggregated_metrics

    def run_backtest(self, df: pd.DataFrame, detector) -> List[Trade]:
        """
        Generic backtest method that works with any detector that has a detect_setups method.
        This method works with DataFrame data and does not require database.

        Args:
            df: DataFrame with OHLCV data (timestamp, open, high, low, close, volume)
            detector: Strategy detector object with detect_setups(df) method

        Returns:
            List of Trade objects
        """
        # Initialize trade manager
        self.trade_manager = TradeManager(
            initial_capital=self.initial_capital,
            risk_per_trade=self.risk_per_trade,
        )

        # Detect setups
        setups = detector.detect_setups(df)

        # Simulate each setup
        for setup in setups:
            if not self.trade_manager.can_open_trade(self.max_concurrent_trades):
                continue

            initial_entry_time = setup.get('entry_time') or setup.get('timestamp')
            initial_entry_price = setup['entry_price']
            direction = TradeDirection.LONG if setup['direction'] == 'LONG' else TradeDirection.SHORT

            # Simulate execution slippage
            entry_time = initial_entry_time
            entry_price = initial_entry_price

            if self.slippage_enabled and random.random() < self.slippage_probability:
                # Find entry index in dataframe
                entry_idx = df[df['timestamp'] == initial_entry_time].index
                if len(entry_idx) > 0:
                    entry_idx = entry_idx[0]
                    # Get price at delayed bar
                    delayed_idx = min(entry_idx + self.slippage_delay_bars, len(df) - 1)
                    if delayed_idx > entry_idx:
                        delayed_bar = df.iloc[delayed_idx]
                        entry_time = delayed_bar['timestamp']
                        entry_price = delayed_bar['close']
                        logger.debug(
                            f"Slippage applied: Entry delayed by {self.slippage_delay_bars} bar(s), "
                            f"price changed from ${initial_entry_price:.2f} to ${entry_price:.2f}"
                        )

            # Get or calculate stop loss and target
            if 'stop_loss' in setup and 'target' in setup and not self.use_percentage_targets:
                # Use provided values if not using percentage targets
                stop_loss = setup['stop_loss']
                target = setup['target']
            else:
                # Use configurable percentage targets
                if self.use_percentage_targets:
                    if direction == TradeDirection.LONG:
                        stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
                        target = entry_price * (1 + self.take_profit_pct / 100)
                    else:
                        stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
                        target = entry_price * (1 - self.take_profit_pct / 100)
                else:
                    # Default risk/reward if not provided
                    if direction == TradeDirection.LONG:
                        stop_loss = entry_price * 0.99  # 1% stop
                        target = entry_price * 1.03  # 3% target
                    else:
                        stop_loss = entry_price * 1.01  # 1% stop
                        target = entry_price * 0.97  # 3% target

            # Open trade
            trade = self.trade_manager.open_trade(
                symbol=df['symbol'].iloc[0] if 'symbol' in df.columns else 'UNKNOWN',
                direction=direction,
                entry_time=entry_time,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                strategy_name=setup.get('setup_type', 'Unknown'),
                setup_data=setup,
            )

            # Find entry index in dataframe
            entry_idx = df[df['timestamp'] == entry_time].index
            if len(entry_idx) == 0:
                # Entry time not found, close immediately
                trade.close(entry_time, entry_price, "no_data")
                self.trade_manager.close_trade(trade)
                continue

            entry_idx = entry_idx[0]

            # Simulate price movement after entry (look ahead 60 bars or until end)
            max_lookforward = min(60, len(df) - entry_idx - 1)

            for i in range(1, max_lookforward + 1):
                bar_idx = entry_idx + i
                if bar_idx >= len(df):
                    break

                row = df.iloc[bar_idx]
                current_time = row['timestamp']
                current_price = row['close']
                high = row['high']
                low = row['low']

                # Update excursions
                trade.update_excursions(current_price)

                # Check exit conditions
                if direction == TradeDirection.LONG:
                    if low <= stop_loss:
                        trade.close(current_time, stop_loss, "stop_loss")
                        self.trade_manager.close_trade(trade)
                        break
                    if high >= target:
                        trade.close(current_time, target, "target")
                        self.trade_manager.close_trade(trade)
                        break
                else:  # SHORT
                    if high >= stop_loss:
                        trade.close(current_time, stop_loss, "stop_loss")
                        self.trade_manager.close_trade(trade)
                        break
                    if low <= target:
                        trade.close(current_time, target, "target")
                        self.trade_manager.close_trade(trade)
                        break

            # If trade still open, close at last price (time stop)
            if trade.exit_time is None:
                last_bar = df.iloc[min(entry_idx + max_lookforward, len(df) - 1)]
                trade.close(last_bar['timestamp'], last_bar['close'], "time_stop")
                self.trade_manager.close_trade(trade)

        # Update current capital
        self.current_capital = self.trade_manager.current_capital

        return self.trade_manager.closed_trades
