#!/usr/bin/env python3
"""
Backtest momentum strategy using real CSV data files.
"""

import argparse
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
from glob import glob


class CSVBacktest:
    """Backtest using CSV data files."""

    def __init__(
        self,
        min_price_change_pct=2.0,
        min_volume_ratio=2.0,
        stop_loss_pct=2.0,
        take_profit_pct=4.0,
        position_size=10000,
    ):
        self.min_price_change_pct = min_price_change_pct
        self.min_volume_ratio = min_volume_ratio
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position_size = position_size
        self.window_bars = 5  # Look at 5-bar windows for momentum

    def load_data(self, file_path):
        """Load data from CSV."""
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        return df

    def detect_momentum_events(self, df, symbol):
        """Detect momentum events."""
        df = df.copy()

        # Calculate indicators
        df['avg_volume'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume']

        events = []

        for i in range(self.window_bars, len(df) - 60):
            window = df.iloc[i - self.window_bars + 1 : i + 1]

            price_change_pct = (
                (window.iloc[-1]['close'] - window.iloc[0]['open'])
                / window.iloc[0]['open']
                * 100
            )

            avg_vol_ratio = window['volume_ratio'].mean()

            if pd.isna(avg_vol_ratio):
                continue

            if (
                abs(price_change_pct) >= self.min_price_change_pct
                and avg_vol_ratio >= self.min_volume_ratio
            ):
                direction = "UP" if price_change_pct > 0 else "DOWN"

                event = {
                    "symbol": symbol,
                    "timestamp": window.iloc[0]['timestamp'],
                    "end_idx": i,
                    "direction": direction,
                    "entry_price": float(window.iloc[-1]['close']),
                    "initial_move_pct": abs(price_change_pct),
                    "volume_ratio": float(avg_vol_ratio),
                }

                events.append(event)

        return events

    def simulate_trades(self, symbol, df, events):
        """Simulate trades."""
        trades = []

        for event in events:
            entry_idx = event["end_idx"]
            entry_price = event["entry_price"]
            direction = event["direction"]

            # Calculate stop/take profit
            if direction == "UP":
                stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
                take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
            else:
                stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)
                take_profit_price = entry_price * (1 - self.take_profit_pct / 100)

            # Check next 120 bars
            for j in range(entry_idx + 1, min(entry_idx + 120, len(df))):
                bar = df.iloc[j]

                if direction == "UP":
                    if bar["low"] <= stop_loss_price:
                        pnl_pct = ((stop_loss_price - entry_price) / entry_price) * 100
                        trades.append(
                            self._create_trade(
                                symbol,
                                event["timestamp"],
                                entry_price,
                                direction,
                                bar["timestamp"],
                                stop_loss_price,
                                "STOP_LOSS",
                                pnl_pct,
                                j - entry_idx,
                            )
                        )
                        break
                    elif bar["high"] >= take_profit_price:
                        pnl_pct = ((take_profit_price - entry_price) / entry_price) * 100
                        trades.append(
                            self._create_trade(
                                symbol,
                                event["timestamp"],
                                entry_price,
                                direction,
                                bar["timestamp"],
                                take_profit_price,
                                "TAKE_PROFIT",
                                pnl_pct,
                                j - entry_idx,
                            )
                        )
                        break
                else:
                    if bar["high"] >= stop_loss_price:
                        pnl_pct = ((entry_price - stop_loss_price) / entry_price) * 100
                        trades.append(
                            self._create_trade(
                                symbol,
                                event["timestamp"],
                                entry_price,
                                direction,
                                bar["timestamp"],
                                stop_loss_price,
                                "STOP_LOSS",
                                pnl_pct,
                                j - entry_idx,
                            )
                        )
                        break
                    elif bar["low"] <= take_profit_price:
                        pnl_pct = ((entry_price - take_profit_price) / entry_price) * 100
                        trades.append(
                            self._create_trade(
                                symbol,
                                event["timestamp"],
                                entry_price,
                                direction,
                                bar["timestamp"],
                                take_profit_price,
                                "TAKE_PROFIT",
                                pnl_pct,
                                j - entry_idx,
                            )
                        )
                        break

        return trades

    def _create_trade(
        self, symbol, entry_time, entry_price, direction, exit_time, exit_price, exit_reason, pnl_pct, duration_bars
    ):
        return {
            "symbol": symbol,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "direction": direction,
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl_pct": round(pnl_pct, 2),
            "pnl_dollars": round((pnl_pct / 100) * self.position_size, 2),
            "duration_days": duration_bars,
        }

    def calculate_performance(self, trades):
        """Calculate performance metrics."""
        if not trades:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0}

        df = pd.DataFrame(trades)
        winning = df[df["pnl_pct"] > 0]
        losing = df[df["pnl_pct"] <= 0]

        win_rate = len(winning) / len(df)
        total_pnl = df["pnl_dollars"].sum()

        gross_profit = winning["pnl_dollars"].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing["pnl_dollars"].sum()) if len(losing) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        returns = df["pnl_pct"].values
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

        return {
            "total_trades": len(df),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate, 3),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(df["pnl_dollars"].mean(), 2),
            "avg_win": round(winning["pnl_dollars"].mean() if len(winning) > 0 else 0, 2),
            "avg_loss": round(losing["pnl_dollars"].mean() if len(losing) > 0 else 0, 2),
            "max_win": round(winning["pnl_dollars"].max() if len(winning) > 0 else 0, 2),
            "max_loss": round(losing["pnl_dollars"].min() if len(losing) > 0 else 0, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "INF",
            "sharpe_ratio": round(sharpe, 2),
            "exit_reasons": df["exit_reason"].value_counts().to_dict(),
        }

    def run_backtest(self, data_dir):
        """Run backtest on CSV files in directory."""
        csv_files = glob(str(Path(data_dir) / "*.csv"))

        if not csv_files:
            print(f"No CSV files found in {data_dir}")
            return None

        print("\n" + "=" * 80)
        print("MOMENTUM STRATEGY BACKTEST - REAL DATA")
        print("=" * 80)
        print(f"Data directory: {data_dir}")
        print(f"Found {len(csv_files)} data files")
        print(f"Strategy: {self.stop_loss_pct}% stop loss, {self.take_profit_pct}% take profit")
        print("=" * 80 + "\n")

        all_trades = []
        performance_by_symbol = {}

        for csv_file in csv_files:
            symbol = Path(csv_file).stem.split('_')[0]
            print(f"\nProcessing {symbol} ({Path(csv_file).name})...")

            df = self.load_data(csv_file)
            print(f"  ✓ Loaded {len(df)} bars")
            print(f"  ✓ Date range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
            print(f"  ✓ Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")

            events = self.detect_momentum_events(df, symbol)
            print(f"  ✓ Detected {len(events)} momentum events")

            if events:
                trades = self.simulate_trades(symbol, df, events)
                print(f"  ✓ Simulated {len(trades)} trades")

                all_trades.extend(trades)
                if trades:
                    performance_by_symbol[symbol] = self.calculate_performance(trades)

        # Overall performance
        overall = self.calculate_performance(all_trades)

        # Print results
        self._print_results(overall, performance_by_symbol)

        return {
            "overall": overall,
            "by_symbol": performance_by_symbol,
            "trades": all_trades,
        }

    def _print_results(self, overall, by_symbol):
        """Print formatted results."""
        print("\n" + "=" * 80)
        print("BACKTEST RESULTS")
        print("=" * 80)
        print(f"\nTotal Trades: {overall['total_trades']}")

        if overall["total_trades"] > 0:
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
            print(f"Max Win:               ${overall['max_win']:,.2f}")
            print(f"Max Loss:              ${overall['max_loss']:,.2f}")
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

        print("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Backtest from CSV data")
    parser.add_argument("--data-dir", required=True, help="Directory containing CSV files")
    parser.add_argument("--output", default="real_backtest_results.csv", help="Output CSV file")
    parser.add_argument("--stop-loss", type=float, default=2.0, help="Stop loss %%")
    parser.add_argument("--take-profit", type=float, default=4.0, help="Take profit %%")

    args = parser.parse_args()

    backtest = CSVBacktest(
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
    )

    results = backtest.run_backtest(args.data_dir)

    if results and results["trades"]:
        trades_df = pd.DataFrame(results["trades"])
        trades_df.to_csv(args.output, index=False)
        print(f"✓ Saved {len(trades_df)} trades to: {args.output}\n")


if __name__ == "__main__":
    main()
