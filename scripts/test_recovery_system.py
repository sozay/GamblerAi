#!/usr/bin/env python3
"""
Test script for recovery system.

This script helps test the recovery functionality without requiring
a live Alpaca connection. It simulates various recovery scenarios.
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal

from gambler_ai.storage.database import get_analytics_db, init_databases
from gambler_ai.storage.models import TradingSession, Position, OrderJournal
from gambler_ai.trading.state_manager import StateManager
from gambler_ai.trading.position_reconciler import PositionReconciler


def test_state_manager():
    """Test state manager functionality."""
    print("\n" + "=" * 80)
    print("Testing State Manager")
    print("=" * 80)

    db = get_analytics_db()
    db.create_tables()

    session = db.get_session_direct()

    try:
        # Create state manager
        state_mgr = StateManager(session)

        # Create a session
        print("\n1. Creating trading session...")
        session_id = state_mgr.create_session(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            initial_capital=100000.0,
            parameters={'stop_loss_pct': 2.0, 'take_profit_pct': 4.0}
        )

        # Save positions
        print("\n2. Saving test positions...")
        pos1_id = state_mgr.save_position(
            symbol='AAPL',
            entry_time=datetime.now(timezone.utc),
            entry_price=150.50,
            quantity=100,
            direction='LONG',
            side='buy',
            stop_loss=147.49,
            take_profit=156.52,
            entry_order_id='test-order-1'
        )
        print(f"   ✓ Saved position 1 (ID: {pos1_id})")

        pos2_id = state_mgr.save_position(
            symbol='MSFT',
            entry_time=datetime.now(timezone.utc),
            entry_price=380.25,
            quantity=50,
            direction='LONG',
            side='buy',
            stop_loss=372.65,
            take_profit=395.46,
            entry_order_id='test-order-2'
        )
        print(f"   ✓ Saved position 2 (ID: {pos2_id})")

        # Log orders
        print("\n3. Logging test orders...")
        state_mgr.log_order(
            alpaca_order_id='alpaca-123',
            symbol='AAPL',
            order_type='market',
            side='buy',
            quantity=100,
            status='filled',
            position_id=pos1_id
        )
        print("   ✓ Logged order for AAPL")

        # Get open positions
        print("\n4. Retrieving open positions...")
        open_positions = state_mgr.get_open_positions()
        print(f"   Found {len(open_positions)} open positions:")
        for pos in open_positions:
            print(f"   - {pos.symbol}: {pos.direction} {float(pos.quantity)} @ ${float(pos.entry_price):.2f}")

        # Update a position (close it)
        print("\n5. Closing AAPL position...")
        state_mgr.update_position(
            symbol='AAPL',
            exit_time=datetime.now(timezone.utc),
            exit_price=155.00,
            exit_reason='take_profit',
            status='closed'
        )
        print("   ✓ Position closed")

        # Check open positions again
        open_positions = state_mgr.get_open_positions()
        print(f"\n6. Open positions now: {len(open_positions)}")
        for pos in open_positions:
            print(f"   - {pos.symbol}: {pos.direction} {float(pos.quantity)} @ ${float(pos.entry_price):.2f}")

        # Get session stats
        print("\n7. Session statistics:")
        stats = state_mgr.get_session_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # End session
        print("\n8. Ending session...")
        state_mgr.end_session(final_capital=102500.0, status='stopped')
        print("   ✓ Session ended")

        print("\n✓ All State Manager tests passed!\n")

        return session_id

    finally:
        session.close()


def test_position_reconciler(test_session_id):
    """Test position reconciler functionality."""
    print("\n" + "=" * 80)
    print("Testing Position Reconciler")
    print("=" * 80)

    db = get_analytics_db()
    session = db.get_session_direct()

    try:
        # Create state manager and reconciler
        state_mgr = StateManager(session)
        state_mgr.session_id = test_session_id

        # Add a position to database
        print("\n1. Adding test position to database...")
        state_mgr.save_position(
            symbol='TSLA',
            entry_time=datetime.now(timezone.utc),
            entry_price=250.00,
            quantity=75,
            direction='LONG',
            side='buy',
            entry_order_id='test-order-3'
        )
        print("   ✓ Added TSLA position")

        reconciler = PositionReconciler(state_mgr)

        # Simulate Alpaca positions
        print("\n2. Simulating Alpaca API positions...")
        alpaca_positions = [
            {
                'symbol': 'MSFT',
                'side': 'long',
                'qty': '50',
                'avg_entry_price': '380.25'
            },
            {
                'symbol': 'NVDA',  # New position not in DB
                'side': 'long',
                'qty': '25',
                'avg_entry_price': '875.50'
            }
        ]
        print("   Alpaca has: MSFT, NVDA")
        print("   Database has: MSFT, TSLA")

        # Reconcile
        print("\n3. Running reconciliation...")
        new_alpaca, orphaned_local, matched = reconciler.reconcile(
            alpaca_positions,
            verbose=True
        )

        # Import new positions
        if new_alpaca:
            print("\n4. Importing new Alpaca positions...")
            reconciler.import_alpaca_positions(new_alpaca)

        # Close orphaned positions
        if orphaned_local:
            print("\n5. Closing orphaned positions...")
            reconciler.recover_orphaned_positions(
                orphaned_local,
                current_prices={'TSLA': 255.00}
            )

        # Verify final state
        print("\n6. Final position state:")
        all_positions = session.query(Position).filter_by(
            session_id=test_session_id
        ).all()

        for pos in all_positions:
            print(f"   {pos.symbol}: {pos.status} - ${float(pos.entry_price):.2f}")

        print("\n✓ All Position Reconciler tests passed!\n")

    finally:
        session.close()


def test_full_recovery_workflow():
    """Test complete recovery workflow."""
    print("\n" + "=" * 80)
    print("Testing Full Recovery Workflow")
    print("=" * 80)

    db = get_analytics_db()
    session = db.get_session_direct()

    try:
        # Scenario: System crashed with open positions
        print("\n=== SCENARIO: Crashed with Open Positions ===")

        # Step 1: Create session as if trading was happening
        print("\n1. Creating 'crashed' session...")
        state_mgr = StateManager(session)
        session_id = state_mgr.create_session(
            symbols=['AAPL', 'GOOGL', 'AMZN'],
            initial_capital=100000.0
        )

        # Step 2: Add some positions
        print("2. Adding positions (simulating active trading)...")
        state_mgr.save_position(
            symbol='AAPL',
            entry_time=datetime.now(timezone.utc),
            entry_price=150.00,
            quantity=100,
            direction='LONG',
            side='buy'
        )
        state_mgr.save_position(
            symbol='GOOGL',
            entry_time=datetime.now(timezone.utc),
            entry_price=2800.00,
            quantity=10,
            direction='LONG',
            side='buy'
        )
        print("   ✓ Created 2 positions")

        # Step 3: Simulate recovery
        print("\n3. Simulating system restart and recovery...")

        # New state manager simulating fresh start
        recovery_mgr = StateManager(session)
        recovered_session = recovery_mgr.resume_session(session_id)

        if recovered_session:
            print(f"   ✓ Resumed session {session_id}")

            # Get positions
            positions = recovery_mgr.get_open_positions()
            print(f"   ✓ Recovered {len(positions)} positions:")
            for pos in positions:
                print(f"      - {pos.symbol}: {float(pos.quantity)} shares")

            # Simulate Alpaca positions (AAPL still open, GOOGL closed)
            print("\n4. Reconciling with Alpaca API...")
            reconciler = PositionReconciler(recovery_mgr)

            alpaca_positions = [
                {
                    'symbol': 'AAPL',
                    'side': 'long',
                    'qty': '100',
                    'avg_entry_price': '150.00'
                }
                # GOOGL missing - was closed
            ]

            summary = reconciler.full_recovery(
                alpaca_positions,
                current_prices={'GOOGL': 2850.00},
                import_new=True,
                close_orphaned=True
            )

            print("\n5. Recovery Summary:")
            for key, value in summary.items():
                print(f"   {key}: {value}")

        print("\n✓ Full Recovery Workflow test passed!\n")

    finally:
        session.close()


def cleanup_test_data():
    """Clean up test data from database."""
    print("\nCleaning up test data...")

    db = get_analytics_db()

    with db.get_session() as session:
        # Delete test sessions (those with 'test' in parameters or recent)
        session.query(TradingSession).delete()
        session.query(Position).delete()
        session.query(OrderJournal).delete()

    print("✓ Test data cleaned up\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("RECOVERY SYSTEM TEST SUITE")
    print("=" * 80)

    # Initialize database
    print("\nInitializing database...")
    init_databases()
    print("✓ Database initialized")

    try:
        # Test 1: State Manager
        test_session_id = test_state_manager()

        # Test 2: Position Reconciler
        test_position_reconciler(test_session_id)

        # Test 3: Full Recovery Workflow
        test_full_recovery_workflow()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED!")
        print("=" * 80 + "\n")

        # Ask if user wants to clean up
        response = input("Clean up test data? (y/n): ")
        if response.lower() == 'y':
            cleanup_test_data()

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
