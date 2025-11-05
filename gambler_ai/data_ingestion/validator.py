"""
Data validation and quality checking for stock price data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy import and_, func

from gambler_ai.storage import DataQualityLog, StockPrice, get_timeseries_db
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class DataValidator:
    """Validate stock price data quality."""

    def __init__(self):
        """Initialize the validator."""
        self.db = get_timeseries_db()

    def validate_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
    ) -> Dict:
        """
        Validate data quality for a symbol and time period.

        Args:
            symbol: Stock ticker symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe to check

        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating data for {symbol} ({timeframe})")

        results = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "total_expected": 0,
            "total_actual": 0,
            "missing_periods": 0,
            "quality_score": 0.0,
            "issues": [],
        }

        try:
            # Fetch data from database
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

                data = pd.read_sql(query.statement, session.bind)

            if data.empty:
                results["issues"].append("No data found")
                results["quality_score"] = 0.0
                return results

            # Check for missing periods
            missing_info = self._check_missing_periods(data, timeframe, start_date, end_date)
            results["total_expected"] = missing_info["expected_periods"]
            results["total_actual"] = missing_info["actual_periods"]
            results["missing_periods"] = missing_info["missing_count"]

            if missing_info["missing_periods"]:
                results["issues"].append(
                    f"Missing {len(missing_info['missing_periods'])} time periods"
                )

            # Check for duplicate timestamps
            duplicates = self._check_duplicates(data)
            if duplicates:
                results["issues"].append(f"Found {len(duplicates)} duplicate timestamps")

            # Check for null values
            null_info = self._check_null_values(data)
            if null_info["has_nulls"]:
                results["issues"].append(
                    f"Null values found: {null_info['null_counts']}"
                )

            # Check for anomalies (extreme price movements, zero volume, etc.)
            anomalies = self._check_anomalies(data)
            if anomalies:
                results["issues"].extend(anomalies)

            # Calculate quality score
            results["quality_score"] = self._calculate_quality_score(results)

            logger.info(
                f"Validation complete for {symbol}: "
                f"Quality={results['quality_score']:.2f}, "
                f"Issues={len(results['issues'])}"
            )

        except Exception as e:
            logger.error(f"Error validating {symbol}: {e}", exc_info=True)
            results["issues"].append(f"Validation error: {str(e)}")

        return results

    def _check_missing_periods(
        self,
        data: pd.DataFrame,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict:
        """Check for missing time periods."""
        # Convert timeframe to frequency
        freq_map = {
            "1min": "1T",
            "5min": "5T",
            "15min": "15T",
            "30min": "30T",
            "1hour": "1H",
            "1day": "1D",
        }
        freq = freq_map.get(timeframe, "5T")

        # Generate expected timestamps (market hours only for intraday)
        if timeframe != "1day":
            expected = self._generate_market_hours_timestamps(
                start_date, end_date, freq
            )
        else:
            expected = pd.date_range(start=start_date, end=end_date, freq=freq)

        # Get actual timestamps
        actual = pd.to_datetime(data["timestamp"])

        # Find missing periods
        missing = expected.difference(actual)

        return {
            "expected_periods": len(expected),
            "actual_periods": len(actual),
            "missing_count": len(missing),
            "missing_periods": missing.tolist(),
        }

    def _generate_market_hours_timestamps(
        self,
        start_date: datetime,
        end_date: datetime,
        freq: str,
    ) -> pd.DatetimeIndex:
        """
        Generate timestamps for market hours only (9:30 AM - 4:00 PM ET).

        Note: This is a simplified version. A production system would need
        to account for market holidays, half days, etc.
        """
        # Generate all timestamps
        all_timestamps = pd.date_range(start=start_date, end=end_date, freq=freq)

        # Filter for market hours (simplified - assumes ET timezone)
        market_hours = []
        for ts in all_timestamps:
            # Market hours: 9:30 AM - 4:00 PM on weekdays
            if ts.weekday() < 5:  # Monday-Friday
                if (ts.hour == 9 and ts.minute >= 30) or (9 < ts.hour < 16):
                    market_hours.append(ts)

        return pd.DatetimeIndex(market_hours)

    def _check_duplicates(self, data: pd.DataFrame) -> List:
        """Check for duplicate timestamps."""
        duplicates = data[data.duplicated(subset=["timestamp"], keep=False)]
        return duplicates["timestamp"].tolist()

    def _check_null_values(self, data: pd.DataFrame) -> Dict:
        """Check for null values in important columns."""
        null_counts = {}
        important_cols = ["open", "high", "low", "close", "volume"]

        for col in important_cols:
            null_count = data[col].isnull().sum()
            if null_count > 0:
                null_counts[col] = null_count

        return {
            "has_nulls": len(null_counts) > 0,
            "null_counts": null_counts,
        }

    def _check_anomalies(self, data: pd.DataFrame) -> List[str]:
        """Check for data anomalies."""
        issues = []

        # Check for zero or negative prices
        if (data["close"] <= 0).any():
            count = (data["close"] <= 0).sum()
            issues.append(f"{count} periods with zero/negative close prices")

        # Check for zero volume
        if (data["volume"] == 0).any():
            count = (data["volume"] == 0).sum()
            issues.append(f"{count} periods with zero volume")

        # Check for extreme price movements (>50% in one period)
        data["price_change_pct"] = data["close"].pct_change() * 100
        extreme_moves = data[abs(data["price_change_pct"]) > 50]
        if not extreme_moves.empty:
            issues.append(
                f"{len(extreme_moves)} periods with extreme price movements (>50%)"
            )

        # Check for invalid OHLC relationships
        invalid_ohlc = data[
            (data["high"] < data["low"])
            | (data["high"] < data["close"])
            | (data["low"] > data["close"])
            | (data["high"] < data["open"])
            | (data["low"] > data["open"])
        ]
        if not invalid_ohlc.empty:
            issues.append(f"{len(invalid_ohlc)} periods with invalid OHLC relationships")

        return issues

    def _calculate_quality_score(self, results: Dict) -> float:
        """
        Calculate overall quality score (0-1).

        Score is based on:
        - Completeness (percentage of expected periods present)
        - Data integrity (no duplicates, nulls, anomalies)
        """
        # Completeness score (0-0.7)
        if results["total_expected"] > 0:
            completeness = results["total_actual"] / results["total_expected"]
            completeness_score = min(completeness, 1.0) * 0.7
        else:
            completeness_score = 0.0

        # Integrity score (0-0.3)
        # Deduct points for each type of issue
        integrity_score = 0.3
        issue_penalty = 0.05

        for issue in results["issues"]:
            if "duplicate" in issue.lower():
                integrity_score -= issue_penalty
            if "null" in issue.lower():
                integrity_score -= issue_penalty
            if "extreme" in issue.lower():
                integrity_score -= issue_penalty / 2  # Less severe
            if "invalid" in issue.lower():
                integrity_score -= issue_penalty

        integrity_score = max(integrity_score, 0.0)

        return completeness_score + integrity_score

    def log_quality_check(self, validation_results: Dict) -> None:
        """
        Save validation results to the database.

        Args:
            validation_results: Results from validate_data()
        """
        try:
            with self.db.get_session() as session:
                log_entry = DataQualityLog(
                    symbol=validation_results["symbol"],
                    check_date=validation_results["start_date"],
                    timeframe=validation_results["timeframe"],
                    missing_periods=validation_results["missing_periods"],
                    total_periods=validation_results["total_expected"],
                    quality_score=validation_results["quality_score"],
                    issues="; ".join(validation_results["issues"]),
                )
                session.add(log_entry)

            logger.info(
                f"Logged quality check for {validation_results['symbol']}"
            )

        except Exception as e:
            logger.error(f"Error logging quality check: {e}", exc_info=True)

    def batch_validate(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "5min",
        log_results: bool = True,
    ) -> List[Dict]:
        """
        Validate data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            timeframe: Timeframe to check
            log_results: Whether to log results to database

        Returns:
            List of validation results
        """
        results = []

        for symbol in symbols:
            try:
                validation = self.validate_data(symbol, start_date, end_date, timeframe)
                results.append(validation)

                if log_results:
                    self.log_quality_check(validation)

            except Exception as e:
                logger.error(f"Error validating {symbol}: {e}", exc_info=True)
                results.append({
                    "symbol": symbol,
                    "error": str(e),
                    "quality_score": 0.0,
                })

        # Summary
        avg_quality = sum(r.get("quality_score", 0) for r in results) / len(results)
        logger.info(
            f"Batch validation complete: {len(results)} symbols, "
            f"avg quality={avg_quality:.2f}"
        )

        return results
