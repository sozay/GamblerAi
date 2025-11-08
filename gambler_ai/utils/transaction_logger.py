"""
Transaction logging utility for recording all trades to database and files.
"""

import csv
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from gambler_ai.storage.database import DatabaseManager
from gambler_ai.storage.models import Transaction
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class TransactionLogger:
    """
    Logs all trading transactions to both database and CSV file.

    Handles trade entries, exits, and updates to provide a complete
    audit trail of all trading activity.
    """

    def __init__(
        self,
        database_manager: Optional[DatabaseManager] = None,
        csv_path: Optional[str] = None,
        json_path: Optional[str] = None,
        trading_mode: str = "backtest",
    ):
        """
        Initialize transaction logger.

        Args:
            database_manager: Database manager instance (if None, creates new one)
            csv_path: Path to CSV log file (default: logs/transactions.csv)
            json_path: Path to JSON log file (default: logs/transactions.jsonl)
            trading_mode: Trading mode ('backtest', 'paper', 'live')
        """
        self.database_manager = database_manager or DatabaseManager()
        self.trading_mode = trading_mode

        # Setup file paths
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        self.csv_path = csv_path or str(logs_dir / "transactions.csv")
        self.json_path = json_path or str(logs_dir / "transactions.jsonl")

        # Initialize CSV file with headers if it doesn't exist
        self._initialize_csv()

        # Track transaction IDs for updates
        self._transaction_map = {}  # trade_id -> transaction_id

    def _initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_path):
            headers = [
                "id",
                "symbol",
                "direction",
                "status",
                "entry_time",
                "entry_price",
                "position_size",
                "stop_loss",
                "target",
                "exit_time",
                "exit_price",
                "exit_reason",
                "pnl",
                "pnl_pct",
                "return_pct",
                "max_adverse_excursion",
                "max_favorable_excursion",
                "strategy_name",
                "trading_mode",
                "duration_seconds",
                "created_at",
            ]
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            logger.info(f"Created transaction CSV log: {self.csv_path}")

    def log_trade_entry(
        self,
        symbol: str,
        direction: str,
        entry_time: datetime,
        entry_price: float,
        position_size: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        strategy_name: str = "unknown",
        trade_id: Optional[str] = None,
    ) -> int:
        """
        Log a trade entry (opening position).

        Args:
            symbol: Trading symbol
            direction: 'LONG' or 'SHORT'
            entry_time: Entry timestamp
            entry_price: Entry price
            position_size: Number of shares/contracts
            stop_loss: Stop loss price
            target: Take profit target price
            strategy_name: Name of trading strategy
            trade_id: Unique trade identifier (for tracking updates)

        Returns:
            Transaction ID from database
        """
        # Create database transaction
        transaction = Transaction(
            symbol=symbol,
            direction=direction,
            status="OPEN",
            entry_time=entry_time,
            entry_price=Decimal(str(entry_price)),
            position_size=Decimal(str(position_size)),
            stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
            target=Decimal(str(target)) if target else None,
            strategy_name=strategy_name,
            trading_mode=self.trading_mode,
        )

        # Save to database
        with self.database_manager.get_session() as session:
            session.add(transaction)
            session.commit()
            transaction_id = transaction.id

        # Track for future updates
        if trade_id:
            self._transaction_map[trade_id] = transaction_id

        # Log to CSV
        self._append_to_csv(transaction)

        # Log to JSON
        self._append_to_json(transaction)

        logger.info(
            f"Trade entry logged: {symbol} {direction} @ {entry_price} "
            f"(size: {position_size}, strategy: {strategy_name})"
        )

        return transaction_id

    def log_trade_exit(
        self,
        transaction_id: int,
        exit_time: datetime,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        pnl_pct: float,
        return_pct: float,
        max_adverse_excursion: float = 0.0,
        max_favorable_excursion: float = 0.0,
        trade_id: Optional[str] = None,
    ) -> None:
        """
        Log a trade exit (closing position).

        Args:
            transaction_id: Database transaction ID (from log_trade_entry)
            exit_time: Exit timestamp
            exit_price: Exit price
            exit_reason: Reason for exit ('stop_loss', 'target', 'time_exit', etc.)
            pnl: Profit/loss in dollars
            pnl_pct: Profit/loss percentage
            return_pct: Return percentage
            max_adverse_excursion: Maximum adverse excursion (%)
            max_favorable_excursion: Maximum favorable excursion (%)
            trade_id: Unique trade identifier (optional, used if transaction_id not known)
        """
        # Get transaction_id from trade_id if needed
        if trade_id and not transaction_id:
            transaction_id = self._transaction_map.get(trade_id)
            if not transaction_id:
                logger.error(f"Cannot find transaction for trade_id: {trade_id}")
                return

        # Update database transaction
        with self.database_manager.get_session() as session:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found in database")
                return

            # Calculate duration
            duration = None
            if exit_time and transaction.entry_time:
                duration = int((exit_time - transaction.entry_time).total_seconds())

            # Update fields
            transaction.status = "CLOSED"
            transaction.exit_time = exit_time
            transaction.exit_price = Decimal(str(exit_price))
            transaction.exit_reason = exit_reason
            transaction.pnl = Decimal(str(pnl))
            transaction.pnl_pct = Decimal(str(pnl_pct))
            transaction.return_pct = Decimal(str(return_pct))
            transaction.max_adverse_excursion = Decimal(str(max_adverse_excursion))
            transaction.max_favorable_excursion = Decimal(str(max_favorable_excursion))
            transaction.duration_seconds = duration

            session.commit()

        # Append updated transaction to CSV (as new row for complete history)
        with self.database_manager.get_session() as session:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            self._append_to_csv(transaction)
            self._append_to_json(transaction)

        logger.info(
            f"Trade exit logged: {transaction.symbol} {transaction.direction} "
            f"@ {exit_price} (P&L: ${pnl:.2f}, {pnl_pct:.2f}%, reason: {exit_reason})"
        )

    def _append_to_csv(self, transaction: Transaction):
        """Append transaction to CSV file."""
        row = {
            "id": transaction.id,
            "symbol": transaction.symbol,
            "direction": transaction.direction,
            "status": transaction.status,
            "entry_time": transaction.entry_time.isoformat() if transaction.entry_time else "",
            "entry_price": float(transaction.entry_price) if transaction.entry_price else "",
            "position_size": float(transaction.position_size) if transaction.position_size else "",
            "stop_loss": float(transaction.stop_loss) if transaction.stop_loss else "",
            "target": float(transaction.target) if transaction.target else "",
            "exit_time": transaction.exit_time.isoformat() if transaction.exit_time else "",
            "exit_price": float(transaction.exit_price) if transaction.exit_price else "",
            "exit_reason": transaction.exit_reason or "",
            "pnl": float(transaction.pnl) if transaction.pnl else "",
            "pnl_pct": float(transaction.pnl_pct) if transaction.pnl_pct else "",
            "return_pct": float(transaction.return_pct) if transaction.return_pct else "",
            "max_adverse_excursion": (
                float(transaction.max_adverse_excursion) if transaction.max_adverse_excursion else ""
            ),
            "max_favorable_excursion": (
                float(transaction.max_favorable_excursion) if transaction.max_favorable_excursion else ""
            ),
            "strategy_name": transaction.strategy_name or "",
            "trading_mode": transaction.trading_mode or "",
            "duration_seconds": transaction.duration_seconds or "",
            "created_at": transaction.created_at.isoformat() if transaction.created_at else "",
        }

        with open(self.csv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)

    def _append_to_json(self, transaction: Transaction):
        """Append transaction to JSON Lines file."""
        row = {
            "id": transaction.id,
            "symbol": transaction.symbol,
            "direction": transaction.direction,
            "status": transaction.status,
            "entry_time": transaction.entry_time.isoformat() if transaction.entry_time else None,
            "entry_price": float(transaction.entry_price) if transaction.entry_price else None,
            "position_size": float(transaction.position_size) if transaction.position_size else None,
            "stop_loss": float(transaction.stop_loss) if transaction.stop_loss else None,
            "target": float(transaction.target) if transaction.target else None,
            "exit_time": transaction.exit_time.isoformat() if transaction.exit_time else None,
            "exit_price": float(transaction.exit_price) if transaction.exit_price else None,
            "exit_reason": transaction.exit_reason,
            "pnl": float(transaction.pnl) if transaction.pnl else None,
            "pnl_pct": float(transaction.pnl_pct) if transaction.pnl_pct else None,
            "return_pct": float(transaction.return_pct) if transaction.return_pct else None,
            "max_adverse_excursion": (
                float(transaction.max_adverse_excursion) if transaction.max_adverse_excursion else None
            ),
            "max_favorable_excursion": (
                float(transaction.max_favorable_excursion) if transaction.max_favorable_excursion else None
            ),
            "strategy_name": transaction.strategy_name,
            "trading_mode": transaction.trading_mode,
            "duration_seconds": transaction.duration_seconds,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
        }

        with open(self.json_path, "a") as f:
            f.write(json.dumps(row) + "\n")

    def get_all_transactions(self, status: Optional[str] = None) -> list:
        """
        Retrieve all transactions from database.

        Args:
            status: Filter by status ('OPEN', 'CLOSED', or None for all)

        Returns:
            List of Transaction objects
        """
        with self.database_manager.get_session() as session:
            query = session.query(Transaction)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(Transaction.entry_time.desc()).all()

    def get_transactions_by_symbol(self, symbol: str) -> list:
        """Get all transactions for a specific symbol."""
        with self.database_manager.get_session() as session:
            return (
                session.query(Transaction)
                .filter_by(symbol=symbol)
                .order_by(Transaction.entry_time.desc())
                .all()
            )

    def get_transactions_by_strategy(self, strategy_name: str) -> list:
        """Get all transactions for a specific strategy."""
        with self.database_manager.get_session() as session:
            return (
                session.query(Transaction)
                .filter_by(strategy_name=strategy_name)
                .order_by(Transaction.entry_time.desc())
                .all()
            )
