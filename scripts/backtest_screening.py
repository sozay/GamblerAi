#!/usr/bin/env python3
"""
Backtesting and screening script for GamblerAI momentum trading strategy.

This script performs:
1. Dynamic stock screening - identifies stocks with current momentum
2. Historical backtesting - simulates trading strategy on historical data
3. Performance analysis - calculates win rates, profit/loss, risk/reward ratios

Usage:
    # Run backtest on historical data
    python backtest_screening.py backtest --start 2021-06-01 --end 2022-06-30 --symbols AAPL,MSFT,GOOGL

    # Screen for current momentum opportunities
    python backtest_screening.py screen --symbols AAPL,MSFT,GOOGL,TSLA,NVDA

    # Run full analysis (collect data + detect + backtest)
    python backtest_screening.py full-analysis --start 2021-06-01 --end 2022-06-30 --symbols AAPL,MSFT,GOOGL
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gambler_ai.analysis import MomentumDetector, StatisticsEngine
from gambler_ai.data_ingestion import HistoricalDataCollector
from gambler_ai.storage import MomentumEvent, StockPrice, get_timeseries_db
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class BacktestScreening:
    """Backtesting and screening engine for momentum trading strategy."""

    def __init__(self):
        """Initialize the backtest screening engine."""
        self.db = get_timeseries_db()
        self.config = get_config()
        self.detector = MomentumDetector()
        self.stats_engine = StatisticsEngine()
        self.collector = HistoricalDataCollector()

        # Trading parameters
        self.entry_threshold_prob = self.config.get(
            "backtest.entry_threshold_probability", 0.6
        )
        self.stop_loss_pct = self.config.get("backtest.stop_loss_percentage", 2.0)
        self.take_profit_pct = self.config.get("backtest.take_profit_percentage", 4.0)
        self.position_size = self.config.get("backtest.position_size", 10000)  # $10k per trade

    def screen_stocks(
        self,
        symbols: List[str],
        timeframe: str = "5min",
        lookback_minutes: int = 30,
    ) -> pd.DataFrame:
        """
        Screen stocks for current momentum opportunities.

        Args:
            symbols: List of stock symbols to screen
            timeframe: Timeframe to analyze
            lookback_minutes: Minutes to look back for momentum

        Returns:
            DataFrame with screening results sorted by opportunity score
        """
        logger.info(f"Screening {len(symbols)} stocks for momentum opportunities")

        results = []
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=lookback_minutes)

        for symbol in symbols:
            try:
                # Fetch recent price data
                with self.db.get_session() as session:
                    from sqlalchemy import and_

                    query = (
                        session.query(StockPrice)
                        .filter(
                            and_(
                                StockPrice.symbol == symbol,
                                StockPrice.timeframe == timeframe,
                                StockPrice.timestamp >= start_time,
                                StockPrice.timestamp <= end_time,
                            )
                        )
                        .order_by(StockPrice.timestamp.desc())
                        .limit(lookback_minutes)
                    )

                    data = pd.read_sql(query.statement, session.bind)

                if data.empty or len(data) < 10:
                    logger.debug(f"Insufficient data for {symbol}")
                    continue

                # Calculate current momentum
                data = data.sort_values("timestamp")
                latest = data.iloc[-1]
                window_start = data.iloc[0]

                price_change_pct = (
                    (latest["close"] - window_start["open"]) / window_start["open"] * 100
                )

                # Calculate volume ratio
                avg_volume = data["volume"].mean()
                current_volume_ratio = latest["volume"] / avg_volume if avg_volume > 0 else 0

                # Check if meets momentum criteria
                if (
                    abs(price_change_pct) >= self.detector.min_price_change_pct
                    and current_volume_ratio >= self.detector.min_volume_ratio
                ):
                    direction = "UP" if price_change_pct > 0 else "DOWN"

                    # Get prediction
                    prediction = self.stats_engine.predict_continuation(
                        symbol=symbol,
                        initial_move_pct=abs(price_change_pct),
                        volume_ratio=current_volume_ratio,
                        timeframe=timeframe,
                        direction=direction,
                    )

                    if "error" not in prediction:
                        # Calculate opportunity score
                        cont_prob = prediction.get("continuation_probability", 0)
                        expected_cont_min = prediction.get("expected_continuation_minutes", 0)
                        opportunity_score = cont_prob * expected_cont_min

                        results.append(
                            {
                                "symbol": symbol,
                                "timestamp": latest["timestamp"],
                                "direction": direction,
                                "price_change_pct": round(price_change_pct, 2),
                                "volume_ratio": round(current_volume_ratio, 2),
                                "current_price": float(latest["close"]),
                                "continuation_probability": cont_prob,
                                "expected_continuation_min": expected_cont_min,
                                "opportunity_score": round(opportunity_score, 2),
                                "recommendation": prediction.get("recommendation"),
                                "sample_size": prediction.get("sample_size", 0),
                            }
                        )

            except Exception as e:
                logger.error(f"Error screening {symbol}: {e}")
                continue

        # Create results DataFrame
        if results:
            df = pd.DataFrame(results)
            df = df.sort_values("opportunity_score", ascending=False)
            logger.info(f"Found {len(df)} momentum opportunities")
            return df
        else:
            logger.warning("No momentum opportunities found")
            return pd.DataFrame()

    def backtest_strategy(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
    ) -> Dict:
        """
        Backtest momentum trading strategy on historical data.

        Args:
            symbols: List of stock symbols to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            timeframe: Timeframe to use

        Returns:
            Dictionary with backtest results and performance metrics
        """
        logger.info(
            f"Running backtest on {len(symbols)} symbols from {start_date} to {end_date}"
        )

        all_trades = []
        performance_by_symbol = {}

        for symbol in symbols:
            logger.info(f"Backtesting {symbol}...")

            try:
                # Get momentum events for this symbol
                events = self.detector.get_events(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe,
                )

                if not events:
                    logger.warning(f"No momentum events found for {symbol}")
                    continue

                # Simulate trades for each event
                symbol_trades = self._simulate_trades(symbol, events, timeframe)
                all_trades.extend(symbol_trades)

                # Calculate per-symbol performance
                if symbol_trades:
                    performance_by_symbol[symbol] = self._calculate_performance(
                        symbol_trades
                    )

            except Exception as e:
                logger.error(f"Error backtesting {symbol}: {e}")
                continue

        # Calculate overall performance
        overall_performance = self._calculate_performance(all_trades)

        results = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "symbols": symbols,
            "total_trades": len(all_trades),
            "overall_performance": overall_performance,
            "performance_by_symbol": performance_by_symbol,
            "all_trades": all_trades,
        }

        self._print_backtest_summary(results)

        return results

    def _simulate_trades(
        self,
        symbol: str,
        events: List[MomentumEvent],
        timeframe: str,
    ) -> List[Dict]:
        """
        Simulate trades based on momentum events.

        Args:
            symbol: Stock symbol
            events: List of momentum events
            timeframe: Timeframe

        Returns:
            List of simulated trades
        """
        trades = []

        for event in events:
            try:
                # Get prediction for this event
                prediction = self.stats_engine.predict_continuation(
                    symbol=symbol,
                    initial_move_pct=float(event.max_move_percentage),
                    volume_ratio=2.5,  # Approximate, as we don't store volume_ratio
                    timeframe=timeframe,
                    direction=event.direction,
                )

                if "error" in prediction:
                    continue

                # Check if we should enter based on continuation probability
                cont_prob = prediction.get("continuation_probability", 0)
                if cont_prob < self.entry_threshold_prob:
                    continue  # Skip low probability trades

                # Entry point: at the end of the initial momentum event
                entry_price = float(event.peak_price)
                entry_time = event.end_time

                # Fetch price data after entry to simulate exit
                exit_result = self._simulate_exit(
                    symbol, entry_time, entry_price, event.direction, timeframe
                )

                if exit_result:
                    trade = {
                        "symbol": symbol,
                        "entry_time": entry_time,
                        "entry_price": entry_price,
                        "direction": event.direction,
                        "exit_time": exit_result["exit_time"],
                        "exit_price": exit_result["exit_price"],
                        "exit_reason": exit_result["exit_reason"],
                        "pnl_pct": exit_result["pnl_pct"],
                        "pnl_dollars": exit_result["pnl_dollars"],
                        "duration_minutes": exit_result["duration_minutes"],
                        "continuation_probability": cont_prob,
                        "initial_move_pct": float(event.max_move_percentage),
                    }
                    trades.append(trade)

            except Exception as e:
                logger.error(f"Error simulating trade for {symbol}: {e}")
                continue

        return trades

    def _simulate_exit(
        self,
        symbol: str,
        entry_time: datetime,
        entry_price: float,
        direction: str,
        timeframe: str,
        max_holding_minutes: int = 120,
    ) -> Optional[Dict]:
        """
        Simulate trade exit based on stop loss, take profit, or time.

        Args:
            symbol: Stock symbol
            entry_time: Entry timestamp
            entry_price: Entry price
            direction: Trade direction ('UP' or 'DOWN')
            timeframe: Timeframe
            max_holding_minutes: Maximum holding period

        Returns:
            Dictionary with exit information or None
        """
        # Calculate stop loss and take profit levels
        if direction == "UP":
            stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
            take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
        else:
            stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)
            take_profit_price = entry_price * (1 - self.take_profit_pct / 100)

        # Fetch price data after entry
        end_time = entry_time + timedelta(minutes=max_holding_minutes)

        try:
            with self.db.get_session() as session:
                from sqlalchemy import and_

                query = (
                    session.query(StockPrice)
                    .filter(
                        and_(
                            StockPrice.symbol == symbol,
                            StockPrice.timeframe == timeframe,
                            StockPrice.timestamp > entry_time,
                            StockPrice.timestamp <= end_time,
                        )
                    )
                    .order_by(StockPrice.timestamp)
                )

                data = pd.read_sql(query.statement, session.bind)

            if data.empty:
                return None

            # Check each bar for stop loss or take profit
            for _, bar in data.iterrows():
                high = float(bar["high"])
                low = float(bar["low"])
                close = float(bar["close"])
                timestamp = bar["timestamp"]

                if direction == "UP":
                    # Check stop loss (price went down)
                    if low <= stop_loss_price:
                        pnl_pct = ((stop_loss_price - entry_price) / entry_price) * 100
                        return {
                            "exit_time": timestamp,
                            "exit_price": stop_loss_price,
                            "exit_reason": "STOP_LOSS",
                            "pnl_pct": round(pnl_pct, 2),
                            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
                            "duration_minutes": int(
                                (timestamp - entry_time).total_seconds() / 60
                            ),
                        }

                    # Check take profit (price went up)
                    if high >= take_profit_price:
                        pnl_pct = ((take_profit_price - entry_price) / entry_price) * 100
                        return {
                            "exit_time": timestamp,
                            "exit_price": take_profit_price,
                            "exit_reason": "TAKE_PROFIT",
                            "pnl_pct": round(pnl_pct, 2),
                            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
                            "duration_minutes": int(
                                (timestamp - entry_time).total_seconds() / 60
                            ),
                        }

                else:  # DOWN
                    # Check stop loss (price went up)
                    if high >= stop_loss_price:
                        pnl_pct = ((entry_price - stop_loss_price) / entry_price) * 100
                        return {
                            "exit_time": timestamp,
                            "exit_price": stop_loss_price,
                            "exit_reason": "STOP_LOSS",
                            "pnl_pct": round(pnl_pct, 2),
                            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
                            "duration_minutes": int(
                                (timestamp - entry_time).total_seconds() / 60
                            ),
                        }

                    # Check take profit (price went down)
                    if low <= take_profit_price:
                        pnl_pct = ((entry_price - take_profit_price) / entry_price) * 100
                        return {
                            "exit_time": timestamp,
                            "exit_price": take_profit_price,
                            "exit_reason": "TAKE_PROFIT",
                            "pnl_pct": round(pnl_pct, 2),
                            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
                            "duration_minutes": int(
                                (timestamp - entry_time).total_seconds() / 60
                            ),
                        }

            # Time-based exit (max holding period reached)
            final_bar = data.iloc[-1]
            final_price = float(final_bar["close"])
            final_time = final_bar["timestamp"]

            if direction == "UP":
                pnl_pct = ((final_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - final_price) / entry_price) * 100

            return {
                "exit_time": final_time,
                "exit_price": final_price,
                "exit_reason": "TIME_BASED",
                "pnl_pct": round(pnl_pct, 2),
                "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
                "duration_minutes": int((final_time - entry_time).total_seconds() / 60),
            }

        except Exception as e:
            logger.error(f"Error simulating exit: {e}")
            return None

    def _calculate_performance(self, trades: List[Dict]) -> Dict:
        """
        Calculate performance metrics from trades.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary with performance metrics
        """
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl_per_trade": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
            }

        df = pd.DataFrame(trades)

        # Winning and losing trades
        winning_trades = df[df["pnl_pct"] > 0]
        losing_trades = df[df["pnl_pct"] <= 0]

        # Calculate metrics
        total_trades = len(df)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        total_pnl = df["pnl_dollars"].sum()
        avg_pnl_per_trade = df["pnl_dollars"].mean()

        avg_win = winning_trades["pnl_dollars"].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades["pnl_dollars"].mean() if len(losing_trades) > 0 else 0

        # Profit factor
        gross_profit = winning_trades["pnl_dollars"].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades["pnl_dollars"].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Sharpe ratio (assuming risk-free rate = 0)
        returns = df["pnl_pct"].values
        sharpe_ratio = (
            (returns.mean() / returns.std()) * np.sqrt(252)
            if returns.std() > 0
            else 0
        )

        # Additional metrics
        max_win = winning_trades["pnl_dollars"].max() if len(winning_trades) > 0 else 0
        max_loss = losing_trades["pnl_dollars"].min() if len(losing_trades) > 0 else 0

        avg_duration = df["duration_minutes"].mean()

        # Exit reason breakdown
        exit_reasons = df["exit_reason"].value_counts().to_dict()

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 3),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(avg_pnl_per_trade, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "INF",
            "sharpe_ratio": round(sharpe_ratio, 2),
            "avg_duration_minutes": round(avg_duration, 1),
            "exit_reasons": exit_reasons,
        }

    def _print_backtest_summary(self, results: Dict) -> None:
        """Print formatted backtest summary."""
        print("\n" + "=" * 80)
        print("BACKTEST RESULTS SUMMARY")
        print("=" * 80)

        print(f"\nPeriod: {results['start_date']} to {results['end_date']}")
        print(f"Symbols: {', '.join(results['symbols'])}")
        print(f"Total Trades: {results['total_trades']}")

        perf = results["overall_performance"]
        print("\n" + "-" * 80)
        print("OVERALL PERFORMANCE")
        print("-" * 80)
        print(f"Win Rate:              {perf['win_rate'] * 100:.1f}%")
        print(f"Total P&L:             ${perf['total_pnl']:,.2f}")
        print(f"Avg P&L per Trade:     ${perf['avg_pnl_per_trade']:,.2f}")
        print(f"Average Win:           ${perf['avg_win']:,.2f}")
        print(f"Average Loss:          ${perf['avg_loss']:,.2f}")
        print(f"Max Win:               ${perf['max_win']:,.2f}")
        print(f"Max Loss:              ${perf['max_loss']:,.2f}")
        print(f"Profit Factor:         {perf['profit_factor']}")
        print(f"Sharpe Ratio:          {perf['sharpe_ratio']}")
        print(f"Avg Trade Duration:    {perf['avg_duration_minutes']:.1f} minutes")

        print("\n" + "-" * 80)
        print("EXIT REASON BREAKDOWN")
        print("-" * 80)
        for reason, count in perf["exit_reasons"].items():
            pct = (count / results["total_trades"]) * 100
            print(f"{reason:20s}: {count:4d} ({pct:5.1f}%)")

        if results["performance_by_symbol"]:
            print("\n" + "-" * 80)
            print("PERFORMANCE BY SYMBOL")
            print("-" * 80)
            for symbol, symbol_perf in results["performance_by_symbol"].items():
                print(
                    f"{symbol:8s}: Trades={symbol_perf['total_trades']:3d}, "
                    f"Win Rate={symbol_perf['win_rate']*100:5.1f}%, "
                    f"Total P&L=${symbol_perf['total_pnl']:8,.2f}"
                )

        print("\n" + "=" * 80 + "\n")

    def full_analysis(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
    ) -> Dict:
        """
        Run full analysis pipeline: collect data -> detect events -> backtest.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            timeframe: Timeframe

        Returns:
            Dictionary with all results
        """
        logger.info(f"Starting full analysis for {len(symbols)} symbols")

        # Step 1: Collect data
        logger.info("Step 1: Collecting historical data...")
        interval = "5m" if timeframe == "5min" else timeframe
        collection_stats = self.collector.collect_and_save(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            intervals=[interval],
        )
        logger.info(f"Collected {collection_stats['total_rows']} rows")

        # Step 2: Detect momentum events
        logger.info("Step 2: Detecting momentum events...")
        detection_stats = self.detector.batch_detect(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )
        logger.info(f"Detected {detection_stats['total_events']} events")

        # Step 3: Run backtest
        logger.info("Step 3: Running backtest simulation...")
        backtest_results = self.backtest_strategy(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )

        return {
            "collection_stats": collection_stats,
            "detection_stats": detection_stats,
            "backtest_results": backtest_results,
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GamblerAI Backtest and Screening Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Screen command
    screen_parser = subparsers.add_parser(
        "screen", help="Screen stocks for momentum opportunities"
    )
    screen_parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of stock symbols",
    )
    screen_parser.add_argument(
        "--timeframe",
        default="5min",
        help="Timeframe to analyze (default: 5min)",
    )
    screen_parser.add_argument(
        "--lookback",
        type=int,
        default=30,
        help="Minutes to look back (default: 30)",
    )

    # Backtest command
    backtest_parser = subparsers.add_parser(
        "backtest", help="Backtest momentum trading strategy"
    )
    backtest_parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of stock symbols",
    )
    backtest_parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    backtest_parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    backtest_parser.add_argument(
        "--timeframe",
        default="5min",
        help="Timeframe to use (default: 5min)",
    )

    # Full analysis command
    full_parser = subparsers.add_parser(
        "full-analysis", help="Run full analysis pipeline"
    )
    full_parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of stock symbols",
    )
    full_parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    full_parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    full_parser.add_argument(
        "--timeframe",
        default="5min",
        help="Timeframe to use (default: 5min)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize engine
    engine = BacktestScreening()

    # Parse symbols
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    # Execute command
    if args.command == "screen":
        results = engine.screen_stocks(
            symbols=symbols,
            timeframe=args.timeframe,
            lookback_minutes=args.lookback,
        )

        if not results.empty:
            print("\n" + "=" * 100)
            print("MOMENTUM SCREENING RESULTS")
            print("=" * 100)
            print(results.to_string(index=False))
            print("\n")

    elif args.command == "backtest":
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")

        engine.backtest_strategy(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=args.timeframe,
        )

    elif args.command == "full-analysis":
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")

        engine.full_analysis(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe=args.timeframe,
        )


if __name__ == "__main__":
    main()
