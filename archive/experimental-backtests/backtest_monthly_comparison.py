#!/usr/bin/env python3
"""
Month-by-Month Strategy Comparison
Runs all 5 strategies for each month of 2024 and compares performance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
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


def generate_monthly_data(year: int, month: int, bars_per_day: int = 20) -> pd.DataFrame:
    """
    Generate realistic intraday data for a specific month

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        bars_per_day: Number of bars per trading day

    Returns:
        DataFrame with OHLCV data
    """
    # Calculate trading days in month (approx 20-23 days)
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    trading_days = int(days_in_month * 0.67)  # ~67% are trading days

    total_bars = trading_days * bars_per_day

    # Month-specific market regimes
    month_regimes = {
        1: {'drift': 0.0002, 'vol': 0.012, 'name': 'January Rally'},
        2: {'drift': 0.0001, 'vol': 0.011, 'name': 'February Consolidation'},
        3: {'drift': -0.0001, 'vol': 0.013, 'name': 'March Volatility'},
        4: {'drift': 0.0003, 'vol': 0.010, 'name': 'April Bounce'},
        5: {'drift': 0.0005, 'vol': 0.009, 'name': 'May Rally'},
        6: {'drift': 0.0007, 'vol': 0.008, 'name': 'June Momentum'},
        7: {'drift': 0.0004, 'vol': 0.010, 'name': 'July Pause'},
        8: {'drift': -0.0002, 'vol': 0.014, 'name': 'August Correction'},
        9: {'drift': -0.0003, 'vol': 0.015, 'name': 'September Weakness'},
        10: {'drift': 0.0006, 'vol': 0.011, 'name': 'October Recovery'},
        11: {'drift': 0.0009, 'vol': 0.009, 'name': 'November Rally'},
        12: {'drift': 0.0010, 'vol': 0.008, 'name': 'December Strength'},
    }

    regime = month_regimes.get(month, {'drift': 0.0003, 'vol': 0.010, 'name': 'Default'})

    # Starting price based on year progression
    base_price = 185.0 + (month - 1) * 35.0  # Gradual increase through year

    # Generate price series with geometric Brownian motion
    np.random.seed(42 + month)
    returns = np.random.normal(regime['drift'], regime['vol'], total_bars)
    prices = base_price * np.exp(np.cumsum(returns))

    # Generate OHLC
    data = []
    start_date = datetime(year, month, 1, 9, 30)

    for i in range(total_bars):
        price = prices[i]

        # Intraday volatility
        high_pct = np.random.uniform(0.002, 0.008)
        low_pct = np.random.uniform(0.002, 0.008)

        open_price = price * (1 + np.random.uniform(-0.003, 0.003))
        high = price * (1 + high_pct)
        low = price * (1 - low_pct)
        close = price

        # Volume with realistic patterns
        base_volume = 50_000_000
        volume_multiplier = np.random.lognormal(0, 0.5)

        # Higher volume on breakouts
        if abs(returns[i]) > regime['vol'] * 2:
            volume_multiplier *= np.random.uniform(2, 4)

        volume = int(base_volume * volume_multiplier)

        # Timestamp - 5-minute bars during trading hours
        minutes_offset = (i % bars_per_day) * (390 // bars_per_day)  # 390 min trading day
        days_offset = i // bars_per_day
        timestamp = start_date + timedelta(days=days_offset, minutes=minutes_offset)

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


def run_monthly_backtest(
    year: int,
    month: int,
    initial_capital: float = 100000
) -> Dict[str, Dict]:
    """
    Run all strategies for a specific month

    Returns:
        Dict of {strategy_name: metrics_dict}
    """
    # Generate data for the month
    df = generate_monthly_data(year, month)

    # Initialize strategies (use_db=False for backtesting)
    strategies = {
        'Momentum': MomentumDetector(use_db=False),
        'Mean Reversion': MeanReversionDetector(),
        'Volatility Breakout': VolatilityBreakoutDetector(),
        'Multi-Timeframe': MultiTimeframeAnalyzer(),
        'Smart Money': SmartMoneyDetector(),
    }

    results = {}

    for strategy_name, detector in strategies.items():
        # Run backtest
        engine = BacktestEngine(
            initial_capital=initial_capital,
            risk_per_trade=0.01,
            max_concurrent_trades=3
        )

        trades = engine.run_backtest(df, detector)

        # Calculate metrics
        metrics_calc = PerformanceMetrics(
            trades=trades,
            initial_capital=initial_capital,
            final_capital=engine.current_capital
        )

        metrics = metrics_calc.calculate_all_metrics()
        results[strategy_name] = metrics

    return results


def create_monthly_comparison_table(year: int, initial_capital: float = 100000):
    """
    Create comprehensive monthly comparison for all strategies
    """
    print(f"\n{'='*120}")
    print(f"MONTHLY STRATEGY COMPARISON - {year}")
    print(f"Starting Capital: ${initial_capital:,.0f}")
    print(f"{'='*120}\n")

    # Store all monthly results
    all_results = {}

    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    for month in range(1, 13):
        print(f"Running simulations for {month_names[month-1]} {year}...")
        results = run_monthly_backtest(year, month, initial_capital)
        all_results[month_names[month-1]] = results

    # Create summary table by strategy
    strategies = ['Momentum', 'Mean Reversion', 'Volatility Breakout', 'Multi-Timeframe', 'Smart Money']

    for strategy in strategies:
        print(f"\n{'='*120}")
        print(f"STRATEGY: {strategy}")
        print(f"{'='*120}")

        # Table header
        print(f"\n{'Month':<12} {'Return %':<12} {'Win Rate':<12} {'Trades':<10} "
              f"{'Profit Factor':<15} {'Sharpe':<10} {'Score':<10}")
        print(f"{'-'*120}")

        total_return = 0
        total_trades = 0
        monthly_returns = []

        for month_name in month_names:
            metrics = all_results[month_name][strategy]

            return_pct = metrics.get('total_return_pct', 0)
            win_rate = metrics.get('win_rate', 0)
            num_trades = metrics.get('total_trades', 0)
            profit_factor = metrics.get('profit_factor', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            score = metrics.get('performance_score', 0)

            monthly_returns.append(return_pct)
            total_trades += num_trades

            # Color coding for returns
            return_str = f"{return_pct:+.2f}%"
            if return_pct > 5:
                return_str = f"🟢 {return_str}"
            elif return_pct < -2:
                return_str = f"🔴 {return_str}"
            else:
                return_str = f"⚪ {return_str}"

            print(f"{month_name:<12} {return_str:<20} {win_rate:<12.1f} {num_trades:<10} "
                  f"{profit_factor:<15.2f} {sharpe:<10.2f} {score:<10.1f}")

        # Calculate annual statistics
        cumulative_return = np.prod([1 + r/100 for r in monthly_returns]) - 1
        avg_monthly_return = np.mean(monthly_returns)
        std_monthly_return = np.std(monthly_returns)

        print(f"\n{'-'*120}")
        print(f"{'ANNUAL SUMMARY':<12} {cumulative_return*100:+.2f}% cumulative | "
              f"Avg: {avg_monthly_return:+.2f}% | Std: {std_monthly_return:.2f}% | "
              f"Total Trades: {total_trades}")
        print(f"{'-'*120}")

        # Best and worst months
        best_month_idx = np.argmax(monthly_returns)
        worst_month_idx = np.argmin(monthly_returns)

        print(f"Best Month:  {month_names[best_month_idx]} ({monthly_returns[best_month_idx]:+.2f}%)")
        print(f"Worst Month: {month_names[worst_month_idx]} ({monthly_returns[worst_month_idx]:+.2f}%)")

    # Cross-strategy monthly comparison
    print(f"\n\n{'='*120}")
    print(f"BEST STRATEGY BY MONTH")
    print(f"{'='*120}\n")

    print(f"{'Month':<12} {'Winner':<25} {'Return':<15} {'Runner-Up':<25} {'Return':<15}")
    print(f"{'-'*120}")

    for month_name in month_names:
        month_results = all_results[month_name]

        # Sort strategies by return for this month
        sorted_strategies = sorted(
            month_results.items(),
            key=lambda x: x[1].get('total_return_pct', 0),
            reverse=True
        )

        winner = sorted_strategies[0]
        runner_up = sorted_strategies[1] if len(sorted_strategies) > 1 else ('N/A', {'total_return_pct': 0})

        print(f"{month_name:<12} {winner[0]:<25} {winner[1].get('total_return_pct', 0):+.2f}% "
              f"{' '*8} {runner_up[0]:<25} {runner_up[1].get('total_return_pct', 0):+.2f}%")

    print(f"\n{'='*120}\n")


def create_dollar_comparison_table(year: int, initial_capital: float = 10000):
    """
    Create dollar-based monthly comparison starting with $10,000
    """
    print(f"\n{'='*120}")
    print(f"MONTHLY PROFIT/LOSS COMPARISON - Starting with ${initial_capital:,.0f}")
    print(f"{'='*120}\n")

    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    strategies = ['Momentum', 'Mean Reversion', 'Volatility Breakout', 'Multi-Timeframe', 'Smart Money']

    # Run all months
    all_results = {}
    for month in range(1, 13):
        results = run_monthly_backtest(year, month, initial_capital)
        all_results[month_names[month-1]] = results

    # Table for each strategy showing running balance
    print(f"{'Month':<12} ", end='')
    for strategy in strategies:
        print(f"{strategy:<20}", end='')
    print()
    print(f"{'-'*120}")

    # Track cumulative capital for each strategy
    capital_tracker = {strategy: initial_capital for strategy in strategies}

    for month_name in month_names:
        print(f"{month_name:<12} ", end='')

        for strategy in strategies:
            metrics = all_results[month_name][strategy]
            return_pct = metrics.get('total_return_pct', 0)

            # Calculate new capital
            monthly_profit = capital_tracker[strategy] * (return_pct / 100)
            capital_tracker[strategy] += monthly_profit

            # Format output
            profit_str = f"${capital_tracker[strategy]:,.0f} ({monthly_profit:+,.0f})"
            print(f"{profit_str:<20}", end='')

        print()

    # Final summary
    print(f"\n{'-'*120}")
    print(f"{'FINAL CAPITAL':<12} ", end='')
    for strategy in strategies:
        total_gain = capital_tracker[strategy] - initial_capital
        gain_pct = (total_gain / initial_capital) * 100
        print(f"${capital_tracker[strategy]:,.0f} ({gain_pct:+.1f}%)"[:20].ljust(20), end='')
    print()
    print(f"{'-'*120}\n")


if __name__ == '__main__':
    print("\n" + "="*120)
    print("GAMBLERAI - MONTHLY STRATEGY COMPARISON SYSTEM")
    print("="*120)

    # Run with $100k capital for percentage comparisons
    create_monthly_comparison_table(2024, initial_capital=100000)

    # Run with $10k capital for dollar tracking
    create_dollar_comparison_table(2024, initial_capital=10000)

    print("\n✅ Monthly comparison analysis complete!\n")
