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
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

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
