#!/usr/bin/env python3
"""
Demonstration script for new simulation features:
1. Execution slippage - XX% of time order executes at next bar
2. Configurable profit/loss targets - User-defined % gain/loss

This script shows how to configure and use these features in backtesting.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.backtesting.performance import PerformanceMetrics
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


def demo_basic_slippage():
    """
    Demo 1: Basic slippage configuration
    30% of the time, orders execute at the next bar instead of current bar
    """
    print("\n" + "="*80)
    print("DEMO 1: Basic Execution Slippage")
    print("="*80)
    print("Configuration: 30% of orders execute at next bar (slippage)")
    print()

    # Create backtest engine with slippage enabled
    engine = BacktestEngine(
        initial_capital=100000.0,
        slippage_enabled=True,
        slippage_probability=0.3,  # 30% of time
        slippage_delay_bars=1,     # Delay by 1 bar
        stop_loss_pct=1.0,         # 1% stop loss
        take_profit_pct=2.0,       # 2% take profit
        use_percentage_targets=True,
    )

    print(f"✓ Slippage enabled: {engine.slippage_enabled}")
    print(f"✓ Slippage probability: {engine.slippage_probability * 100}%")
    print(f"✓ Slippage delay: {engine.slippage_delay_bars} bar(s)")
    print(f"✓ Stop loss: {engine.stop_loss_pct}%")
    print(f"✓ Take profit: {engine.take_profit_pct}%")


def demo_custom_profit_loss_targets():
    """
    Demo 2: Custom profit/loss targets
    User can configure different % for gains and losses
    """
    print("\n" + "="*80)
    print("DEMO 2: Custom Profit/Loss Targets")
    print("="*80)
    print("Configuration: 1% loss, 3% gain targets")
    print()

    # Create backtest engine with custom targets
    engine = BacktestEngine(
        initial_capital=100000.0,
        stop_loss_pct=1.0,          # 1% stop loss
        take_profit_pct=3.0,        # 3% take profit
        use_percentage_targets=True,
    )

    # Example: LONG trade at $100
    entry_price = 100.0
    stop_loss = entry_price * (1 - engine.stop_loss_pct / 100)
    target = entry_price * (1 + engine.take_profit_pct / 100)

    print(f"Example LONG trade at ${entry_price:.2f}:")
    print(f"  • Stop Loss: ${stop_loss:.2f} ({engine.stop_loss_pct}% loss)")
    print(f"  • Target: ${target:.2f} ({engine.take_profit_pct}% gain)")
    print(f"  • Risk/Reward Ratio: 1:{engine.take_profit_pct/engine.stop_loss_pct:.1f}")
    print()

    # Example: SHORT trade at $100
    stop_loss_short = entry_price * (1 + engine.stop_loss_pct / 100)
    target_short = entry_price * (1 - engine.take_profit_pct / 100)

    print(f"Example SHORT trade at ${entry_price:.2f}:")
    print(f"  • Stop Loss: ${stop_loss_short:.2f} ({engine.stop_loss_pct}% loss)")
    print(f"  • Target: ${target_short:.2f} ({engine.take_profit_pct}% gain)")


def demo_aggressive_vs_conservative():
    """
    Demo 3: Compare aggressive vs conservative settings
    """
    print("\n" + "="*80)
    print("DEMO 3: Aggressive vs Conservative Configurations")
    print("="*80)
    print()

    # Aggressive: Higher risk/reward, more slippage
    print("Aggressive Configuration:")
    aggressive = BacktestEngine(
        initial_capital=100000.0,
        slippage_enabled=True,
        slippage_probability=0.5,  # 50% slippage
        slippage_delay_bars=2,     # 2 bar delay
        stop_loss_pct=2.0,         # 2% stop
        take_profit_pct=6.0,       # 6% target
        use_percentage_targets=True,
    )
    print(f"  • Slippage: {aggressive.slippage_probability * 100}% chance, {aggressive.slippage_delay_bars} bars")
    print(f"  • Stop Loss: {aggressive.stop_loss_pct}%")
    print(f"  • Take Profit: {aggressive.take_profit_pct}%")
    print(f"  • Risk/Reward: 1:{aggressive.take_profit_pct/aggressive.stop_loss_pct:.1f}")
    print()

    # Conservative: Lower risk/reward, less slippage
    print("Conservative Configuration:")
    conservative = BacktestEngine(
        initial_capital=100000.0,
        slippage_enabled=True,
        slippage_probability=0.2,  # 20% slippage
        slippage_delay_bars=1,     # 1 bar delay
        stop_loss_pct=0.5,         # 0.5% stop
        take_profit_pct=1.0,       # 1% target
        use_percentage_targets=True,
    )
    print(f"  • Slippage: {conservative.slippage_probability * 100}% chance, {conservative.slippage_delay_bars} bar")
    print(f"  • Stop Loss: {conservative.stop_loss_pct}%")
    print(f"  • Take Profit: {conservative.take_profit_pct}%")
    print(f"  • Risk/Reward: 1:{conservative.take_profit_pct/conservative.stop_loss_pct:.1f}")


def demo_configuration_from_yaml():
    """
    Demo 4: Loading configuration from config.yaml
    """
    print("\n" + "="*80)
    print("DEMO 4: Configuration from config.yaml")
    print("="*80)
    print()

    import yaml

    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        backtest_config = config.get('backtest', {})
        slippage_config = backtest_config.get('execution_slippage', {})
        target_config = backtest_config.get('profit_loss_targets', {})

        print("Configuration loaded from config.yaml:")
        print()
        print("Execution Slippage:")
        print(f"  • Enabled: {slippage_config.get('enabled', False)}")
        print(f"  • Probability: {slippage_config.get('probability', 0) * 100}%")
        print(f"  • Delay Bars: {slippage_config.get('delay_bars', 1)}")
        print()
        print("Profit/Loss Targets:")
        print(f"  • Use Percentage Targets: {target_config.get('use_percentage_targets', False)}")
        print(f"  • Stop Loss: {target_config.get('stop_loss_pct', 1.0)}%")
        print(f"  • Take Profit: {target_config.get('take_profit_pct', 2.0)}%")
        print()

        # Create engine from config
        engine = BacktestEngine(
            initial_capital=100000.0,
            slippage_enabled=slippage_config.get('enabled', True),
            slippage_probability=slippage_config.get('probability', 0.3),
            slippage_delay_bars=slippage_config.get('delay_bars', 1),
            stop_loss_pct=target_config.get('stop_loss_pct', 1.0),
            take_profit_pct=target_config.get('take_profit_pct', 2.0),
            use_percentage_targets=target_config.get('use_percentage_targets', True),
        )

        print("✓ Backtest engine created with config.yaml settings")
    else:
        print("⚠ config.yaml not found")


def main():
    """Run all demonstrations"""
    print("\n")
    print("="*80)
    print("GAMBLER AI - NEW SIMULATION FEATURES DEMONSTRATION")
    print("="*80)
    print()
    print("This script demonstrates two new simulation features:")
    print("1. Execution Slippage: Orders execute at next bar XX% of time")
    print("2. Configurable Targets: Custom % for stop loss and take profit")

    # Run demos
    demo_basic_slippage()
    demo_custom_profit_loss_targets()
    demo_aggressive_vs_conservative()
    demo_configuration_from_yaml()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print()
    print("Key Features:")
    print("✓ Execution slippage simulates real-world order delays")
    print("✓ Configurable probability (XX% of orders affected)")
    print("✓ Configurable delay (1, 2, or more bars)")
    print("✓ User-defined profit/loss targets (e.g., 1% loss, 2% gain)")
    print("✓ Easy configuration via config.yaml or code")
    print()
    print("To use these features in your backtests:")
    print("1. Edit config.yaml to set your preferred values")
    print("2. Or pass parameters directly to BacktestEngine()")
    print("3. Run your backtest as usual - slippage and targets will be applied")
    print()
    print("="*80)


if __name__ == "__main__":
    main()
