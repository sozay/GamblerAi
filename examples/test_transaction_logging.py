#!/usr/bin/env python3
"""
Example script demonstrating transaction logging functionality.

This script shows how to:
1. Initialize the TransactionLogger
2. Log trade entries and exits
3. Query logged transactions
4. Use the logger with TradeManager
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gambler_ai.backtesting.trade import TradeManager, TradeDirection
from gambler_ai.utils.transaction_logger import TransactionLogger
from gambler_ai.storage.database import DatabaseManager


def example_basic_logging():
    """Example 1: Basic transaction logging without TradeManager."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Transaction Logging")
    print("="*80 + "\n")

    # Initialize logger
    logger = TransactionLogger(trading_mode="backtest")

    # Log a trade entry
    print("Logging trade entry...")
    entry_time = datetime.now()
    transaction_id = logger.log_trade_entry(
        symbol="AAPL",
        direction="LONG",
        entry_time=entry_time,
        entry_price=150.50,
        position_size=100,
        stop_loss=147.00,
        target=156.00,
        strategy_name="momentum_up",
    )
    print(f"✓ Trade entry logged with ID: {transaction_id}")

    # Simulate some time passing
    print("\nSimulating trade duration...")

    # Log trade exit
    print("Logging trade exit...")
    exit_time = entry_time + timedelta(minutes=45)
    logger.log_trade_exit(
        transaction_id=transaction_id,
        exit_time=exit_time,
        exit_price=156.00,
        exit_reason="target",
        pnl=550.00,
        pnl_pct=3.65,
        return_pct=3.65,
        max_adverse_excursion=-0.5,
        max_favorable_excursion=4.2,
    )
    print("✓ Trade exit logged")

    # Query transactions
    print("\nQuerying logged transactions...")
    transactions = logger.get_all_transactions()
    print(f"Total transactions: {len(transactions)}")
    for txn in transactions[:5]:  # Show first 5
        print(f"  {txn.symbol} {txn.direction} @ {txn.entry_price} | "
              f"Status: {txn.status} | P&L: ${txn.pnl if txn.pnl else 'N/A'}")


def example_trademanager_integration():
    """Example 2: Using TransactionLogger with TradeManager."""
    print("\n" + "="*80)
    print("EXAMPLE 2: TradeManager Integration")
    print("="*80 + "\n")

    # Initialize logger
    logger = TransactionLogger(trading_mode="backtest")

    # Initialize TradeManager with logger
    trade_manager = TradeManager(
        initial_capital=100000.0,
        risk_per_trade=0.01,
        transaction_logger=logger,
    )

    print(f"Initial Capital: ${trade_manager.current_capital:,.2f}\n")

    # Open some trades
    print("Opening trades...")

    trade1 = trade_manager.open_trade(
        symbol="TSLA",
        direction=TradeDirection.LONG,
        entry_time=datetime.now(),
        entry_price=250.00,
        stop_loss=245.00,
        target=260.00,
        strategy_name="momentum_breakout",
    )
    print(f"✓ Opened {trade1.symbol} trade (ID: {trade1.transaction_id})")

    trade2 = trade_manager.open_trade(
        symbol="NVDA",
        direction=TradeDirection.LONG,
        entry_time=datetime.now(),
        entry_price=480.00,
        stop_loss=470.00,
        target=500.00,
        strategy_name="momentum_breakout",
    )
    print(f"✓ Opened {trade2.symbol} trade (ID: {trade2.transaction_id})")

    print(f"\nOpen trades: {len(trade_manager.open_trades)}")

    # Simulate trade exits
    print("\nClosing trades...")

    # Close trade 1 at target
    trade1.close(
        exit_time=datetime.now() + timedelta(minutes=30),
        exit_price=260.00,
        reason="target",
    )
    trade_manager.close_trade(trade1)
    print(f"✓ Closed {trade1.symbol} at target (P&L: ${trade1.pnl:.2f})")

    # Close trade 2 at stop loss
    trade2.close(
        exit_time=datetime.now() + timedelta(minutes=15),
        exit_price=470.00,
        reason="stop_loss",
    )
    trade_manager.close_trade(trade2)
    print(f"✓ Closed {trade2.symbol} at stop loss (P&L: ${trade2.pnl:.2f})")

    # Show results
    print(f"\nFinal Capital: ${trade_manager.current_capital:,.2f}")
    print(f"Total P&L: ${trade_manager.get_total_pnl():,.2f}")
    print(f"Return: {trade_manager.get_total_return_pct():.2f}%")

    # Query transactions
    print("\nQuerying transactions by strategy...")
    momentum_trades = logger.get_transactions_by_strategy("momentum_breakout")
    print(f"Momentum breakout trades: {len(momentum_trades)}")


def example_query_transactions():
    """Example 3: Querying and analyzing logged transactions."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Querying Transactions")
    print("="*80 + "\n")

    logger = TransactionLogger()

    # Get all transactions
    all_txns = logger.get_all_transactions()
    print(f"Total transactions: {len(all_txns)}")

    # Get only open positions
    open_txns = logger.get_all_transactions(status="OPEN")
    print(f"Open positions: {len(open_txns)}")

    # Get only closed trades
    closed_txns = logger.get_all_transactions(status="CLOSED")
    print(f"Closed trades: {len(closed_txns)}")

    if closed_txns:
        # Calculate statistics
        total_pnl = sum(float(t.pnl) for t in closed_txns if t.pnl)
        winning_trades = [t for t in closed_txns if t.pnl and float(t.pnl) > 0]
        win_rate = len(winning_trades) / len(closed_txns) * 100

        print(f"\nStatistics:")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Winning Trades: {len(winning_trades)}")
        print(f"  Losing Trades: {len(closed_txns) - len(winning_trades)}")

    # Get transactions by symbol
    print("\nTransactions by symbol:")
    symbols = set(t.symbol for t in all_txns)
    for symbol in list(symbols)[:5]:  # Show first 5 symbols
        symbol_txns = logger.get_transactions_by_symbol(symbol)
        print(f"  {symbol}: {len(symbol_txns)} trades")


def example_file_output():
    """Example 4: Check CSV and JSON file output."""
    print("\n" + "="*80)
    print("EXAMPLE 4: File Output Locations")
    print("="*80 + "\n")

    logger = TransactionLogger()

    print("Transaction logs are saved to:")
    print(f"  CSV:  {logger.csv_path}")
    print(f"  JSON: {logger.json_path}")

    # Check if files exist
    if os.path.exists(logger.csv_path):
        size = os.path.getsize(logger.csv_path)
        print(f"\n✓ CSV file exists ({size:,} bytes)")
        print(f"  You can open it in Excel or any spreadsheet software")

    if os.path.exists(logger.json_path):
        size = os.path.getsize(logger.json_path)
        print(f"\n✓ JSON file exists ({size:,} bytes)")
        print(f"  You can process it with jq or any JSON tool")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TRANSACTION LOGGING EXAMPLES" + " "*30 + "║")
    print("╚" + "="*78 + "╝")

    # Run examples
    example_basic_logging()
    example_trademanager_integration()
    example_query_transactions()
    example_file_output()

    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
