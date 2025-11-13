#!/usr/bin/env python3
"""
Optimize Profit Targets for Mean Reversion Strategy

Tests different profit target percentages (1% to 10%) on last 3 months of data
to find the optimal risk/reward ratio.

Usage:
    python scripts/optimize_profit_targets.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import pandas as pd
import numpy as np
from tabulate import tabulate
import yfinance as yf

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector


class ProfitTargetOptimizer:
    """Optimize profit target percentage for mean reversion strategy."""

    def __init__(self, symbols: List[str], lookback_days: int = 90):
        """
        Initialize optimizer.

        Args:
            symbols: List of stock symbols to test
            lookback_days: Number of days of historical data (default 90 = 3 months)
        """
        self.symbols = symbols
        self.lookback_days = lookback_days

        # Test range: profit targets from 1% to 10%
        self.profit_targets_to_test = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]

        # Fixed stop loss at 1% for all tests
        self.stop_loss_pct = 1.0

    def download_data(self):
        """Download historical data for all symbols using yfinance."""
        print(f"\n📊 Downloading {self.lookback_days} days of data for {len(self.symbols)} symbols...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days + 30)  # Extra for indicators

        self.data = {}
        for symbol in self.symbols:
            print(f"  Downloading {symbol}...", end=" ")
            try:
                # Download 5-minute data (last 60 days available)
                ticker = yf.Ticker(symbol)
                df = ticker.history(period='60d', interval='5m')

                if df is not None and len(df) > 0:
                    # Rename columns to match expected format
                    df = df.rename(columns={
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    })
                    df.reset_index(inplace=True)
                    df = df.rename(columns={'Datetime': 'timestamp'})

                    self.data[symbol] = df
                    print(f"✓ {len(df)} bars")
                else:
                    print("✗ No data")
            except Exception as e:
                print(f"✗ Error: {e}")

        print(f"\n✓ Downloaded data for {len(self.data)} symbols\n")

    def backtest_profit_target(self, profit_target_pct: float) -> Dict:
        """
        Backtest strategy with specific profit target.

        Args:
            profit_target_pct: Profit target percentage to test

        Returns:
            Dict with performance metrics
        """
        # Initialize detector with this profit target
        detector = MeanReversionDetector(
            bb_period=20,
            bb_std=2.5,
            rsi_oversold=30,
            rsi_overbought=70,
            volume_multiplier=3.0,
            profit_target_pct=profit_target_pct,
            stop_loss_pct=self.stop_loss_pct,
        )

        all_trades = []

        # Test on each symbol
        for symbol, df in self.data.items():
            if len(df) < 100:
                continue

            # Detect setups
            setups = detector.detect_setups(df)

            if not setups:
                continue

            # Simulate trades
            for setup in setups:
                entry_price = setup['entry_price']
                target = setup['target']
                stop = setup['stop_loss']

                # Find what happens after entry
                entry_idx = df[df['close'] == entry_price].index
                if len(entry_idx) == 0:
                    continue

                entry_idx = entry_idx[0]

                # Look ahead up to 100 bars (or end of data)
                future_data = df.iloc[entry_idx:entry_idx+100]

                if len(future_data) < 2:
                    continue

                # Check if target or stop hit first
                exit_price = None
                exit_reason = None
                bars_held = 0

                for idx, row in future_data.iloc[1:].iterrows():
                    bars_held += 1

                    # Check stop loss hit
                    if row['low'] <= stop:
                        exit_price = stop
                        exit_reason = 'stop_loss'
                        break

                    # Check target hit
                    if row['high'] >= target:
                        exit_price = target
                        exit_reason = 'take_profit'
                        break

                    # Max holding 30 minutes (6 bars of 5min)
                    if bars_held >= 6:
                        exit_price = row['close']
                        exit_reason = 'time_stop'
                        break

                # If no exit, use last price
                if exit_price is None:
                    exit_price = future_data.iloc[-1]['close']
                    exit_reason = 'end_of_data'

                # Calculate P&L
                if setup['direction'] == 'LONG':
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price

                pnl_pct = (pnl / entry_price) * 100

                all_trades.append({
                    'symbol': symbol,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'bars_held': bars_held,
                    'won': pnl > 0
                })

        # Calculate metrics
        if not all_trades:
            return {
                'profit_target': profit_target_pct,
                'stop_loss': self.stop_loss_pct,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'risk_reward': 0,
                'expectancy': 0,
            }

        trades_df = pd.DataFrame(all_trades)

        winning_trades = trades_df[trades_df['won'] == True]
        losing_trades = trades_df[trades_df['won'] == False]

        win_rate = len(winning_trades) / len(trades_df) * 100
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0

        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Expectancy = (win_rate × avg_win) + (loss_rate × avg_loss)
        loss_rate = (100 - win_rate) / 100
        expectancy = (win_rate/100 * avg_win) + (loss_rate * avg_loss)

        return {
            'profit_target': profit_target_pct,
            'stop_loss': self.stop_loss_pct,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl_pct': trades_df['pnl_pct'].sum(),
            'risk_reward': risk_reward,
            'expectancy': expectancy,
        }

    def run_optimization(self):
        """Run optimization across all profit targets."""
        print("=" * 80)
        print("PROFIT TARGET OPTIMIZATION - MEAN REVERSION STRATEGY")
        print("=" * 80)
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Lookback: {self.lookback_days} days (~3 months)")
        print(f"Stop Loss: {self.stop_loss_pct}% (fixed)")
        print(f"Testing profit targets: {self.profit_targets_to_test}")
        print("=" * 80)

        # Download data
        self.download_data()

        if not self.data:
            print("✗ No data available. Exiting.")
            return

        # Test each profit target
        results = []

        print("\n🔬 Testing profit targets...\n")

        for profit_target in self.profit_targets_to_test:
            print(f"Testing {profit_target}% profit target...", end=" ")
            result = self.backtest_profit_target(profit_target)
            results.append(result)
            print(f"✓ {result['total_trades']} trades, Win Rate: {result['win_rate']:.1f}%")

        # Display results
        self.display_results(results)

    def display_results(self, results: List[Dict]):
        """Display optimization results in a table."""
        print("\n" + "=" * 80)
        print("OPTIMIZATION RESULTS")
        print("=" * 80 + "\n")

        # Prepare table data
        table_data = []
        for r in results:
            rr_ratio = f"1:{r['risk_reward']:.2f}" if r['risk_reward'] > 0 else "N/A"

            table_data.append([
                f"{r['profit_target']:.1f}%",
                f"{r['stop_loss']:.1f}%",
                rr_ratio,
                r['total_trades'],
                f"{r['win_rate']:.1f}%",
                f"{r['avg_win']:.2f}%",
                f"{r['avg_loss']:.2f}%",
                f"{r['total_pnl_pct']:.2f}%",
                f"{r['expectancy']:.3f}%"
            ])

        headers = [
            "Target", "Stop", "R:R", "Trades", "Win Rate",
            "Avg Win", "Avg Loss", "Total P&L", "Expectancy"
        ]

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Find best configurations
        print("\n" + "=" * 80)
        print("BEST CONFIGURATIONS")
        print("=" * 80 + "\n")

        # Best by expectancy
        best_expectancy = max(results, key=lambda x: x['expectancy'])
        print(f"✅ HIGHEST EXPECTANCY: {best_expectancy['profit_target']:.1f}% target")
        print(f"   Expectancy: {best_expectancy['expectancy']:.3f}%")
        print(f"   Win Rate: {best_expectancy['win_rate']:.1f}%")
        print(f"   Total P&L: {best_expectancy['total_pnl_pct']:.2f}%")
        print(f"   Risk/Reward: 1:{best_expectancy['risk_reward']:.2f}")

        # Best by total P&L
        best_pnl = max(results, key=lambda x: x['total_pnl_pct'])
        print(f"\n💰 HIGHEST TOTAL P&L: {best_pnl['profit_target']:.1f}% target")
        print(f"   Total P&L: {best_pnl['total_pnl_pct']:.2f}%")
        print(f"   Win Rate: {best_pnl['win_rate']:.1f}%")
        print(f"   Expectancy: {best_pnl['expectancy']:.3f}%")

        # Best win rate
        best_winrate = max(results, key=lambda x: x['win_rate'])
        print(f"\n🎯 HIGHEST WIN RATE: {best_winrate['profit_target']:.1f}% target")
        print(f"   Win Rate: {best_winrate['win_rate']:.1f}%")
        print(f"   Expectancy: {best_winrate['expectancy']:.3f}%")
        print(f"   Total P&L: {best_winrate['total_pnl_pct']:.2f}%")

        print("\n" + "=" * 80)
        print("\n💡 RECOMMENDATION:")
        print(f"   Use {best_expectancy['profit_target']:.1f}% profit target for best long-term results")
        print(f"   (Expectancy is the average expected return per trade)")
        print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Optimize Profit Target for Mean Reversion Strategy")
    parser.add_argument(
        "--symbols",
        type=str,
        default="AAPL,MSFT,GOOGL,TSLA,NVDA,AMD,META,NFLX",
        help="Comma-separated stock symbols to test"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of days of historical data (default: 90 = 3 months)"
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    optimizer = ProfitTargetOptimizer(symbols=symbols, lookback_days=args.days)
    optimizer.run_optimization()


if __name__ == "__main__":
    main()
