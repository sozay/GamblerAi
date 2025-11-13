#!/usr/bin/env python3
"""
Optimize Profit Targets for Volatility Breakout Strategy

Usage:
    python scripts/optimize_volatility_breakout.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA
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

sys.path.insert(0, str(Path(__file__).parent.parent))

from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector


class VolatilityBreakoutOptimizer:
    """Optimize profit target for volatility breakout strategy."""

    def __init__(self, symbols: List[str], lookback_days: int = 90):
        self.symbols = symbols
        self.lookback_days = lookback_days
        self.profit_targets_to_test = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]
        self.stop_loss_pct = 1.5  # Wider stop for breakouts

    def download_data(self):
        """Download historical data using yfinance."""
        print(f"\n📊 Downloading {self.lookback_days} days of data for {len(self.symbols)} symbols...")

        self.data = {}
        for symbol in self.symbols:
            print(f"  Downloading {symbol}...", end=" ")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period='60d', interval='5m')

                if df is not None and len(df) > 0:
                    df = df.rename(columns={
                        'Open': 'open', 'High': 'high', 'Low': 'low',
                        'Close': 'close', 'Volume': 'volume'
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
        """Backtest strategy with specific profit target."""

        detector = VolatilityBreakoutDetector(
            atr_period=14,
            atr_compression_ratio=0.5,
            consolidation_min_bars=20,
            breakout_threshold_pct=0.5,
            volume_multiplier=2.0,
        )

        all_trades = []

        for symbol, df in self.data.items():
            if len(df) < 100:
                continue

            setups = detector.detect_setups(df)
            if not setups:
                continue

            for setup in setups:
                entry_price = setup['entry_price']
                direction = setup['direction']

                # Calculate targets based on profit_target_pct
                if direction == 'LONG':
                    target = entry_price * (1 + profit_target_pct / 100)
                    stop = entry_price * (1 - self.stop_loss_pct / 100)
                else:
                    target = entry_price * (1 - profit_target_pct / 100)
                    stop = entry_price * (1 + self.stop_loss_pct / 100)

                # Find entry bar (approximate)
                entry_bars = df[df['close'].between(entry_price * 0.999, entry_price * 1.001)]
                if len(entry_bars) == 0:
                    continue

                entry_idx = entry_bars.index[0]
                future_data = df.iloc[entry_idx:entry_idx+100]

                if len(future_data) < 2:
                    continue

                # Simulate trade
                exit_price = None
                exit_reason = None
                bars_held = 0

                for idx, row in future_data.iloc[1:].iterrows():
                    bars_held += 1

                    if direction == 'LONG':
                        if row['low'] <= stop:
                            exit_price = stop
                            exit_reason = 'stop_loss'
                            break
                        if row['high'] >= target:
                            exit_price = target
                            exit_reason = 'take_profit'
                            break
                    else:  # SHORT
                        if row['high'] >= stop:
                            exit_price = stop
                            exit_reason = 'stop_loss'
                            break
                        if row['low'] <= target:
                            exit_price = target
                            exit_reason = 'take_profit'
                            break

                    if bars_held >= 18:  # 90 minutes / 5min bars
                        exit_price = row['close']
                        exit_reason = 'time_stop'
                        break

                if exit_price is None:
                    exit_price = future_data.iloc[-1]['close']
                    exit_reason = 'end_of_data'

                # Calculate P&L
                if direction == 'LONG':
                    pnl = exit_price - entry_price
                else:
                    pnl = entry_price - exit_price

                pnl_pct = (pnl / entry_price) * 100

                all_trades.append({
                    'symbol': symbol,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'won': pnl > 0
                })

        if not all_trades:
            return {
                'profit_target': profit_target_pct,
                'stop_loss': self.stop_loss_pct,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_pnl_pct': 0,
                'risk_reward': 0,
                'expectancy': 0,
            }

        trades_df = pd.DataFrame(all_trades)
        winning = trades_df[trades_df['won'] == True]
        losing = trades_df[trades_df['won'] == False]

        win_rate = len(winning) / len(trades_df) * 100
        avg_win = winning['pnl_pct'].mean() if len(winning) > 0 else 0
        avg_loss = losing['pnl_pct'].mean() if len(losing) > 0 else 0
        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0

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
        print("PROFIT TARGET OPTIMIZATION - VOLATILITY BREAKOUT STRATEGY")
        print("=" * 80)
        print(f"Symbols: {', '.join(self.symbols)}")
        print(f"Lookback: {self.lookback_days} days")
        print(f"Stop Loss: {self.stop_loss_pct}% (fixed)")
        print(f"Testing profit targets: {self.profit_targets_to_test}")
        print("=" * 80)

        self.download_data()

        if not self.data:
            print("✗ No data available. Exiting.")
            return

        results = []
        print("\n🔬 Testing profit targets...\n")

        for profit_target in self.profit_targets_to_test:
            print(f"Testing {profit_target}% profit target...", end=" ")
            result = self.backtest_profit_target(profit_target)
            results.append(result)
            print(f"✓ {result['total_trades']} trades, Win Rate: {result['win_rate']:.1f}%")

        self.display_results(results)

    def display_results(self, results: List[Dict]):
        """Display optimization results."""
        print("\n" + "=" * 80)
        print("OPTIMIZATION RESULTS - VOLATILITY BREAKOUT")
        print("=" * 80 + "\n")

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

        headers = ["Target", "Stop", "R:R", "Trades", "Win Rate", "Avg Win", "Avg Loss", "Total P&L", "Expectancy"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        if results and results[0]['total_trades'] > 0:
            best_expectancy = max(results, key=lambda x: x['expectancy'])
            print("\n" + "=" * 80)
            print("BEST CONFIGURATION")
            print("=" * 80)
            print(f"\n✅ BEST: {best_expectancy['profit_target']:.1f}% profit target")
            print(f"   Expectancy: {best_expectancy['expectancy']:.3f}%")
            print(f"   Win Rate: {best_expectancy['win_rate']:.1f}%")
            print(f"   Total P&L: {best_expectancy['total_pnl_pct']:.2f}%")
            print(f"   Risk/Reward: 1:{best_expectancy['risk_reward']:.2f}")
            print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Optimize Volatility Breakout Strategy")
    parser.add_argument("--symbols", type=str, default="AAPL,MSFT,GOOGL,TSLA,NVDA,AMD,META,NFLX",
                        help="Comma-separated stock symbols")
    parser.add_argument("--days", type=int, default=90, help="Days of historical data")

    args = parser.parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    optimizer = VolatilityBreakoutOptimizer(symbols=symbols, lookback_days=args.days)
    optimizer.run_optimization()


if __name__ == "__main__":
    main()
