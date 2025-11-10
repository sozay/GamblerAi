"""
Alpaca paper trading API endpoints for real-time monitoring.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker

from gambler_ai.storage.models import (
    TradingSession,
    Position,
    Transaction,
    OrderJournal,
)
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Database setup
config = get_config()
db_url = config.analytics_db_url
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)


# Pydantic models for API responses
class PositionResponse(BaseModel):
    id: int
    session_id: str
    instance_id: int
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    qty: int
    direction: str
    side: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    order_id: Optional[str]
    status: str
    exit_reason: Optional[str]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    duration_minutes: Optional[int]

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: int
    session_id: str
    instance_id: int
    strategy_name: Optional[str]
    allocated_capital: Optional[float]
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    symbols: Optional[str]
    duration_minutes: Optional[int]
    initial_portfolio_value: Optional[float]
    final_portfolio_value: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    total_trades: int

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    status: str
    entry_time: datetime
    entry_price: float
    position_size: float
    stop_loss: Optional[float]
    target: Optional[float]
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    duration_seconds: Optional[int]
    strategy_name: Optional[str]

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    total_trades: int
    open_positions: int
    closed_positions: int
    total_pnl: float
    win_rate: float
    avg_pnl_per_trade: float
    best_trade: Optional[float]
    worst_trade: Optional[float]


class OrderResponse(BaseModel):
    id: int
    session_id: str
    symbol: str
    order_type: str
    side: str
    quantity: float
    status: str
    filled_qty: Optional[float]
    filled_avg_price: Optional[float]
    submitted_at: datetime
    filled_at: Optional[datetime]
    rejection_reason: Optional[str]

    class Config:
        from_attributes = True


class InstanceResponse(BaseModel):
    instance_id: int
    name: str
    strategy: Optional[str]
    status: str
    current_pnl: float
    active_positions: int
    total_trades: int
    win_rate: float


class ComparisonResponse(BaseModel):
    instance_id: int
    name: str
    strategy: Optional[str]
    win_rate: float
    avg_pnl: float
    total_trades: int
    total_pnl: float
    sharpe_ratio: Optional[float]


def decimal_to_float(value):
    """Convert Decimal to float, handle None."""
    if value is None:
        return None
    return float(value) if isinstance(value, Decimal) else value


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(active|completed|crashed)$"),
    instance_id: Optional[int] = Query(None),
):
    """Get recent trading sessions."""
    db = SessionLocal()
    try:
        query = db.query(TradingSession).order_by(desc(TradingSession.start_time))

        if status:
            query = query.filter(TradingSession.status == status)

        if instance_id is not None:
            query = query.filter(TradingSession.instance_id == instance_id)

        sessions = query.limit(limit).all()

        return [
            SessionResponse(
                id=s.id,
                session_id=s.session_id,
                instance_id=s.instance_id,
                strategy_name=s.strategy_name,
                allocated_capital=decimal_to_float(s.allocated_capital),
                start_time=s.start_time,
                end_time=s.end_time,
                status=s.status,
                symbols=s.symbols,
                duration_minutes=s.duration_minutes,
                initial_portfolio_value=decimal_to_float(s.initial_portfolio_value),
                final_portfolio_value=decimal_to_float(s.final_portfolio_value),
                pnl=decimal_to_float(s.pnl),
                pnl_pct=decimal_to_float(s.pnl_pct),
                total_trades=s.total_trades or 0,
            )
            for s in sessions
        ]
    finally:
        db.close()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get specific session details."""
    db = SessionLocal()
    try:
        session = (
            db.query(TradingSession)
            .filter(TradingSession.session_id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            id=session.id,
            session_id=session.session_id,
            instance_id=session.instance_id,
            strategy_name=session.strategy_name,
            allocated_capital=decimal_to_float(session.allocated_capital),
            start_time=session.start_time,
            end_time=session.end_time,
            status=session.status,
            symbols=session.symbols,
            duration_minutes=session.duration_minutes,
            initial_portfolio_value=decimal_to_float(session.initial_portfolio_value),
            final_portfolio_value=decimal_to_float(session.final_portfolio_value),
            pnl=decimal_to_float(session.pnl),
            pnl_pct=decimal_to_float(session.pnl_pct),
            total_trades=session.total_trades or 0,
        )
    finally:
        db.close()


@router.get("/positions/active", response_model=List[PositionResponse])
async def get_active_positions(instance_id: Optional[int] = Query(None)):
    """Get all active positions."""
    db = SessionLocal()
    try:
        query = (
            db.query(Position)
            .join(TradingSession, Position.session_id == TradingSession.session_id)
            .filter(Position.status == "active")
        )

        if instance_id is not None:
            query = query.filter(TradingSession.instance_id == instance_id)

        positions = query.order_by(desc(Position.entry_time)).all()

        return [
            PositionResponse(
                id=p.id,
                session_id=p.session_id,
                instance_id=p.session.instance_id,
                symbol=p.symbol,
                entry_time=p.entry_time,
                exit_time=p.exit_time,
                entry_price=decimal_to_float(p.entry_price),
                exit_price=decimal_to_float(p.exit_price),
                qty=p.qty,
                direction=p.direction,
                side=p.side,
                stop_loss=decimal_to_float(p.stop_loss),
                take_profit=decimal_to_float(p.take_profit),
                order_id=p.order_id,
                status=p.status,
                exit_reason=p.exit_reason,
                pnl=decimal_to_float(p.pnl),
                pnl_pct=decimal_to_float(p.pnl_pct),
                duration_minutes=p.duration_minutes,
            )
            for p in positions
        ]
    finally:
        db.close()


@router.get("/positions/closed", response_model=List[PositionResponse])
async def get_closed_positions(
    limit: int = Query(20, ge=1, le=100),
    instance_id: Optional[int] = Query(None)
):
    """Get recently closed positions."""
    db = SessionLocal()
    try:
        query = (
            db.query(Position)
            .join(TradingSession, Position.session_id == TradingSession.session_id)
            .filter(Position.status == "closed")
        )

        if instance_id is not None:
            query = query.filter(TradingSession.instance_id == instance_id)

        positions = query.order_by(desc(Position.exit_time)).limit(limit).all()

        return [
            PositionResponse(
                id=p.id,
                session_id=p.session_id,
                instance_id=p.session.instance_id,
                symbol=p.symbol,
                entry_time=p.entry_time,
                exit_time=p.exit_time,
                entry_price=decimal_to_float(p.entry_price),
                exit_price=decimal_to_float(p.exit_price),
                qty=p.qty,
                direction=p.direction,
                side=p.side,
                stop_loss=decimal_to_float(p.stop_loss),
                take_profit=decimal_to_float(p.take_profit),
                order_id=p.order_id,
                status=p.status,
                exit_reason=p.exit_reason,
                pnl=decimal_to_float(p.pnl),
                pnl_pct=decimal_to_float(p.pnl_pct),
                duration_minutes=p.duration_minutes,
            )
            for p in positions
        ]
    finally:
        db.close()


@router.get("/trades/recent", response_model=List[TransactionResponse])
async def get_recent_trades(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(OPEN|CLOSED)$"),
):
    """Get recent trades from transactions table."""
    db = SessionLocal()
    try:
        query = db.query(Transaction).order_by(desc(Transaction.entry_time))

        if status:
            query = query.filter(Transaction.status == status)

        trades = query.limit(limit).all()

        return [
            TransactionResponse(
                id=t.id,
                symbol=t.symbol,
                direction=t.direction,
                status=t.status,
                entry_time=t.entry_time,
                entry_price=decimal_to_float(t.entry_price),
                position_size=decimal_to_float(t.position_size),
                stop_loss=decimal_to_float(t.stop_loss),
                target=decimal_to_float(t.target),
                exit_time=t.exit_time,
                exit_price=decimal_to_float(t.exit_price),
                exit_reason=t.exit_reason,
                pnl=decimal_to_float(t.pnl),
                pnl_pct=decimal_to_float(t.pnl_pct),
                duration_seconds=t.duration_seconds,
                strategy_name=t.strategy_name,
            )
            for t in trades
        ]
    finally:
        db.close()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(instance_id: Optional[int] = Query(None)):
    """Get overall trading statistics."""
    db = SessionLocal()
    try:
        # Base queries
        session_query = db.query(func.count(TradingSession.id))
        if instance_id is not None:
            session_query = session_query.filter(TradingSession.instance_id == instance_id)

        total_sessions = session_query.scalar() or 0

        active_session_query = db.query(func.count(TradingSession.id)).filter(TradingSession.status == "active")
        if instance_id is not None:
            active_session_query = active_session_query.filter(TradingSession.instance_id == instance_id)

        active_sessions = active_session_query.scalar() or 0

        # Position counts with instance filter
        position_query_base = db.query(Position).join(TradingSession, Position.session_id == TradingSession.session_id)
        if instance_id is not None:
            position_query_base = position_query_base.filter(TradingSession.instance_id == instance_id)

        open_positions = position_query_base.filter(Position.status == "active").count() or 0
        closed_positions = position_query_base.filter(Position.status == "closed").count() or 0
        total_trades = open_positions + closed_positions

        # P&L stats from closed positions
        pnl_query = (
            db.query(
                func.sum(Position.pnl).label("total_pnl"),
                func.avg(Position.pnl).label("avg_pnl"),
                func.max(Position.pnl).label("best_trade"),
                func.min(Position.pnl).label("worst_trade"),
                func.count(Position.id).label("trade_count"),
            )
            .join(TradingSession, Position.session_id == TradingSession.session_id)
            .filter(Position.status == "closed", Position.pnl.isnot(None))
        )

        if instance_id is not None:
            pnl_query = pnl_query.filter(TradingSession.instance_id == instance_id)

        pnl_stats = pnl_query.first()

        total_pnl = decimal_to_float(pnl_stats.total_pnl) or 0.0
        avg_pnl = decimal_to_float(pnl_stats.avg_pnl) or 0.0
        best_trade = decimal_to_float(pnl_stats.best_trade)
        worst_trade = decimal_to_float(pnl_stats.worst_trade)

        # Win rate
        winning_query = (
            db.query(func.count(Position.id))
            .join(TradingSession, Position.session_id == TradingSession.session_id)
            .filter(Position.status == "closed", Position.pnl > 0)
        )

        if instance_id is not None:
            winning_query = winning_query.filter(TradingSession.instance_id == instance_id)

        winning_trades = winning_query.scalar() or 0
        win_rate = (
            (winning_trades / pnl_stats.trade_count * 100)
            if pnl_stats.trade_count
            else 0.0
        )

        return StatsResponse(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_trades=total_trades,
            open_positions=open_positions,
            closed_positions=closed_positions,
            total_pnl=total_pnl,
            win_rate=round(win_rate, 2),
            avg_pnl_per_trade=avg_pnl,
            best_trade=best_trade,
            worst_trade=worst_trade,
        )
    finally:
        db.close()


@router.get("/orders/recent", response_model=List[OrderResponse])
async def get_recent_orders(limit: int = Query(20, ge=1, le=100)):
    """Get recent orders from order journal."""
    db = SessionLocal()
    try:
        orders = (
            db.query(OrderJournal)
            .order_by(desc(OrderJournal.submitted_at))
            .limit(limit)
            .all()
        )

        return [
            OrderResponse(
                id=o.id,
                session_id=o.session_id,
                symbol=o.symbol,
                order_type=o.order_type,
                side=o.side,
                quantity=decimal_to_float(o.quantity),
                status=o.status,
                filled_qty=decimal_to_float(o.filled_qty),
                filled_avg_price=decimal_to_float(o.filled_avg_price),
                submitted_at=o.submitted_at,
                filled_at=o.filled_at,
                rejection_reason=o.rejection_reason,
            )
            for o in orders
        ]
    finally:
        db.close()


@router.get("/instances", response_model=List[InstanceResponse])
async def get_instances():
    """Get all instances with their current status."""
    db = SessionLocal()
    try:
        # Get unique instance IDs from sessions
        instances = db.query(TradingSession.instance_id).distinct().all()

        results = []
        for (instance_id,) in instances:
            # Get most recent session for this instance
            latest_session = (
                db.query(TradingSession)
                .filter(TradingSession.instance_id == instance_id)
                .order_by(desc(TradingSession.start_time))
                .first()
            )

            # Get active positions count
            active_positions = (
                db.query(func.count(Position.id))
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(
                    TradingSession.instance_id == instance_id,
                    Position.status == "active"
                )
                .scalar() or 0
            )

            # Get total trades count
            total_trades = (
                db.query(func.count(Position.id))
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(TradingSession.instance_id == instance_id)
                .scalar() or 0
            )

            # Get current P&L (sum of all closed positions)
            current_pnl_query = (
                db.query(func.sum(Position.pnl))
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(
                    TradingSession.instance_id == instance_id,
                    Position.status == "closed",
                    Position.pnl.isnot(None)
                )
                .scalar()
            )
            current_pnl = decimal_to_float(current_pnl_query) or 0.0

            # Get win rate
            closed_trades = (
                db.query(func.count(Position.id))
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(
                    TradingSession.instance_id == instance_id,
                    Position.status == "closed"
                )
                .scalar() or 0
            )

            winning_trades = (
                db.query(func.count(Position.id))
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(
                    TradingSession.instance_id == instance_id,
                    Position.status == "closed",
                    Position.pnl > 0
                )
                .scalar() or 0
            )

            win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0

            # Determine status
            status = latest_session.status if latest_session else "unknown"
            strategy = latest_session.strategy_name if latest_session else "Unknown"

            results.append(
                InstanceResponse(
                    instance_id=instance_id,
                    name=f"Instance {instance_id}",
                    strategy=strategy,
                    status=status,
                    current_pnl=current_pnl,
                    active_positions=active_positions,
                    total_trades=total_trades,
                    win_rate=round(win_rate, 2),
                )
            )

        return sorted(results, key=lambda x: x.instance_id)
    finally:
        db.close()


@router.get("/comparison", response_model=List[ComparisonResponse])
async def get_comparison():
    """Get comparison data for all instances."""
    db = SessionLocal()
    try:
        # Get unique instance IDs from sessions
        instances = db.query(TradingSession.instance_id).distinct().all()

        results = []
        for (instance_id,) in instances:
            # Get most recent session for strategy name
            latest_session = (
                db.query(TradingSession)
                .filter(TradingSession.instance_id == instance_id)
                .order_by(desc(TradingSession.start_time))
                .first()
            )

            strategy = latest_session.strategy_name if latest_session else "Unknown"

            # Get statistics for closed positions
            stats = (
                db.query(
                    func.sum(Position.pnl).label("total_pnl"),
                    func.avg(Position.pnl).label("avg_pnl"),
                    func.count(Position.id).label("total_trades"),
                )
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(
                    TradingSession.instance_id == instance_id,
                    Position.status == "closed",
                    Position.pnl.isnot(None)
                )
                .first()
            )

            total_pnl = decimal_to_float(stats.total_pnl) or 0.0
            avg_pnl = decimal_to_float(stats.avg_pnl) or 0.0
            total_trades = stats.total_trades or 0

            # Get win rate
            winning_trades = (
                db.query(func.count(Position.id))
                .join(TradingSession, Position.session_id == TradingSession.session_id)
                .filter(
                    TradingSession.instance_id == instance_id,
                    Position.status == "closed",
                    Position.pnl > 0
                )
                .scalar() or 0
            )

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

            # Sharpe ratio calculation (simplified - would need more data for accurate calculation)
            # For now, we'll set it to None as we don't have daily returns data
            sharpe_ratio = None

            results.append(
                ComparisonResponse(
                    instance_id=instance_id,
                    name=f"Instance {instance_id}",
                    strategy=strategy,
                    win_rate=round(win_rate, 2),
                    avg_pnl=avg_pnl,
                    total_trades=total_trades,
                    total_pnl=total_pnl,
                    sharpe_ratio=sharpe_ratio,
                )
            )

        return sorted(results, key=lambda x: x.instance_id)
    finally:
        db.close()
