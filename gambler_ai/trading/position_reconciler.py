"""
Position reconciler for startup recovery.

Compares Alpaca API positions with local database state and reconciles differences.
"""

from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple
from decimal import Decimal

from gambler_ai.storage.models import Position
from gambler_ai.trading.state_manager import StateManager


class PositionReconciler:
    """Reconciles positions between Alpaca API and local database."""

    def __init__(self, state_manager: StateManager):
        """
        Initialize reconciler.

        Args:
            state_manager: StateManager instance
        """
        self.state_manager = state_manager

    def reconcile(
        self,
        alpaca_positions: List[Dict],
        verbose: bool = True
    ) -> Tuple[List[Dict], List[Position], List[str]]:
        """
        Reconcile Alpaca positions with local database.

        Args:
            alpaca_positions: List of positions from Alpaca API
            verbose: Print reconciliation details

        Returns:
            Tuple of (new_alpaca_positions, orphaned_local_positions, matched_symbols)
        """
        # Get local open positions
        local_positions = self.state_manager.get_open_positions()

        # Build lookup sets
        alpaca_symbols = {p['symbol'] for p in alpaca_positions}
        local_symbols = {p.symbol for p in local_positions}

        # Find differences
        new_in_alpaca = alpaca_symbols - local_symbols  # Positions in Alpaca but not in local DB
        orphaned_in_local = local_symbols - alpaca_symbols  # Positions in local DB but not in Alpaca
        matched = alpaca_symbols & local_symbols  # Positions in both

        if verbose:
            print("\n" + "=" * 80)
            print("POSITION RECONCILIATION")
            print("=" * 80)
            print(f"Alpaca positions: {len(alpaca_positions)}")
            print(f"Local positions:  {len(local_positions)}")
            print(f"Matched:          {len(matched)}")
            print(f"New in Alpaca:    {len(new_in_alpaca)}")
            print(f"Orphaned (local): {len(orphaned_in_local)}")

        # Handle new Alpaca positions (not in local DB)
        new_alpaca_positions = []
        if new_in_alpaca:
            if verbose:
                print("\n⚠ Positions found in Alpaca but not in local database:")
            for symbol in new_in_alpaca:
                alpaca_pos = next(p for p in alpaca_positions if p['symbol'] == symbol)
                if verbose:
                    print(f"  - {symbol}: {alpaca_pos['side']} {alpaca_pos['qty']} @ ${float(alpaca_pos['avg_entry_price']):.2f}")
                new_alpaca_positions.append(alpaca_pos)

        # Handle orphaned local positions (not in Alpaca)
        orphaned_local_positions = []
        if orphaned_in_local:
            if verbose:
                print("\n⚠ Positions found in local database but not in Alpaca (likely closed):")
            for symbol in orphaned_in_local:
                local_pos = next(p for p in local_positions if p.symbol == symbol)
                if verbose:
                    print(f"  - {symbol}: {local_pos.direction} {float(local_pos.quantity)} @ ${float(local_pos.entry_price):.2f}")
                orphaned_local_positions.append(local_pos)

        # Verify matched positions
        if matched and verbose:
            print(f"\n✓ {len(matched)} positions matched and tracking correctly:")
            for symbol in matched:
                alpaca_pos = next(p for p in alpaca_positions if p['symbol'] == symbol)
                local_pos = next(p for p in local_positions if p.symbol == symbol)
                print(f"  - {symbol}: {alpaca_pos['side']} {alpaca_pos['qty']} shares")

        if verbose:
            print("=" * 80 + "\n")

        return new_alpaca_positions, orphaned_local_positions, list(matched)

    def recover_orphaned_positions(
        self,
        orphaned_positions: List[Position],
        current_prices: Dict[str, float] = None
    ):
        """
        Mark orphaned local positions as closed.

        Args:
            orphaned_positions: List of orphaned Position objects
            current_prices: Optional dict of current prices for P&L calculation
        """
        for position in orphaned_positions:
            # Position was in DB but not in Alpaca - it was likely closed
            # We'll mark it as closed with unknown exit details

            exit_price = None
            if current_prices and position.symbol in current_prices:
                exit_price = current_prices[position.symbol]

            self.state_manager.update_position(
                symbol=position.symbol,
                exit_time=datetime.now(timezone.utc),
                exit_price=exit_price,
                exit_reason='recovered_closed',
                status='closed'
            )

            print(f"✓ Marked orphaned position as closed: {position.symbol}")

    def import_alpaca_positions(
        self,
        new_alpaca_positions: List[Dict]
    ):
        """
        Import positions from Alpaca that are not in local DB.

        Args:
            new_alpaca_positions: List of position dicts from Alpaca API
        """
        for alpaca_pos in new_alpaca_positions:
            symbol = alpaca_pos['symbol']
            qty = float(alpaca_pos['qty'])
            avg_entry_price = float(alpaca_pos['avg_entry_price'])
            side = alpaca_pos['side']  # 'long' or 'short'

            # Map Alpaca side to our direction
            direction = 'LONG' if side == 'long' else 'SHORT'

            # We don't have full entry details, so use current time
            entry_time = datetime.now(timezone.utc)

            # Save to database
            self.state_manager.save_position(
                symbol=symbol,
                entry_time=entry_time,
                entry_price=avg_entry_price,
                quantity=qty,
                direction=direction,
                side='buy' if side == 'long' else 'sell',
                alpaca_position_id=None  # Alpaca doesn't provide position IDs directly
            )

            print(f"✓ Imported Alpaca position: {symbol} {direction} {qty} @ ${avg_entry_price:.2f}")

    def full_recovery(
        self,
        alpaca_positions: List[Dict],
        current_prices: Dict[str, float] = None,
        import_new: bool = True,
        close_orphaned: bool = True
    ) -> Dict:
        """
        Perform full recovery reconciliation.

        Args:
            alpaca_positions: Positions from Alpaca API
            current_prices: Current market prices
            import_new: Import new Alpaca positions to local DB
            close_orphaned: Close orphaned local positions

        Returns:
            Recovery summary dict
        """
        # Reconcile positions
        new_alpaca, orphaned_local, matched = self.reconcile(
            alpaca_positions,
            verbose=True
        )

        # Import new Alpaca positions
        if import_new and new_alpaca:
            print(f"\n⟳ Importing {len(new_alpaca)} positions from Alpaca...")
            self.import_alpaca_positions(new_alpaca)

        # Close orphaned positions
        if close_orphaned and orphaned_local:
            print(f"\n⟳ Closing {len(orphaned_local)} orphaned positions...")
            self.recover_orphaned_positions(orphaned_local, current_prices)

        # Build summary
        summary = {
            'total_alpaca_positions': len(alpaca_positions),
            'total_local_positions': len(self.state_manager.get_open_positions()),
            'matched': len(matched),
            'imported_from_alpaca': len(new_alpaca) if import_new else 0,
            'closed_orphaned': len(orphaned_local) if close_orphaned else 0,
        }

        print(f"\n✓ Recovery complete:")
        print(f"  - Total positions now tracking: {summary['total_local_positions']}")
        print(f"  - Matched: {summary['matched']}")
        print(f"  - Imported: {summary['imported_from_alpaca']}")
        print(f"  - Closed: {summary['closed_orphaned']}\n")

        return summary
