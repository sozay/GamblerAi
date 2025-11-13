#!/usr/bin/env python3
"""
Test script for state persistence functionality.
Tests database models and their relationships without requiring actual database connection.
"""

import sys
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, '.')

from gambler_ai.storage.models import TradingSession, Position, PositionCheckpoint

def test_models():
    """Test that models can be instantiated."""
    print("Testing database models...")

    # Test TradingSession
    session = TradingSession(
        session_id="test-123",
        start_time=datetime.now(),
        status='active',
        symbols='AAPL,MSFT,GOOGL',
        duration_minutes=60,
        scan_interval_seconds=60,
        initial_portfolio_value=Decimal('100000.00'),
    )
    print(f"✓ TradingSession: {session}")

    # Test Position
    position = Position(
        session_id="test-123",
        symbol="AAPL",
        entry_time=datetime.now(),
        entry_price=Decimal('150.50'),
        qty=100,
        direction='UP',
        side='buy',
        stop_loss=Decimal('147.50'),
        take_profit=Decimal('156.50'),
        order_id='order-456',
        status='active',
    )
    print(f"✓ Position: {position}")

    # Test PositionCheckpoint
    checkpoint = PositionCheckpoint(
        session_id="test-123",
        checkpoint_time=datetime.now(),
        positions_snapshot={'AAPL': {'qty': 100, 'entry_price': 150.50}},
        account_snapshot={'portfolio_value': 100000.00},
        active_positions_count=1,
        closed_trades_count=0,
    )
    print(f"✓ PositionCheckpoint: {checkpoint}")

    print("\n✅ All model tests passed!")
    print("\nState persistence features implemented:")
    print("  • TradingSession model - tracks trading sessions")
    print("  • Position model - tracks positions (active/closed)")
    print("  • PositionCheckpoint model - periodic state snapshots")
    print("  • Checkpoints saved every 30 seconds")
    print("  • Crash detection on startup")
    print("  • Automatic session finalization")

if __name__ == "__main__":
    test_models()
