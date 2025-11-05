#!/usr/bin/env python3
"""
Parameter optimization script for momentum trading strategy.

Tests different combinations of:
- Stop loss percentages
- Take profit percentages
- Entry threshold probabilities
- Minimum price move requirements

Outputs a matrix of results to find optimal parameters.
"""

import argparse
from datetime import datetime
from itertools import product
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import demo backtest (works without database)
from scripts.demo_backtest import DemoBacktest


class ParameterOptimizer:
    """Optimize trading strategy parameters."""

    def __init__(self):
        self.results = []

    def optimize(
        self,
        symbols: list,
        start_date: datetime,
        end_date: datetime,
        param_grid: dict,
    ):
        """
        Run backtest with different parameter combinations.

        Args:
            symbols: List of symbols to test
            start_date: Start date
            end_date: End date
            param_grid: Dictionary of parameters to test
        """
        print("\n" + "=" * 80)
        print("PARAMETER OPTIMIZATION")
        print("=" * 80)
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Symbols: {', '.join(symbols)}")
        print("\nParameter Grid:")
        for param, values in param_grid.items():
            print(f"  {param}: {values}")
        print("=" * 80 + "\n")

        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))

        total_combinations = len(combinations)
        print(f"Testing {total_combinations} parameter combinations...\n")

        for idx, params in enumerate(combinations, 1):
            # Create parameter dict
            param_dict = dict(zip(param_names, params))

            print(f"[{idx}/{total_combinations}] Testing: {param_dict}")

            # Create backtest instance with these parameters
            backtest = DemoBacktest()
            backtest.min_price_change_pct = param_dict.get(
                "min_price_change_pct", 2.0
            )
            backtest.stop_loss_pct = param_dict.get("stop_loss_pct", 2.0)
            backtest.take_profit_pct = param_dict.get("take_profit_pct", 4.0)
            backtest.min_volume_ratio = param_dict.get("min_volume_ratio", 2.0)

            # Run backtest (suppress output)
            try:
                results = backtest.run_backtest(
                    symbols, start_date, end_date
                )

                overall = results["overall"]

                # Store results
                result_row = {
                    **param_dict,
                    "total_trades": overall["total_trades"],
                    "win_rate": overall["win_rate"],
                    "total_pnl": overall["total_pnl"],
                    "avg_pnl_per_trade": overall["avg_pnl_per_trade"],
                    "profit_factor": overall["profit_factor"],
                    "sharpe_ratio": overall["sharpe_ratio"],
                }

                self.results.append(result_row)

                print(
                    f"  → Trades: {overall['total_trades']}, "
                    f"Win Rate: {overall['win_rate']*100:.1f}%, "
                    f"Total P&L: ${overall['total_pnl']:,.0f}\n"
                )

            except Exception as e:
                print(f"  ✗ Error: {e}\n")
                continue

        return self.results

    def analyze_results(self):
        """Analyze optimization results."""
        if not self.results:
            print("No results to analyze")
            return

        df = pd.DataFrame(self.results)

        print("\n" + "=" * 80)
        print("OPTIMIZATION RESULTS SUMMARY")
        print("=" * 80)

        # Top 10 by total P&L
        print("\n📊 TOP 10 BY TOTAL P&L")
        print("-" * 80)
        top_pnl = df.nlargest(10, "total_pnl")
        for idx, row in top_pnl.iterrows():
            print(
                f"Stop Loss: {row['stop_loss_pct']:.1f}%, "
                f"Take Profit: {row['take_profit_pct']:.1f}%, "
                f"Min Move: {row['min_price_change_pct']:.1f}%"
            )
            print(
                f"  → Total P&L: ${row['total_pnl']:,.0f}, "
                f"Win Rate: {row['win_rate']*100:.1f}%, "
                f"Sharpe: {row['sharpe_ratio']:.2f}, "
                f"Trades: {row['total_trades']}\n"
            )

        # Top 10 by Sharpe ratio
        print("\n📈 TOP 10 BY SHARPE RATIO")
        print("-" * 80)
        top_sharpe = df.nlargest(10, "sharpe_ratio")
        for idx, row in top_sharpe.iterrows():
            print(
                f"Stop Loss: {row['stop_loss_pct']:.1f}%, "
                f"Take Profit: {row['take_profit_pct']:.1f}%, "
                f"Min Move: {row['min_price_change_pct']:.1f}%"
            )
            print(
                f"  → Sharpe: {row['sharpe_ratio']:.2f}, "
                f"Total P&L: ${row['total_pnl']:,.0f}, "
                f"Win Rate: {row['win_rate']*100:.1f}%, "
                f"Trades: {row['total_trades']}\n"
            )

        # Top 10 by win rate
        print("\n🎯 TOP 10 BY WIN RATE")
        print("-" * 80)
        top_winrate = df.nlargest(10, "win_rate")
        for idx, row in top_winrate.iterrows():
            print(
                f"Stop Loss: {row['stop_loss_pct']:.1f}%, "
                f"Take Profit: {row['take_profit_pct']:.1f}%, "
                f"Min Move: {row['min_price_change_pct']:.1f}%"
            )
            print(
                f"  → Win Rate: {row['win_rate']*100:.1f}%, "
                f"Total P&L: ${row['total_pnl']:,.0f}, "
                f"Sharpe: {row['sharpe_ratio']:.2f}, "
                f"Trades: {row['total_trades']}\n"
            )

        # Overall statistics
        print("\n📊 OVERALL STATISTICS")
        print("-" * 80)
        print(f"Total Combinations Tested: {len(df)}")
        print(f"Profitable Combinations:   {len(df[df['total_pnl'] > 0])} ({len(df[df['total_pnl'] > 0])/len(df)*100:.1f}%)")
        print(f"Average Total P&L:         ${df['total_pnl'].mean():,.0f}")
        print(f"Best Total P&L:            ${df['total_pnl'].max():,.0f}")
        print(f"Worst Total P&L:           ${df['total_pnl'].min():,.0f}")
        print(f"Average Win Rate:          {df['win_rate'].mean()*100:.1f}%")
        print(f"Average Sharpe Ratio:      {df['sharpe_ratio'].mean():.2f}")

        # Parameter correlations
        print("\n🔗 PARAMETER CORRELATIONS WITH TOTAL P&L")
        print("-" * 80)
        param_cols = [
            "stop_loss_pct",
            "take_profit_pct",
            "min_price_change_pct",
            "min_volume_ratio",
        ]
        for param in param_cols:
            if param in df.columns:
                corr = df[param].corr(df["total_pnl"])
                print(f"{param:30s}: {corr:+.3f}")

        print("\n" + "=" * 80 + "\n")

        return df

    def save_results(self, filename: str):
        """Save results to CSV."""
        if not self.results:
            print("No results to save")
            return

        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False)
        print(f"✓ Results saved to: {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimize momentum trading strategy parameters"
    )
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,GOOGL",
        help="Comma-separated list of symbols",
    )
    parser.add_argument(
        "--start",
        default="2021-06-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default="2022-06-30",
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick optimization with fewer combinations",
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    # Define parameter grid
    if args.quick:
        param_grid = {
            "stop_loss_pct": [1.5, 2.0, 2.5],
            "take_profit_pct": [3.0, 4.0, 5.0],
            "min_price_change_pct": [2.0, 2.5],
            "min_volume_ratio": [2.0],
        }
    else:
        param_grid = {
            "stop_loss_pct": [1.0, 1.5, 2.0, 2.5, 3.0],
            "take_profit_pct": [2.0, 3.0, 4.0, 5.0, 6.0],
            "min_price_change_pct": [1.5, 2.0, 2.5, 3.0],
            "min_volume_ratio": [1.5, 2.0, 2.5],
        }

    # Run optimization
    optimizer = ParameterOptimizer()
    results = optimizer.optimize(symbols, start_date, end_date, param_grid)

    # Analyze results
    df = optimizer.analyze_results()

    # Save results
    if df is not None:
        output_file = f"optimization_results_{start_date.date()}_{end_date.date()}.csv"
        optimizer.save_results(output_file)


if __name__ == "__main__":
    main()
