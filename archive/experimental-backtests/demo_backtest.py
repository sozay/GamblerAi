"""
Demonstration of backtesting framework with sample data.

This script demonstrates the backtesting capabilities without requiring
a full database setup. It uses synthetic price data to show how the
system would work with real historical data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Setup basic imports
import sys
sys.path.insert(0, '/home/user/GamblerAi')

from gambler_ai.backtesting.trade import Trade, TradeDirection, TradeManager
from gambler_ai.backtesting.performance import PerformanceMetrics


def generate_sample_trades(num_trades=50):
    """
    Generate sample trades to demonstrate performance metrics.

    Simulates a momentum trading strategy with realistic win rate (~60%)
    and risk/reward characteristics.
    """
    print("Generating sample trades...")

    trades = []
    current_time = datetime(2024, 1, 1, 9, 30)

    # Simulate 50 trades
    for i in range(num_trades):
        # Random entry price around $150
        entry_price = 150 + np.random.uniform(-10, 10)

        # Direction
        direction = TradeDirection.LONG if np.random.random() > 0.5 else TradeDirection.SHORT

        # Position size
        position_size = np.random.uniform(50, 200)

        # Create trade
        trade = Trade(
            symbol="DEMO",
            direction=direction,
            entry_time=current_time,
            entry_price=entry_price,
            position_size=position_size,
            strategy_name="momentum",
        )

        # Simulate trade outcome
        # 60% win rate
        is_winner = np.random.random() < 0.60

        # Exit after 15-60 minutes
        duration_minutes = np.random.uniform(15, 60)
        exit_time = current_time + timedelta(minutes=duration_minutes)

        if is_winner:
            # Winners: 1-3% profit
            profit_pct = np.random.uniform(1.0, 3.0)
            if direction == TradeDirection.LONG:
                exit_price = entry_price * (1 + profit_pct/100)
            else:
                exit_price = entry_price * (1 - profit_pct/100)

            # Update excursions for winners
            trade.max_favorable_excursion = profit_pct * 1.2  # Peak is a bit higher
            trade.max_adverse_excursion = -np.random.uniform(0.2, 0.5)  # Small drawdown
        else:
            # Losers: 0.5-1.5% loss (better R:R)
            loss_pct = np.random.uniform(0.5, 1.5)
            if direction == TradeDirection.LONG:
                exit_price = entry_price * (1 - loss_pct/100)
            else:
                exit_price = entry_price * (1 + loss_pct/100)

            # Update excursions for losers
            trade.max_favorable_excursion = np.random.uniform(0.1, 0.5)  # Small profit before loss
            trade.max_adverse_excursion = -loss_pct * 1.1  # Slightly worse than exit

        # Close the trade
        trade.close(exit_time, exit_price, "target" if is_winner else "stop_loss")

        trades.append(trade)

        # Move time forward
        current_time += timedelta(hours=np.random.uniform(1, 4))

    return trades


def demo_backtest_results():
    """Demonstrate backtest results and performance metrics."""

    print("="*80)
    print("GAMBLERAI BACKTESTING FRAMEWORK DEMONSTRATION")
    print("="*80)
    print()
    print("This demonstration shows the backtesting framework capabilities using")
    print("sample trade data. In production, this would analyze real historical")
    print("market data from your database.")
    print()
    print("="*80)
    print()

    # Generate sample trades
    trades = generate_sample_trades(num_trades=50)

    # Calculate capital
    initial_capital = 100000.0
    total_pnl = sum(t.pnl for t in trades)
    final_capital = initial_capital + total_pnl

    print(f"✓ Generated {len(trades)} sample trades")
    print(f"  Initial Capital: ${initial_capital:,.2f}")
    print(f"  Final Capital: ${final_capital:,.2f}")
    print()

    # Create performance metrics
    print("Calculating performance metrics...")
    performance = PerformanceMetrics(
        trades=trades,
        initial_capital=initial_capital,
        final_capital=final_capital,
    )

    # Display full report
    report = performance.generate_report()
    print(report)

    # Show individual trades
    print("\n" + "="*80)
    print("SAMPLE TRADES (First 10)")
    print("="*80)
    print()

    print(f"{'#':<4} {'Time':<20} {'Dir':<6} {'Entry':<10} {'Exit':<10} {'P&L %':<10} {'Reason':<15}")
    print("-"*80)

    for i, trade in enumerate(trades[:10], 1):
        print(
            f"{i:<4} "
            f"{trade.entry_time.strftime('%Y-%m-%d %H:%M'):<20} "
            f"{trade.direction.value:<6} "
            f"${trade.entry_price:<9.2f} "
            f"${trade.exit_price:<9.2f} "
            f"{trade.pnl_pct:>8.2f}% "
            f"{trade.exit_reason:<15}"
        )

    print()
    print("="*80)
    print("FRAMEWORK FEATURES DEMONSTRATED")
    print("="*80)
    print()
    print("✓ Trade Management:")
    print("  - Position sizing based on risk")
    print("  - Stop loss and target tracking")
    print("  - Max adverse/favorable excursion tracking")
    print()
    print("✓ Performance Metrics:")
    print("  - Win rate, profit factor, Sharpe ratio")
    print("  - Drawdown analysis")
    print("  - Risk-adjusted returns")
    print()
    print("✓ Risk Management:")
    print("  - Position sizing per trade")
    print("  - Maximum concurrent trades")
    print("  - Stop loss execution")
    print()
    print("="*80)
    print("NEXT STEPS TO USE WITH REAL DATA")
    print("="*80)
    print()
    print("1. Collect Historical Data:")
    print("   $ gambler-cli collect -s AAPL --start 2024-01-01 --end 2024-12-31")
    print()
    print("2. Run Backtest:")
    print("   $ gambler-cli backtest -s AAPL --start 2024-01-01 --end 2024-12-31")
    print()
    print("3. Compare Multiple Symbols:")
    print("   $ gambler-cli backtest -s MSFT --start 2024-01-01 --end 2024-12-31")
    print()
    print("4. Export Results:")
    print("   $ gambler-cli backtest -s AAPL --start 2024-01-01 --end 2024-12-31 -o results.json")
    print()
    print("="*80)
    print()


if __name__ == "__main__":
    demo_backtest_results()
