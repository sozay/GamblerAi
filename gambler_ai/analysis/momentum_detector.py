"""
Momentum event detector for identifying significant price movements.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import and_

from gambler_ai.storage import MomentumEvent, StockPrice, get_timeseries_db
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class MomentumDetector:
    """Detect and analyze momentum events in stock price data."""

    def __init__(self):
        """Initialize the momentum detector."""
        self.db = get_timeseries_db()
        self.config = get_config()

        # Load configuration
        self.min_price_change_pct = self.config.get(
            "analysis.momentum_detection.min_price_change_pct", 2.0
        )
        self.min_volume_ratio = self.config.get(
            "analysis.momentum_detection.min_volume_ratio", 2.0
        )
        self.window_minutes = self.config.get(
            "analysis.momentum_detection.window_minutes", 5
        )
        self.lookback_periods = self.config.get(
            "analysis.momentum_detection.lookback_periods", 20
        )

    def detect_events(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
        save_to_db: bool = True,
    ) -> List[Dict]:
        """
        Detect momentum events for a symbol in a date range.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date for detection
            end_date: End date for detection
            timeframe: Timeframe to analyze
            save_to_db: Whether to save detected events to database

        Returns:
            List of detected momentum events
        """
        logger.info(
            f"Detecting momentum events for {symbol} "
            f"from {start_date} to {end_date} ({timeframe})"
        )

        # Fetch price data
        data = self._fetch_price_data(symbol, start_date, end_date, timeframe)

        if data.empty:
            logger.warning(f"No data found for {symbol}")
            return []

        # Calculate indicators
        data = self._calculate_indicators(data)

        # Detect events
        events = self._scan_for_events(data, symbol, timeframe)

        logger.info(f"Detected {len(events)} momentum events for {symbol}")

        # Save to database
        if save_to_db and events:
            self._save_events(events)

        return events

    def _fetch_price_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
    ) -> pd.DataFrame:
        """Fetch price data from database."""
        with self.db.get_session() as session:
            query = (
                session.query(StockPrice)
                .filter(
                    and_(
                        StockPrice.symbol == symbol,
                        StockPrice.timeframe == timeframe,
                        StockPrice.timestamp >= start_date,
                        StockPrice.timestamp <= end_date,
                    )
                )
                .order_by(StockPrice.timestamp)
            )

            df = pd.read_sql(query.statement, session.bind)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators needed for detection."""
        # Calculate rolling average volume
        df["avg_volume"] = df["volume"].rolling(window=self.lookback_periods).mean()

        # Volume ratio
        df["volume_ratio"] = df["volume"] / df["avg_volume"]

        # Price change in rolling window
        df["window_open"] = df["open"].shift(self.window_minutes - 1)
        df["price_change_pct"] = (
            (df["close"] - df["window_open"]) / df["window_open"] * 100
        )

        # Price momentum (rate of change)
        df["price_momentum"] = df["close"].pct_change(periods=self.window_minutes) * 100

        return df

    def _scan_for_events(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> List[Dict]:
        """Scan data for momentum events."""
        events = []

        for i in range(self.window_minutes, len(df)):
            row = df.iloc[i]

            # Skip if we don't have enough data
            if pd.isna(row["avg_volume"]) or pd.isna(row["price_change_pct"]):
                continue

            # Check if this qualifies as a momentum event
            abs_price_change = abs(row["price_change_pct"])

            if (
                abs_price_change >= self.min_price_change_pct
                and row["volume_ratio"] >= self.min_volume_ratio
            ):
                # Determine direction
                direction = "UP" if row["price_change_pct"] > 0 else "DOWN"

                # Get the window of data for this event
                window_start_idx = i - self.window_minutes + 1
                event_window = df.iloc[window_start_idx : i + 1]

                # Calculate event metrics
                start_time = event_window.iloc[0]["timestamp"]
                initial_price = float(event_window.iloc[0]["open"])
                peak_price = (
                    float(event_window["high"].max())
                    if direction == "UP"
                    else float(event_window["low"].min())
                )

                # Analyze continuation and reversal
                continuation_data = self._analyze_continuation(
                    df, i, direction, initial_price, peak_price
                )

                event = {
                    "symbol": symbol,
                    "start_time": start_time,
                    "end_time": row["timestamp"],
                    "direction": direction,
                    "initial_price": initial_price,
                    "peak_price": peak_price,
                    "duration_seconds": self.window_minutes * 60,  # Assuming minute data
                    "max_move_percentage": abs_price_change,
                    "initial_volume": int(event_window["volume"].sum()),
                    "timeframe": timeframe,
                    **continuation_data,
                }

                events.append(event)

                logger.debug(
                    f"Event detected: {symbol} {direction} "
                    f"{abs_price_change:.2f}% at {start_time}"
                )

        return events

    def _analyze_continuation(
        self,
        df: pd.DataFrame,
        event_end_idx: int,
        direction: str,
        initial_price: float,
        peak_price: float,
    ) -> Dict:
        """
        Analyze how long momentum continues and when/how it reverses.

        Args:
            df: Price data
            event_end_idx: Index where the initial momentum event ends
            direction: 'UP' or 'DOWN'
            initial_price: Starting price
            peak_price: Peak price during initial event

        Returns:
            Dictionary with continuation and reversal metrics
        """
        max_lookforward = 60  # Look forward up to 60 periods

        continuation_duration = 0
        reversal_percentage = None
        reversal_time = None

        # Define reversal threshold (e.g., 50% retracement of initial move)
        reversal_threshold_pct = self.config.get(
            "analysis.pattern_analysis.reversal_threshold_pct", 0.5
        )

        initial_move = abs(peak_price - initial_price)
        reversal_threshold_price = (
            peak_price - (initial_move * reversal_threshold_pct)
            if direction == "UP"
            else peak_price + (initial_move * reversal_threshold_pct)
        )

        current_peak = peak_price

        # Look forward to find continuation and reversal
        for j in range(event_end_idx + 1, min(event_end_idx + max_lookforward, len(df))):
            row = df.iloc[j]
            current_price = float(row["close"])

            # Check if momentum continues
            if direction == "UP":
                if current_price > current_peak:
                    current_peak = current_price
                    continuation_duration = (j - event_end_idx)

                # Check for reversal
                if current_price <= reversal_threshold_price and reversal_time is None:
                    reversal_time = (j - event_end_idx)
                    reversal_percentage = (
                        (current_peak - current_price) / current_peak * 100
                    )
                    break

            else:  # DOWN
                if current_price < current_peak:
                    current_peak = current_price
                    continuation_duration = (j - event_end_idx)

                # Check for reversal
                if current_price >= reversal_threshold_price and reversal_time is None:
                    reversal_time = (j - event_end_idx)
                    reversal_percentage = (
                        (current_price - current_peak) / current_peak * 100
                    )
                    break

        # Convert periods to seconds (assuming minute data)
        continuation_duration_seconds = continuation_duration * 60 if continuation_duration > 0 else None
        reversal_time_seconds = reversal_time * 60 if reversal_time else None

        return {
            "continuation_duration_seconds": continuation_duration_seconds,
            "reversal_percentage": float(reversal_percentage) if reversal_percentage else None,
            "reversal_time_seconds": reversal_time_seconds,
        }

    def _save_events(self, events: List[Dict]) -> None:
        """Save detected events to database."""
        try:
            with self.db.get_session() as session:
                for event_data in events:
                    event = MomentumEvent(**event_data)
                    session.add(event)

            logger.info(f"✓ Saved {len(events)} events to database")

        except Exception as e:
            logger.error(f"Error saving events: {e}", exc_info=True)
            raise

    def get_events(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        direction: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> List[MomentumEvent]:
        """
        Retrieve momentum events from database with optional filters.

        Args:
            symbol: Filter by symbol
            start_date: Filter by start date
            end_date: Filter by end date
            direction: Filter by direction ('UP' or 'DOWN')
            timeframe: Filter by timeframe

        Returns:
            List of MomentumEvent objects
        """
        with self.db.get_session() as session:
            query = session.query(MomentumEvent)

            if symbol:
                query = query.filter(MomentumEvent.symbol == symbol)
            if start_date:
                query = query.filter(MomentumEvent.start_time >= start_date)
            if end_date:
                query = query.filter(MomentumEvent.start_time <= end_date)
            if direction:
                query = query.filter(MomentumEvent.direction == direction)
            if timeframe:
                query = query.filter(MomentumEvent.timeframe == timeframe)

            events = query.order_by(MomentumEvent.start_time.desc()).all()

        return events

    def batch_detect(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
    ) -> Dict:
        """
        Detect momentum events for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            timeframe: Timeframe

        Returns:
            Dictionary with detection statistics
        """
        stats = {
            "symbols_processed": 0,
            "total_events": 0,
            "events_by_symbol": {},
            "errors": [],
        }

        for symbol in symbols:
            try:
                events = self.detect_events(
                    symbol, start_date, end_date, timeframe, save_to_db=True
                )

                stats["symbols_processed"] += 1
                stats["total_events"] += len(events)
                stats["events_by_symbol"][symbol] = len(events)

            except Exception as e:
                error_msg = f"Error processing {symbol}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        logger.info(
            f"Batch detection complete: {stats['symbols_processed']} symbols, "
            f"{stats['total_events']} events, {len(stats['errors'])} errors"
        )

        return stats
