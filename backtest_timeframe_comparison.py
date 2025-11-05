#!/usr/bin/env python3
"""
Multi-Timeframe Strategy Comparison
Tests all 5 strategies across different timeframes:
1-minute, 2-minute, 5-minute, 15-minute, 1-hour, and daily bars
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.backtesting.performance import PerformanceMetrics
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from gambler_ai.analysis.smart_money_detector import SmartMoneyDetector


class TimeframeDataGenerator:
    """Generate realistic market data for different timeframes"""

    def __init__(self, base_price: float = 185.0, seed: int = 42):
        self.base_price = base_price
        self.seed = seed

    def generate_intraday_data(
        self,
        timeframe_minutes: int,
        num_days: int = 252,
        drift: float = 0.0005,
        volatility: float = 0.010
    ) -> pd.DataFrame:
        """
        Generate intraday bar data

        Args:
            timeframe_minutes: Bar duration (1, 2, 5, 15, 60, etc.)
            num_days: Number of trading days
            drift: Daily drift (return)
            volatility: Daily volatility

        Returns:
            DataFrame with OHLCV data
        """
        np.random.seed(self.seed)

        # Calculate number of bars
        minutes_per_day = 390  # 6.5 hour trading day
        bars_per_day = minutes_per_day // timeframe_minutes
        total_bars = num_days * bars_per_day

        # Adjust drift and volatility to timeframe
        # drift and vol are daily, so scale down to bar level
        bars_per_day_actual = 390 / timeframe_minutes
        bar_drift = drift / bars_per_day_actual
        bar_volatility = volatility / np.sqrt(bars_per_day_actual)

        # Generate returns with geometric Brownian motion
        returns = np.random.normal(bar_drift, bar_volatility, total_bars)

        # Add occasional volatility clusters and trends
        for i in range(0, total_bars, 100):
            cluster_length = np.random.randint(10, 30)
            if np.random.random() > 0.5:
                # Trending period
                returns[i:i+cluster_length] += np.random.uniform(0.0001, 0.0005)
            else:
                # Volatile period
                returns[i:i+cluster_length] *= np.random.uniform(1.5, 2.5)

        # Generate prices
        prices = self.base_price * np.exp(np.cumsum(returns))

        # Generate OHLCV
        data = []
        start_date = datetime(2024, 1, 2, 9, 30)

        for i in range(total_bars):
            price = prices[i]

            # Intraday range depends on timeframe
            range_pct = 0.001 * np.sqrt(timeframe_minutes / 5)  # Longer bars = wider range

            open_price = price * (1 + np.random.uniform(-range_pct/2, range_pct/2))
            high = price * (1 + np.random.uniform(range_pct/2, range_pct*2))
            low = price * (1 - np.random.uniform(range_pct/2, range_pct*2))
            close = price

            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Volume inversely proportional to timeframe
            base_volume = 50_000_000 // (timeframe_minutes // 5 + 1)
            volume_multiplier = np.random.lognormal(0, 0.5)

            # Higher volume on large moves
            if abs(returns[i]) > bar_volatility * 2:
                volume_multiplier *= np.random.uniform(2, 5)

            volume = int(base_volume * volume_multiplier)

            # Calculate timestamp
            bar_number = i % bars_per_day
            day_number = i // bars_per_day
            minutes_offset = bar_number * timeframe_minutes
            timestamp = start_date + timedelta(days=day_number, minutes=minutes_offset)

            # Skip weekends
            while timestamp.weekday() >= 5:
                timestamp += timedelta(days=1)

            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
            })

        df = pd.DataFrame(data)
        df['symbol'] = 'AAPL'

        return df

    def generate_daily_data(
        self,
        num_days: int = 252,
        drift: float = 0.0005,
        volatility: float = 0.010
    ) -> pd.DataFrame:
        """Generate daily bar data"""
        np.random.seed(self.seed)

        returns = np.random.normal(drift, volatility, num_days)
        prices = self.base_price * np.exp(np.cumsum(returns))

        data = []
        start_date = datetime(2024, 1, 2, 9, 30)

        for i in range(num_days):
            price = prices[i]

            # Daily OHLC with realistic intraday movement
            open_price = price * (1 + np.random.uniform(-0.005, 0.005))
            high = price * (1 + np.random.uniform(0.005, 0.020))
            low = price * (1 - np.random.uniform(0.005, 0.020))
            close = price

            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Daily volume
            base_volume = 50_000_000
            volume = int(base_volume * np.random.lognormal(0, 0.5))

            timestamp = start_date + timedelta(days=i)
            while timestamp.weekday() >= 5:
                timestamp += timedelta(days=1)

            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
            })

        df = pd.DataFrame(data)
        df['symbol'] = 'AAPL'

        return df


def run_timeframe_backtest(
    timeframe_name: str,
    timeframe_data: pd.DataFrame,
    initial_capital: float = 100000
) -> Dict[str, Dict]:
    """
    Run all strategies on a specific timeframe

    Returns:
        Dict of {strategy_name: metrics_dict}
    """
    strategies = {
        'Momentum': MomentumDetector(use_db=False),
        'Mean Reversion': MeanReversionDetector(),
        'Volatility Breakout': VolatilityBreakoutDetector(),
        'Multi-Timeframe': MultiTimeframeAnalyzer(),
        'Smart Money': SmartMoneyDetector(),
    }

    results = {}

    for strategy_name, detector in strategies.items():
        engine = BacktestEngine(
            initial_capital=initial_capital,
            risk_per_trade=0.01,
            max_concurrent_trades=3
        )

        trades = engine.run_backtest(timeframe_data, detector)

        metrics_calc = PerformanceMetrics(
            trades=trades,
            initial_capital=initial_capital,
            final_capital=engine.current_capital
        )

        metrics = metrics_calc.calculate_all_metrics()
        results[strategy_name] = metrics

    return results


def create_timeframe_comparison_table():
    """Create comprehensive comparison across all timeframes"""

    print(f"\n{'='*140}")
    print(f"MULTI-TIMEFRAME STRATEGY COMPARISON")
    print(f"Testing: 1-min, 2-min, 5-min, 15-min, 1-hour, and Daily bars")
    print(f"{'='*140}\n")

    # Define timeframes
    timeframes = [
        ('1-Minute', 1, 60),      # 1-min bars, 60 days
        ('2-Minute', 2, 60),      # 2-min bars, 60 days
        ('5-Minute', 5, 60),      # 5-min bars, 60 days
        ('15-Minute', 15, 120),   # 15-min bars, 120 days
        ('1-Hour', 60, 252),      # 1-hour bars, full year
        ('Daily', None, 252),     # Daily bars, full year
    ]

    generator = TimeframeDataGenerator()
    all_results = {}

    # Generate data and run backtests
    for tf_name, tf_minutes, num_days in timeframes:
        print(f"Running backtests on {tf_name} timeframe ({num_days} days)...")

        if tf_minutes is None:
            # Daily data
            df = generator.generate_daily_data(num_days=num_days)
        else:
            # Intraday data
            df = generator.generate_intraday_data(
                timeframe_minutes=tf_minutes,
                num_days=num_days
            )

        results = run_timeframe_backtest(tf_name, df)
        all_results[tf_name] = results

    # Create comparison tables by strategy
    strategies = ['Momentum', 'Mean Reversion', 'Volatility Breakout', 'Multi-Timeframe', 'Smart Money']

    for strategy in strategies:
        print(f"\n{'='*140}")
        print(f"STRATEGY: {strategy}")
        print(f"{'='*140}")

        print(f"\n{'Timeframe':<15} {'Return %':<12} {'Win Rate':<12} {'Trades':<10} "
              f"{'Profit Factor':<15} {'Sharpe':<10} {'Max DD %':<12} {'Score':<10}")
        print(f"{'-'*140}")

        best_timeframe = None
        best_score = 0

        for tf_name, _, _ in timeframes:
            metrics = all_results[tf_name][strategy]

            return_pct = metrics.get('total_return_pct', 0)
            win_rate = metrics.get('win_rate', 0)
            num_trades = metrics.get('total_trades', 0)
            profit_factor = metrics.get('profit_factor', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            max_dd = metrics.get('max_drawdown_pct', 0)
            score = metrics.get('performance_score', 0)

            if score > best_score:
                best_score = score
                best_timeframe = tf_name

            # Highlight best performing timeframe
            marker = "⭐" if score > 70 else "  "

            print(f"{marker} {tf_name:<13} {return_pct:+6.2f}% {' '*3} {win_rate:>6.1f}% {' '*3} "
                  f"{num_trades:>6} {' '*3} {profit_factor:>10.2f} {' '*3} {sharpe:>6.2f} {' '*3} "
                  f"{max_dd:>6.2f}% {' '*3} {score:>6.1f}")

        print(f"\n{'-'*140}")
        print(f"Best Timeframe: {best_timeframe} (Score: {best_score:.1f})")
        print(f"{'-'*140}")

    # Cross-timeframe winner summary
    print(f"\n\n{'='*140}")
    print(f"BEST STRATEGY BY TIMEFRAME")
    print(f"{'='*140}\n")

    print(f"{'Timeframe':<15} {'Winner':<25} {'Return':<12} {'Trades':<10} {'Score':<10}")
    print(f"{'-'*140}")

    for tf_name, _, _ in timeframes:
        tf_results = all_results[tf_name]

        # Find best strategy for this timeframe
        sorted_strategies = sorted(
            tf_results.items(),
            key=lambda x: x[1].get('performance_score', 0),
            reverse=True
        )

        winner = sorted_strategies[0]
        winner_metrics = winner[1]

        print(f"{tf_name:<15} {winner[0]:<25} {winner_metrics.get('total_return_pct', 0):+6.2f}% "
              f"{' '*3} {winner_metrics.get('total_trades', 0):>6} {' '*3} "
              f"{winner_metrics.get('performance_score', 0):>6.1f}")

    print(f"{'-'*140}\n")


def create_timeframe_heatmap():
    """Create a heatmap-style table showing which strategies work best on which timeframes"""

    print(f"\n{'='*140}")
    print(f"STRATEGY-TIMEFRAME PERFORMANCE HEATMAP")
    print(f"Color coding: 🟢 Excellent (70+) | 🟡 Good (50-70) | 🔴 Poor (<50)")
    print(f"{'='*140}\n")

    timeframes = [
        ('1-Min', 1, 60),
        ('2-Min', 2, 60),
        ('5-Min', 5, 60),
        ('15-Min', 15, 120),
        ('1-Hour', 60, 252),
        ('Daily', None, 252),
    ]

    strategies = ['Momentum', 'Mean Reversion', 'Volatility Breakout', 'Multi-Timeframe', 'Smart Money']

    generator = TimeframeDataGenerator()

    # Collect all data
    heatmap_data = {strategy: [] for strategy in strategies}

    for tf_name, tf_minutes, num_days in timeframes:
        print(f"Processing {tf_name}...", end=' ')

        if tf_minutes is None:
            df = generator.generate_daily_data(num_days=num_days)
        else:
            df = generator.generate_intraday_data(
                timeframe_minutes=tf_minutes,
                num_days=num_days
            )

        results = run_timeframe_backtest(tf_name, df)

        for strategy in strategies:
            score = results[strategy].get('performance_score', 0)
            heatmap_data[strategy].append((tf_name, score))

        print("✓")

    # Print heatmap
    print(f"\n{'Strategy':<25} ", end='')
    for tf_name, _, _ in timeframes:
        print(f"{tf_name:<12}", end='')
    print()
    print(f"{'-'*140}")

    for strategy in strategies:
        print(f"{strategy:<25} ", end='')

        for tf_name, score in heatmap_data[strategy]:
            if score >= 70:
                marker = "🟢"
            elif score >= 50:
                marker = "🟡"
            else:
                marker = "🔴"

            print(f"{marker} {score:>5.1f}    ", end='')

        print()

    print(f"{'-'*140}\n")

    # Summary insights
    print(f"KEY INSIGHTS:")
    print(f"{'-'*140}")

    for strategy in strategies:
        scores = [score for _, score in heatmap_data[strategy]]
        best_idx = np.argmax(scores)
        worst_idx = np.argmin(scores)

        best_tf = heatmap_data[strategy][best_idx][0]
        worst_tf = heatmap_data[strategy][worst_idx][0]
        avg_score = np.mean(scores)

        print(f"\n{strategy}:")
        print(f"  Best on: {best_tf} ({scores[best_idx]:.1f})")
        print(f"  Worst on: {worst_tf} ({scores[worst_idx]:.1f})")
        print(f"  Average Score: {avg_score:.1f}")

    print(f"\n{'='*140}\n")


if __name__ == '__main__':
    print("\n" + "="*140)
    print("GAMBLERAI - MULTI-TIMEFRAME STRATEGY COMPARISON SYSTEM")
    print("="*140)

    # Run comprehensive timeframe comparison
    create_timeframe_comparison_table()

    # Create performance heatmap
    create_timeframe_heatmap()

    print("\n✅ Timeframe comparison analysis complete!\n")
