#!/usr/bin/env python3
"""
GamblerAI Comprehensive Analysis Runner

Runs multiple types of backtesting analyses:
1. Month-by-month comparison (12 months, all strategies)
2. Multi-timeframe comparison (6 timeframes, all strategies)
3. Custom date range analysis
4. Quick performance summary
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                        GAMBLERAI ANALYSIS SUITE                              ║
║                                                                              ║
║          Comprehensive Backtesting & Strategy Comparison System              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Available Analyses:
  1. Monthly Comparison    - Test all strategies month-by-month for 2024
  2. Timeframe Comparison  - Test all strategies across different bar sizes
  3. Combined Analysis     - Run both monthly and timeframe analyses
  4. Quick Summary         - Fast overview of all strategies
  5. Adaptive Strategy     - Test adaptive regime-based strategy selection
  6. Bear Market Test      - Test strategies in 2022-style bear market

"""
    print(banner)


def run_monthly_analysis():
    """Run month-by-month comparison"""
    print("\n" + "="*80)
    print("RUNNING MONTHLY ANALYSIS")
    print("="*80 + "\n")

    from backtest_monthly_comparison import create_monthly_comparison_table, create_dollar_comparison_table

    print("This will test all 5 strategies across 12 months of 2024...")
    print("Estimated time: 2-3 minutes\n")

    # Run with $100k for percentage analysis
    create_monthly_comparison_table(2024, initial_capital=100000)

    # Run with $10k for dollar tracking
    create_dollar_comparison_table(2024, initial_capital=10000)


def run_timeframe_analysis():
    """Run multi-timeframe comparison"""
    print("\n" + "="*80)
    print("RUNNING TIMEFRAME ANALYSIS")
    print("="*80 + "\n")

    from backtest_timeframe_comparison import create_timeframe_comparison_table, create_timeframe_heatmap

    print("This will test all 5 strategies across 6 different timeframes...")
    print("Timeframes: 1-min, 2-min, 5-min, 15-min, 1-hour, Daily")
    print("Estimated time: 3-4 minutes\n")

    create_timeframe_comparison_table()
    create_timeframe_heatmap()


def run_quick_summary():
    """Run quick performance summary"""
    print("\n" + "="*80)
    print("QUICK STRATEGY SUMMARY")
    print("="*80 + "\n")

    from backtest_10k_detailed import run_all_strategies_detailed

    print("Running fast comparison with $10,000 starting capital...")
    print("Using 5-minute bars over 60 days\n")

    run_all_strategies_detailed()


def run_combined_analysis():
    """Run both monthly and timeframe analyses"""
    print("\n" + "="*80)
    print("RUNNING COMBINED ANALYSIS")
    print("="*80 + "\n")

    print("This will run:")
    print("  1. Monthly comparison (12 months)")
    print("  2. Timeframe comparison (6 timeframes)")
    print("Estimated total time: 5-7 minutes\n")

    input("Press Enter to start, or Ctrl+C to cancel...")

    run_monthly_analysis()
    run_timeframe_analysis()


def run_adaptive_analysis():
    """Run adaptive strategy comparison"""
    print("\n" + "="*80)
    print("RUNNING ADAPTIVE STRATEGY ANALYSIS")
    print("="*80 + "\n")

    print("This will test adaptive regime-based strategy selection")
    print("Compares static strategies vs auto-switching adaptive approach")
    print("Estimated time: 2-3 minutes\n")

    import subprocess
    result = subprocess.run(['python', 'backtest_adaptive.py'], capture_output=False)


def run_bear_market_analysis():
    """Run bear market test"""
    print("\n" + "="*80)
    print("RUNNING BEAR MARKET ANALYSIS")
    print("="*80 + "\n")

    print("This will test all strategies in 2022-style bear market")
    print("Market decline: -40% over 12 months")
    print("Estimated time: 2-3 minutes\n")

    import subprocess
    result = subprocess.run(['python', 'backtest_bear_market.py'], capture_output=False)


def print_menu():
    """Interactive menu"""
    print("\nSelect analysis type:")
    print("  1 - Monthly Comparison")
    print("  2 - Timeframe Comparison")
    print("  3 - Combined Analysis (Monthly + Timeframe)")
    print("  4 - Quick Summary")
    print("  5 - Adaptive Strategy Test")
    print("  6 - Bear Market Test")
    print("  7 - Exit")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='GamblerAI Comprehensive Analysis Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_comprehensive_analysis.py --monthly
  python run_comprehensive_analysis.py --timeframe
  python run_comprehensive_analysis.py --combined
  python run_comprehensive_analysis.py --quick
  python run_comprehensive_analysis.py  (interactive mode)
        """
    )

    parser.add_argument('--monthly', action='store_true',
                        help='Run month-by-month comparison')
    parser.add_argument('--timeframe', action='store_true',
                        help='Run multi-timeframe comparison')
    parser.add_argument('--combined', action='store_true',
                        help='Run combined analysis')
    parser.add_argument('--quick', action='store_true',
                        help='Run quick summary')
    parser.add_argument('--adaptive', action='store_true',
                        help='Run adaptive strategy test')
    parser.add_argument('--bear', action='store_true',
                        help='Run bear market test')

    args = parser.parse_args()

    print_banner()

    # Command-line mode
    if args.monthly:
        run_monthly_analysis()
        return
    elif args.timeframe:
        run_timeframe_analysis()
        return
    elif args.combined:
        run_combined_analysis()
        return
    elif args.quick:
        run_quick_summary()
        return
    elif args.adaptive:
        run_adaptive_analysis()
        return
    elif args.bear:
        run_bear_market_analysis()
        return

    # Interactive mode
    while True:
        print_menu()

        try:
            choice = input("Enter choice (1-7): ").strip()

            if choice == '1':
                run_monthly_analysis()
            elif choice == '2':
                run_timeframe_analysis()
            elif choice == '3':
                run_combined_analysis()
            elif choice == '4':
                run_quick_summary()
            elif choice == '5':
                run_adaptive_analysis()
            elif choice == '6':
                run_bear_market_analysis()
            elif choice == '7':
                print("\n👋 Goodbye!\n")
                break
            else:
                print("\n❌ Invalid choice. Please enter 1-7.\n")

            print("\n" + "="*80)
            print("Analysis complete!")
            print("="*80 + "\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
