"""
Trade management for backtesting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid


class TradeDirection(Enum):
    """Trade direction enum."""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(Enum):
    """Trade status enum."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class Trade:
    """Represents a single trade."""

    symbol: str
    direction: TradeDirection
    entry_time: datetime
    entry_price: float
    position_size: float

    # Stop loss and target
    stop_loss: Optional[float] = None
    target: Optional[float] = None

    # Exit information
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # Performance
    pnl: float = 0.0
    pnl_pct: float = 0.0
    return_pct: float = 0.0

    # Trade metadata
    strategy_name: str = "unknown"
    setup_data: dict = field(default_factory=dict)
    status: TradeStatus = TradeStatus.OPEN

    # Risk metrics
    max_adverse_excursion: float = 0.0  # Worst drawdown during trade
    max_favorable_excursion: float = 0.0  # Best profit during trade

    # Unique identifier for transaction logging
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: Optional[int] = None  # Database transaction ID

    def update_excursions(self, current_price: float):
        """Update max adverse and favorable excursions."""
        if self.direction == TradeDirection.LONG:
            # For LONG: favorable is up, adverse is down
            excursion_pct = (current_price - self.entry_price) / self.entry_price * 100
        else:
            # For SHORT: favorable is down, adverse is up
            excursion_pct = (self.entry_price - current_price) / self.entry_price * 100

        if excursion_pct > self.max_favorable_excursion:
            self.max_favorable_excursion = excursion_pct

        if excursion_pct < self.max_adverse_excursion:
            self.max_adverse_excursion = excursion_pct

    def close(self, exit_time: datetime, exit_price: float, reason: str):
        """Close the trade."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        self.status = TradeStatus.CLOSED

        # Calculate P&L
        if self.direction == TradeDirection.LONG:
            self.pnl = (exit_price - self.entry_price) * self.position_size
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price * 100
        else:
            self.pnl = (self.entry_price - exit_price) * self.position_size
            self.pnl_pct = (self.entry_price - exit_price) / self.entry_price * 100

        self.return_pct = self.pnl_pct

    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss is hit."""
        if self.stop_loss is None:
            return False

        if self.direction == TradeDirection.LONG:
            return current_price <= self.stop_loss
        else:
            return current_price >= self.stop_loss

    def check_target(self, current_price: float) -> bool:
        """Check if target is hit."""
        if self.target is None:
            return False

        if self.direction == TradeDirection.LONG:
            return current_price >= self.target
        else:
            return current_price <= self.target

    def to_dict(self) -> dict:
        """Convert trade to dictionary."""
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strategy": self.strategy_name,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "entry_price": self.entry_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "return_pct": round(self.return_pct, 2),
            "duration_seconds": (
                (self.exit_time - self.entry_time).total_seconds()
                if self.exit_time and self.entry_time
                else None
            ),
            "max_adverse_excursion": round(self.max_adverse_excursion, 2),
            "max_favorable_excursion": round(self.max_favorable_excursion, 2),
            "status": self.status.value,
        }


class TradeManager:
    """Manages trades during backtesting."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        risk_per_trade: float = 0.01,
        transaction_logger=None,
    ):
        """
        Initialize trade manager.

        Args:
            initial_capital: Starting capital
            risk_per_trade: Risk per trade as fraction of capital (0.01 = 1%)
            transaction_logger: TransactionLogger instance for logging trades
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade = risk_per_trade

        self.open_trades = []
        self.closed_trades = []

        self.equity_curve = []
        self.max_concurrent_trades = 0

        # Transaction logging
        self.transaction_logger = transaction_logger

    def can_open_trade(self, max_concurrent: int = 3) -> bool:
        """Check if we can open a new trade."""
        return len(self.open_trades) < max_concurrent

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        direction: TradeDirection
    ) -> float:
        """
        Calculate position size based on risk.

        Risk per trade is defined as a % of capital.
        Position size = (Capital * Risk%) / (Entry - Stop) * Entry
        """
        if stop_loss is None or stop_loss == 0:
            # Default to fixed % of capital if no stop
            return (self.current_capital * self.risk_per_trade) / entry_price

        # Calculate risk per share
        if direction == TradeDirection.LONG:
            risk_per_share = abs(entry_price - stop_loss)
        else:
            risk_per_share = abs(stop_loss - entry_price)

        if risk_per_share == 0:
            risk_per_share = entry_price * 0.01  # 1% default

        # Position size = Risk amount / Risk per share
        risk_amount = self.current_capital * self.risk_per_trade
        position_size = risk_amount / risk_per_share

        # Don't exceed 20% of capital in one trade
        max_position_value = self.current_capital * 0.20
        max_shares = max_position_value / entry_price

        return min(position_size, max_shares)

    def open_trade(
        self,
        symbol: str,
        direction: TradeDirection,
        entry_time: datetime,
        entry_price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        strategy_name: str = "unknown",
        setup_data: dict = None,
    ) -> Trade:
        """Open a new trade."""

        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss, direction)

        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            target=target,
            strategy_name=strategy_name,
            setup_data=setup_data or {},
        )

        self.open_trades.append(trade)

        # Track max concurrent
        if len(self.open_trades) > self.max_concurrent_trades:
            self.max_concurrent_trades = len(self.open_trades)

        # Log trade entry to database and files
        if self.transaction_logger:
            try:
                transaction_id = self.transaction_logger.log_trade_entry(
                    symbol=symbol,
                    direction=direction.value,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    position_size=position_size,
                    stop_loss=stop_loss,
                    target=target,
                    strategy_name=strategy_name,
                    trade_id=trade.trade_id,
                )
                trade.transaction_id = transaction_id
            except Exception as e:
                # Don't fail the trade if logging fails
                print(f"Warning: Failed to log trade entry: {e}")

        return trade

    def update_trades(self, current_time: datetime, current_prices: dict):
        """Update all open trades with current prices."""
        trades_to_close = []

        for trade in self.open_trades:
            if trade.symbol not in current_prices:
                continue

            current_price = current_prices[trade.symbol]

            # Update excursions
            trade.update_excursions(current_price)

            # Check stop loss
            if trade.check_stop_loss(current_price):
                trade.close(current_time, trade.stop_loss, "stop_loss")
                trades_to_close.append(trade)

            # Check target
            elif trade.check_target(current_price):
                trade.close(current_time, trade.target, "target")
                trades_to_close.append(trade)

        # Close trades and update capital
        for trade in trades_to_close:
            self.close_trade(trade)

    def close_trade(self, trade: Trade):
        """Close a trade and update capital."""
        if trade not in self.open_trades:
            return

        self.open_trades.remove(trade)
        self.closed_trades.append(trade)

        # Update capital
        self.current_capital += trade.pnl

        # Record equity
        self.equity_curve.append({
            "time": trade.exit_time,
            "equity": self.current_capital,
        })

        # Log trade exit to database and files
        if self.transaction_logger and trade.transaction_id:
            try:
                self.transaction_logger.log_trade_exit(
                    transaction_id=trade.transaction_id,
                    exit_time=trade.exit_time,
                    exit_price=trade.exit_price,
                    exit_reason=trade.exit_reason,
                    pnl=trade.pnl,
                    pnl_pct=trade.pnl_pct,
                    return_pct=trade.return_pct,
                    max_adverse_excursion=trade.max_adverse_excursion,
                    max_favorable_excursion=trade.max_favorable_excursion,
                    trade_id=trade.trade_id,
                )
            except Exception as e:
                # Don't fail the trade if logging fails
                print(f"Warning: Failed to log trade exit: {e}")

    def force_close_all(self, current_time: datetime, current_prices: dict, reason: str = "end_of_backtest"):
        """Force close all open trades at current prices."""
        for trade in list(self.open_trades):
            if trade.symbol in current_prices:
                current_price = current_prices[trade.symbol]
                trade.close(current_time, current_price, reason)
                self.close_trade(trade)

    def get_total_pnl(self) -> float:
        """Get total P&L."""
        return sum(trade.pnl for trade in self.closed_trades)

    def get_total_return_pct(self) -> float:
        """Get total return percentage."""
        return (self.current_capital - self.initial_capital) / self.initial_capital * 100

    def get_trade_count(self) -> int:
        """Get total number of closed trades."""
        return len(self.closed_trades)

    def get_winning_trades(self) -> list:
        """Get list of winning trades."""
        return [t for t in self.closed_trades if t.pnl > 0]

    def get_losing_trades(self) -> list:
        """Get list of losing trades."""
        return [t for t in self.closed_trades if t.pnl <= 0]
