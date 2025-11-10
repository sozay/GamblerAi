"""
Database models for GamblerAI using SQLAlchemy ORM.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class StockPrice(Base):
    """Time-series stock price data (OHLCV)."""

    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(DECIMAL(10, 2))
    high = Column(DECIMAL(10, 2))
    low = Column(DECIMAL(10, 2))
    close = Column(DECIMAL(10, 2))
    volume = Column(BigInteger)
    timeframe = Column(String(10), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "timeframe", name="uix_symbol_time_tf"),
    )

    def __repr__(self):
        return f"<StockPrice(symbol={self.symbol}, timestamp={self.timestamp}, close={self.close})>"


class MomentumEvent(Base):
    """Detected momentum events with continuation and reversal metrics."""

    __tablename__ = "momentum_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True))
    direction = Column(String(10), nullable=False, index=True)  # 'UP' or 'DOWN'
    initial_price = Column(DECIMAL(10, 2))
    peak_price = Column(DECIMAL(10, 2))
    duration_seconds = Column(Integer)
    max_move_percentage = Column(DECIMAL(5, 2))
    initial_volume = Column(BigInteger)
    continuation_duration_seconds = Column(Integer)
    reversal_percentage = Column(DECIMAL(5, 2))
    reversal_time_seconds = Column(Integer)
    timeframe = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<MomentumEvent(symbol={self.symbol}, start={self.start_time}, "
            f"direction={self.direction}, move={self.max_move_percentage}%)>"
        )


class PatternStatistic(Base):
    """Aggregated statistical patterns for momentum events."""

    __tablename__ = "pattern_statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_type = Column(String(50), nullable=False)
    timeframe = Column(String(10), nullable=False)
    direction = Column(String(10))  # 'UP', 'DOWN', or None for both
    avg_continuation_duration = Column(Integer)
    median_continuation_duration = Column(Integer)
    avg_reversal_percentage = Column(DECIMAL(5, 2))
    median_reversal_percentage = Column(DECIMAL(5, 2))
    avg_reversal_time = Column(Integer)
    median_reversal_time = Column(Integer)
    confidence_score = Column(DECIMAL(3, 2))
    sample_size = Column(Integer)
    win_rate = Column(DECIMAL(3, 2))
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "pattern_type", "timeframe", "direction", name="uix_pattern_tf_dir"
        ),
    )

    def __repr__(self):
        return (
            f"<PatternStatistic(type={self.pattern_type}, timeframe={self.timeframe}, "
            f"samples={self.sample_size})>"
        )


class ComputedFeature(Base):
    """Cached computed features and technical indicators."""

    __tablename__ = "computed_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    timeframe = Column(String(10))
    feature_name = Column(String(50), nullable=False, index=True)
    feature_value = Column(DECIMAL(10, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timestamp",
            "timeframe",
            "feature_name",
            name="uix_symbol_time_tf_feature",
        ),
    )

    def __repr__(self):
        return (
            f"<ComputedFeature(symbol={self.symbol}, feature={self.feature_name}, "
            f"value={self.feature_value})>"
        )


class DataQualityLog(Base):
    """Log of data quality checks and issues."""

    __tablename__ = "data_quality_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    check_date = Column(DateTime(timezone=True), nullable=False)
    timeframe = Column(String(10))
    missing_periods = Column(Integer, default=0)
    total_periods = Column(Integer)
    quality_score = Column(DECIMAL(3, 2))
    issues = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<DataQualityLog(symbol={self.symbol}, date={self.check_date}, "
            f"score={self.quality_score})>"
        )


class TradingSession(Base):
    """Paper trading session tracking for crash recovery."""

    __tablename__ = "trading_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    instance_id = Column(Integer, nullable=False, default=1, index=True)  # Multi-instance support
    strategy_name = Column(String(100), index=True)  # Strategy identifier
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default='active', index=True)  # active, completed, crashed
    symbols = Column(Text)  # Comma-separated list
    duration_minutes = Column(Integer)
    scan_interval_seconds = Column(Integer)
    initial_portfolio_value = Column(DECIMAL(12, 2))
    final_portfolio_value = Column(DECIMAL(12, 2))
    pnl = Column(DECIMAL(12, 2))
    pnl_pct = Column(DECIMAL(5, 2))
    total_trades = Column(Integer, default=0)
    allocated_capital = Column(DECIMAL(12, 2))  # Capital allocated to this instance
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    positions = relationship("Position", back_populates="session", cascade="all, delete-orphan")
    checkpoints = relationship("PositionCheckpoint", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<TradingSession(id={self.session_id}, status={self.status}, "
            f"start={self.start_time})>"
        )


class Position(Base):
    """Trading position tracking (active and historical)."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('trading_sessions.session_id'), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True))
    entry_price = Column(DECIMAL(10, 2), nullable=False)
    exit_price = Column(DECIMAL(10, 2))
    qty = Column(Integer, nullable=False)
    direction = Column(String(10), nullable=False)  # UP or DOWN
    side = Column(String(10), nullable=False)  # buy or sell
    stop_loss = Column(DECIMAL(10, 2))
    take_profit = Column(DECIMAL(10, 2))
    order_id = Column(String(50), index=True)  # Alpaca order ID
    status = Column(String(20), nullable=False, default='active', index=True)  # active, closed
    exit_reason = Column(String(50))  # stop_loss_hit, take_profit_hit, manual, session_end
    pnl = Column(DECIMAL(12, 2))
    pnl_pct = Column(DECIMAL(5, 2))
    duration_minutes = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    session = relationship("TradingSession", back_populates="positions")

    def __repr__(self):
        return (
            f"<Position(symbol={self.symbol}, direction={self.direction}, "
            f"status={self.status}, entry={self.entry_price})>"
        )


class PositionCheckpoint(Base):
    """Periodic state checkpoints for crash recovery."""

    __tablename__ = "position_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey('trading_sessions.session_id'), nullable=False, index=True)
    checkpoint_time = Column(DateTime(timezone=True), nullable=False, index=True)
    positions_snapshot = Column(JSON)  # Snapshot of active positions
    account_snapshot = Column(JSON)  # Snapshot of account state
    active_positions_count = Column(Integer, default=0)
    closed_trades_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    session = relationship("TradingSession", back_populates="checkpoints")

    def __repr__(self):
        return (
            f"<PositionCheckpoint(session={self.session_id}, time={self.checkpoint_time}, "
            f"positions={self.active_positions_count})>"
        )


class Transaction(Base):
    """Log of all trading transactions (entries and exits)."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Trade identification
    symbol = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # 'LONG' or 'SHORT'
    status = Column(String(10), nullable=False, index=True)  # 'OPEN' or 'CLOSED'

    # Entry details
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    entry_price = Column(DECIMAL(10, 2), nullable=False)
    position_size = Column(DECIMAL(15, 4), nullable=False)

    # Stop loss and target
    stop_loss = Column(DECIMAL(10, 2))
    target = Column(DECIMAL(10, 2))

    # Exit details (null if trade is still open)
    exit_time = Column(DateTime(timezone=True), index=True)
    exit_price = Column(DECIMAL(10, 2))
    exit_reason = Column(String(50))

    # Performance metrics
    pnl = Column(DECIMAL(15, 2))
    pnl_pct = Column(DECIMAL(10, 4))
    return_pct = Column(DECIMAL(10, 4))

    # Risk metrics
    max_adverse_excursion = Column(DECIMAL(10, 4))
    max_favorable_excursion = Column(DECIMAL(10, 4))

    # Trade context
    strategy_name = Column(String(100), index=True)
    trading_mode = Column(String(20))  # 'backtest', 'paper', 'live'

    # Duration
    duration_seconds = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return (
            f"<Transaction(symbol={self.symbol}, direction={self.direction}, "
            f"entry_time={self.entry_time}, status={self.status}, pnl={self.pnl})>"
        )


class OrderJournal(Base):
    """Immutable transaction journal for all orders."""

    __tablename__ = "order_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    position_id = Column(Integer, index=True)  # FK to positions table

    # Order details
    alpaca_order_id = Column(String(50), unique=True, index=True)
    client_order_id = Column(String(50), unique=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)

    # Order specifics
    order_type = Column(String(20), nullable=False)  # 'market', 'limit', 'stop', 'stop_limit'
    side = Column(String(10), nullable=False)  # 'buy', 'sell'
    quantity = Column(DECIMAL(12, 4), nullable=False)
    limit_price = Column(DECIMAL(10, 4))
    stop_price = Column(DECIMAL(10, 4))

    # Status and execution
    status = Column(String(20), nullable=False, index=True)  # 'pending', 'filled', 'partial', 'cancelled', 'rejected'
    filled_qty = Column(DECIMAL(12, 4))
    filled_avg_price = Column(DECIMAL(10, 4))

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    filled_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))

    # Metadata
    order_class = Column(String(20))  # 'simple', 'bracket', 'oco', 'oto'
    time_in_force = Column(String(10))  # 'day', 'gtc', 'ioc', 'fok'
    extended_hours = Column(String(5))  # 'true' or 'false'

    # Linked orders (for bracket orders)
    parent_order_id = Column(String(50), index=True)

    # Error tracking
    rejection_reason = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return (
            f"<OrderJournal(id={self.alpaca_order_id}, symbol={self.symbol}, "
            f"side={self.side}, status={self.status})>"
        )


class RecordedSession(Base):
    """Metadata for recorded trading sessions."""

    __tablename__ = "recorded_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    session_id = Column(String(36), ForeignKey('trading_sessions.session_id'), nullable=False, index=True)
    instance_id = Column(Integer, nullable=False, index=True)
    strategy_name = Column(String(100), nullable=False, index=True)

    # Recording time window
    recording_start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    recording_end_time = Column(DateTime(timezone=True))

    # Recording status
    status = Column(String(20), nullable=False, default='recording', index=True)  # recording, completed, failed

    # Original strategy parameters (stored as JSON for flexibility)
    original_parameters = Column(JSON)  # All strategy params used during recording

    # Market conditions during recording
    symbols_recorded = Column(Text)  # Comma-separated list of symbols
    total_bars_recorded = Column(Integer, default=0)
    total_events_recorded = Column(Integer, default=0)

    # Summary statistics from original run
    original_trades = Column(Integer, default=0)
    original_pnl = Column(DECIMAL(12, 2))
    original_win_rate = Column(DECIMAL(5, 2))

    # Metadata
    description = Column(Text)  # User-provided description
    tags = Column(Text)  # Comma-separated tags for easy searching

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    market_data = relationship("RecordedMarketData", back_populates="recording", cascade="all, delete-orphan")
    events = relationship("RecordedEvent", back_populates="recording", cascade="all, delete-orphan")
    replays = relationship("ReplaySession", back_populates="recording", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<RecordedSession(id={self.recording_id}, strategy={self.strategy_name}, "
            f"status={self.status}, start={self.recording_start_time})>"
        )


class RecordedMarketData(Base):
    """Market data captured during recording."""

    __tablename__ = "recorded_market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String(36), ForeignKey('recorded_sessions.recording_id'), nullable=False, index=True)

    # Market data
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(DECIMAL(10, 4), nullable=False)
    high = Column(DECIMAL(10, 4), nullable=False)
    low = Column(DECIMAL(10, 4), nullable=False)
    close = Column(DECIMAL(10, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)

    # Technical indicators calculated at this bar (stored for exact replay)
    indicators = Column(JSON)  # RSI, BB, ATR, etc. as computed during recording

    # Sequence number for ordered replay
    sequence = Column(Integer, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    recording = relationship("RecordedSession", back_populates="market_data")

    __table_args__ = (
        UniqueConstraint("recording_id", "symbol", "timestamp", name="uix_recording_symbol_time"),
    )

    def __repr__(self):
        return (
            f"<RecordedMarketData(recording={self.recording_id}, symbol={self.symbol}, "
            f"time={self.timestamp}, close={self.close})>"
        )


class RecordedEvent(Base):
    """Events captured during recording (signals, orders, fills, position changes)."""

    __tablename__ = "recorded_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String(36), ForeignKey('recorded_sessions.recording_id'), nullable=False, index=True)

    # Event identification
    event_type = Column(String(50), nullable=False, index=True)  # SIGNAL_DETECTED, ORDER_PLACED, ORDER_FILLED, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    sequence = Column(Integer, nullable=False, index=True)  # For ordered replay

    # Event context
    symbol = Column(String(10), index=True)

    # Event data (flexible JSON storage)
    event_data = Column(JSON, nullable=False)  # Contains all relevant data for the event

    # Decision metadata (why did strategy make this decision?)
    decision_metadata = Column(JSON)  # Indicator values, scores, reasoning at decision time

    # Market state at event time
    market_state = Column(JSON)  # Snapshot of market conditions when event occurred

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    recording = relationship("RecordedSession", back_populates="events")

    def __repr__(self):
        return (
            f"<RecordedEvent(recording={self.recording_id}, type={self.event_type}, "
            f"symbol={self.symbol}, time={self.timestamp})>"
        )


class ReplaySession(Base):
    """Results from replaying a recorded session with different parameters."""

    __tablename__ = "replay_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    replay_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    recording_id = Column(String(36), ForeignKey('recorded_sessions.recording_id'), nullable=False, index=True)

    # Replay execution
    replay_time = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='running', index=True)  # running, completed, failed

    # Modified parameters for this replay
    modified_parameters = Column(JSON, nullable=False)  # Parameters changed from original

    # Replay results
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(DECIMAL(12, 2))
    win_rate = Column(DECIMAL(5, 2))
    max_drawdown = Column(DECIMAL(12, 2))
    sharpe_ratio = Column(DECIMAL(5, 2))

    # Comparison with original
    trades_diff = Column(Integer)  # Difference in number of trades
    pnl_diff = Column(DECIMAL(12, 2))  # Difference in P&L
    win_rate_diff = Column(DECIMAL(5, 2))  # Difference in win rate

    # Detailed comparison data
    comparison_data = Column(JSON)  # Trade-by-trade comparison, missed signals, extra signals, etc.

    # Events generated during replay
    replay_events = Column(JSON)  # All events from replay for detailed analysis

    # Metadata
    description = Column(Text)  # User notes about this replay

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    recording = relationship("RecordedSession", back_populates="replays")

    def __repr__(self):
        return (
            f"<ReplaySession(id={self.replay_id}, recording={self.recording_id}, "
            f"trades={self.total_trades}, pnl={self.total_pnl})>"
        )
