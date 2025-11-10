"""
Session Recorder for capturing trading sessions for replay and analysis.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy.orm import Session

from gambler_ai.storage.models import (
    RecordedSession,
    RecordedMarketData,
    RecordedEvent,
    TradingSession,
)


class SessionRecorder:
    """
    Records trading sessions with full market data and event capture.

    This allows later replay with different parameters to analyze strategy behavior.
    """

    def __init__(
        self,
        db_session: Session,
        trading_session_id: str,
        instance_id: int,
        strategy_name: str,
        strategy_parameters: Dict[str, Any],
        symbols: List[str],
    ):
        """
        Initialize a new recording session.

        Args:
            db_session: Database session for persistence
            trading_session_id: ID of the trading session being recorded
            instance_id: Trading instance ID
            strategy_name: Name of the strategy being used
            strategy_parameters: Full set of strategy parameters
            symbols: List of symbols being tracked
        """
        self.db = db_session
        self.trading_session_id = trading_session_id
        self.instance_id = instance_id
        self.strategy_name = strategy_name
        self.symbols = symbols

        # Generate unique recording ID
        self.recording_id = str(uuid.uuid4())

        # Track sequence numbers for ordered replay
        self.market_data_sequence = 0
        self.event_sequence = 0

        # Recording state
        self.is_recording = False
        self.recording_start_time = None

        # Create recording metadata in database
        self._create_recording_metadata(strategy_parameters)

    def _create_recording_metadata(self, strategy_parameters: Dict[str, Any]):
        """Create the RecordedSession entry in the database."""
        recording = RecordedSession(
            recording_id=self.recording_id,
            session_id=self.trading_session_id,
            instance_id=self.instance_id,
            strategy_name=self.strategy_name,
            recording_start_time=datetime.now(timezone.utc),
            status='recording',
            original_parameters=strategy_parameters,
            symbols_recorded=','.join(self.symbols),
            total_bars_recorded=0,
            total_events_recorded=0,
        )
        self.db.add(recording)
        self.db.commit()

        self.is_recording = True
        self.recording_start_time = datetime.now(timezone.utc)

    def record_market_data(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        indicators: Optional[Dict[str, float]] = None
    ):
        """
        Record a market data bar.

        Args:
            symbol: Stock symbol
            timestamp: Bar timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            indicators: Optional dict of calculated indicators (RSI, BB, ATR, etc.)
        """
        if not self.is_recording:
            return

        market_data = RecordedMarketData(
            recording_id=self.recording_id,
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(open_price)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=volume,
            indicators=indicators or {},
            sequence=self.market_data_sequence,
        )

        self.db.add(market_data)
        self.market_data_sequence += 1

        # Update total bars counter
        self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).update({
            'total_bars_recorded': RecordedSession.total_bars_recorded + 1
        })

    def record_event(
        self,
        event_type: str,
        symbol: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        decision_metadata: Optional[Dict[str, Any]] = None,
        market_state: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a trading event.

        Args:
            event_type: Type of event (SIGNAL_DETECTED, ORDER_PLACED, etc.)
            symbol: Stock symbol (if applicable)
            event_data: Event-specific data
            decision_metadata: Why the decision was made (indicator values, scores, etc.)
            market_state: Snapshot of market conditions at event time
        """
        if not self.is_recording:
            return

        event = RecordedEvent(
            recording_id=self.recording_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            sequence=self.event_sequence,
            symbol=symbol,
            event_data=event_data or {},
            decision_metadata=decision_metadata or {},
            market_state=market_state or {},
        )

        self.db.add(event)
        self.event_sequence += 1

        # Update total events counter
        self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).update({
            'total_events_recorded': RecordedSession.total_events_recorded + 1
        })

    def record_signal_detected(
        self,
        symbol: str,
        signal_type: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        indicators: Dict[str, float],
        signal_strength: float,
        reasoning: str,
    ):
        """
        Record a detected trading signal with full context.

        Args:
            symbol: Stock symbol
            signal_type: Type of signal (MEAN_REVERSION, VOLATILITY_BREAKOUT, etc.)
            entry_price: Proposed entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            indicators: All indicator values at signal time
            signal_strength: Signal strength score
            reasoning: Human-readable reasoning for the signal
        """
        self.record_event(
            event_type='SIGNAL_DETECTED',
            symbol=symbol,
            event_data={
                'signal_type': signal_type,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'signal_strength': signal_strength,
                'reasoning': reasoning,
            },
            decision_metadata={
                'indicators': indicators,
            },
        )

    def record_order_placed(
        self,
        symbol: str,
        order_id: str,
        order_type: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
    ):
        """Record an order being placed."""
        self.record_event(
            event_type='ORDER_PLACED',
            symbol=symbol,
            event_data={
                'order_id': order_id,
                'order_type': order_type,
                'side': side,
                'quantity': quantity,
                'price': price,
            },
        )

    def record_order_filled(
        self,
        symbol: str,
        order_id: str,
        filled_qty: int,
        filled_price: float,
    ):
        """Record an order being filled."""
        self.record_event(
            event_type='ORDER_FILLED',
            symbol=symbol,
            event_data={
                'order_id': order_id,
                'filled_qty': filled_qty,
                'filled_price': filled_price,
            },
        )

    def record_position_opened(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        direction: str,
        stop_loss: float,
        take_profit: float,
    ):
        """Record a position being opened."""
        self.record_event(
            event_type='POSITION_OPENED',
            symbol=symbol,
            event_data={
                'entry_price': entry_price,
                'quantity': quantity,
                'direction': direction,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
            },
        )

    def record_position_closed(
        self,
        symbol: str,
        exit_price: float,
        quantity: int,
        exit_reason: str,
        pnl: float,
        pnl_pct: float,
        duration_seconds: int,
    ):
        """Record a position being closed."""
        self.record_event(
            event_type='POSITION_CLOSED',
            symbol=symbol,
            event_data={
                'exit_price': exit_price,
                'quantity': quantity,
                'exit_reason': exit_reason,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'duration_seconds': duration_seconds,
            },
        )

    def record_scan_cycle(self, scan_number: int, symbols_scanned: List[str]):
        """Record a scan cycle completion."""
        self.record_event(
            event_type='SCAN_CYCLE',
            event_data={
                'scan_number': scan_number,
                'symbols_scanned': symbols_scanned,
            },
        )

    def update_summary_stats(
        self,
        total_trades: int,
        total_pnl: Decimal,
        win_rate: Decimal,
    ):
        """
        Update summary statistics for the recording.

        Args:
            total_trades: Total number of trades during recording
            total_pnl: Total P&L during recording
            win_rate: Win rate percentage
        """
        self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).update({
            'original_trades': total_trades,
            'original_pnl': total_pnl,
            'original_win_rate': win_rate,
        })
        self.db.commit()

    def stop_recording(self, description: Optional[str] = None, tags: Optional[List[str]] = None):
        """
        Stop recording and mark as completed.

        Args:
            description: Optional description of what was recorded
            tags: Optional tags for categorizing the recording
        """
        if not self.is_recording:
            return

        # Update recording status
        update_data = {
            'recording_end_time': datetime.now(timezone.utc),
            'status': 'completed',
        }

        if description:
            update_data['description'] = description

        if tags:
            update_data['tags'] = ','.join(tags)

        self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).update(update_data)

        self.db.commit()
        self.is_recording = False

    def mark_failed(self, error_message: str):
        """Mark recording as failed with error message."""
        self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).update({
            'status': 'failed',
            'description': f'Recording failed: {error_message}',
            'recording_end_time': datetime.now(timezone.utc),
        })
        self.db.commit()
        self.is_recording = False

    def get_recording_info(self) -> Dict[str, Any]:
        """Get information about the current recording."""
        recording = self.db.query(RecordedSession).filter(
            RecordedSession.recording_id == self.recording_id
        ).first()

        if not recording:
            return {}

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
        }
