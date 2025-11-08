"""
Session checkpoint manager for saving and restoring trading session state.

This module provides functionality to create periodic checkpoints of trading sessions,
allowing the system to resume from the last known state after crashes or restarts.
"""

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from gambler_ai.storage.models import PositionCheckpoint, TradingSession, Position


class SessionCheckpointManager:
    """Manages session checkpoints for crash recovery and state restoration."""

    def __init__(self, db_session: Session):
        """
        Initialize checkpoint manager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_checkpoint(
        self,
        session_id: str,
        account_info: Dict = None,
        strategy_params: Dict = None
    ) -> int:
        """
        Create a checkpoint of the current session state.

        Args:
            session_id: Trading session ID
            account_info: Optional account snapshot (portfolio_value, buying_power, cash, etc.)
            strategy_params: Optional strategy parameters to save with checkpoint

        Returns:
            Checkpoint ID

        Raises:
            ValueError: If session not found
        """
        # Verify session exists
        session = self.db.query(TradingSession).filter_by(
            session_id=session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get all active positions for this session
        active_positions = self.db.query(Position).filter_by(
            session_id=session_id,
            status='active'
        ).all()

        # Get all closed positions for this session
        closed_positions = self.db.query(Position).filter_by(
            session_id=session_id,
            status='closed'
        ).all()

        # Build positions snapshot
        positions_snapshot = {}
        for pos in active_positions:
            positions_snapshot[pos.symbol] = {
                'id': pos.id,
                'symbol': pos.symbol,
                'entry_time': pos.entry_time.isoformat(),
                'entry_price': float(pos.entry_price),
                'qty': pos.qty,
                'direction': pos.direction,
                'side': pos.side,
                'stop_loss': float(pos.stop_loss) if pos.stop_loss else None,
                'take_profit': float(pos.take_profit) if pos.take_profit else None,
                'order_id': pos.order_id,
                'status': pos.status
            }

        # Build account snapshot
        account_snapshot = account_info or {}

        # Add strategy parameters if provided
        if strategy_params:
            account_snapshot['strategy_params'] = strategy_params

        # Create checkpoint
        checkpoint = PositionCheckpoint(
            session_id=session_id,
            checkpoint_time=datetime.now(timezone.utc),
            positions_snapshot=positions_snapshot,
            account_snapshot=account_snapshot,
            active_positions_count=len(active_positions),
            closed_trades_count=len(closed_positions)
        )

        self.db.add(checkpoint)
        self.db.commit()

        return checkpoint.id

    def get_latest_checkpoint(self, session_id: str) -> Optional[PositionCheckpoint]:
        """
        Get the most recent checkpoint for a session.

        Args:
            session_id: Trading session ID

        Returns:
            Latest PositionCheckpoint or None if no checkpoints exist
        """
        return self.db.query(PositionCheckpoint).filter_by(
            session_id=session_id
        ).order_by(PositionCheckpoint.checkpoint_time.desc()).first()

    def get_checkpoint_by_id(self, checkpoint_id: int) -> Optional[PositionCheckpoint]:
        """
        Get a specific checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            PositionCheckpoint or None if not found
        """
        return self.db.query(PositionCheckpoint).filter_by(
            id=checkpoint_id
        ).first()

    def list_checkpoints(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[PositionCheckpoint]:
        """
        List checkpoints for a session.

        Args:
            session_id: Trading session ID
            limit: Maximum number of checkpoints to return

        Returns:
            List of PositionCheckpoint objects, newest first
        """
        return self.db.query(PositionCheckpoint).filter_by(
            session_id=session_id
        ).order_by(PositionCheckpoint.checkpoint_time.desc()).limit(limit).all()

    def restore_from_checkpoint(
        self,
        checkpoint: PositionCheckpoint
    ) -> Dict:
        """
        Extract state information from a checkpoint for restoration.

        Args:
            checkpoint: PositionCheckpoint object to restore from

        Returns:
            Dictionary containing:
                - session_id: Session ID
                - checkpoint_time: When checkpoint was created
                - positions: List of position data
                - account_info: Account snapshot
                - active_count: Number of active positions
                - closed_count: Number of closed trades
        """
        positions = []

        if checkpoint.positions_snapshot:
            for symbol, pos_data in checkpoint.positions_snapshot.items():
                positions.append(pos_data)

        return {
            'session_id': checkpoint.session_id,
            'checkpoint_time': checkpoint.checkpoint_time,
            'checkpoint_id': checkpoint.id,
            'positions': positions,
            'account_info': checkpoint.account_snapshot or {},
            'active_count': checkpoint.active_positions_count,
            'closed_count': checkpoint.closed_trades_count
        }

    def cleanup_old_checkpoints(
        self,
        session_id: str,
        keep_count: int = 100,
        older_than_hours: int = None
    ) -> int:
        """
        Remove old checkpoints to save database space.

        Args:
            session_id: Trading session ID
            keep_count: Minimum number of recent checkpoints to keep
            older_than_hours: Optionally delete checkpoints older than N hours

        Returns:
            Number of checkpoints deleted
        """
        query = self.db.query(PositionCheckpoint).filter_by(
            session_id=session_id
        ).order_by(PositionCheckpoint.checkpoint_time.desc())

        all_checkpoints = query.all()

        # Keep at least keep_count most recent checkpoints
        checkpoints_to_delete = []

        if len(all_checkpoints) > keep_count:
            checkpoints_to_delete = all_checkpoints[keep_count:]

        # Additionally filter by age if specified
        if older_than_hours:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            checkpoints_to_delete = [
                cp for cp in checkpoints_to_delete
                if cp.checkpoint_time < cutoff_time
            ]

        # Delete checkpoints
        for checkpoint in checkpoints_to_delete:
            self.db.delete(checkpoint)

        self.db.commit()

        return len(checkpoints_to_delete)

    def get_checkpoint_stats(self, session_id: str) -> Dict:
        """
        Get statistics about checkpoints for a session.

        Args:
            session_id: Trading session ID

        Returns:
            Dictionary with checkpoint statistics
        """
        checkpoints = self.db.query(PositionCheckpoint).filter_by(
            session_id=session_id
        ).order_by(PositionCheckpoint.checkpoint_time).all()

        if not checkpoints:
            return {
                'total_checkpoints': 0,
                'first_checkpoint': None,
                'last_checkpoint': None,
                'time_span_minutes': 0
            }

        first_checkpoint = checkpoints[0]
        last_checkpoint = checkpoints[-1]

        time_span = (last_checkpoint.checkpoint_time - first_checkpoint.checkpoint_time).total_seconds() / 60

        return {
            'total_checkpoints': len(checkpoints),
            'first_checkpoint': first_checkpoint.checkpoint_time,
            'last_checkpoint': last_checkpoint.checkpoint_time,
            'time_span_minutes': int(time_span),
            'avg_interval_seconds': int(time_span * 60 / len(checkpoints)) if len(checkpoints) > 1 else 0
        }
