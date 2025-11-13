#!/usr/bin/env python3
"""
Debug why scanners aren't generating trades
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector


def generate_simple_test_data():
    """Generate simple test data with known characteristics."""
    print("Generating test data with HIGH volume and HIGH price moves...")

    bars = 500
    timestamps = [datetime(2020, 1, 1, 9, 30) + timedelta(minutes=i*5) for i in range(bars)]

    # Generate price with big moves
    price = 100 * (1 + np.cumsum(np.random.normal(0.002, 0.01, bars)))  # Big volatility

    # Generate volume with spikes
    base_volume = 1_000_000
    volume = base_volume * np.ones(bars)

    # Add explicit volume spikes every 50 bars
    for i in range(0, bars, 50):
        volume[i:i+10] *= 5.0  # 5x volume spike

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': price * 0.99,
        'high': price * 1.01,
        'low': price * 0.98,
        'close': price,
        'volume': volume,
    })

    return {"TEST": df, "SPY": df.copy()}


def test_scanner(scanner_type: ScannerType):
    """Test a specific scanner and print diagnostic info."""
    print(f"\n{'='*80}")
    print(f"TESTING: {scanner_type.value.upper()}")
    print(f"{'='*80}\n")

    # Generate test data
    stock_data = generate_simple_test_data()
    test_df = stock_data["TEST"]

    print(f"Test data stats:")
    print(f"  Bars: {len(test_df)}")
    print(f"  Price range: ${test_df['close'].min():.2f} - ${test_df['close'].max():.2f}")
    print(f"  Price change: {((test_df['close'].iloc[-1] - test_df['close'].iloc[0]) / test_df['close'].iloc[0] * 100):+.2f}%")
    print(f"  Volume range: {test_df['volume'].min():,.0f} - {test_df['volume'].max():,.0f}")
    print(f"  Volume spike: {(test_df['volume'].max() / test_df['volume'].min()):.1f}x")
    print()

    # Create scanner
    scanner = StockScanner(scanner_type=scanner_type, max_stocks=5)

    # Create adaptive selector
    adaptive_selector = AdaptiveStrategySelector()

    # Test detect_setups first
    print("Step 1: Testing setup detection...")
    setups = adaptive_selector.detect_setups(test_df)
    print(f"  Setups found: {len(setups)}")

    if not setups:
        print("  ❌ NO SETUPS FOUND!")
        print("  This is why scanner returns no results.")
        print("  Issue: Strategy detector not finding any trade opportunities.")
        return

    print(f"  ✓ Found {len(setups)} setups")
    print(f"  First setup: {setups[0]}")
    print()

    # Test scanner metrics calculation
    print("Step 2: Testing scanner metric calculations...")

    # Price change
    price_change = scanner._calculate_price_change(test_df, periods=20)
    print(f"  Price change (20-bar): {price_change:+.2f}%")

    # Volume ratio
    volume_ratio = scanner._calculate_volume_ratio(test_df)
    print(f"  Volume ratio (peak in last 20 bars): {volume_ratio:.2f}x")
    print()

    # Test scanner-specific scoring
    print("Step 3: Testing scanner-specific scoring...")

    if scanner_type == ScannerType.TOP_MOVERS:
        score, reason = scanner._score_top_movers(price_change, volume_ratio, setups)
        print(f"  TOP_MOVERS scoring:")
        print(f"    Requires: abs(price_change) >= 1.0% AND volume_ratio >= 1.5")
        print(f"    Got: price_change = {price_change:+.2f}%, volume_ratio = {volume_ratio:.2f}x")
        print(f"    Score: {score}")
        print(f"    Reason: {reason}")

        if score == 0:
            print(f"  ❌ REJECTED!")
            if abs(price_change) < 1.0:
                print(f"    Problem: Price change {abs(price_change):.2f}% < 1.0% threshold")
            if volume_ratio < 1.5:
                print(f"    Problem: Volume ratio {volume_ratio:.2f}x < 1.5x threshold")

    elif scanner_type == ScannerType.HIGH_VOLUME:
        score, reason = scanner._score_high_volume(volume_ratio, setups)
        print(f"  HIGH_VOLUME scoring:")
        print(f"    Requires: volume_ratio >= 1.5")
        print(f"    Got: volume_ratio = {volume_ratio:.2f}x")
        print(f"    Score: {score}")
        print(f"    Reason: {reason}")

        if score == 0:
            print(f"  ❌ REJECTED!")
            print(f"    Problem: Volume ratio {volume_ratio:.2f}x < 1.5x threshold")

    elif scanner_type == ScannerType.GAP_SCANNER:
        score, reason = scanner._score_gap(test_df, setups)
        print(f"  GAP_SCANNER scoring:")
        print(f"    Requires: abs(gap) >= 1.0%")
        print(f"    Gap = (current_open - previous_close) / previous_close * 100")

        if len(test_df) >= 2:
            current_open = test_df['open'].iloc[-1]
            previous_close = test_df['close'].iloc[-2]
            gap_pct = (current_open - previous_close) / previous_close * 100
            print(f"    Got: gap = {gap_pct:+.4f}%")

        print(f"    Score: {score}")
        print(f"    Reason: {reason}")

        if score == 0:
            print(f"  ❌ REJECTED!")
            print(f"    Problem: Gaps don't exist in continuous intraday data!")
            print(f"    Each 5-min bar follows smoothly from previous bar.")

    print()

    # Full scan test
    print("Step 4: Running full scan...")
    results = scanner.scan_stocks(
        stock_data=stock_data,
        adaptive_selector=adaptive_selector,
        benchmark_data=stock_data.get("SPY"),
    )

    print(f"  Stocks selected: {len(results)}")

    if results:
        print(f"  ✓ Scanner working!")
        for r in results:
            print(f"    {r.symbol}: score={r.score:.1f}, setups={r.setup_count}, reason={r.reason}")
    else:
        print(f"  ❌ NO STOCKS SELECTED!")

    print()


if __name__ == "__main__":
    print("="*80)
    print("SCANNER DIAGNOSTIC TOOL")
    print("="*80)

    # Test the scanners that failed
    print("\nTesting scanners that generated 0 trades:")

    test_scanner(ScannerType.TOP_MOVERS)
    test_scanner(ScannerType.HIGH_VOLUME)
    test_scanner(ScannerType.GAP_SCANNER)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print("Expected issues:")
    print("1. GAP_SCANNER - Cannot detect gaps in continuous intraday data")
    print("2. TOP_MOVERS/HIGH_VOLUME - Volume ratio calculation issue")
    print("3. Possible: Setup detection not finding opportunities")
    print()
