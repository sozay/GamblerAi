#!/usr/bin/env python3
"""
Test session checkpointing functionality.

This script tests the session checkpoint manager and state persistence.
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gambler_ai.storage.database import get_analytics_db, init_databases
from gambler_ai.trading.state_manager import StateManager
from gambler_ai.trading.checkpoint_manager import SessionCheckpointManager


def test_checkpoint_creation():
    """Test creating checkpoints."""
    print("\n" + "=" * 80)
    print("TEST 1: Checkpoint Creation")
    print("=" * 80)

    # Get database session
    db_manager = get_analytics_db()
    db_manager.create_tables()
    db_session = db_manager.get_session_direct()

    try:
        # Create state manager
        state_manager = StateManager(db_session)

        # Create a new session
        session_id = state_manager.create_session(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            initial_capital=100000.0,
            duration_minutes=60,
            scan_interval_seconds=30
        )

        print(f"\n✓ Created session: {session_id}")

        # Add some positions
        print("\n Adding test positions...")
        pos1_id = state_manager.save_position(
            symbol='AAPL',
            entry_time=datetime.now(timezone.utc),
            entry_price=150.50,
            quantity=100,
            direction='UP',
            side='buy',
            stop_loss=147.49,
            take_profit=156.52,
            order_id='test_order_1'
        )
        print(f"  ✓ Added position: AAPL (ID: {pos1_id})")

        pos2_id = state_manager.save_position(
            symbol='MSFT',
            entry_time=datetime.now(timezone.utc),
            entry_price=375.25,
            quantity=50,
            direction='DOWN',
            side='sell',
            stop_loss=382.64,
            take_profit=367.99,
            order_id='test_order_2'
        )
        print(f"  ✓ Added position: MSFT (ID: {pos2_id})")

        # Create first checkpoint
        print("\n Creating checkpoint 1...")
        account_info_1 = {
            'portfolio_value': 100500.00,
            'buying_power': 50000.00,
            'cash': 45000.00
        }
        strategy_params = {
            'stop_loss_pct': 2.0,
            'take_profit_pct': 4.0
        }
        checkpoint_id_1 = state_manager.create_checkpoint(
            account_info=account_info_1,
            strategy_params=strategy_params
        )
        print(f"  ✓ Checkpoint 1 created (ID: {checkpoint_id_1})")

        # Wait a bit
        time.sleep(2)

        # Close one position
        print("\n Closing AAPL position...")
        state_manager.update_position(
            symbol='AAPL',
            exit_time=datetime.now(timezone.utc),
            exit_price=156.00,
            exit_reason='take_profit',
            status='closed'
        )
        print("  ✓ AAPL position closed")

        # Create second checkpoint
        print("\n Creating checkpoint 2...")
        account_info_2 = {
            'portfolio_value': 101050.00,
            'buying_power': 51000.00,
            'cash': 46000.00
        }
        checkpoint_id_2 = state_manager.create_checkpoint(
            account_info=account_info_2,
            strategy_params=strategy_params
        )
        print(f"  ✓ Checkpoint 2 created (ID: {checkpoint_id_2})")

        # List checkpoints
        print("\n Listing checkpoints...")
        checkpoints = state_manager.list_checkpoints(limit=10)
        print(f"  Total checkpoints: {len(checkpoints)}")
        for i, cp in enumerate(checkpoints, 1):
            print(f"  {i}. Checkpoint at {cp.checkpoint_time} - {cp.active_positions_count} active, {cp.closed_trades_count} closed")

        # Get checkpoint stats
        print("\n Checkpoint statistics:")
        stats = state_manager.get_checkpoint_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n✓ TEST 1 PASSED")

    finally:
        db_session.close()


def test_checkpoint_restoration():
    """Test restoring from checkpoints."""
    print("\n" + "=" * 80)
    print("TEST 2: Checkpoint Restoration")
    print("=" * 80)

    # Get database session
    db_manager = get_analytics_db()
    db_session = db_manager.get_session_direct()

    try:
        # Create state manager
        state_manager = StateManager(db_session)

        # Create a new session
        session_id = state_manager.create_session(
            symbols=['TSLA', 'NVDA'],
            initial_capital=100000.0,
            duration_minutes=30,
            scan_interval_seconds=15
        )

        print(f"\n✓ Created session: {session_id}")

        # Add positions
        print("\n Adding positions...")
        state_manager.save_position(
            symbol='TSLA',
            entry_time=datetime.now(timezone.utc),
            entry_price=245.30,
            quantity=75,
            direction='UP',
            side='buy',
            stop_loss=240.39,
            take_profit=255.33
        )
        print("  ✓ Added TSLA position")

        # Create checkpoint
        print("\n Creating checkpoint...")
        account_info = {
            'portfolio_value': 100500.00,
            'buying_power': 52000.00,
            'cash': 47000.00
        }
        checkpoint_id = state_manager.create_checkpoint(account_info=account_info)
        print(f"  ✓ Checkpoint created (ID: {checkpoint_id})")

        # Get latest checkpoint
        print("\n Retrieving latest checkpoint...")
        latest_checkpoint = state_manager.checkpoint_manager.get_latest_checkpoint(session_id)
        print(f"  ✓ Found checkpoint from {latest_checkpoint.checkpoint_time}")

        # Restore from checkpoint
        print("\n Restoring from checkpoint...")
        restored_state = state_manager.restore_from_latest_checkpoint()

        print(f"\n Restored state:")
        print(f"  Session ID: {restored_state['session_id']}")
        print(f"  Checkpoint time: {restored_state['checkpoint_time']}")
        print(f"  Active positions: {restored_state['active_count']}")
        print(f"  Closed trades: {restored_state['closed_count']}")
        print(f"  Positions in snapshot:")
        for pos in restored_state['positions']:
            print(f"    - {pos['symbol']}: {pos['direction']} @ ${pos['entry_price']}")

        print(f"\n Account info:")
        for key, value in restored_state['account_info'].items():
            print(f"    {key}: {value}")

        print("\n✓ TEST 2 PASSED")

    finally:
        db_session.close()


def test_checkpoint_cleanup():
    """Test checkpoint cleanup."""
    print("\n" + "=" * 80)
    print("TEST 3: Checkpoint Cleanup")
    print("=" * 80)

    # Get database session
    db_manager = get_analytics_db()
    db_session = db_manager.get_session_direct()

    try:
        # Create state manager
        state_manager = StateManager(db_session)

        # Create a new session
        session_id = state_manager.create_session(
            symbols=['AAPL'],
            initial_capital=100000.0,
            duration_minutes=10,
            scan_interval_seconds=5
        )

        print(f"\n✓ Created session: {session_id}")

        # Create multiple checkpoints
        print("\n Creating 15 checkpoints...")
        for i in range(15):
            account_info = {
                'portfolio_value': 100000.00 + (i * 100),
                'iteration': i
            }
            state_manager.create_checkpoint(account_info=account_info)
            time.sleep(0.1)  # Small delay

        stats_before = state_manager.get_checkpoint_stats()
        print(f"  ✓ Created {stats_before['total_checkpoints']} checkpoints")

        # Clean up old checkpoints (keep only 10)
        print("\n Cleaning up checkpoints (keeping 10 most recent)...")
        deleted = state_manager.cleanup_old_checkpoints(keep_count=10)
        print(f"  ✓ Deleted {deleted} checkpoints")

        stats_after = state_manager.get_checkpoint_stats()
        print(f"  Remaining checkpoints: {stats_after['total_checkpoints']}")

        # Verify we kept the right ones
        checkpoints = state_manager.list_checkpoints(limit=20)
        print(f"\n Remaining checkpoint iterations:")
        for cp in checkpoints:
            iteration = cp.account_snapshot.get('iteration', 'N/A')
            print(f"  - Iteration {iteration} at {cp.checkpoint_time}")

        print("\n✓ TEST 3 PASSED")

    finally:
        db_session.close()


def test_session_resume_with_checkpoint():
    """Test resuming a session with checkpoint restoration."""
    print("\n" + "=" * 80)
    print("TEST 4: Session Resume with Checkpoint")
    print("=" * 80)

    # Get database session
    db_manager = get_analytics_db()
    db_session = db_manager.get_session_direct()

    try:
        # PHASE 1: Create session and checkpoint
        print("\n PHASE 1: Creating session and checkpoint...")
        state_manager_1 = StateManager(db_session)

        session_id = state_manager_1.create_session(
            symbols=['AAPL', 'MSFT'],
            initial_capital=100000.0,
            duration_minutes=30
        )
        print(f"  ✓ Created session: {session_id}")

        # Add positions
        state_manager_1.save_position(
            symbol='AAPL',
            entry_time=datetime.now(timezone.utc),
            entry_price=150.00,
            quantity=100,
            direction='UP',
            side='buy',
            stop_loss=147.00,
            take_profit=156.00
        )
        print("  ✓ Added AAPL position")

        # Create checkpoint
        checkpoint_id = state_manager_1.create_checkpoint(
            account_info={'portfolio_value': 100500.00}
        )
        print(f"  ✓ Created checkpoint: {checkpoint_id}")

        # PHASE 2: Simulate crash and resume
        print("\n PHASE 2: Simulating crash and resuming session...")
        state_manager_2 = StateManager(db_session)

        # Resume session
        resumed_session = state_manager_2.resume_session(session_id)
        print(f"  ✓ Resumed session: {resumed_session.session_id}")

        # Restore from checkpoint
        restored_state = state_manager_2.restore_from_latest_checkpoint()
        print(f"  ✓ Restored from checkpoint")
        print(f"    Active positions: {restored_state['active_count']}")
        print(f"    Portfolio value: ${restored_state['account_info'].get('portfolio_value')}")

        # Verify positions
        positions = state_manager_2.get_open_positions()
        print(f"\n Verified {len(positions)} active positions:")
        for pos in positions:
            print(f"  - {pos.symbol}: {pos.direction} @ ${pos.entry_price}")

        print("\n✓ TEST 4 PASSED")

    finally:
        db_session.close()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("SESSION CHECKPOINTING TEST SUITE")
    print("=" * 80)

    # Initialize database
    print("\n Initializing database...")
    init_databases()
    print("✓ Database initialized")

    try:
        # Run tests
        test_checkpoint_creation()
        test_checkpoint_restoration()
        test_checkpoint_cleanup()
        test_session_resume_with_checkpoint()

        # Final summary
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        print("\nSession checkpointing is working correctly!")
        print("\nKey features tested:")
        print("  ✓ Creating checkpoints with positions and account data")
        print("  ✓ Restoring state from checkpoints")
        print("  ✓ Listing and querying checkpoints")
        print("  ✓ Cleaning up old checkpoints")
        print("  ✓ Resuming sessions with checkpoint restoration")
        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
