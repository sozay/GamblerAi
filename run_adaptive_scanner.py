#!/usr/bin/env python3
"""
Run Adaptive Scanner Trading System

This is the MAIN entry point for running the adaptive strategy with stock scanner.

Combines:
1. TOP_MOVERS scanner (selects best stocks)
2. Adaptive strategy selection (auto-switches based on regime)
3. Volatility-adjusted filtering (prevents losses in choppy markets)

Usage:
    python run_adaptive_scanner.py
    python run_adaptive_scanner.py --duration 120 --scan-interval 60
    python run_adaptive_scanner.py --scanner high_volume --max-stocks 5

Configuration:
    Edit config.yaml to change:
    - scanner.type (top_movers, high_volume, etc.)
    - scanner.max_stocks (how many stocks to trade)
    - adaptive_strategy.use_volatility_filter (enable/disable)
"""

import argparse
import os
import sys
import yaml
from pathlib import Path

from gambler_ai.live.scanner_runner import LiveScannerRunner, create_live_scanner
from gambler_ai.live.adaptive_trader import AdaptiveTrader
from gambler_ai.analysis.stock_scanner import ScannerType


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent / "config.yaml"

    if not config_path.exists():
        print(f"⚠ Config file not found: {config_path}")
        return {}

    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Adaptive Scanner Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (from config.yaml)
  python run_adaptive_scanner.py

  # Run for 2 hours, scan every minute
  python run_adaptive_scanner.py --duration 120 --scan-interval 60

  # Use high_volume scanner with 5 stocks
  python run_adaptive_scanner.py --scanner high_volume --max-stocks 5

  # Disable volatility filter
  python run_adaptive_scanner.py --no-volatility-filter

  # Re-scan stocks every 30 minutes
  python run_adaptive_scanner.py --rescan 30

Scanner Types:
  - top_movers (WINNER: +39% vs SPY) 🏆
  - high_volume
  - volatility_range
  - best_setups
  - market_cap_weighted
  - relative_strength
        """
    )

    # API credentials
    parser.add_argument("--api-key", help="Alpaca API Key (or set ALPACA_API_KEY env var)")
    parser.add_argument("--api-secret", help="Alpaca API Secret (or set ALPACA_API_SECRET env var)")

    # Scanner options
    parser.add_argument("--scanner", help="Scanner type (default: from config.yaml)")
    parser.add_argument("--max-stocks", type=int, help="Maximum stocks to select")
    parser.add_argument("--universe", help="Stock universe (liquid, tech, volatile, etc.)")

    # Trading session options
    parser.add_argument("--duration", type=int, help="Duration in minutes (default: 60)")
    parser.add_argument("--scan-interval", type=int, help="Scan interval in seconds (default: 60)")
    parser.add_argument("--rescan", type=int, help="Re-scan stocks every N minutes (default: 0 = once)")

    # Strategy options
    parser.add_argument("--no-volatility-filter", action="store_true", help="Disable volatility filter")
    parser.add_argument("--risk-per-trade", type=float, help="Risk per trade % (default: 1.0)")
    parser.add_argument("--stop-loss", type=float, help="Stop loss % (default: 1.0)")
    parser.add_argument("--take-profit", type=float, help="Take profit % (default: 3.0)")

    # Modes
    parser.add_argument("--scan-only", action="store_true", help="Only run scanner, don't trade")
    parser.add_argument("--test-connection", action="store_true", help="Test API connection and exit")

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Get API credentials
    api_key = args.api_key or os.environ.get('ALPACA_API_KEY')
    api_secret = args.api_secret or os.environ.get('ALPACA_API_SECRET')

    # Try to get from config if not provided
    if not api_key and config.get('data_sources', {}).get('alpaca', {}).get('api_key'):
        api_key = config['data_sources']['alpaca']['api_key']
    if not api_secret and config.get('data_sources', {}).get('alpaca', {}).get('api_secret'):
        api_secret = config['data_sources']['alpaca']['api_secret']

    if not api_key or not api_secret:
        print("ERROR: Alpaca API credentials required!")
        print("\nOptions:")
        print("1. Set environment variables:")
        print("   export ALPACA_API_KEY='your_key'")
        print("   export ALPACA_API_SECRET='your_secret'")
        print("\n2. Pass as arguments:")
        print("   --api-key YOUR_KEY --api-secret YOUR_SECRET")
        print("\n3. Add to config.yaml under data_sources.alpaca")
        print("\n4. Get free paper trading account:")
        print("   https://alpaca.markets (sign up for paper trading)")
        return 1

    # Get scanner settings from config or args
    scanner_config = config.get('scanner', {})
    scanner_type = args.scanner or scanner_config.get('type', 'top_movers')
    max_stocks = args.max_stocks or scanner_config.get('max_stocks', 3)
    universe = args.universe or scanner_config.get('universe', 'liquid')

    # Get adaptive strategy settings
    adaptive_config = config.get('adaptive_strategy', {})
    use_volatility_filter = not args.no_volatility_filter

    # Get trading parameters
    duration = args.duration or 60
    scan_interval = args.scan_interval or 60
    rescan_minutes = args.rescan or scanner_config.get('scan_frequency_minutes', 0)
    risk_per_trade = args.risk_per_trade or 0.01
    stop_loss = args.stop_loss or 1.0
    take_profit = args.take_profit or 3.0

    print("\n" + "=" * 80)
    print("ADAPTIVE SCANNER TRADING SYSTEM")
    print("=" * 80)
    print(f"\n📊 Scanner: {scanner_type.upper()}")
    print(f"  Max Stocks: {max_stocks}")
    print(f"  Universe: {universe}")

    print(f"\n🤖 Adaptive Strategy:")
    print(f"  Volatility Filter: {'✓ ENABLED' if use_volatility_filter else '✗ DISABLED'}")
    print(f"  Risk per Trade: {risk_per_trade*100}%")
    print(f"  Stop Loss: {stop_loss}% | Take Profit: {take_profit}%")

    print(f"\n⏱️  Session:")
    print(f"  Duration: {duration} minutes")
    print(f"  Scan Interval: {scan_interval} seconds")
    if rescan_minutes > 0:
        print(f"  Re-scan Stocks: Every {rescan_minutes} minutes")
    else:
        print(f"  Re-scan Stocks: Once at start")

    print("=" * 80 + "\n")

    # Test connection
    if args.test_connection:
        print("Testing Alpaca connection...")
        try:
            scanner = create_live_scanner(
                api_key=api_key,
                api_secret=api_secret,
                scanner_type=scanner_type,
                max_stocks=1,
                universe=universe,
            )
            print("\n✓ Connection successful!")
            print("  You can now run the full trading system.")
            return 0
        except Exception as e:
            print(f"\n✗ Connection failed: {e}")
            return 1

    # Create scanner
    print("Initializing scanner...")
    try:
        scanner = create_live_scanner(
            api_key=api_key,
            api_secret=api_secret,
            scanner_type=scanner_type,
            max_stocks=max_stocks,
            universe=universe,
        )
    except Exception as e:
        print(f"✗ Failed to create scanner: {e}")
        return 1

    # Scan-only mode
    if args.scan_only:
        print("\n🔍 Running scanner (scan-only mode)...\n")
        try:
            results = scanner.scan_market()
            if results:
                print(f"\n✓ Found {len(results)} trading opportunities")
                print("\nTo start trading, run without --scan-only flag")
            else:
                print("\n⚠ No opportunities found")
            return 0
        except Exception as e:
            print(f"✗ Scanner failed: {e}")
            return 1

    # Create adaptive trader
    print("Initializing adaptive trader...")
    try:
        trader = AdaptiveTrader(
            api_key=api_key,
            api_secret=api_secret,
            scanner=scanner,
            use_volatility_filter=use_volatility_filter,
            risk_per_trade=risk_per_trade,
            stop_loss_pct=stop_loss,
            take_profit_pct=take_profit,
        )
    except Exception as e:
        print(f"✗ Failed to create trader: {e}")
        return 1

    print("\n✓ System ready!")
    print("\nPress CTRL+C to stop at any time.")
    input("\nPress ENTER to start trading...")

    # Run trading session
    try:
        trader.run_trading_session(
            duration_minutes=duration,
            scan_interval_seconds=scan_interval,
            rescan_stocks_minutes=rescan_minutes,
        )
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠ Trading session interrupted by user")
        return 0
    except Exception as e:
        print(f"\n✗ Trading session failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
