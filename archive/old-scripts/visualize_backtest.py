#!/usr/bin/env python3
"""
Visualization script for backtest results.

Creates charts and analysis visualizations including:
- Equity curve
- Drawdown chart
- Win/Loss distribution
- Performance by symbol
- Trade duration analysis
- Exit reason breakdown
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path


class BacktestVisualizer:
    """Visualize backtest results."""

    def __init__(self, trades_file: str):
        """
        Initialize visualizer with trades CSV file.

        Args:
            trades_file: Path to CSV file with trade results
        """
        self.df = pd.read_csv(trades_file)
        self.df["entry_time"] = pd.to_datetime(self.df["entry_time"])
        self.df["exit_time"] = pd.to_datetime(self.df["exit_time"])
        self.df = self.df.sort_values("entry_time")

        print(f"✓ Loaded {len(self.df)} trades from {trades_file}")

    def create_equity_curve(self, output_file: str = "equity_curve.png"):
        """Create equity curve chart."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

        # Calculate cumulative P&L
        self.df["cumulative_pnl"] = self.df["pnl_dollars"].cumsum()

        # Plot equity curve
        ax1.plot(
            self.df["exit_time"],
            self.df["cumulative_pnl"],
            linewidth=2,
            color="#2E86AB",
            label="Equity Curve",
        )
        ax1.axhline(y=0, color="black", linestyle="--", alpha=0.3)
        ax1.fill_between(
            self.df["exit_time"],
            0,
            self.df["cumulative_pnl"],
            where=self.df["cumulative_pnl"] >= 0,
            color="#06D6A0",
            alpha=0.3,
        )
        ax1.fill_between(
            self.df["exit_time"],
            0,
            self.df["cumulative_pnl"],
            where=self.df["cumulative_pnl"] < 0,
            color="#EF476F",
            alpha=0.3,
        )

        ax1.set_ylabel("Cumulative P&L ($)", fontsize=12, fontweight="bold")
        ax1.set_title(
            "Equity Curve - Cumulative Profit & Loss",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper left")

        # Format y-axis as currency
        ax1.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
        )

        # Calculate drawdown
        running_max = self.df["cumulative_pnl"].expanding().max()
        drawdown = self.df["cumulative_pnl"] - running_max

        # Plot drawdown
        ax2.fill_between(
            self.df["exit_time"],
            0,
            drawdown,
            color="#EF476F",
            alpha=0.5,
            label="Drawdown",
        )
        ax2.plot(self.df["exit_time"], drawdown, color="#EF476F", linewidth=1.5)

        ax2.set_ylabel("Drawdown ($)", fontsize=12, fontweight="bold")
        ax2.set_xlabel("Date", fontsize=12, fontweight="bold")
        ax2.set_title("Drawdown", fontsize=14, fontweight="bold", pad=20)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc="lower left")

        # Format y-axis as currency
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
        )

        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.xticks(rotation=45)

        # Add statistics text
        stats_text = (
            f"Total Trades: {len(self.df)}\n"
            f"Final P&L: ${self.df['cumulative_pnl'].iloc[-1]:,.0f}\n"
            f"Max Drawdown: ${drawdown.min():,.0f}\n"
            f"Win Rate: {(self.df['pnl_pct'] > 0).mean()*100:.1f}%"
        )
        ax1.text(
            0.02,
            0.98,
            stats_text,
            transform=ax1.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"✓ Saved equity curve to: {output_file}")
        plt.close()

    def create_win_loss_distribution(
        self, output_file: str = "win_loss_distribution.png"
    ):
        """Create win/loss distribution chart."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # 1. P&L Distribution (histogram)
        ax1.hist(
            self.df["pnl_dollars"],
            bins=30,
            color="#2E86AB",
            alpha=0.7,
            edgecolor="black",
        )
        ax1.axvline(x=0, color="red", linestyle="--", linewidth=2)
        ax1.axvline(
            x=self.df["pnl_dollars"].mean(),
            color="green",
            linestyle="--",
            linewidth=2,
            label=f'Mean: ${self.df["pnl_dollars"].mean():.2f}',
        )
        ax1.set_xlabel("P&L per Trade ($)", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Frequency", fontsize=11, fontweight="bold")
        ax1.set_title("P&L Distribution", fontsize=12, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 2. Win vs Loss breakdown
        wins = self.df[self.df["pnl_pct"] > 0]
        losses = self.df[self.df["pnl_pct"] <= 0]

        labels = ["Wins", "Losses"]
        sizes = [len(wins), len(losses)]
        colors = ["#06D6A0", "#EF476F"]
        explode = (0.05, 0.05)

        ax2.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            shadow=True,
            startangle=90,
            textprops={"fontsize": 11, "fontweight": "bold"},
        )
        ax2.set_title("Win vs Loss Breakdown", fontsize=12, fontweight="bold")

        # 3. Exit reason breakdown
        exit_counts = self.df["exit_reason"].value_counts()
        ax3.bar(
            exit_counts.index,
            exit_counts.values,
            color=["#06D6A0", "#EF476F", "#FFD166"],
            edgecolor="black",
            alpha=0.7,
        )
        ax3.set_xlabel("Exit Reason", fontsize=11, fontweight="bold")
        ax3.set_ylabel("Count", fontsize=11, fontweight="bold")
        ax3.set_title("Exit Reason Breakdown", fontsize=12, fontweight="bold")
        ax3.grid(True, alpha=0.3, axis="y")

        # 4. Trade duration distribution
        ax4.hist(
            self.df["duration_minutes"],
            bins=30,
            color="#FFD166",
            alpha=0.7,
            edgecolor="black",
        )
        ax4.axvline(
            x=self.df["duration_minutes"].mean(),
            color="red",
            linestyle="--",
            linewidth=2,
            label=f'Mean: {self.df["duration_minutes"].mean():.1f} min',
        )
        ax4.set_xlabel("Duration (minutes)", fontsize=11, fontweight="bold")
        ax4.set_ylabel("Frequency", fontsize=11, fontweight="bold")
        ax4.set_title("Trade Duration Distribution", fontsize=12, fontweight="bold")
        ax4.grid(True, alpha=0.3)
        ax4.legend()

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"✓ Saved win/loss distribution to: {output_file}")
        plt.close()

    def create_performance_by_symbol(
        self, output_file: str = "performance_by_symbol.png"
    ):
        """Create performance by symbol chart."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # Group by symbol
        symbol_stats = self.df.groupby("symbol").agg(
            {
                "pnl_dollars": ["sum", "mean", "count"],
                "pnl_pct": lambda x: (x > 0).mean(),
            }
        )
        symbol_stats.columns = ["total_pnl", "avg_pnl", "trade_count", "win_rate"]
        symbol_stats = symbol_stats.sort_values("total_pnl", ascending=False)

        symbols = symbol_stats.index

        # 1. Total P&L by symbol
        colors = ["#06D6A0" if x >= 0 else "#EF476F" for x in symbol_stats["total_pnl"]]
        ax1.bar(
            symbols,
            symbol_stats["total_pnl"],
            color=colors,
            edgecolor="black",
            alpha=0.7,
        )
        ax1.set_ylabel("Total P&L ($)", fontsize=11, fontweight="bold")
        ax1.set_title("Total P&L by Symbol", fontsize=12, fontweight="bold")
        ax1.grid(True, alpha=0.3, axis="y")
        ax1.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
        )

        # 2. Win rate by symbol
        ax2.bar(
            symbols,
            symbol_stats["win_rate"] * 100,
            color="#2E86AB",
            edgecolor="black",
            alpha=0.7,
        )
        ax2.axhline(y=50, color="red", linestyle="--", linewidth=2, alpha=0.5)
        ax2.set_ylabel("Win Rate (%)", fontsize=11, fontweight="bold")
        ax2.set_title("Win Rate by Symbol", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3, axis="y")

        # 3. Trade count by symbol
        ax3.bar(
            symbols,
            symbol_stats["trade_count"],
            color="#FFD166",
            edgecolor="black",
            alpha=0.7,
        )
        ax3.set_ylabel("Number of Trades", fontsize=11, fontweight="bold")
        ax3.set_title("Trade Count by Symbol", fontsize=12, fontweight="bold")
        ax3.grid(True, alpha=0.3, axis="y")

        # 4. Average P&L by symbol
        colors = ["#06D6A0" if x >= 0 else "#EF476F" for x in symbol_stats["avg_pnl"]]
        ax4.bar(
            symbols,
            symbol_stats["avg_pnl"],
            color=colors,
            edgecolor="black",
            alpha=0.7,
        )
        ax4.set_ylabel("Avg P&L per Trade ($)", fontsize=11, fontweight="bold")
        ax4.set_title("Average P&L by Symbol", fontsize=12, fontweight="bold")
        ax4.grid(True, alpha=0.3, axis="y")
        ax4.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"✓ Saved performance by symbol to: {output_file}")
        plt.close()

    def create_all_charts(self, output_dir: str = "."):
        """Create all charts."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print("\nGenerating visualizations...")
        self.create_equity_curve(str(output_path / "equity_curve.png"))
        self.create_win_loss_distribution(
            str(output_path / "win_loss_distribution.png")
        )
        self.create_performance_by_symbol(
            str(output_path / "performance_by_symbol.png")
        )
        print("\n✓ All visualizations complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize backtest results"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to trades CSV file",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for charts (default: current directory)",
    )

    args = parser.parse_args()

    # Create visualizer
    visualizer = BacktestVisualizer(args.file)

    # Generate all charts
    visualizer.create_all_charts(args.output_dir)


if __name__ == "__main__":
    main()
