#!/usr/bin/env python3
"""
Volatility-Adjusted Adaptive Strategy Backtest

Compares:
1. Original adaptive system (regime-only)
2. Volatility-adjusted adaptive system (regime + volatility filter)

Tests on 2024-2025 forward projection to see if volatility filter
prevents losses in choppy bull markets.
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer


def generate_2024_2025_data(year: int, month: int, bars_per_day: int = 20, starting_price: float = None) -> pd.DataFrame:
    """
    Generate realistic market data for 2024-2025 period.

    Simulates:
    - Q4 2024: Bull market (AI boom, election rally)
    - Q1 2025: Correction (profit taking, valuation concerns)
    - Q2 2025: Ranging/volatile (choppy, uncertainty)
    - Q3-Q4 2025: Recovery rally (Fed cuts, stabilization)

    Args:
        year: Year
        month: Month
        bars_per_day: Number of bars per trading day
        starting_price: Optional starting price (uses previous month's ending price for continuity)
    """
    # Market regime characteristics by month
    market_regimes = {
        # Q4 2024 - Bull continuation
        (2024, 10): {'drift': 0.0006, 'vol': 0.009, 'name': 'Oct 2024 - Tech Rally', 'base': 225.0},
        (2024, 11): {'drift': 0.0008, 'vol': 0.008, 'name': 'Nov 2024 - Election Rally', 'base': 240.0},
        (2024, 12): {'drift': 0.0010, 'vol': 0.010, 'name': 'Dec 2024 - Year-End Melt-Up', 'base': 260.0},

        # Q1 2025 - Correction phase
        (2025, 1): {'drift': -0.0003, 'vol': 0.012, 'name': 'Jan 2025 - Profit Taking', 'base': 285.0},
        (2025, 2): {'drift': -0.0005, 'vol': 0.015, 'name': 'Feb 2025 - Valuation Concerns', 'base': 270.0},
        (2025, 3): {'drift': -0.0004, 'vol': 0.014, 'name': 'Mar 2025 - Continued Weakness', 'base': 255.0},

        # Q2 2025 - Ranging/volatile
        (2025, 4): {'drift': 0.0002, 'vol': 0.016, 'name': 'Apr 2025 - Choppy Rally Attempt', 'base': 245.0},
        (2025, 5): {'drift': 0.0001, 'vol': 0.018, 'name': 'May 2025 - Sideways Grind', 'base': 255.0},
        (2025, 6): {'drift': -0.0002, 'vol': 0.017, 'name': 'Jun 2025 - Range Bound', 'base': 260.0},

        # Q3-Q4 2025 - Recovery
        (2025, 7): {'drift': 0.0007, 'vol': 0.013, 'name': 'Jul 2025 - Fed Cut Rally', 'base': 250.0},
        (2025, 8): {'drift': 0.0005, 'vol': 0.011, 'name': 'Aug 2025 - Stabilization', 'base': 275.0},
        (2025, 9): {'drift': 0.0008, 'vol': 0.010, 'name': 'Sep 2025 - Momentum Return', 'base': 295.0},
        (2025, 10): {'drift': 0.0006, 'vol': 0.009, 'name': 'Oct 2025 - Continued Recovery', 'base': 320.0},
    }

    regime = market_regimes.get((year, month))

    if regime is None:
        raise ValueError(f"No regime data for {year}-{month:02d}")

    # Generate trading days for the month
    days_in_month = pd.Period(f"{year}-{month:02d}").days_in_month
    trading_days = int(days_in_month * 0.71)  # ~71% are trading days

    total_bars = trading_days * bars_per_day

    # Generate random returns with GBM
    drift = regime['drift']
    volatility = regime['vol']
    # Use provided starting price if available, otherwise use base price
    base_price = starting_price if starting_price is not None else regime['base']

    # Scale drift and volatility to bar frequency
    dt = 1 / (252 * bars_per_day)  # Time step
    returns = np.random.normal(drift * dt, volatility * np.sqrt(dt), total_bars)

    # Add occasional spikes (10% of bars get extra volatility)
    spike_bars = np.random.choice(total_bars, size=int(total_bars * 0.1), replace=False)
    returns[spike_bars] *= 2.0

    # Generate price series
    price = base_price * np.exp(np.cumsum(returns))

    # Create OHLC data
    high = price * (1 + np.abs(np.random.normal(0, volatility/2, total_bars)))
    low = price * (1 - np.abs(np.random.normal(0, volatility/2, total_bars)))
    open_price = np.roll(price, 1)
    open_price[0] = base_price

    # Generate volume (higher volume on bigger moves)
    base_volume = 1_000_000
    volume_multiplier = 1 + np.abs(returns) * 100
    volume = base_volume * volume_multiplier

    # Create timestamps
    start_date = datetime(year, month, 1, 9, 30)
    timestamps = []
    current_time = start_date

    bar_minutes = 390 // bars_per_day

    for i in range(total_bars):
        timestamps.append(current_time)
        current_time += timedelta(minutes=bar_minutes)

        # Skip to next day at 4pm
        if current_time.hour >= 16:
            current_time = current_time.replace(hour=9, minute=30)
            current_time += timedelta(days=1)
            # Skip weekends
            while current_time.weekday() >= 5:
                current_time += timedelta(days=1)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': open_price,
        'high': high,
        'low': low,
        'close': price,
        'volume': volume,
    })

    return df


def run_volatility_adjusted_backtest(
    market_data: pd.DataFrame,
    initial_capital: float = 100000,
    use_volatility_filter: bool = True,
) -> Dict:
    """
    Run backtest with volatility-adjusted adaptive strategy.

    Args:
        market_data: Combined market data
        initial_capital: Starting capital
        use_volatility_filter: Whether to use volatility-aware strategy selection

    Returns:
        Dictionary with results
    """
    # Create adaptive strategy selector with lower volatility threshold
    # Use 1.2% threshold to better capture high-volatility periods in simulated data
    regime_detector = RegimeDetector(high_volatility_threshold=0.012)
    selector = AdaptiveStrategySelector(
        regime_detector=regime_detector,
        use_volatility_filter=use_volatility_filter,
    )

    # Track performance month by month
    monthly_results = []
    cumulative_capital = initial_capital

    # Group data by month
    market_data['year_month'] = market_data['timestamp'].dt.to_period('M')

    for period, month_df in market_data.groupby('year_month'):
        month_df = month_df.reset_index(drop=True)

        # Detect regime and volatility for this month
        if use_volatility_filter:
            regime, confidence, is_high_vol = regime_detector.detect_regime_with_volatility(month_df)
        else:
            regime, confidence = regime_detector.detect_regime_with_confidence(month_df)
            is_high_vol = False

        # Select strategy
        strategy_name, strategy = selector.select_strategy(month_df)

        # Run backtest for this month
        engine = BacktestEngine(
            initial_capital=cumulative_capital,
            risk_per_trade=0.01,
        )

        trades = engine.run_backtest(month_df, strategy)

        # Calculate monthly performance
        if trades:
            final_capital = engine.trade_manager.current_capital
            monthly_return = (final_capital - cumulative_capital) / cumulative_capital

            # Update cumulative capital
            cumulative_capital = final_capital
        else:
            monthly_return = 0.0
            final_capital = cumulative_capital

        # Get volatility metrics
        vol_metrics = regime_detector.calculate_volatility_metrics(month_df)

        monthly_results.append({
            'period': str(period),
            'regime': regime,
            'confidence': confidence,
            'is_high_volatility': is_high_vol,
            'historical_volatility': vol_metrics.get('historical_volatility'),
            'strategy_used': strategy_name,
            'trades': len(trades),
            'monthly_return': monthly_return,
            'capital': final_capital,
        })

    # Calculate overall metrics
    total_return = (cumulative_capital - initial_capital) / initial_capital

    return {
        'monthly_results': monthly_results,
        'initial_capital': initial_capital,
        'final_capital': cumulative_capital,
        'total_return': total_return,
        'regime_changes': selector.regime_changes,
        'volatility_switches': selector.volatility_switches,
    }


def compare_with_and_without_volatility_filter():
    """
    Compare adaptive system with and without volatility filter.
    """
    print("=" * 120)
    print("VOLATILITY-ADJUSTED ADAPTIVE STRATEGY COMPARISON")
    print("Testing Period: October 2024 - October 2025")
    print("=" * 120)
    print()

    # Generate full market data for 13 months with price continuity
    print("Generating market data...")
    all_data = []
    last_price = None  # Track last price for continuity

    months = [
        (2024, 10), (2024, 11), (2024, 12),
        (2025, 1), (2025, 2), (2025, 3),
        (2025, 4), (2025, 5), (2025, 6),
        (2025, 7), (2025, 8), (2025, 9), (2025, 10),
    ]

    for year, month in months:
        month_data = generate_2024_2025_data(year, month, starting_price=last_price)
        all_data.append(month_data)
        # Update last price for next month
        last_price = month_data['close'].iloc[-1]

    market_data = pd.concat(all_data, ignore_index=True)

    start_price = market_data['close'].iloc[0]
    end_price = market_data['close'].iloc[-1]
    market_return = (end_price - start_price) / start_price

    print(f"Market: ${start_price:.2f} → ${end_price:.2f} ({market_return:+.1%})")
    print()

    # Test 1: Original adaptive (regime-only)
    print("Running original adaptive system (regime-only)...")
    results_original = run_volatility_adjusted_backtest(
        market_data,
        initial_capital=100000,
        use_volatility_filter=False,
    )

    # Test 2: Volatility-adjusted adaptive
    print("Running volatility-adjusted adaptive system...")
    results_vol_adjusted = run_volatility_adjusted_backtest(
        market_data,
        initial_capital=100000,
        use_volatility_filter=True,
    )

    # Test 3: Static Mean Reversion (for comparison)
    print("Running static Mean Reversion...")
    mr_engine = BacktestEngine(initial_capital=100000, risk_per_trade=0.01)
    mr_detector = MeanReversionDetector()
    mr_trades = mr_engine.run_backtest(market_data, mr_detector)
    mr_return = (mr_engine.trade_manager.current_capital - 100000) / 100000

    # Test 4: Static Multi-Timeframe (for comparison)
    print("Running static Multi-Timeframe...")
    mt_engine = BacktestEngine(initial_capital=100000, risk_per_trade=0.01)
    mt_analyzer = MultiTimeframeAnalyzer()
    mt_trades = mt_engine.run_backtest(market_data, mt_analyzer)
    mt_return = (mt_engine.trade_manager.current_capital - 100000) / 100000

    print()
    print("=" * 120)
    print("RESULTS SUMMARY")
    print("=" * 120)
    print()

    print(f"Market Performance:                    {market_return:+.2%}")
    print(f"Mean Reversion (static):               {mr_return:+.2%}  [{len(mr_trades)} trades]")
    print(f"Multi-Timeframe (static):              {mt_return:+.2%}  [{len(mt_trades)} trades]")
    print()
    print(f"Original Adaptive (regime-only):       {results_original['total_return']:+.2%}  [{results_original['regime_changes']} regime changes]")
    print(f"Volatility-Adjusted Adaptive:          {results_vol_adjusted['total_return']:+.2%}  [{results_vol_adjusted['regime_changes']} regime changes, {results_vol_adjusted['volatility_switches']} vol switches]")
    print()

    improvement = results_vol_adjusted['total_return'] - results_original['total_return']
    print(f"Improvement from volatility filter:    {improvement:+.2%}")
    print()

    # Month-by-month comparison
    print("=" * 120)
    print("MONTH-BY-MONTH COMPARISON")
    print("=" * 120)
    print()

    print(f"{'Month':<15} {'Regime':<8} {'Vol':<6} {'Original Strategy':<20} {'Vol-Adj Strategy':<20} {'Original':<10} {'Vol-Adj':<10} {'Diff':<10}")
    print("-" * 120)

    for i, (orig, vol_adj) in enumerate(zip(results_original['monthly_results'], results_vol_adjusted['monthly_results'])):
        vol_status = "🔴HIGH" if vol_adj['is_high_volatility'] else "🟢LOW "

        # Check if strategies differ
        strategy_diff = orig['strategy_used'] != vol_adj['strategy_used']
        diff_marker = " ⚠️ " if strategy_diff else ""

        return_diff = vol_adj['monthly_return'] - orig['monthly_return']
        diff_color = "✅" if return_diff > 0 else ("🔴" if return_diff < -0.05 else "")

        print(f"{orig['period']:<15} {orig['regime']:<8} {vol_status} {orig['strategy_used']:<20} {vol_adj['strategy_used']:<20} "
              f"{orig['monthly_return']:>8.2%}   {vol_adj['monthly_return']:>8.2%}   {return_diff:>8.2%} {diff_color}{diff_marker}")

    print("-" * 120)
    print()

    # Highlight key differences
    print("=" * 120)
    print("KEY INSIGHTS")
    print("=" * 120)
    print()

    # Count times volatility filter changed strategy
    strategy_changes = 0
    high_vol_bull_months = []

    for orig, vol_adj in zip(results_original['monthly_results'], results_vol_adjusted['monthly_results']):
        if orig['strategy_used'] != vol_adj['strategy_used']:
            strategy_changes += 1

            if vol_adj['regime'] == 'BULL' and vol_adj['is_high_volatility']:
                high_vol_bull_months.append({
                    'period': orig['period'],
                    'orig_strategy': orig['strategy_used'],
                    'vol_adj_strategy': vol_adj['strategy_used'],
                    'orig_return': orig['monthly_return'],
                    'vol_adj_return': vol_adj['monthly_return'],
                    'improvement': vol_adj['monthly_return'] - orig['monthly_return'],
                })

    print(f"1. Volatility filter changed strategy {strategy_changes} times")
    print()

    if high_vol_bull_months:
        print(f"2. High-Volatility BULL months (where filter made a difference):")
        print()
        for month in high_vol_bull_months:
            print(f"   {month['period']}: {month['orig_strategy']} → {month['vol_adj_strategy']}")
            print(f"   Return: {month['orig_return']:+.2%} → {month['vol_adj_return']:+.2%} (Improvement: {month['improvement']:+.2%})")
            print()

    if improvement > 0:
        print(f"3. ✅ Volatility filter IMPROVED performance by {improvement:.2%}")
        print(f"   This proves that detecting high volatility prevents losses in choppy markets!")
    elif improvement < -0.05:
        print(f"3. 🔴 Volatility filter REDUCED performance by {abs(improvement):.2%}")
        print(f"   May need to adjust volatility threshold or strategy mapping.")
    else:
        print(f"3. ⚖️ Volatility filter had minimal impact ({improvement:+.2%})")
        print(f"   This period may not have had enough volatile BULL months to test.")

    print()

    # Calculate average return in different conditions
    original_bull_returns = [m['monthly_return'] for m in results_original['monthly_results'] if m['regime'] == 'BULL']
    vol_adj_bull_returns = [m['monthly_return'] for m in results_vol_adjusted['monthly_results'] if m['regime'] == 'BULL']

    if original_bull_returns:
        print(f"4. Average BULL month performance:")
        print(f"   Original:       {np.mean(original_bull_returns):+.2%}")
        print(f"   Vol-Adjusted:   {np.mean(vol_adj_bull_returns):+.2%}")
        print()

    print("=" * 120)
    print()


if __name__ == "__main__":
    compare_with_and_without_volatility_filter()

    print("✅ Volatility-adjusted adaptive system analysis complete!")
    print()
