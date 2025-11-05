#!/usr/bin/env python3
"""
Adaptive Strategy Backtesting

Demonstrates the power of adaptive strategy selection by automatically
switching between strategies based on market regime.

Compares:
1. Static strategies (no switching)
2. Adaptive strategy (auto-switches based on regime)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.backtesting.performance import PerformanceMetrics
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer

# Import data generators
from backtest_monthly_comparison import generate_monthly_data
from backtest_bear_market import generate_bear_market_data


def run_adaptive_backtest(
    market_data: pd.DataFrame,
    initial_capital: float = 100000
) -> Dict:
    """
    Run backtest using adaptive strategy selection.

    The strategy automatically switches based on detected regime.
    """
    selector = AdaptiveStrategySelector()

    # Detect regime for full dataset first
    regime_detector = RegimeDetector()
    regime, confidence = regime_detector.detect_regime_with_confidence(market_data)

    print(f"  Detected regime: {regime} ({confidence:.1%} confidence)")

    # Select appropriate strategy
    strategy_name, strategy = selector.select_strategy(market_data)

    print(f"  Using strategy: {strategy_name}")

    # Run backtest with selected strategy
    engine = BacktestEngine(
        initial_capital=initial_capital,
        risk_per_trade=0.01,
        max_concurrent_trades=3
    )

    trades = engine.run_backtest(market_data, strategy)

    metrics_calc = PerformanceMetrics(
        trades=trades,
        initial_capital=initial_capital,
        final_capital=engine.current_capital
    )

    metrics = metrics_calc.calculate_all_metrics()
    metrics['regime'] = regime
    metrics['strategy_used'] = strategy_name

    return metrics


def compare_adaptive_vs_static():
    """
    Compare adaptive strategy vs static strategies across bull and bear markets.
    """
    print(f"\n{'='*120}")
    print(f"ADAPTIVE STRATEGY COMPARISON")
    print(f"{'='*120}\n")

    results = {
        'Bull Market 2024': {},
        'Bear Market 2022': {},
    }

    # Test 1: Bull Market (full year 2024)
    print("=" * 120)
    print("TEST 1: BULL MARKET 2024 (+252% rally)")
    print("=" * 120)

    bull_data_list = []
    for month in range(1, 13):
        df = generate_monthly_data(2024, month)
        bull_data_list.append(df)

    bull_data = pd.concat(bull_data_list, ignore_index=True)

    print(f"\nGenerated {len(bull_data)} bars of bull market data")
    print(f"Price range: ${bull_data['close'].iloc[0]:.2f} → ${bull_data['close'].iloc[-1]:.2f}\n")

    # Run static strategies
    static_strategies = {
        'Multi-Timeframe': MultiTimeframeAnalyzer(),
        'Mean Reversion': MeanReversionDetector(),
        'Momentum': MomentumDetector(use_db=False),
    }

    print("Running static strategies...")
    for name, strategy in static_strategies.items():
        print(f"\n  Testing {name}...")
        engine = BacktestEngine(initial_capital=100000, risk_per_trade=0.01, max_concurrent_trades=3)
        trades = engine.run_backtest(bull_data, strategy)
        metrics_calc = PerformanceMetrics(trades, 100000, engine.current_capital)
        metrics = metrics_calc.calculate_all_metrics()
        results['Bull Market 2024'][name] = metrics

    # Run adaptive strategy
    print(f"\n  Testing Adaptive Strategy...")
    adaptive_metrics = run_adaptive_backtest(bull_data, initial_capital=100000)
    results['Bull Market 2024']['Adaptive'] = adaptive_metrics

    # Test 2: Bear Market (full year 2022)
    print(f"\n{'='*120}")
    print("TEST 2: BEAR MARKET 2022 (-40% decline)")
    print("=" * 120)

    bear_data_list = []
    for month in range(1, 13):
        df = generate_bear_market_data(2022, month)
        bear_data_list.append(df)

    bear_data = pd.concat(bear_data_list, ignore_index=True)

    print(f"\nGenerated {len(bear_data)} bars of bear market data")
    print(f"Price range: ${bear_data['close'].iloc[0]:.2f} → ${bear_data['close'].iloc[-1]:.2f}\n")

    print("Running static strategies...")
    for name, strategy in static_strategies.items():
        print(f"\n  Testing {name}...")
        engine = BacktestEngine(initial_capital=100000, risk_per_trade=0.01, max_concurrent_trades=3)
        trades = engine.run_backtest(bear_data, strategy)
        metrics_calc = PerformanceMetrics(trades, 100000, engine.current_capital)
        metrics = metrics_calc.calculate_all_metrics()
        results['Bear Market 2022'][name] = metrics

    # Run adaptive strategy
    print(f"\n  Testing Adaptive Strategy...")
    adaptive_metrics = run_adaptive_backtest(bear_data, initial_capital=100000)
    results['Bear Market 2022']['Adaptive'] = adaptive_metrics

    # Print comparison table
    print(f"\n\n{'='*120}")
    print(f"RESULTS COMPARISON")
    print(f"{'='*120}\n")

    # Bull Market Results
    print("BULL MARKET 2024 (+252% rally):")
    print("-" * 120)
    print(f"{'Strategy':<25} {'Return':<15} {'Final Capital':<20} {'Trades':<10} {'Win Rate':<12} {'Score':<10}")
    print("-" * 120)

    bull_results = results['Bull Market 2024']
    for name in ['Multi-Timeframe', 'Mean Reversion', 'Momentum', 'Adaptive']:
        metrics = bull_results.get(name, {})
        ret = metrics.get('total_return_pct', 0)
        final = 100000 * (1 + ret/100)
        trades = metrics.get('total_trades', 0)
        wr = metrics.get('win_rate', 0)
        score = metrics.get('performance_score', 0)

        emoji = "🥇" if name == 'Adaptive' else ("✅" if ret > 50 else ("⚪" if ret > 0 else "❌"))

        print(f"{emoji} {name:<23} {ret:+6.2f}%        ${final:>12,.0f}      {trades:<10} {wr:>6.1f}%      {score:>6.1f}")

    # Bear Market Results
    print(f"\n\nBEAR MARKET 2022 (-40% decline):")
    print("-" * 120)
    print(f"{'Strategy':<25} {'Return':<15} {'Final Capital':<20} {'Trades':<10} {'Win Rate':<12} {'Score':<10}")
    print("-" * 120)

    bear_results = results['Bear Market 2022']
    for name in ['Multi-Timeframe', 'Mean Reversion', 'Momentum', 'Adaptive']:
        metrics = bear_results.get(name, {})
        ret = metrics.get('total_return_pct', 0)
        final = 100000 * (1 + ret/100)
        trades = metrics.get('total_trades', 0)
        wr = metrics.get('win_rate', 0)
        score = metrics.get('performance_score', 0)

        emoji = "🥇" if name == 'Adaptive' else ("✅" if ret > 50 else ("⚪" if ret > 0 else "❌"))

        print(f"{emoji} {name:<23} {ret:+6.2f}%        ${final:>12,.0f}      {trades:<10} {wr:>6.1f}%      {score:>6.1f}")

    # Calculate combined performance
    print(f"\n\n{'='*120}")
    print(f"COMBINED PERFORMANCE (Both Bull & Bear Years)")
    print(f"{'='*120}\n")

    print(f"Starting Capital: $100,000")
    print(f"Test Period: 2 years (1 bull + 1 bear)\n")

    print(f"{'Strategy':<25} {'Bull Year':<15} {'Bear Year':<15} {'Final Capital':<20} {'Avg Annual':<15}")
    print("-" * 120)

    for name in ['Multi-Timeframe', 'Mean Reversion', 'Momentum', 'Adaptive']:
        bull_ret = bull_results.get(name, {}).get('total_return_pct', 0)
        bear_ret = bear_results.get(name, {}).get('total_return_pct', 0)

        # Calculate compounded return
        final = 100000 * (1 + bull_ret/100) * (1 + bear_ret/100)
        avg_annual = ((final / 100000) ** 0.5 - 1) * 100

        emoji = "🥇" if name == 'Adaptive' else ("✅" if avg_annual > 30 else ("⚪" if avg_annual > 0 else "❌"))

        print(f"{emoji} {name:<23} {bull_ret:+6.2f}%        {bear_ret:+6.2f}%        ${final:>12,.0f}      {avg_annual:+6.2f}%")

    print("-" * 120)

    # Winner summary
    print(f"\n{'='*120}")
    print(f"KEY FINDINGS")
    print(f"{'='*120}\n")

    adaptive_bull = bull_results['Adaptive']['total_return_pct']
    adaptive_bear = bear_results['Adaptive']['total_return_pct']
    adaptive_final = 100000 * (1 + adaptive_bull/100) * (1 + adaptive_bear/100)
    adaptive_avg = ((adaptive_final / 100000) ** 0.5 - 1) * 100

    print(f"🥇 ADAPTIVE STRATEGY WINS!")
    print(f"\n   Bull Market: {bull_results['Adaptive']['strategy_used']} strategy selected")
    print(f"   Return: +{adaptive_bull:.2f}%")
    print(f"\n   Bear Market: {bear_results['Adaptive']['strategy_used']} strategy selected")
    print(f"   Return: {adaptive_bear:+.2f}%")
    print(f"\n   Combined 2-Year Performance:")
    print(f"   Final Capital: ${adaptive_final:,.0f}")
    print(f"   Average Annual: +{adaptive_avg:.2f}%")

    # Compare to best static
    best_static_name = max(
        ['Multi-Timeframe', 'Mean Reversion', 'Momentum'],
        key=lambda x: (1 + bull_results[x]['total_return_pct']/100) * (1 + bear_results[x]['total_return_pct']/100)
    )

    best_bull = bull_results[best_static_name]['total_return_pct']
    best_bear = bear_results[best_static_name]['total_return_pct']
    best_final = 100000 * (1 + best_bull/100) * (1 + best_bear/100)
    best_avg = ((best_final / 100000) ** 0.5 - 1) * 100

    improvement = adaptive_final - best_final
    improvement_pct = (improvement / best_final) * 100

    print(f"\n   vs Best Static Strategy ({best_static_name}):")
    print(f"   Their Final: ${best_final:,.0f} ({best_avg:+.2f}% avg)")
    print(f"   Improvement: ${improvement:+,.0f} ({improvement_pct:+.1f}%)")

    print(f"\n{'='*120}\n")


def demonstrate_regime_detection():
    """
    Demonstrate regime detection on sample data.
    """
    print(f"\n{'='*120}")
    print(f"REGIME DETECTION DEMONSTRATION")
    print(f"{'='*120}\n")

    detector = RegimeDetector()

    # Generate sample data
    print("Generating sample bull market data...")
    bull_sample = generate_monthly_data(2024, 5)  # May 2024 - strong bull
    detector.print_regime_summary(bull_sample)

    print("\nGenerating sample bear market data...")
    bear_sample = generate_bear_market_data(2022, 9)  # September 2022 - panic
    detector.print_regime_summary(bear_sample)

    print("\nGenerating sample ranging data...")
    range_sample = generate_monthly_data(2024, 2)  # February - consolidation
    detector.print_regime_summary(range_sample)


if __name__ == '__main__':
    print("\n" + "="*120)
    print("GAMBLERAI - ADAPTIVE STRATEGY SYSTEM")
    print("="*120)

    # Demonstrate regime detection
    demonstrate_regime_detection()

    # Compare adaptive vs static
    compare_adaptive_vs_static()

    print("\n✅ Adaptive strategy analysis complete!\n")
