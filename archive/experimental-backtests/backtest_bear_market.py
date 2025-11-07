#!/usr/bin/env python3
"""
Bear Market Backtesting (2022-Style Correction)

Tests all 5 strategies in a bear market environment to show how
SHORT strategies perform during market declines.

2022 Market: S&P 500 declined -18%, Tech -30%
Simulates: $185 → $110 (-40% decline over 12 months)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.backtesting.performance import PerformanceMetrics
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from gambler_ai.analysis.smart_money_detector import SmartMoneyDetector


def generate_bear_market_data(year: int, month: int, bars_per_day: int = 20) -> pd.DataFrame:
    """
    Generate realistic bear market data for a specific month.

    Simulates 2022-style bear market with:
    - Overall downtrend (-40% over year)
    - Higher volatility
    - Sharp selloffs followed by weak bounces
    - Distribution patterns

    Args:
        year: Year (e.g., 2022)
        month: Month (1-12)
        bars_per_day: Number of bars per trading day

    Returns:
        DataFrame with OHLCV data
    """
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    trading_days = int(days_in_month * 0.67)
    total_bars = trading_days * bars_per_day

    # Bear market regime characteristics by month
    bear_market_regimes = {
        1: {'drift': -0.0002, 'vol': 0.014, 'name': 'January Selloff'},
        2: {'drift': -0.0001, 'vol': 0.015, 'name': 'February Weakness'},
        3: {'drift': 0.0001, 'vol': 0.013, 'name': 'March Dead Cat Bounce'},
        4: {'drift': -0.0004, 'vol': 0.016, 'name': 'April Breakdown'},
        5: {'drift': -0.0005, 'vol': 0.018, 'name': 'May Capitulation'},
        6: {'drift': -0.0006, 'vol': 0.020, 'name': 'June Panic'},
        7: {'drift': 0.0002, 'vol': 0.017, 'name': 'July Relief Rally'},
        8: {'drift': 0.0003, 'vol': 0.014, 'name': 'August Bounce'},
        9: {'drift': -0.0005, 'vol': 0.019, 'name': 'September Flush'},
        10: {'drift': -0.0004, 'vol': 0.021, 'name': 'October Crash'},
        11: {'drift': 0.0001, 'vol': 0.016, 'name': 'November Stabilization'},
        12: {'drift': 0.0000, 'vol': 0.015, 'name': 'December Chop'},
    }

    regime = bear_market_regimes.get(month, {'drift': -0.0003, 'vol': 0.015, 'name': 'Default'})

    # Starting price progresses downward through year
    # Month 1: $185, Month 12: $110 (-40% total)
    base_price = 185.0 - (month - 1) * 6.25  # ~$6.25 drop per month

    # Generate price series with geometric Brownian motion (bearish drift)
    np.random.seed(42 + month + 1000)  # Different seed from bull market
    returns = np.random.normal(regime['drift'], regime['vol'], total_bars)

    # Add bear market characteristics
    # 1. Occasional panic selloffs (gap downs)
    panic_selloffs = np.random.randint(0, total_bars, size=int(total_bars * 0.05))
    for idx in panic_selloffs:
        if idx < len(returns):
            returns[idx] -= np.random.uniform(0.02, 0.04)  # -2% to -4% drops

    # 2. Weak bounce attempts that fail
    for i in range(0, total_bars - 50, 50):
        # Small rally that gets sold
        rally_length = np.random.randint(5, 15)
        for j in range(rally_length):
            if i + j < len(returns):
                returns[i + j] += 0.0005  # Small positive drift
        # Then back to selling
        for j in range(rally_length, rally_length + 10):
            if i + j < len(returns):
                returns[i + j] -= 0.001  # Resume selling

    prices = base_price * np.exp(np.cumsum(returns))

    # Generate OHLC
    data = []
    start_date = datetime(year, month, 1, 9, 30)

    for i in range(total_bars):
        price = prices[i]

        # Bear market OHLC characteristics
        # More downside range than upside
        high_pct = np.random.uniform(0.001, 0.004)  # Smaller highs
        low_pct = np.random.uniform(0.003, 0.010)   # Larger lows

        open_price = price * (1 + np.random.uniform(-0.002, 0.002))
        high = price * (1 + high_pct)
        low = price * (1 - low_pct)
        close = price

        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Volume characteristics
        base_volume = 50_000_000

        # Higher volume on down moves (panic)
        if returns[i] < -0.01:
            volume_multiplier = np.random.uniform(3, 6)  # Panic volume
        elif returns[i] > 0.01:
            volume_multiplier = np.random.uniform(0.5, 1.5)  # Low volume rallies
        else:
            volume_multiplier = np.random.lognormal(0, 0.5)

        volume = int(base_volume * volume_multiplier)

        # Timestamp
        minutes_offset = (i % bars_per_day) * (390 // bars_per_day)
        days_offset = i // bars_per_day
        timestamp = start_date + timedelta(days=days_offset, minutes=minutes_offset)

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


def run_bear_market_backtest(
    year: int,
    month: int,
    initial_capital: float = 100000
) -> Dict[str, Dict]:
    """
    Run all strategies for a specific bear market month.

    Returns:
        Dict of {strategy_name: metrics_dict}
    """
    df = generate_bear_market_data(year, month)

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

        trades = engine.run_backtest(df, detector)

        metrics_calc = PerformanceMetrics(
            trades=trades,
            initial_capital=initial_capital,
            final_capital=engine.current_capital
        )

        metrics = metrics_calc.calculate_all_metrics()

        # Add trade direction analysis
        long_trades = sum(1 for t in trades if t.direction.name == 'LONG')
        short_trades = sum(1 for t in trades if t.direction.name == 'SHORT')

        metrics['long_trades'] = long_trades
        metrics['short_trades'] = short_trades

        results[strategy_name] = metrics

    return results


def create_bear_market_comparison():
    """Create comprehensive bear market comparison."""
    print(f"\n{'='*120}")
    print(f"BEAR MARKET STRATEGY COMPARISON - 2022-Style Correction")
    print(f"Market Scenario: $185 → $110 (-40% decline)")
    print(f"Starting Capital: $100,000")
    print(f"{'='*120}\n")

    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Run all months
    all_results = {}

    for month in range(1, 13):
        print(f"Running simulations for {month_names[month-1]} 2022...")
        results = run_bear_market_backtest(2022, month, initial_capital=100000)
        all_results[month_names[month-1]] = results

    # Create summary table by strategy
    strategies = ['Momentum', 'Mean Reversion', 'Volatility Breakout', 'Multi-Timeframe', 'Smart Money']

    for strategy in strategies:
        print(f"\n{'='*120}")
        print(f"STRATEGY: {strategy}")
        print(f"{'='*120}")

        print(f"\n{'Month':<12} {'Return %':<12} {'Win Rate':<12} {'Trades':<10} "
              f"{'LONG':<8} {'SHORT':<8} {'Sharpe':<10} {'Score':<10}")
        print(f"{'-'*120}")

        monthly_returns = []
        total_trades = 0
        total_long = 0
        total_short = 0

        for month_name in month_names:
            metrics = all_results[month_name][strategy]

            return_pct = metrics.get('total_return_pct', 0)
            win_rate = metrics.get('win_rate', 0)
            num_trades = metrics.get('total_trades', 0)
            long_trades = metrics.get('long_trades', 0)
            short_trades = metrics.get('short_trades', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            score = metrics.get('performance_score', 0)

            monthly_returns.append(return_pct)
            total_trades += num_trades
            total_long += long_trades
            total_short += short_trades

            # Color coding
            return_str = f"{return_pct:+.2f}%"
            if return_pct > 5:
                return_str = f"🟢 {return_str}"
            elif return_pct < -2:
                return_str = f"🔴 {return_str}"
            else:
                return_str = f"⚪ {return_str}"

            print(f"{month_name:<12} {return_str:<20} {win_rate:<12.1f} {num_trades:<10} "
                  f"{long_trades:<8} {short_trades:<8} {sharpe:<10.2f} {score:<10.1f}")

        # Calculate annual statistics
        cumulative_return = np.prod([1 + r/100 for r in monthly_returns]) - 1
        avg_monthly_return = np.mean(monthly_returns)
        std_monthly_return = np.std(monthly_returns)

        print(f"\n{'-'*120}")
        print(f"{'ANNUAL SUMMARY':<12} {cumulative_return*100:+.2f}% cumulative | "
              f"Avg: {avg_monthly_return:+.2f}% | Std: {std_monthly_return:.2f}% | "
              f"Trades: {total_trades} (L:{total_long} S:{total_short})")
        print(f"{'-'*120}")

        # Best and worst months
        best_month_idx = np.argmax(monthly_returns)
        worst_month_idx = np.argmin(monthly_returns)

        print(f"Best Month:  {month_names[best_month_idx]} ({monthly_returns[best_month_idx]:+.2f}%)")
        print(f"Worst Month: {month_names[worst_month_idx]} ({monthly_returns[worst_month_idx]:+.2f}%)")

        # Long/Short analysis
        if total_trades > 0:
            long_pct = (total_long / total_trades) * 100
            short_pct = (total_short / total_trades) * 100
            print(f"Trade Split: {long_pct:.1f}% LONG / {short_pct:.1f}% SHORT")

    # Dollar comparison
    print(f"\n\n{'='*120}")
    print(f"DOLLAR-BASED TRACKING - Starting with $10,000")
    print(f"{'='*120}\n")

    print(f"{'Month':<12} ", end='')
    for strategy in strategies:
        print(f"{strategy:<20}", end='')
    print()
    print(f"{'-'*120}")

    capital_tracker = {strategy: 10000 for strategy in strategies}

    for month_name in month_names:
        results = run_bear_market_backtest(2022, month_names.index(month_name) + 1, initial_capital=10000)

        print(f"{month_name:<12} ", end='')

        for strategy in strategies:
            metrics = results[strategy]
            return_pct = metrics.get('total_return_pct', 0)

            monthly_profit = capital_tracker[strategy] * (return_pct / 100)
            capital_tracker[strategy] += monthly_profit

            profit_str = f"${capital_tracker[strategy]:,.0f}"
            print(f"{profit_str:<20}", end='')

        print()

    # Final summary
    print(f"\n{'-'*120}")
    print(f"{'FINAL CAPITAL':<12} ", end='')
    for strategy in strategies:
        total_gain = capital_tracker[strategy] - 10000
        gain_pct = (total_gain / 10000) * 100
        final_str = f"${capital_tracker[strategy]:,.0f} ({gain_pct:+.1f}%)"
        print(f"{final_str:<20}", end='')
    print()
    print(f"{'-'*120}\n")

    # Market comparison
    print(f"\n{'='*120}")
    print(f"COMPARISON TO MARKET")
    print(f"{'='*120}")
    print(f"\nBuy & Hold: $10,000 → $6,000 (-40% market decline)")
    print(f"\nStrategy Performance vs Market:")
    print(f"{'-'*120}")

    for strategy in strategies:
        final_value = capital_tracker[strategy]
        vs_market = final_value - 6000

        if final_value > 10000:
            status = "🟢 ABSOLUTE GAIN"
        elif final_value > 6000:
            status = "🟡 BEAT MARKET"
        else:
            status = "🔴 WORSE THAN MARKET"

        print(f"{strategy:<25} ${final_value:>8,.0f}  |  {status}  |  vs Market: {vs_market:+,.0f}")

    print(f"{'-'*120}\n")


if __name__ == '__main__':
    print("\n" + "="*120)
    print("GAMBLERAI - BEAR MARKET ANALYSIS (2022-Style)")
    print("="*120)

    create_bear_market_comparison()

    print("\n✅ Bear market analysis complete!\n")
