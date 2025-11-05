#!/usr/bin/env python3
"""
2024-2025 Forward Analysis

Tests adaptive regime detection for recent past and forward projection:
- October 2024 - December 2024: Current market conditions
- January 2025 - October 2025: Forward projection with mixed scenarios

Scenarios modeled:
1. Bull continuation (AI boom continues)
2. Mid-year correction (profit-taking)
3. Recovery into year-end

This represents a realistic "soft landing" scenario with volatility.
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
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer


def generate_2024_2025_data(year: int, month: int, bars_per_day: int = 20) -> pd.DataFrame:
    """
    Generate realistic 2024-2025 market data.

    Scenario: AI boom continuation with volatility
    - Q4 2024: Strong bull market (AI hype continues)
    - Q1 2025: Minor correction (profit taking)
    - Q2 2025: Ranging/volatile (uncertainty)
    - Q3 2025: Recovery rally
    """
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    trading_days = int(days_in_month * 0.67)
    total_bars = trading_days * bars_per_day

    # Market characteristics by month
    market_regimes = {
        # Q4 2024 - Bull Market Continuation
        (2024, 10): {'drift': 0.0006, 'vol': 0.009, 'name': 'Oct 2024 - Tech Rally', 'base': 225.0},
        (2024, 11): {'drift': 0.0008, 'vol': 0.008, 'name': 'Nov 2024 - Election Rally', 'base': 240.0},
        (2024, 12): {'drift': 0.0007, 'vol': 0.007, 'name': 'Dec 2024 - Year-End Strength', 'base': 255.0},

        # Q1 2025 - Correction Phase
        (2025, 1): {'drift': 0.0003, 'vol': 0.011, 'name': 'Jan 2025 - Profit Taking', 'base': 270.0},
        (2025, 2): {'drift': -0.0002, 'vol': 0.013, 'name': 'Feb 2025 - Valuation Concerns', 'base': 275.0},
        (2025, 3): {'drift': -0.0004, 'vol': 0.015, 'name': 'Mar 2025 - Correction Low', 'base': 270.0},

        # Q2 2025 - Ranging/Volatile Period
        (2025, 4): {'drift': 0.0001, 'vol': 0.014, 'name': 'Apr 2025 - Choppy', 'base': 255.0},
        (2025, 5): {'drift': 0.0000, 'vol': 0.013, 'name': 'May 2025 - Range-Bound', 'base': 260.0},
        (2025, 6): {'drift': 0.0002, 'vol': 0.012, 'name': 'Jun 2025 - Stabilization', 'base': 258.0},

        # Q3 2025 - Recovery Rally
        (2025, 7): {'drift': 0.0005, 'vol': 0.010, 'name': 'Jul 2025 - Earnings Beat', 'base': 265.0},
        (2025, 8): {'drift': 0.0006, 'vol': 0.009, 'name': 'Aug 2025 - Rally Resumes', 'base': 275.0},
        (2025, 9): {'drift': 0.0007, 'vol': 0.008, 'name': 'Sep 2025 - Momentum', 'base': 290.0},
        (2025, 10): {'drift': 0.0008, 'vol': 0.008, 'name': 'Oct 2025 - Strong Close', 'base': 305.0},
    }

    regime = market_regimes.get((year, month), {
        'drift': 0.0003,
        'vol': 0.010,
        'name': 'Default',
        'base': 250.0
    })

    base_price = regime['base']

    # Generate returns
    np.random.seed(42 + month + year * 100)
    returns = np.random.normal(regime['drift'], regime['vol'], total_bars)

    # Add realistic events
    if (year, month) == (2024, 11):
        # Election rally spike
        rally_day = np.random.randint(10, 15)
        returns[rally_day] += 0.035  # +3.5% rally day

    elif (year, month) == (2025, 2):
        # Valuation scare selloff
        selloff_day = np.random.randint(40, 60)
        returns[selloff_day] -= 0.025  # -2.5% selloff

    elif (year, month) == (2025, 3):
        # Correction low - capitulation
        for i in range(80, 100):
            returns[i] -= 0.003  # Persistent selling

    elif (year, month) == (2025, 7):
        # Earnings beat catalyst
        earnings_day = np.random.randint(20, 40)
        returns[earnings_day] += 0.04  # +4% earnings surprise
        returns[earnings_day + 1] += 0.02  # Follow through

    elif (year, month) == (2025, 9):
        # Strong momentum - add trend
        for i in range(0, total_bars, 10):
            returns[i:i+5] += 0.002  # Persistent uptrend

    prices = base_price * np.exp(np.cumsum(returns))

    # Generate OHLC
    data = []
    start_date = datetime(year, month, 1, 9, 30)

    for i in range(total_bars):
        price = prices[i]

        # Volatility varies by period
        if (year, month) in [(2025, 2), (2025, 3), (2025, 4)]:
            range_factor = 1.5  # Higher volatility in correction
        else:
            range_factor = 1.0

        high_pct = np.random.uniform(0.002, 0.007) * range_factor
        low_pct = np.random.uniform(0.002, 0.007) * range_factor

        open_price = price * (1 + np.random.uniform(-0.003, 0.003))
        high = price * (1 + high_pct)
        low = price * (1 - low_pct)
        close = price

        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Volume patterns
        base_volume = 50_000_000

        # Higher volume during volatile periods
        if (year, month) in [(2025, 2), (2025, 3)]:
            volume_mult = np.random.lognormal(0.2, 0.6)
        else:
            volume_mult = np.random.lognormal(0, 0.5)

        # Spike volume on event days
        if abs(returns[i]) > regime['vol'] * 2.5:
            volume_mult *= 3

        volume = int(base_volume * volume_mult)

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


def analyze_2024_2025_regimes():
    """
    Analyze regime detection for 2024-2025 period.
    """
    print(f"\n{'='*120}")
    print(f"REGIME DETECTION: October 2024 - October 2025")
    print(f"{'='*120}\n")

    detector = RegimeDetector()

    # Generate data for each month
    all_data = []
    months_data = []

    for year in [2024, 2025]:
        start_month = 10 if year == 2024 else 1
        end_month = 12 if year == 2024 else 10

        for month in range(start_month, end_month + 1):
            df = generate_2024_2025_data(year, month)
            months_data.append((year, month, df))
            all_data.append(df)

    # Concatenate all data
    full_df = pd.concat(all_data, ignore_index=True)

    print(f"Total data points: {len(full_df)} bars")
    print(f"Date range: {full_df['timestamp'].iloc[0]} to {full_df['timestamp'].iloc[-1]}")
    print(f"Price trajectory: ${full_df['close'].iloc[0]:.2f} → ${full_df['close'].iloc[-1]:.2f}")
    print(f"Overall return: {((full_df['close'].iloc[-1] / full_df['close'].iloc[0]) - 1) * 100:+.1f}%\n")

    # Analyze regime for each month
    print(f"{'Month':<20} {'Regime':<10} {'Confidence':<12} {'Price':<12} {'200 EMA':<12} {'Distance':<12}")
    print(f"{'-'*120}")

    cumulative_df = pd.DataFrame()
    regime_history = []

    for year, month, df in months_data:
        cumulative_df = pd.concat([cumulative_df, df], ignore_index=True)

        if len(cumulative_df) >= 200:
            regime, confidence = detector.detect_regime_with_confidence(cumulative_df)

            current_price = cumulative_df['close'].iloc[-1]
            ema_200 = cumulative_df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
            distance = ((current_price - ema_200) / ema_200) * 100

            month_name = datetime(year, month, 1).strftime('%b %Y')

            # Emoji based on regime and phase
            if year == 2024 or (year == 2025 and month <= 1):
                phase_emoji = '📈'  # Bull phase
            elif year == 2025 and 2 <= month <= 3:
                phase_emoji = '📉'  # Correction phase
            elif year == 2025 and 4 <= month <= 6:
                phase_emoji = '📊'  # Ranging phase
            else:
                phase_emoji = '🚀'  # Recovery phase

            if regime == 'BULL':
                regime_emoji = '📈'
            elif regime == 'BEAR':
                regime_emoji = '📉'
            else:
                regime_emoji = '📊'

            emoji = phase_emoji + regime_emoji

            print(f"{emoji} {month_name:<17} {regime:<10} {confidence:>6.1%}      "
                  f"${current_price:>8.2f}   ${ema_200:>8.2f}   {distance:>+6.2f}%")

            regime_history.append({
                'month': month_name,
                'regime': regime,
                'confidence': confidence,
                'price': current_price,
                'ema': ema_200,
                'year': year,
                'month_num': month
            })

    print(f"{'-'*120}\n")

    # Identify regime changes
    print(f"REGIME CHANGES DETECTED:")
    print(f"{'-'*120}")

    prev_regime = None
    change_count = 0
    for entry in regime_history:
        if entry['regime'] != prev_regime:
            if prev_regime is not None:
                change_count += 1
                print(f"🔔 {entry['month']}: {prev_regime} → {entry['regime']} "
                      f"(Price: ${entry['price']:.2f}, Confidence: {entry['confidence']:.1%})")
            prev_regime = entry['regime']

    print(f"\nTotal regime changes: {change_count}")
    print(f"{'-'*120}\n")

    # Phase analysis
    print(f"MARKET PHASE ANALYSIS:")
    print(f"{'-'*120}")

    q4_2024 = [r for r in regime_history if r['year'] == 2024]
    q1_2025 = [r for r in regime_history if r['year'] == 2025 and r['month_num'] <= 3]
    q2_2025 = [r for r in regime_history if r['year'] == 2025 and 4 <= r['month_num'] <= 6]
    q3_2025 = [r for r in regime_history if r['year'] == 2025 and 7 <= r['month_num'] <= 10]

    def analyze_phase(phase_data, phase_name):
        if not phase_data:
            return

        avg_confidence = np.mean([r['confidence'] for r in phase_data])
        regime_counts = {}
        for r in phase_data:
            regime_counts[r['regime']] = regime_counts.get(r['regime'], 0) + 1

        dominant_regime = max(regime_counts.items(), key=lambda x: x[1])

        start_price = phase_data[0]['price']
        end_price = phase_data[-1]['price']
        phase_return = ((end_price - start_price) / start_price) * 100

        print(f"\n{phase_name}:")
        print(f"  Dominant Regime: {dominant_regime[0]} ({dominant_regime[1]}/{len(phase_data)} months)")
        print(f"  Avg Confidence: {avg_confidence:.1%}")
        print(f"  Phase Return: {phase_return:+.2f}%")
        print(f"  Price: ${start_price:.2f} → ${end_price:.2f}")

    analyze_phase(q4_2024, "Q4 2024 (Bull Continuation)")
    analyze_phase(q1_2025, "Q1 2025 (Correction)")
    analyze_phase(q2_2025, "Q2 2025 (Ranging)")
    analyze_phase(q3_2025, "Q3-Q4 2025 (Recovery)")

    print(f"{'-'*120}\n")

    return full_df, regime_history


def run_2024_2025_strategy_comparison():
    """
    Compare adaptive strategy vs static strategies for 2024-2025.
    """
    print(f"\n{'='*120}")
    print(f"STRATEGY PERFORMANCE: October 2024 - October 2025")
    print(f"{'='*120}\n")

    # Generate full period data
    all_data = []
    for year in [2024, 2025]:
        start_month = 10 if year == 2024 else 1
        end_month = 12 if year == 2024 else 10

        for month in range(start_month, end_month + 1):
            df = generate_2024_2025_data(year, month)
            all_data.append(df)

    full_data = pd.concat(all_data, ignore_index=True)

    market_start = full_data['close'].iloc[0]
    market_end = full_data['close'].iloc[-1]
    market_return = ((market_end - market_start) / market_start) * 100

    print(f"Testing period: {full_data['timestamp'].iloc[0].strftime('%Y-%m-%d')} to "
          f"{full_data['timestamp'].iloc[-1].strftime('%Y-%m-%d')}")
    print(f"Market performance: ${market_start:.2f} → ${market_end:.2f} ({market_return:+.1f}%)\n")

    # Test strategies
    strategies = {
        'Multi-Timeframe': MultiTimeframeAnalyzer(),
        'Mean Reversion': MeanReversionDetector(),
        'Momentum': MomentumDetector(use_db=False),
    }

    results = {}

    print("Running static strategies...")
    for name, strategy in strategies.items():
        print(f"  Testing {name}...", end=' ')
        engine = BacktestEngine(initial_capital=100000, risk_per_trade=0.01, max_concurrent_trades=3)
        trades = engine.run_backtest(full_data, strategy)
        metrics_calc = PerformanceMetrics(trades, 100000, engine.current_capital)
        metrics = metrics_calc.calculate_all_metrics()
        results[name] = metrics
        print(f"✓ ({metrics.get('total_return_pct', 0):+.2f}%)")

    # Test adaptive strategy
    print(f"  Testing Adaptive Strategy...", end=' ')
    selector = AdaptiveStrategySelector()

    monthly_segments = []
    cumulative_capital = 100000

    for year in [2024, 2025]:
        start_month = 10 if year == 2024 else 1
        end_month = 12 if year == 2024 else 10

        for month in range(start_month, end_month + 1):
            df = generate_2024_2025_data(year, month)

            strategy_name, strategy = selector.select_strategy(df)

            engine = BacktestEngine(
                initial_capital=cumulative_capital,
                risk_per_trade=0.01,
                max_concurrent_trades=3
            )
            trades = engine.run_backtest(df, strategy)

            month_return = ((engine.current_capital - cumulative_capital) / cumulative_capital) * 100
            cumulative_capital = engine.current_capital

            monthly_segments.append({
                'month': datetime(year, month, 1).strftime('%b %Y'),
                'strategy': strategy_name,
                'return': month_return,
                'capital': cumulative_capital,
                'year': year,
                'month_num': month
            })

    adaptive_return = ((cumulative_capital - 100000) / 100000) * 100
    print(f"✓ ({adaptive_return:+.2f}%)")

    # Results table
    print(f"\n{'='*120}")
    print(f"RESULTS COMPARISON")
    print(f"{'='*120}\n")

    print(f"{'Strategy':<25} {'Return':<15} {'Final Capital':<20} {'Trades':<10} {'Win Rate':<12} {'Score':<10}")
    print(f"{'-'*120}")

    for name in ['Multi-Timeframe', 'Mean Reversion', 'Momentum']:
        metrics = results[name]
        ret = metrics.get('total_return_pct', 0)
        final = 100000 * (1 + ret/100)
        trades = metrics.get('total_trades', 0)
        wr = metrics.get('win_rate', 0)
        score = metrics.get('performance_score', 0)

        emoji = "✅" if ret > 30 else ("⚪" if ret > 0 else "❌")
        print(f"{emoji} {name:<23} {ret:+6.2f}%        ${final:>12,.0f}      {trades:<10} {wr:>6.1f}%      {score:>6.1f}")

    print(f"🥇 {'Adaptive':<23} {adaptive_return:+6.2f}%        ${cumulative_capital:>12,.0f}      "
          f"{'varies':<10} {'varies':<12} {'N/A':<10}")

    print(f"{'-'*120}\n")

    # Monthly breakdown
    print(f"\nADAPTIVE STRATEGY - MONTHLY BREAKDOWN:")
    print(f"{'-'*120}")
    print(f"{'Month':<15} {'Regime/Strategy':<30} {'Return':<12} {'Capital':<15}")
    print(f"{'-'*120}")

    for segment in monthly_segments:
        if segment['year'] == 2024:
            emoji = "📈"
        elif segment['month_num'] <= 3:
            emoji = "📉" if segment['return'] < -2 else "⚪"
        elif segment['month_num'] <= 6:
            emoji = "📊"
        else:
            emoji = "🚀" if segment['return'] > 3 else "📈"

        print(f"{emoji} {segment['month']:<13} {segment['strategy']:<30} {segment['return']:+6.2f}%     "
              f"${segment['capital']:>12,.0f}")

    print(f"{'-'*120}\n")

    # Performance by phase
    print(f"PERFORMANCE BY MARKET PHASE:")
    print(f"{'-'*120}")

    q4_2024_segs = [s for s in monthly_segments if s['year'] == 2024]
    q1_2025_segs = [s for s in monthly_segments if s['year'] == 2025 and s['month_num'] <= 3]
    q2_2025_segs = [s for s in monthly_segments if s['year'] == 2025 and 4 <= s['month_num'] <= 6]
    q3_2025_segs = [s for s in monthly_segments if s['year'] == 2025 and 7 <= s['month_num'] <= 10]

    def phase_performance(segments, phase_name):
        if not segments:
            return

        total_return = ((segments[-1]['capital'] - segments[0]['capital'] + (100000 if segments[0] != monthly_segments[0] else 0)) /
                       (segments[0]['capital'] if segments[0] != monthly_segments[0] else 100000)) * 100
        strategies_used = list(set([s['strategy'] for s in segments]))

        print(f"\n{phase_name}:")
        print(f"  Return: {total_return:+.2f}%")
        print(f"  Strategies Used: {', '.join(strategies_used)}")

    phase_performance(q4_2024_segs, "Q4 2024 (Bull Market)")
    phase_performance(q1_2025_segs, "Q1 2025 (Correction)")
    phase_performance(q2_2025_segs, "Q2 2025 (Ranging)")
    phase_performance(q3_2025_segs, "Q3-Q4 2025 (Recovery)")

    print(f"{'-'*120}\n")


if __name__ == '__main__':
    print("\n" + "="*120)
    print("GAMBLERAI - 2024-2025 FORWARD ANALYSIS")
    print("Testing Period: October 2024 - October 2025 (Current & Forward)")
    print("="*120)

    # Analyze regime detection
    full_data, regime_history = analyze_2024_2025_regimes()

    # Compare strategies
    run_2024_2025_strategy_comparison()

    print("\n✅ 2024-2025 forward analysis complete!\n")
    print("Note: 2025 data is simulated projection based on realistic scenario modeling.")
