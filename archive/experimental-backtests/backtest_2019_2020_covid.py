#!/usr/bin/env python3
"""
2019-2020 COVID Crash Analysis

Tests adaptive regime detection during the fastest bear market in history:
- June 2019 - February 2020: Bull market (steady growth)
- March 2020: COVID crash (-35% in ONE MONTH!)
- April-June 2020: V-shaped recovery (+40% rebound)

This tests if the system can:
1. Detect sudden crashes quickly
2. Switch strategies in time
3. Capture the V-shaped recovery
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


def generate_2019_2020_data(year: int, month: int, bars_per_day: int = 20) -> pd.DataFrame:
    """
    Generate realistic 2019-2020 COVID crash data.

    Timeline:
    - June 2019 - February 2020: Bull market (slow grind up)
    - March 2020: COVID CRASH (-35% in 4 weeks!)
    - April-June 2020: V-shaped recovery (+40%)
    """
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    trading_days = int(days_in_month * 0.67)
    total_bars = trading_days * bars_per_day

    # Market characteristics by month
    market_regimes = {
        # 2019 Bull Market - Steady Growth
        (2019, 6): {'drift': 0.0004, 'vol': 0.007, 'name': 'Jun 2019 - Recovery', 'base': 195.0},
        (2019, 7): {'drift': 0.0005, 'vol': 0.008, 'name': 'Jul 2019 - Rally', 'base': 205.0},
        (2019, 8): {'drift': -0.0001, 'vol': 0.011, 'name': 'Aug 2019 - Trade War Fears', 'base': 215.0},
        (2019, 9): {'drift': 0.0003, 'vol': 0.009, 'name': 'Sep 2019 - Bounce', 'base': 210.0},
        (2019, 10): {'drift': 0.0006, 'vol': 0.008, 'name': 'Oct 2019 - Melt Up Begins', 'base': 220.0},
        (2019, 11): {'drift': 0.0007, 'vol': 0.007, 'name': 'Nov 2019 - Strong Rally', 'base': 235.0},
        (2019, 12): {'drift': 0.0005, 'vol': 0.006, 'name': 'Dec 2019 - Year-End Rally', 'base': 250.0},

        # 2020 Pre-COVID
        (2020, 1): {'drift': 0.0008, 'vol': 0.006, 'name': 'Jan 2020 - ATH Push', 'base': 260.0},
        (2020, 2): {'drift': 0.0004, 'vol': 0.010, 'name': 'Feb 2020 - COVID Rumors', 'base': 280.0},

        # 2020 COVID CRASH
        (2020, 3): {'drift': -0.0025, 'vol': 0.035, 'name': 'Mar 2020 - COVID CRASH', 'base': 285.0},

        # 2020 V-Recovery
        (2020, 4): {'drift': 0.0015, 'vol': 0.025, 'name': 'Apr 2020 - Fed Rescue', 'base': 185.0},
        (2020, 5): {'drift': 0.0010, 'vol': 0.020, 'name': 'May 2020 - Reopening Hope', 'base': 230.0},
        (2020, 6): {'drift': 0.0008, 'vol': 0.018, 'name': 'Jun 2020 - Tech Rally', 'base': 260.0},
    }

    regime = market_regimes.get((year, month), {
        'drift': 0.0000,
        'vol': 0.010,
        'name': 'Default',
        'base': 250.0
    })

    base_price = regime['base']

    # Generate returns
    np.random.seed(42 + month + year * 100)
    returns = np.random.normal(regime['drift'], regime['vol'], total_bars)

    # Special events
    if (year, month) == (2020, 3):
        # COVID CRASH - Multiple circuit breakers
        # Week 1: Initial panic
        for i in range(20, 40):
            returns[i] -= 0.015  # -1.5% per bar

        # Week 2: Circuit breakers (-7%, -13%)
        returns[60] -= 0.07  # -7% circuit breaker day
        returns[75] -= 0.09  # -9% another crash day
        returns[90] -= 0.12  # -12% CIRCUIT BREAKER!

        # Week 3: Continued selling
        for i in range(100, 140):
            returns[i] -= 0.008

        # Week 4: Capitulation
        returns[160] -= 0.10  # Final flush

        # Panic volume on crash days
        # This is handled in volume section below

    elif (year, month) == (2020, 4):
        # April - Fed announcement V-bounce
        # First week: Still fear
        for i in range(0, 20):
            returns[i] -= 0.002

        # Week 2: Fed announces unlimited QE
        returns[40] += 0.09  # +9% Fed day!
        returns[41] += 0.07  # +7% follow through

        # Rest of month: Strong recovery
        for i in range(60, total_bars):
            returns[i] += 0.005  # Persistent buying

    prices = base_price * np.exp(np.cumsum(returns))

    # Generate OHLC
    data = []
    start_date = datetime(year, month, 1, 9, 30)

    for i in range(total_bars):
        price = prices[i]

        # Volatility characteristics
        if (year, month) == (2020, 3):
            # Extreme volatility during crash
            range_factor = 3.0
        elif (year, month) == (2020, 4):
            # High volatility during recovery
            range_factor = 2.0
        else:
            range_factor = 1.0

        high_pct = np.random.uniform(0.003, 0.012) * range_factor
        low_pct = np.random.uniform(0.003, 0.012) * range_factor

        open_price = price * (1 + np.random.uniform(-0.005, 0.005))
        high = price * (1 + high_pct)
        low = price * (1 - low_pct)
        close = price

        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Volume patterns
        base_volume = 50_000_000

        if (year, month) == (2020, 3):
            # PANIC VOLUME during crash
            if i in [60, 75, 90, 160]:  # Crash days
                volume_mult = np.random.uniform(8, 15)  # EXTREME volume
            else:
                volume_mult = np.random.uniform(2, 5)  # Elevated volume
        elif (year, month) == (2020, 4) and i in [40, 41]:
            # High volume on Fed rally
            volume_mult = np.random.uniform(5, 8)
        else:
            volume_mult = np.random.lognormal(0, 0.5)

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


def analyze_regime_during_covid():
    """
    Analyze how regime detection handled the COVID crash.
    """
    print(f"\n{'='*120}")
    print(f"REGIME DETECTION DURING COVID CRASH: June 2019 - June 2020")
    print(f"{'='*120}\n")

    detector = RegimeDetector()

    # Generate data for each month
    all_data = []
    months_data = []

    for year in [2019, 2020]:
        start_month = 6 if year == 2019 else 1
        end_month = 12 if year == 2019 else 6

        for month in range(start_month, end_month + 1):
            df = generate_2019_2020_data(year, month)
            months_data.append((year, month, df))
            all_data.append(df)

    # Concatenate all data
    full_df = pd.concat(all_data, ignore_index=True)

    print(f"Total data points: {len(full_df)} bars")
    print(f"Date range: {full_df['timestamp'].iloc[0]} to {full_df['timestamp'].iloc[-1]}")
    print(f"Price range: ${full_df['close'].iloc[0]:.2f} → ${full_df['close'].iloc[-1]:.2f}")
    print(f"COVID crash: Feb 2020 (${months_data[8][2]['close'].iloc[-1]:.2f}) → "
          f"Mar 2020 (${months_data[9][2]['close'].iloc[-1]:.2f})\n")

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

            # Special emoji for COVID crash
            if (year, month) == (2020, 3):
                emoji = '💥'  # Crash
            elif (year, month) == (2020, 4):
                emoji = '🚀'  # Recovery
            elif regime == 'BULL':
                emoji = '📈'
            elif regime == 'BEAR':
                emoji = '📉'
            else:
                emoji = '📊'

            print(f"{emoji} {month_name:<18} {regime:<10} {confidence:>6.1%}      "
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

    # Analyze COVID crash specifically
    print(f"COVID CRASH ANALYSIS (March 2020):")
    print(f"{'-'*120}")

    march_2020 = [r for r in regime_history if r['year'] == 2020 and r['month_num'] == 3][0]
    feb_2020 = [r for r in regime_history if r['year'] == 2020 and r['month_num'] == 2][0]

    crash_magnitude = ((march_2020['price'] - feb_2020['price']) / feb_2020['price']) * 100

    print(f"February 2020: ${feb_2020['price']:.2f} (ATH)")
    print(f"March 2020: ${march_2020['price']:.2f}")
    print(f"Decline: {crash_magnitude:.1f}% in ONE MONTH")
    print(f"Regime detected: {march_2020['regime']} ({march_2020['confidence']:.1%} confidence)")
    print(f"Detection speed: {'✅ FAST' if march_2020['regime'] == 'BEAR' else '⚠️ DELAYED'}")
    print(f"{'-'*120}\n")

    # Regime changes
    print(f"REGIME CHANGES DETECTED:")
    print(f"{'-'*120}")

    prev_regime = None
    for entry in regime_history:
        if entry['regime'] != prev_regime:
            if prev_regime is not None:
                change_emoji = "🔔" if entry['month'] != 'Mar 2020' else "💥"
                print(f"{change_emoji} {entry['month']}: {prev_regime} → {entry['regime']} "
                      f"(Price: ${entry['price']:.2f}, Confidence: {entry['confidence']:.1%})")
            prev_regime = entry['regime']

    print(f"{'-'*120}\n")

    return full_df, regime_history


def run_covid_strategy_comparison():
    """
    Compare adaptive strategy vs static strategies during COVID crash.
    """
    print(f"\n{'='*120}")
    print(f"STRATEGY PERFORMANCE DURING COVID: June 2019 - June 2020")
    print(f"{'='*120}\n")

    # Generate full period data
    all_data = []
    for year in [2019, 2020]:
        start_month = 6 if year == 2019 else 1
        end_month = 12 if year == 2019 else 6

        for month in range(start_month, end_month + 1):
            df = generate_2019_2020_data(year, month)
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

    # Test adaptive strategy (month by month)
    print(f"  Testing Adaptive Strategy...", end=' ')
    selector = AdaptiveStrategySelector()

    monthly_segments = []
    cumulative_capital = 100000

    for year in [2019, 2020]:
        start_month = 6 if year == 2019 else 1
        end_month = 12 if year == 2019 else 6

        for month in range(start_month, end_month + 1):
            df = generate_2019_2020_data(year, month)

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

        emoji = "✅" if ret > 20 else ("⚪" if ret > 0 else "❌")
        print(f"{emoji} {name:<23} {ret:+6.2f}%        ${final:>12,.0f}      {trades:<10} {wr:>6.1f}%      {score:>6.1f}")

    print(f"🥇 {'Adaptive':<23} {adaptive_return:+6.2f}%        ${cumulative_capital:>12,.0f}      "
          f"{'varies':<10} {'varies':<12} {'N/A':<10}")

    print(f"{'-'*120}\n")

    # Monthly breakdown focusing on COVID period
    print(f"\nADAPTIVE STRATEGY - MONTHLY BREAKDOWN (Focus: COVID Period):")
    print(f"{'-'*120}")
    print(f"{'Month':<15} {'Regime/Strategy':<30} {'Return':<12} {'Capital':<15}")
    print(f"{'-'*120}")

    for segment in monthly_segments:
        # Highlight COVID crash period
        if segment['year'] == 2020 and segment['month_num'] in [2, 3, 4]:
            if segment['month_num'] == 2:
                emoji = "⚠️ "  # Pre-crash
            elif segment['month_num'] == 3:
                emoji = "💥"  # Crash
            else:
                emoji = "🚀"  # Recovery
        else:
            emoji = "📈" if segment['return'] > 3 else ("📉" if segment['return'] < -3 else "⚪")

        print(f"{emoji} {segment['month']:<13} {segment['strategy']:<30} {segment['return']:+6.2f}%     "
              f"${segment['capital']:>12,.0f}")

    print(f"{'-'*120}\n")

    # COVID crash analysis
    feb_segment = [s for s in monthly_segments if s['year'] == 2020 and s['month_num'] == 2][0]
    mar_segment = [s for s in monthly_segments if s['year'] == 2020 and s['month_num'] == 3][0]
    apr_segment = [s for s in monthly_segments if s['year'] == 2020 and s['month_num'] == 4][0]

    print(f"COVID CRASH PERIOD ANALYSIS:")
    print(f"{'-'*120}")
    print(f"February 2020 (Pre-Crash):")
    print(f"  Strategy: {feb_segment['strategy']}")
    print(f"  Return: {feb_segment['return']:+.2f}%")
    print(f"\nMarch 2020 (CRASH):")
    print(f"  Market: -35% (circuit breakers triggered)")
    print(f"  Strategy: {mar_segment['strategy']}")
    print(f"  Return: {mar_segment['return']:+.2f}%")
    print(f"  {'✅ Outperformed' if mar_segment['return'] > -35 else '❌ Underperformed'}")
    print(f"\nApril 2020 (Recovery):")
    print(f"  Strategy: {apr_segment['strategy']}")
    print(f"  Return: {apr_segment['return']:+.2f}%")
    print(f"{'-'*120}\n")


if __name__ == '__main__':
    print("\n" + "="*120)
    print("GAMBLERAI - COVID CRASH ANALYSIS")
    print("Testing Period: June 2019 - June 2020 (Including March 2020 Crash)")
    print("="*120)

    # Analyze regime detection
    full_data, regime_history = analyze_regime_during_covid()

    # Compare strategies
    run_covid_strategy_comparison()

    print("\n✅ COVID crash analysis complete!\n")
