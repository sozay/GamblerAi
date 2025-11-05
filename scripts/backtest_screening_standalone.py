#!/usr/bin/env python3
"""
Standalone backtesting script for GamblerAI momentum trading strategy.

This version works WITHOUT a database - fetches data directly from Yahoo Finance
and processes everything in-memory.

Usage:
    python backtest_screening_standalone.py --symbols AAPL,MSFT,GOOGL --start 2021-06-01 --end 2022-06-30
"""

import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


class StandaloneMomentumBacktest:
    """Standalone momentum backtesting engine."""

    def __init__(
        self,
        min_price_change_pct: float = 2.0,
        min_volume_ratio: float = 2.0,
        window_minutes: int = 5,
        lookback_periods: int = 20,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
        entry_threshold_prob: float = 0.6,
        position_size: float = 10000,
    ):
        """Initialize backtest engine with parameters."""
        self.min_price_change_pct = min_price_change_pct
        self.min_volume_ratio = min_volume_ratio
        self.window_minutes = window_minutes
        self.lookback_periods = lookback_periods
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.entry_threshold_prob = entry_threshold_prob
        self.position_size = position_size

    def fetch_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "5m",
    ) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance."""
        print(f"Fetching {interval} data for {symbol}...")

        try:
            ticker = yf.Ticker(symbol)

            # Yahoo Finance limitations
            all_data = []
            current_start = start_date
            chunk_days = 60 if interval in ["5m", "15m", "30m", "1h"] else 365

            while current_start < end_date:
                current_end = min(current_start + timedelta(days=chunk_days), end_date)

                df = ticker.history(
                    start=current_start.strftime("%Y-%m-%d"),
                    end=current_end.strftime("%Y-%m-%d"),
                    interval=interval,
                    actions=False,
                )

                if not df.empty:
                    all_data.append(df)

                current_start = current_end

            if not all_data:
                print(f"  ✗ No data returned for {symbol}")
                return pd.DataFrame()

            # Combine all chunks
            result = pd.concat(all_data)
            result.columns = [col.lower() for col in result.columns]
            result = result.reset_index()
            result.rename(
                columns={"date": "timestamp", "index": "timestamp"}, inplace=True
            )

            print(f"  ✓ Fetched {len(result)} bars for {symbol}")
            return result

        except Exception as e:
            print(f"  ✗ Error fetching {symbol}: {e}")
            return pd.DataFrame()

    def detect_momentum_events(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Detect momentum events in price data."""
        if df.empty or len(df) < self.lookback_periods:
            return []

        # Calculate indicators
        df = df.copy()
        df["avg_volume"] = df["volume"].rolling(window=self.lookback_periods).mean()
        df["volume_ratio"] = df["volume"] / df["avg_volume"]

        events = []

        for i in range(self.window_minutes, len(df)):
            if i + self.lookback_periods > len(df):
                break

            # Get window
            window_start_idx = i - self.window_minutes + 1
            window = df.iloc[window_start_idx : i + 1]

            # Calculate price change
            price_change_pct = (
                (window.iloc[-1]["close"] - window.iloc[0]["open"])
                / window.iloc[0]["open"]
                * 100
            )

            avg_vol_ratio = window["volume_ratio"].mean()

            # Check if this qualifies as momentum event
            if pd.isna(avg_vol_ratio):
                continue

            if (
                abs(price_change_pct) >= self.min_price_change_pct
                and avg_vol_ratio >= self.min_volume_ratio
            ):
                direction = "UP" if price_change_pct > 0 else "DOWN"

                # Analyze continuation
                continuation = self._analyze_continuation(
                    df, i, direction, float(window.iloc[0]["open"])
                )

                event = {
                    "symbol": symbol,
                    "timestamp": window.iloc[0]["timestamp"],
                    "end_idx": i,
                    "direction": direction,
                    "entry_price": float(window.iloc[-1]["close"]),
                    "initial_move_pct": abs(price_change_pct),
                    "volume_ratio": float(avg_vol_ratio),
                    "continuation_bars": continuation["continuation_bars"],
                    "reversal_bars": continuation["reversal_bars"],
                }

                events.append(event)

        return events

    def _analyze_continuation(
        self, df: pd.DataFrame, event_end_idx: int, direction: str, initial_price: float
    ) -> Dict:
        """Analyze continuation and reversal."""
        max_lookforward = 60
        continuation_bars = 0
        reversal_bars = None

        peak_price = df.iloc[event_end_idx]["close"]
        initial_move = abs(peak_price - initial_price)
        reversal_threshold_price = (
            peak_price - (initial_move * 0.5)
            if direction == "UP"
            else peak_price + (initial_move * 0.5)
        )

        current_peak = peak_price

        for j in range(
            event_end_idx + 1, min(event_end_idx + max_lookforward, len(df))
        ):
            row = df.iloc[j]
            current_price = float(row["close"])

            if direction == "UP":
                if current_price > current_peak:
                    current_peak = current_price
                    continuation_bars = j - event_end_idx

                if current_price <= reversal_threshold_price and reversal_bars is None:
                    reversal_bars = j - event_end_idx
                    break
            else:
                if current_price < current_peak:
                    current_peak = current_price
                    continuation_bars = j - event_end_idx

                if current_price >= reversal_threshold_price and reversal_bars is None:
                    reversal_bars = j - event_end_idx
                    break

        return {
            "continuation_bars": continuation_bars,
            "reversal_bars": reversal_bars,
        }

    def calculate_continuation_probability(
        self, events: List[Dict], initial_move_pct: float, tolerance: float = 0.5
    ) -> float:
        """Calculate continuation probability from similar historical events."""
        if not events:
            return 0.0

        # Filter similar events
        lower = initial_move_pct * (1 - tolerance)
        upper = initial_move_pct * (1 + tolerance)

        similar = [
            e
            for e in events
            if lower <= e["initial_move_pct"] <= upper and e["continuation_bars"] > 0
        ]

        if len(similar) < 5:
            return 0.5  # Default probability if insufficient data

        # Count events with meaningful continuation
        continued = [e for e in similar if e["continuation_bars"] > 5]

        return len(continued) / len(similar) if similar else 0.5

    def simulate_trades(
        self, symbol: str, df: pd.DataFrame, events: List[Dict]
    ) -> List[Dict]:
        """Simulate trades for detected events."""
        trades = []

        for event in events:
            # Calculate continuation probability from past events
            past_events = [e for e in events if e["timestamp"] < event["timestamp"]]
            cont_prob = self.calculate_continuation_probability(
                past_events, event["initial_move_pct"]
            )

            # Only enter if probability is high enough
            if cont_prob < self.entry_threshold_prob:
                continue

            # Entry
            entry_idx = event["end_idx"]
            entry_price = event["entry_price"]
            direction = event["direction"]

            # Simulate exit
            exit_result = self._simulate_exit(
                df, entry_idx, entry_price, direction
            )

            if exit_result:
                trade = {
                    "symbol": symbol,
                    "entry_time": event["timestamp"],
                    "entry_price": entry_price,
                    "direction": direction,
                    "exit_time": exit_result["exit_time"],
                    "exit_price": exit_result["exit_price"],
                    "exit_reason": exit_result["exit_reason"],
                    "pnl_pct": exit_result["pnl_pct"],
                    "pnl_dollars": exit_result["pnl_dollars"],
                    "duration_minutes": exit_result["duration_minutes"],
                    "continuation_probability": cont_prob,
                    "initial_move_pct": event["initial_move_pct"],
                }
                trades.append(trade)

        return trades

    def _simulate_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        entry_price: float,
        direction: str,
        max_holding_bars: int = 120,
    ) -> Optional[Dict]:
        """Simulate trade exit."""
        # Calculate stop/take profit levels
        if direction == "UP":
            stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
            take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
        else:
            stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)
            take_profit_price = entry_price * (1 - self.take_profit_pct / 100)

        # Check subsequent bars
        for j in range(entry_idx + 1, min(entry_idx + max_holding_bars, len(df))):
            bar = df.iloc[j]
            high = float(bar["high"])
            low = float(bar["low"])
            close = float(bar["close"])
            timestamp = bar["timestamp"]

            if direction == "UP":
                if low <= stop_loss_price:
                    pnl_pct = ((stop_loss_price - entry_price) / entry_price) * 100
                    return self._create_exit(
                        timestamp, stop_loss_price, "STOP_LOSS", pnl_pct, j - entry_idx
                    )
                if high >= take_profit_price:
                    pnl_pct = ((take_profit_price - entry_price) / entry_price) * 100
                    return self._create_exit(
                        timestamp, take_profit_price, "TAKE_PROFIT", pnl_pct, j - entry_idx
                    )
            else:
                if high >= stop_loss_price:
                    pnl_pct = ((entry_price - stop_loss_price) / entry_price) * 100
                    return self._create_exit(
                        timestamp, stop_loss_price, "STOP_LOSS", pnl_pct, j - entry_idx
                    )
                if low <= take_profit_price:
                    pnl_pct = ((entry_price - take_profit_price) / entry_price) * 100
                    return self._create_exit(
                        timestamp, take_profit_price, "TAKE_PROFIT", pnl_pct, j - entry_idx
                    )

        # Time-based exit
        final_bar = df.iloc[min(entry_idx + max_holding_bars, len(df) - 1)]
        final_price = float(final_bar["close"])

        if direction == "UP":
            pnl_pct = ((final_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - final_price) / entry_price) * 100

        return self._create_exit(
            final_bar["timestamp"], final_price, "TIME_BASED", pnl_pct,
            min(max_holding_bars, len(df) - entry_idx - 1)
        )

    def _create_exit(
        self, timestamp, price, reason, pnl_pct, duration_bars
    ) -> Dict:
        """Create exit result dictionary."""
        return {
            "exit_time": timestamp,
            "exit_price": price,
            "exit_reason": reason,
            "pnl_pct": round(pnl_pct, 2),
            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
            "duration_minutes": duration_bars * 5,  # Assuming 5min bars
        }

    def calculate_performance(self, trades: List[Dict]) -> Dict:
        """Calculate performance metrics."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl_per_trade": 0,
            }

        df = pd.DataFrame(trades)

        winning_trades = df[df["pnl_pct"] > 0]
        losing_trades = df[df["pnl_pct"] <= 0]

        total_trades = len(df)
        win_rate = len(winning_trades) / total_trades
        total_pnl = df["pnl_dollars"].sum()
        avg_pnl = df["pnl_dollars"].mean()

        avg_win = winning_trades["pnl_dollars"].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades["pnl_dollars"].mean() if len(losing_trades) > 0 else 0

        gross_profit = winning_trades["pnl_dollars"].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades["pnl_dollars"].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        returns = df["pnl_pct"].values
        sharpe = (
            (returns.mean() / returns.std()) * np.sqrt(252)
            if returns.std() > 0
            else 0
        )

        exit_reasons = df["exit_reason"].value_counts().to_dict()

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(win_rate, 3),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(avg_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "INF",
            "sharpe_ratio": round(sharpe, 2),
            "exit_reasons": exit_reasons,
        }

    def run_backtest(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "5m",
    ) -> Dict:
        """Run complete backtest."""
        print("\n" + "=" * 80)
        print("MOMENTUM STRATEGY BACKTEST")
        print("=" * 80)
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Parameters: min_move={self.min_price_change_pct}%, "
              f"min_vol_ratio={self.min_volume_ratio}x")
        print("=" * 80 + "\n")

        all_trades = []
        performance_by_symbol = {}

        for symbol in symbols:
            print(f"\nProcessing {symbol}...")

            # Fetch data
            df = self.fetch_data(symbol, start_date, end_date, interval)

            if df.empty:
                continue

            # Detect momentum events
            events = self.detect_momentum_events(df, symbol)
            print(f"  ✓ Detected {len(events)} momentum events")

            if not events:
                continue

            # Simulate trades
            trades = self.simulate_trades(symbol, df, events)
            print(f"  ✓ Simulated {len(trades)} trades")

            all_trades.extend(trades)

            if trades:
                performance_by_symbol[symbol] = self.calculate_performance(trades)

        # Calculate overall performance
        overall = self.calculate_performance(all_trades)

        # Print results
        self._print_results(overall, performance_by_symbol, start_date, end_date)

        return {
            "overall": overall,
            "by_symbol": performance_by_symbol,
            "trades": all_trades,
        }

    def _print_results(self, overall, by_symbol, start_date, end_date):
        """Print formatted results."""
        print("\n" + "=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)

        print(f"\nPeriod: {start_date.date()} to {end_date.date()}")
        print(f"Total Trades: {overall['total_trades']}")

        if overall['total_trades'] > 0:
            print("\n" + "-" * 80)
            print("OVERALL PERFORMANCE")
            print("-" * 80)
            print(f"Win Rate:              {overall['win_rate'] * 100:.1f}%")
            print(f"Winning Trades:        {overall['winning_trades']}")
            print(f"Losing Trades:         {overall['losing_trades']}")
            print(f"Total P&L:             ${overall['total_pnl']:,.2f}")
            print(f"Avg P&L per Trade:     ${overall['avg_pnl_per_trade']:,.2f}")
            print(f"Average Win:           ${overall['avg_win']:,.2f}")
            print(f"Average Loss:          ${overall['avg_loss']:,.2f}")
            print(f"Profit Factor:         {overall['profit_factor']}")
            print(f"Sharpe Ratio:          {overall['sharpe_ratio']}")

            print("\n" + "-" * 80)
            print("EXIT REASON BREAKDOWN")
            print("-" * 80)
            for reason, count in overall["exit_reasons"].items():
                pct = (count / overall["total_trades"]) * 100
                print(f"{reason:20s}: {count:4d} ({pct:5.1f}%)")

            if by_symbol:
                print("\n" + "-" * 80)
                print("PERFORMANCE BY SYMBOL")
                print("-" * 80)
                for symbol, perf in by_symbol.items():
                    print(
                        f"{symbol:8s}: Trades={perf['total_trades']:3d}, "
                        f"Win Rate={perf['win_rate']*100:5.1f}%, "
                        f"Total P&L=${perf['total_pnl']:8,.2f}"
                    )
        else:
            print("\n✗ No trades were generated. Try adjusting parameters.")

        print("\n" + "=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Standalone Momentum Backtest (no database required)"
    )
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of stock symbols",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--interval",
        default="5m",
        help="Data interval (default: 5m)",
    )
    parser.add_argument(
        "--min-move",
        type=float,
        default=2.0,
        help="Minimum price move %% (default: 2.0)",
    )
    parser.add_argument(
        "--min-vol-ratio",
        type=float,
        default=2.0,
        help="Minimum volume ratio (default: 2.0)",
    )
    parser.add_argument(
        "--stop-loss",
        type=float,
        default=2.0,
        help="Stop loss %% (default: 2.0)",
    )
    parser.add_argument(
        "--take-profit",
        type=float,
        default=4.0,
        help="Take profit %% (default: 4.0)",
    )

    args = parser.parse_args()

    # Parse inputs
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    # Create backtest engine
    backtest = StandaloneMomentumBacktest(
        min_price_change_pct=args.min_move,
        min_volume_ratio=args.min_vol_ratio,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
    )

    # Run backtest
    results = backtest.run_backtest(symbols, start_date, end_date, args.interval)

    # Save results to CSV
    if results["trades"]:
        trades_df = pd.DataFrame(results["trades"])
        output_file = f"backtest_results_{start_date.date()}_{end_date.date()}.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"✓ Detailed trade log saved to: {output_file}\n")


if __name__ == "__main__":
    main()
