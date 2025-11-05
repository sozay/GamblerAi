#!/usr/bin/env python3
"""
Stock Screening Examples

Demonstrates how to use the stock screener to find trading opportunities.
"""

import pandas as pd
from datetime import datetime, timedelta

from gambler_ai.screening import StockScreener, StockRanker
from gambler_ai.analysis.regime_detector import RegimeDetector


def example_momentum_screening():
    """Example: Find momentum stocks."""
    print("\n" + "=" * 60)
    print("Example 1: Momentum Screening")
    print("=" * 60)
    print("Finding stocks with strong upward momentum...")
    print()

    screener = StockScreener()

    # Screen for momentum
    candidates = screener.screen_momentum(
        lookback_days=20,
        min_gain_pct=10.0,  # Gained at least 10%
        top_n=10
    )

    print(f"✓ Found {len(candidates)} momentum candidates:")
    print()

    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. {candidate.symbol:6s} - Score: {candidate.score:6.1f} - ${candidate.price:7.2f}")
        print(f"   {candidate.reason}")
        print()


def example_mean_reversion_screening():
    """Example: Find oversold stocks."""
    print("\n" + "=" * 60)
    print("Example 2: Mean Reversion Screening")
    print("=" * 60)
    print("Finding oversold stocks ready to bounce...")
    print()

    screener = StockScreener()

    # Screen for mean reversion
    candidates = screener.screen_mean_reversion(
        lookback_days=20,
        oversold_threshold=-10.0,  # Down at least 10%
        top_n=10
    )

    print(f"✓ Found {len(candidates)} mean reversion candidates:")
    print()

    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. {candidate.symbol:6s} - Score: {candidate.score:6.1f} - ${candidate.price:7.2f}")
        print(f"   {candidate.reason}")
        print()


def example_breakout_screening():
    """Example: Find breakout candidates."""
    print("\n" + "=" * 60)
    print("Example 3: Breakout Screening")
    print("=" * 60)
    print("Finding stocks breaking out of consolidation...")
    print()

    screener = StockScreener()

    # Screen for breakouts
    candidates = screener.screen_breakout(
        lookback_days=60,
        consolidation_days=20,
        top_n=10
    )

    print(f"✓ Found {len(candidates)} breakout candidates:")
    print()

    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. {candidate.symbol:6s} - Score: {candidate.score:6.1f} - ${candidate.price:7.2f}")
        print(f"   {candidate.reason}")
        print()


def example_volume_surge_screening():
    """Example: Find volume surges."""
    print("\n" + "=" * 60)
    print("Example 4: Volume Surge Screening")
    print("=" * 60)
    print("Finding stocks with unusual volume activity...")
    print()

    screener = StockScreener()

    # Screen for volume surges
    candidates = screener.screen_volume_surge(
        lookback_days=20,
        min_volume_ratio=3.0,  # 3x average volume
        top_n=10
    )

    print(f"✓ Found {len(candidates)} volume surge candidates:")
    print()

    for i, candidate in enumerate(candidates, 1):
        print(f"{i}. {candidate.symbol:6s} - Score: {candidate.score:6.1f} - ${candidate.price:7.2f}")
        print(f"   {candidate.reason}")
        print()


def example_combined_screening():
    """Example: Combine all screening strategies."""
    print("\n" + "=" * 60)
    print("Example 5: Combined Screening")
    print("=" * 60)
    print("Running all screening strategies...")
    print()

    screener = StockScreener()

    # Run all strategies
    results = screener.screen_all(top_n_per_strategy=5)

    print("Results by Strategy:")
    print()

    for strategy, candidates in results.items():
        print(f"\n{strategy.upper()}:")
        print("-" * 40)

        for candidate in candidates:
            print(f"  {candidate.symbol:6s} - {candidate.reason}")

    # Get combined top picks
    print("\n" + "=" * 60)
    print("COMBINED TOP PICKS")
    print("=" * 60)

    top_picks = screener.get_combined_top_picks(top_n=10)

    for i, pick in enumerate(top_picks, 1):
        print(f"\n{i}. {pick.symbol} - ${pick.price:.2f}")
        print(f"   Score: {pick.score:.1f}")
        print(f"   {pick.reason}")


def example_regime_based_ranking():
    """Example: Rank stocks based on market regime."""
    print("\n" + "=" * 60)
    print("Example 6: Regime-Based Ranking")
    print("=" * 60)
    print("Ranking stocks based on current market regime...")
    print()

    screener = StockScreener()
    ranker = StockRanker()

    # Screen all strategies
    results = screener.screen_all(top_n_per_strategy=5)

    # Get SPY data for regime detection
    print("Detecting market regime...")

    # For this example, create synthetic data
    # In real usage, you'd get actual SPY data
    dates = pd.date_range(end=datetime.now(), periods=200, freq='D')
    spy_data = pd.DataFrame({
        'close': [450 + i * 0.5 for i in range(200)],  # Simulated uptrend
    }, index=dates)

    # Rank based on regime
    ranked = ranker.rank_by_regime(results, spy_data)

    print(f"\n✓ Ranked {len(ranked)} stocks:")
    print()

    for i, stock in enumerate(ranked[:10], 1):
        print(f"{i}. {stock.symbol:6s} - Score: {stock.score:6.1f}")
        print(f"   {stock.reason}")
        print()


def example_custom_filtering():
    """Example: Custom filtering of candidates."""
    print("\n" + "=" * 60)
    print("Example 7: Custom Filtering")
    print("=" * 60)
    print("Filtering stocks with custom criteria...")
    print()

    screener = StockScreener(
        min_price=10.0,
        max_price=200.0,
        min_volume=2_000_000,
    )

    ranker = StockRanker()

    # Get all candidates
    candidates = screener.get_combined_top_picks(top_n=20)

    print(f"Before filtering: {len(candidates)} candidates")

    # Apply custom filters
    filtered = ranker.filter_by_criteria(
        candidates,
        min_score=20.0,
        min_volume=2_000_000,
        max_price=200.0,
    )

    print(f"After filtering: {len(filtered)} candidates")
    print()

    for i, stock in enumerate(filtered[:10], 1):
        print(f"{i}. {stock.symbol:6s} - ${stock.price:.2f} - Vol: {stock.volume:,}")
        print(f"   Score: {stock.score:.1f} - {stock.reason}")
        print()


def example_practical_workflow():
    """Example: Complete practical workflow for trading."""
    print("\n" + "=" * 60)
    print("Example 8: Complete Trading Workflow")
    print("=" * 60)
    print("Step-by-step workflow for selecting stocks to trade")
    print()

    # Step 1: Initialize screener
    print("Step 1: Initialize screener...")
    screener = StockScreener(
        min_price=10.0,
        max_price=300.0,
        min_volume=1_000_000,
    )

    # Step 2: Detect market regime
    print("Step 2: Detect market regime...")
    # In practice, get real SPY data
    print("   Regime: BULL market (simulated)")

    # Step 3: Screen for opportunities
    print("\nStep 3: Screen for opportunities...")
    results = screener.screen_all(top_n_per_strategy=3)

    total = sum(len(c) for c in results.values())
    print(f"   Found {total} candidates across 4 strategies")

    # Step 4: Rank and select
    print("\nStep 4: Rank and select top picks...")
    top_picks = screener.get_combined_top_picks(top_n=5)

    print(f"   Selected {len(top_picks)} top picks")

    # Step 5: Show final selections
    print("\nStep 5: Final trading candidates:")
    print("=" * 60)

    for i, pick in enumerate(top_picks, 1):
        print(f"\n{i}. {pick.symbol} - ${pick.price:.2f}")
        print(f"   Score: {pick.score:.1f}")
        print(f"   Strategy: {pick.reason}")
        print(f"   → READY TO TRADE")

    print("\n" + "=" * 60)
    print("Workflow complete! Ready to execute trades.")
    print("=" * 60)


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("STOCK SCREENING EXAMPLES")
    print("=" * 70)
    print("\n⚠️  Note: These examples use simulated data.")
    print("   Real usage requires valid Alpaca API credentials.")
    print()

    examples = [
        ("Momentum Screening", example_momentum_screening),
        ("Mean Reversion Screening", example_mean_reversion_screening),
        ("Breakout Screening", example_breakout_screening),
        ("Volume Surge Screening", example_volume_surge_screening),
        ("Combined Screening", example_combined_screening),
        ("Regime-Based Ranking", example_regime_based_ranking),
        ("Custom Filtering", example_custom_filtering),
        ("Complete Workflow", example_practical_workflow),
    ]

    for name, func in examples:
        try:
            func()
            input(f"\nPress Enter to continue to next example...")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n⚠️  Error in {name}: {e}")
            input("Press Enter to continue...")

    print("\n" + "=" * 70)
    print("All examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
