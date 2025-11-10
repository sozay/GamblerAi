"""
Session Replayer for replaying recorded trading sessions with different parameters.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from gambler_ai.storage.models import (
    RecordedSession,
    RecordedMarketData,
    RecordedEvent,
    ReplaySession,
)


class Position:
    """Simple position tracking for replay."""

    def __init__(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        direction: str,
        stop_loss: float,
        take_profit: float,
        entry_time: datetime,
    ):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.direction = direction
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = entry_time
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl = 0.0
        self.pnl_pct = 0.0

    def close(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """Close the position and calculate P&L."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = exit_reason

        if self.direction == 'LONG':
            self.pnl = (exit_price - self.entry_price) * self.quantity
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - exit_price) * self.quantity
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.exit_price is not None

    def get_duration_seconds(self) -> int:
        """Get position duration in seconds."""
        if self.exit_time:
            return int((self.exit_time - self.entry_time).total_seconds())
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'direction': self.direction,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_reason': self.exit_reason,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'duration_seconds': self.get_duration_seconds(),
        }


class SessionReplayer:
    """
    Replays recorded trading sessions with different parameters.

    This allows testing how strategy behavior changes with parameter modifications.
    """

    def __init__(self, db_session: Session, recording_id: str):
        """
        Initialize replayer with a recorded session.

        Args:
            db_session: Database session
            recording_id: ID of the recording to replay
        """
        self.db = db_session
        self.recording_id = recording_id

        # Load recording metadata
        self.recording = self._load_recording()
        if not self.recording:
            raise ValueError(f"Recording {recording_id} not found")

        # Initialize replay state
        self.replay_id = str(uuid.uuid4())
        self.modified_parameters = {}
        self.positions: List[Position] = []
        self.active_positions: Dict[str, Position] = {}
        self.replay_events: List[Dict[str, Any]] = []

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.equity_curve: List[float] = [0.0]

    def _load_recording(self) -> Optional[RecordedSession]:
        """Load the recording metadata."""
        return self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).first()

    def set_parameter(self, param_name: str, param_value: Any):
        """
        Set a modified parameter for replay.

        Args:
            param_name: Name of parameter to modify
            param_value: New value for the parameter
        """
        self.modified_parameters[param_name] = param_value

    def set_parameters(self, parameters: Dict[str, Any]):
        """
        Set multiple modified parameters.

        Args:
            parameters: Dictionary of parameter names and values
        """
        self.modified_parameters.update(parameters)

    def get_parameter(self, param_name: str, default: Any = None) -> Any:
        """
        Get a parameter value (modified or original).

        Args:
            param_name: Name of parameter
            default: Default value if not found

        Returns:
            Parameter value (modified if set, otherwise original)
        """
        if param_name in self.modified_parameters:
            return self.modified_parameters[param_name]

        if self.recording.original_parameters and param_name in self.recording.original_parameters:
            return self.recording.original_parameters[param_name]

        return default

    def replay(self, strategy_detector) -> Dict[str, Any]:
        """
        Replay the recorded session with modified parameters.

        Args:
            strategy_detector: Strategy detector instance to use for signal detection

        Returns:
            Dictionary with replay results and comparison to original
        """
        # Create replay session record
        replay_session = ReplaySession(
            replay_id=self.replay_id,
            recording_id=self.recording_id,
            replay_time=datetime.now(timezone.utc),
            status='running',
            modified_parameters=self.modified_parameters,
        )
        self.db.add(replay_session)
        self.db.commit()

        try:
            # Load market data ordered by sequence
            market_data = self.db.query(RecordedMarketData).filter(
                RecordedMarketData.recording_id == self.recording_id
            ).order_by(RecordedMarketData.sequence).all()

            # Process each bar
            bars_by_symbol = defaultdict(list)
            for bar in market_data:
                bars_by_symbol[bar.symbol].append(bar)

            # Replay bar by bar
            all_bars_sorted = sorted(market_data, key=lambda x: (x.timestamp, x.sequence))

            for bar in all_bars_sorted:
                # Check existing positions for stop loss / take profit
                self._check_positions(bar)

                # Get all bars for this symbol up to this point
                symbol_bars = [
                    b for b in bars_by_symbol[bar.symbol]
                    if b.sequence <= bar.sequence
                ]

                # Check for signal with modified parameters
                signal = self._check_for_signal(
                    strategy_detector,
                    bar.symbol,
                    symbol_bars,
                    bar.indicators or {}
                )

                if signal:
                    # Open position
                    self._open_position(signal, bar.timestamp)

            # Close any remaining open positions
            self._close_all_positions(all_bars_sorted[-1] if all_bars_sorted else None)

            # Calculate statistics
            self._calculate_statistics()

            # Compare with original
            comparison = self._compare_with_original()

            # Update replay session with results
            self._update_replay_session(replay_session, comparison)

            return {
                'replay_id': self.replay_id,
                'recording_id': self.recording_id,
                'status': 'completed',
                'modified_parameters': self.modified_parameters,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
                'total_pnl': self.total_pnl,
                'max_drawdown': self.max_drawdown,
                'comparison': comparison,
                'positions': [p.to_dict() for p in self.positions],
            }

        except Exception as e:
            # Mark replay as failed
            self.db.query(ReplaySession).filter(
                ReplaySession.replay_id == self.replay_id
            ).update({
                'status': 'failed',
                'description': f'Replay failed: {str(e)}',
            })
            self.db.commit()
            raise

    def _check_for_signal(
        self,
        strategy_detector,
        symbol: str,
        bars: List[RecordedMarketData],
        indicators: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if signal is detected with current parameters.

        This is a simplified version - in reality you'd call the actual
        strategy detector with the bars and parameters.
        """
        if len(bars) < 20:  # Need enough bars for indicators
            return None

        # Convert bars to DataFrame-like structure for detector
        # This is simplified - actual implementation would depend on detector interface
        current_price = float(bars[-1].close)

        # Example: Mean Reversion signal detection with modified parameters
        rsi_threshold = self.get_parameter('rsi_threshold', 30)
        bb_std = self.get_parameter('bb_std', 2.5)

        # Check indicators from recorded data or recalculate
        rsi = indicators.get('rsi', 50)
        bb_lower = indicators.get('bb_lower', current_price)

        # Mean reversion signal: price below BB lower and RSI < threshold
        if current_price < bb_lower and rsi < rsi_threshold:
            return {
                'symbol': symbol,
                'entry_price': current_price,
                'stop_loss': current_price * 0.99,  # 1% stop loss
                'take_profit': bb_lower + (bb_lower * 0.005),  # Target BB middle (simplified)
                'direction': 'LONG',
                'quantity': self.get_parameter('position_size', 10),
                'signal_strength': (rsi_threshold - rsi) / rsi_threshold,  # Simplified
            }

        return None

    def _open_position(self, signal: Dict[str, Any], timestamp: datetime):
        """Open a new position from signal."""
        position = Position(
            symbol=signal['symbol'],
            entry_price=signal['entry_price'],
            quantity=signal['quantity'],
            direction=signal['direction'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            entry_time=timestamp,
        )

        self.active_positions[signal['symbol']] = position
        self.replay_events.append({
            'type': 'POSITION_OPENED',
            'timestamp': timestamp.isoformat(),
            'data': signal,
        })

    def _check_positions(self, current_bar: RecordedMarketData):
        """Check active positions for stop loss or take profit."""
        to_close = []

        for symbol, position in self.active_positions.items():
            if symbol != current_bar.symbol:
                continue

            current_price = float(current_bar.close)
            high = float(current_bar.high)
            low = float(current_bar.low)

            exit_price = None
            exit_reason = None

            # Check stop loss
            if position.direction == 'LONG' and low <= position.stop_loss:
                exit_price = position.stop_loss
                exit_reason = 'stop_loss_hit'
            elif position.direction == 'SHORT' and high >= position.stop_loss:
                exit_price = position.stop_loss
                exit_reason = 'stop_loss_hit'

            # Check take profit
            if position.direction == 'LONG' and high >= position.take_profit:
                exit_price = position.take_profit
                exit_reason = 'take_profit_hit'
            elif position.direction == 'SHORT' and low <= position.take_profit:
                exit_price = position.take_profit
                exit_reason = 'take_profit_hit'

            if exit_price and exit_reason:
                position.close(exit_price, current_bar.timestamp, exit_reason)
                self.positions.append(position)
                to_close.append(symbol)

                # Update statistics
                self.total_trades += 1
                self.total_pnl += position.pnl

                if position.pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1

                self.equity_curve.append(self.total_pnl)

                # Track drawdown
                peak = max(self.equity_curve)
                drawdown = peak - self.total_pnl
                self.max_drawdown = max(self.max_drawdown, drawdown)

                self.replay_events.append({
                    'type': 'POSITION_CLOSED',
                    'timestamp': current_bar.timestamp.isoformat(),
                    'data': position.to_dict(),
                })

        # Remove closed positions
        for symbol in to_close:
            del self.active_positions[symbol]

    def _close_all_positions(self, last_bar: Optional[RecordedMarketData]):
        """Close all remaining open positions at end of replay."""
        if not last_bar:
            return

        for position in self.active_positions.values():
            position.close(
                float(last_bar.close),
                last_bar.timestamp,
                'session_end'
            )
            self.positions.append(position)
            self.total_trades += 1
            self.total_pnl += position.pnl

            if position.pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

        self.active_positions.clear()

    def _calculate_statistics(self):
        """Calculate additional statistics."""
        if not self.positions:
            return

        # Calculate Sharpe ratio (simplified)
        returns = [p.pnl for p in self.positions]
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            self.sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0
        else:
            self.sharpe_ratio = 0

    def _compare_with_original(self) -> Dict[str, Any]:
        """Compare replay results with original recording."""
        original = self.recording

        comparison = {
            'original_trades': original.original_trades or 0,
            'replay_trades': self.total_trades,
            'trades_diff': self.total_trades - (original.original_trades or 0),
            'original_pnl': float(original.original_pnl or 0),
            'replay_pnl': self.total_pnl,
            'pnl_diff': self.total_pnl - float(original.original_pnl or 0),
            'original_win_rate': float(original.original_win_rate or 0),
            'replay_win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
        }

        comparison['win_rate_diff'] = comparison['replay_win_rate'] - comparison['original_win_rate']

        # Load original events for detailed comparison
        original_events = self.db.query(RecordedEvent).filter(
            RecordedEvent.recording_id == self.recording_id,
            RecordedEvent.event_type == 'SIGNAL_DETECTED'
        ).all()

        comparison['original_signals'] = len(original_events)
        comparison['replay_signals'] = len([e for e in self.replay_events if e['type'] == 'POSITION_OPENED'])

        return comparison

    def _update_replay_session(self, replay_session: ReplaySession, comparison: Dict[str, Any]):
        """Update replay session with final results."""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        self.db.query(ReplaySession).filter(
            ReplaySession.replay_id == self.replay_id
        ).update({
            'status': 'completed',
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_pnl': Decimal(str(self.total_pnl)),
            'win_rate': Decimal(str(win_rate)),
            'max_drawdown': Decimal(str(self.max_drawdown)),
            'sharpe_ratio': Decimal(str(getattr(self, 'sharpe_ratio', 0))),
            'trades_diff': comparison['trades_diff'],
            'pnl_diff': Decimal(str(comparison['pnl_diff'])),
            'win_rate_diff': Decimal(str(comparison['win_rate_diff'])),
            'comparison_data': comparison,
            'replay_events': self.replay_events,
        })
        self.db.commit()


def list_recordings(db_session: Session, instance_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List all recordings, optionally filtered by instance.

    Args:
        db_session: Database session
        instance_id: Optional instance ID to filter by

    Returns:
        List of recording metadata dictionaries
    """
    query = db_session.query(RecordedSession)

    if instance_id is not None:
        query = query.filter(RecordedSession.instance_id == instance_id)

    recordings = query.order_by(RecordedSession.recording_start_time.desc()).all()

    return [
        {
            'recording_id': r.recording_id,
            'session_id': r.session_id,
            'instance_id': r.instance_id,
            'strategy_name': r.strategy_name,
            'status': r.status,
            'recording_start_time': r.recording_start_time.isoformat(),
            'recording_end_time': r.recording_end_time.isoformat() if r.recording_end_time else None,
            'symbols_recorded': r.symbols_recorded,
            'total_bars_recorded': r.total_bars_recorded,
            'total_events_recorded': r.total_events_recorded,
            'original_trades': r.original_trades,
            'original_pnl': float(r.original_pnl) if r.original_pnl else 0,
            'original_win_rate': float(r.original_win_rate) if r.original_win_rate else 0,
            'description': r.description,
            'tags': r.tags,
        }
        for r in recordings
    ]


def get_recording_details(db_session: Session, recording_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a recording including events.

    Args:
        db_session: Database session
        recording_id: Recording ID

    Returns:
        Dictionary with recording details and events
    """
    recording = db_session.query(RecordedSession).filter(
        RecordedSession.recording_id == recording_id
    ).first()

    if not recording:
        return None

    # Get event counts by type
    event_counts = {}
    events = db_session.query(
        RecordedEvent.event_type,
        func.count(RecordedEvent.id)
    ).filter(
        RecordedEvent.recording_id == recording_id
    ).group_by(RecordedEvent.event_type).all()

    for event_type, count in events:
        event_counts[event_type] = count

    # Get replays
    replays = db_session.query(ReplaySession).filter(
        ReplaySession.recording_id == recording_id
    ).order_by(ReplaySession.replay_time.desc()).all()

    return {
        'recording_id': recording.recording_id,
        'session_id': recording.session_id,
        'instance_id': recording.instance_id,
        'strategy_name': recording.strategy_name,
        'status': recording.status,
        'recording_start_time': recording.recording_start_time.isoformat(),
        'recording_end_time': recording.recording_end_time.isoformat() if recording.recording_end_time else None,
        'symbols_recorded': recording.symbols_recorded,
        'total_bars_recorded': recording.total_bars_recorded,
        'total_events_recorded': recording.total_events_recorded,
        'original_parameters': recording.original_parameters,
        'original_trades': recording.original_trades,
        'original_pnl': float(recording.original_pnl) if recording.original_pnl else 0,
        'original_win_rate': float(recording.original_win_rate) if recording.original_win_rate else 0,
        'description': recording.description,
        'tags': recording.tags,
        'event_counts': event_counts,
        'replays': [
            {
                'replay_id': r.replay_id,
                'replay_time': r.replay_time.isoformat(),
                'status': r.status,
                'modified_parameters': r.modified_parameters,
                'total_trades': r.total_trades,
                'total_pnl': float(r.total_pnl) if r.total_pnl else 0,
                'win_rate': float(r.win_rate) if r.win_rate else 0,
                'pnl_diff': float(r.pnl_diff) if r.pnl_diff else 0,
            }
            for r in replays
        ],
    }
