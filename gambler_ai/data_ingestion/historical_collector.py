"""
Historical stock data collector using multiple data sources.
"""

from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert

from gambler_ai.storage import StockPrice, get_timeseries_db
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class HistoricalDataCollector:
    """Collect historical stock price data from various sources."""

    def __init__(self):
        """Initialize the data collector."""
        self.db = get_timeseries_db()

    def collect_yahoo_finance(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "5m",
    ) -> pd.DataFrame:
        """
        Collect historical data from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            start_date: Start date for data collection
            end_date: End date for data collection
            interval: Data interval ('1m', '5m', '15m', '1h', '1d')

        Returns:
            DataFrame with OHLCV data
        """
        logger.info(
            f"Collecting {interval} data for {symbol} from {start_date} to {end_date}"
        )

        try:
            ticker = yf.Ticker(symbol)

            # Yahoo Finance has limitations:
            # - 1m data: max 7 days
            # - 5m, 15m, 30m, 1h data: max 60 days
            # We need to chunk the requests

            all_data = []
            current_start = start_date
            chunk_days = self._get_chunk_size(interval)

            while current_start < end_date:
                current_end = min(current_start + timedelta(days=chunk_days), end_date)

                logger.debug(f"Fetching chunk: {current_start} to {current_end}")

                # Fetch data
                df = ticker.history(
                    start=current_start.strftime("%Y-%m-%d"),
                    end=current_end.strftime("%Y-%m-%d"),
                    interval=interval,
                    actions=False,  # Don't include dividends/splits
                )

                if not df.empty:
                    all_data.append(df)

                current_start = current_end

            if not all_data:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Combine all chunks
            result = pd.concat(all_data)

            # Standardize column names
            result.columns = [col.lower() for col in result.columns]

            # Reset index to make timestamp a column
            result = result.reset_index()
            result.rename(columns={"date": "timestamp", "index": "timestamp"}, inplace=True)

            logger.info(f"Collected {len(result)} rows for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Error collecting data for {symbol}: {e}", exc_info=True)
            raise

    def _get_chunk_size(self, interval: str) -> int:
        """Get appropriate chunk size based on interval."""
        chunk_sizes = {
            "1m": 7,
            "2m": 7,
            "5m": 60,
            "15m": 60,
            "30m": 60,
            "60m": 60,
            "1h": 60,
            "1d": 365,
        }
        return chunk_sizes.get(interval, 60)

    def save_to_database(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        upsert: bool = True,
    ) -> int:
        """
        Save collected data to database.

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol
            timeframe: Timeframe (e.g., '5min')
            upsert: If True, update existing records; if False, skip duplicates

        Returns:
            Number of rows inserted/updated
        """
        if df.empty:
            logger.warning(f"No data to save for {symbol}")
            return 0

        logger.info(f"Saving {len(df)} rows for {symbol} ({timeframe})")

        try:
            # Prepare data for insertion
            records = []
            for _, row in df.iterrows():
                records.append({
                    "symbol": symbol,
                    "timestamp": row["timestamp"],
                    "open": float(row["open"]) if pd.notna(row["open"]) else None,
                    "high": float(row["high"]) if pd.notna(row["high"]) else None,
                    "low": float(row["low"]) if pd.notna(row["low"]) else None,
                    "close": float(row["close"]) if pd.notna(row["close"]) else None,
                    "volume": int(row["volume"]) if pd.notna(row["volume"]) else None,
                    "timeframe": timeframe,
                })

            with self.db.get_session() as session:
                if upsert:
                    # Use PostgreSQL's ON CONFLICT DO UPDATE
                    stmt = insert(StockPrice).values(records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["symbol", "timestamp", "timeframe"],
                        set_={
                            "open": stmt.excluded.open,
                            "high": stmt.excluded.high,
                            "low": stmt.excluded.low,
                            "close": stmt.excluded.close,
                            "volume": stmt.excluded.volume,
                        },
                    )
                    session.execute(stmt)
                else:
                    # Use ON CONFLICT DO NOTHING
                    stmt = insert(StockPrice).values(records)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["symbol", "timestamp", "timeframe"]
                    )
                    session.execute(stmt)

            logger.info(f"✓ Saved {len(records)} rows for {symbol}")
            return len(records)

        except Exception as e:
            logger.error(f"Error saving data for {symbol}: {e}", exc_info=True)
            raise

    def collect_and_save(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        intervals: List[str] = ["5m"],
    ) -> dict:
        """
        Collect and save data for multiple symbols and intervals.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            intervals: List of intervals to collect

        Returns:
            Dictionary with collection statistics
        """
        stats = {
            "symbols_processed": 0,
            "total_rows": 0,
            "errors": [],
        }

        for symbol in symbols:
            for interval in intervals:
                try:
                    # Convert interval to timeframe format
                    timeframe = self._interval_to_timeframe(interval)

                    # Collect data
                    df = self.collect_yahoo_finance(symbol, start_date, end_date, interval)

                    if not df.empty:
                        # Save to database
                        rows = self.save_to_database(df, symbol, timeframe)
                        stats["total_rows"] += rows

                    stats["symbols_processed"] += 1

                except Exception as e:
                    error_msg = f"Error processing {symbol} ({interval}): {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

        logger.info(
            f"Collection complete: {stats['symbols_processed']} symbols, "
            f"{stats['total_rows']} rows, {len(stats['errors'])} errors"
        )

        return stats

    def _interval_to_timeframe(self, interval: str) -> str:
        """Convert Yahoo Finance interval to our timeframe format."""
        mapping = {
            "1m": "1min",
            "2m": "2min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "60m": "1hour",
            "1h": "1hour",
            "1d": "1day",
        }
        return mapping.get(interval, interval)

    def get_latest_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """
        Get the latest timestamp for a symbol/timeframe in the database.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe

        Returns:
            Latest timestamp or None if no data exists
        """
        with self.db.get_session() as session:
            result = (
                session.query(StockPrice.timestamp)
                .filter(
                    StockPrice.symbol == symbol,
                    StockPrice.timeframe == timeframe,
                )
                .order_by(StockPrice.timestamp.desc())
                .first()
            )

            return result[0] if result else None

    def incremental_update(
        self,
        symbols: List[str],
        intervals: List[str] = ["5m"],
        lookback_days: int = 7,
    ) -> dict:
        """
        Incrementally update data for symbols.

        This checks the latest data in the database and only fetches new data.

        Args:
            symbols: List of stock symbols
            intervals: List of intervals
            lookback_days: Days to look back if no data exists

        Returns:
            Collection statistics
        """
        stats = {
            "symbols_updated": 0,
            "total_rows": 0,
            "errors": [],
        }

        end_date = datetime.now()

        for symbol in symbols:
            for interval in intervals:
                try:
                    timeframe = self._interval_to_timeframe(interval)

                    # Get latest timestamp
                    latest = self.get_latest_timestamp(symbol, timeframe)

                    if latest:
                        # Start from latest timestamp
                        start_date = latest + timedelta(minutes=1)
                        logger.info(f"Updating {symbol} from {start_date}")
                    else:
                        # No data exists, fetch lookback period
                        start_date = end_date - timedelta(days=lookback_days)
                        logger.info(f"No data for {symbol}, fetching {lookback_days} days")

                    if start_date >= end_date:
                        logger.info(f"{symbol} is up to date")
                        continue

                    # Collect and save
                    df = self.collect_yahoo_finance(symbol, start_date, end_date, interval)

                    if not df.empty:
                        rows = self.save_to_database(df, symbol, timeframe)
                        stats["total_rows"] += rows

                    stats["symbols_updated"] += 1

                except Exception as e:
                    error_msg = f"Error updating {symbol} ({interval}): {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

        logger.info(
            f"Update complete: {stats['symbols_updated']} symbols, "
            f"{stats['total_rows']} new rows, {len(stats['errors'])} errors"
        )

        return stats
