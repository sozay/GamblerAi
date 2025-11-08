"""
State manager for persisting and recovering trading state.
"""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from gambler_ai.storage.models import TradingSession, Position, OrderJournal


class StateManager:
    """Manages persistent state for trading sessions and positions."""

    def __init__(self, db_session: Session):
        """
        Initialize state manager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.session_id = None
        self.current_session = None

    def create_session(
        self,
        symbols: List[str],
        initial_capital: float,
        parameters: Dict = None
    ) -> str:
        """
        Create a new trading session.

        Args:
            symbols: List of symbols to trade
            initial_capital: Starting capital
            parameters: Strategy parameters

        Returns:
            Session ID
        """
        self.session_id = str(uuid.uuid4())

        session = TradingSession(
            session_id=self.session_id,
            start_time=datetime.now(timezone.utc),
            status='active',
            initial_capital=Decimal(str(initial_capital)),
            symbols=json.dumps(symbols),
            parameters=json.dumps(parameters or {})
        )

        self.db.add(session)
        self.db.commit()

        self.current_session = session
        print(f"✓ Created trading session: {self.session_id}")

        return self.session_id

    def resume_session(self, session_id: str = None) -> Optional[TradingSession]:
        """
        Resume an existing session or find the last active session.

        Args:
            session_id: Specific session ID to resume (or None for last active)

        Returns:
            TradingSession object if found, None otherwise
        """
        if session_id:
            session = self.db.query(TradingSession).filter_by(
                session_id=session_id
            ).first()
        else:
            # Find most recent active session
            session = self.db.query(TradingSession).filter_by(
                status='active'
            ).order_by(TradingSession.start_time.desc()).first()

        if session:
            self.session_id = session.session_id
            self.current_session = session
            print(f"✓ Resumed session: {self.session_id}")
            print(f"  Started: {session.start_time}")
            print(f"  Symbols: {json.loads(session.symbols)}")

        return session

    def end_session(self, final_capital: float, status: str = 'stopped'):
        """
        End the current trading session.

        Args:
            final_capital: Final portfolio value
            status: 'stopped' or 'crashed'
        """
        if not self.current_session:
            return

        self.current_session.end_time = datetime.now(timezone.utc)
        self.current_session.final_capital = Decimal(str(final_capital))
        self.current_session.status = status

        self.db.commit()
        print(f"✓ Session ended: {status}")

    def save_position(
        self,
        symbol: str,
        entry_time: datetime,
        entry_price: float,
        quantity: float,
        direction: str,
        side: str,
        stop_loss: float = None,
        take_profit: float = None,
        entry_order_id: str = None,
        stop_loss_order_id: str = None,
        take_profit_order_id: str = None
    ) -> int:
        """
        Save a position to the database.

        Returns:
            Position ID
        """
        if not self.session_id:
            raise ValueError("No active session")

        position = Position(
            session_id=self.session_id,
            symbol=symbol,
            entry_time=entry_time,
            entry_price=Decimal(str(entry_price)),
            quantity=Decimal(str(quantity)),
            direction=direction,
            side=side,
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            take_profit=Decimal(str(take_profit)) if take_profit else None,
            entry_order_id=entry_order_id,
            stop_loss_order_id=stop_loss_order_id,
            take_profit_order_id=take_profit_order_id,
            status='open'
        )

        self.db.add(position)
        self.db.commit()

        return position.id

    def update_position(
        self,
        symbol: str,
        exit_time: datetime = None,
        exit_price: float = None,
        exit_reason: str = None,
        status: str = None
    ):
        """
        Update a position (usually to close it).

        Args:
            symbol: Symbol to update
            exit_time: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit
            status: New status
        """
        if not self.session_id:
            return

        position = self.db.query(Position).filter_by(
            session_id=self.session_id,
            symbol=symbol,
            status='open'
        ).first()

        if not position:
            return

        if exit_time:
            position.exit_time = exit_time
        if exit_price is not None:
            position.exit_price = Decimal(str(exit_price))

            # Calculate P&L
            if position.direction == 'LONG':
                pnl = (Decimal(str(exit_price)) - position.entry_price) * position.quantity
                pnl_pct = (Decimal(str(exit_price)) - position.entry_price) / position.entry_price * 100
            else:  # SHORT
                pnl = (position.entry_price - Decimal(str(exit_price))) * position.quantity
                pnl_pct = (position.entry_price - Decimal(str(exit_price))) / position.entry_price * 100

            position.pnl = pnl
            position.pnl_pct = pnl_pct

        if exit_reason:
            position.exit_reason = exit_reason
        if status:
            position.status = status

        self.db.commit()

    def get_open_positions(self) -> List[Position]:
        """
        Get all open positions for current session.

        Returns:
            List of Position objects
        """
        if not self.session_id:
            return []

        return self.db.query(Position).filter_by(
            session_id=self.session_id,
            status='open'
        ).all()

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """
        Get open position for a symbol.

        Returns:
            Position object or None
        """
        if not self.session_id:
            return None

        return self.db.query(Position).filter_by(
            session_id=self.session_id,
            symbol=symbol,
            status='open'
        ).first()

    def log_order(
        self,
        alpaca_order_id: str,
        symbol: str,
        order_type: str,
        side: str,
        quantity: float,
        status: str,
        client_order_id: str = None,
        limit_price: float = None,
        stop_price: float = None,
        position_id: int = None,
        order_class: str = None,
        time_in_force: str = None,
        parent_order_id: str = None
    ) -> int:
        """
        Log an order to the transaction journal.

        Returns:
            Order journal entry ID
        """
        if not self.session_id:
            raise ValueError("No active session")

        order = OrderJournal(
            session_id=self.session_id,
            position_id=position_id,
            alpaca_order_id=alpaca_order_id,
            client_order_id=client_order_id or str(uuid.uuid4()),
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=Decimal(str(quantity)),
            limit_price=Decimal(str(limit_price)) if limit_price else None,
            stop_price=Decimal(str(stop_price)) if stop_price else None,
            status=status,
            submitted_at=datetime.now(timezone.utc),
            order_class=order_class,
            time_in_force=time_in_force,
            parent_order_id=parent_order_id
        )

        self.db.add(order)
        self.db.commit()

        return order.id

    def update_order_status(
        self,
        alpaca_order_id: str,
        status: str,
        filled_qty: float = None,
        filled_avg_price: float = None,
        filled_at: datetime = None,
        rejection_reason: str = None
    ):
        """
        Update order status in journal.

        Args:
            alpaca_order_id: Alpaca order ID
            status: New status
            filled_qty: Filled quantity
            filled_avg_price: Average fill price
            filled_at: Fill timestamp
            rejection_reason: Rejection reason if rejected
        """
        order = self.db.query(OrderJournal).filter_by(
            alpaca_order_id=alpaca_order_id
        ).first()

        if not order:
            return

        order.status = status

        if filled_qty is not None:
            order.filled_qty = Decimal(str(filled_qty))
        if filled_avg_price is not None:
            order.filled_avg_price = Decimal(str(filled_avg_price))
        if filled_at:
            order.filled_at = filled_at
        if rejection_reason:
            order.rejection_reason = rejection_reason

        self.db.commit()

    def get_session_stats(self) -> Dict:
        """
        Get statistics for current session.

        Returns:
            Dictionary with session stats
        """
        if not self.session_id:
            return {}

        open_positions = self.get_open_positions()
        closed_positions = self.db.query(Position).filter_by(
            session_id=self.session_id,
            status='closed'
        ).all()

        total_pnl = sum(
            float(p.pnl) for p in closed_positions if p.pnl
        )

        return {
            'session_id': self.session_id,
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_pnl': total_pnl,
            'open_symbols': [p.symbol for p in open_positions]
        }
