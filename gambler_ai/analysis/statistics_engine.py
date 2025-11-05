"""
Statistics engine for calculating probabilities and predictions.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sqlalchemy import and_

from gambler_ai.storage import MomentumEvent, PatternStatistic, get_timeseries_db
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class StatisticsEngine:
    """Calculate statistical metrics and predictions for momentum trading."""

    def __init__(self):
        """Initialize the statistics engine."""
        self.db = get_timeseries_db()
        self.config = get_config()
        self.confidence_level = self.config.get(
            "analysis.statistics.confidence_level", 0.95
        )

    def predict_continuation(
        self,
        symbol: str,
        initial_move_pct: float,
        volume_ratio: float,
        timeframe: str = "5min",
        direction: Optional[str] = None,
    ) -> Dict:
        """
        Predict continuation probability and metrics for a current momentum event.

        Args:
            symbol: Stock symbol
            initial_move_pct: Initial price move percentage
            volume_ratio: Current volume vs average
            timeframe: Timeframe
            direction: Optional direction ('UP' or 'DOWN')

        Returns:
            Dictionary with prediction metrics
        """
        logger.info(
            f"Predicting continuation for {symbol}: "
            f"move={initial_move_pct}%, vol_ratio={volume_ratio}"
        )

        # Fetch similar historical events
        similar_events = self._find_similar_events(
            symbol, initial_move_pct, volume_ratio, timeframe, direction
        )

        if similar_events.empty:
            return {
                "error": "Insufficient historical data",
                "recommendation": "INSUFFICIENT_DATA",
            }

        # Calculate prediction metrics
        prediction = self._calculate_prediction_metrics(similar_events)

        # Add context
        prediction["symbol"] = symbol
        prediction["initial_move_pct"] = initial_move_pct
        prediction["volume_ratio"] = volume_ratio
        prediction["timeframe"] = timeframe
        prediction["sample_size"] = len(similar_events)

        # Generate recommendation
        prediction["recommendation"] = self._generate_recommendation(prediction)

        logger.info(
            f"Prediction: continuation_prob={prediction['continuation_probability']:.2f}, "
            f"recommendation={prediction['recommendation']}"
        )

        return prediction

    def _find_similar_events(
        self,
        symbol: str,
        initial_move_pct: float,
        volume_ratio: float,
        timeframe: str,
        direction: Optional[str],
        tolerance: float = 0.5,
    ) -> pd.DataFrame:
        """
        Find similar historical events.

        Args:
            symbol: Stock symbol (can also look at other stocks)
            initial_move_pct: Initial move percentage
            volume_ratio: Volume ratio
            timeframe: Timeframe
            direction: Direction filter
            tolerance: Tolerance for matching (0.5 = ±50%)

        Returns:
            DataFrame of similar events
        """
        with self.db.get_session() as session:
            query = session.query(MomentumEvent)

            # Filter by timeframe
            query = query.filter(MomentumEvent.timeframe == timeframe)

            # Optionally filter by direction
            if direction:
                query = query.filter(MomentumEvent.direction == direction)

            # Fetch all events, then filter by similarity
            df = pd.read_sql(query.statement, session.bind)

        if df.empty:
            return df

        # Filter by similar magnitude
        abs_initial_move = abs(initial_move_pct)
        lower_bound = abs_initial_move * (1 - tolerance)
        upper_bound = abs_initial_move * (1 + tolerance)

        similar = df[
            (abs(df["max_move_percentage"]) >= lower_bound)
            & (abs(df["max_move_percentage"]) <= upper_bound)
        ]

        logger.debug(
            f"Found {len(similar)} similar events "
            f"(move {lower_bound:.1f}%-{upper_bound:.1f}%)"
        )

        return similar

    def _calculate_prediction_metrics(self, events: pd.DataFrame) -> Dict:
        """Calculate prediction metrics from similar events."""

        # Filter events with continuation data
        continuation_events = events[
            events["continuation_duration_seconds"].notna()
        ].copy()

        # Filter events with reversal data
        reversal_events = events[
            (events["reversal_percentage"].notna())
            & (events["reversal_time_seconds"].notna())
        ].copy()

        metrics = {}

        # Continuation probability
        if not continuation_events.empty:
            # Events with continuation > 0 are considered successful continuations
            successful_continuations = continuation_events[
                continuation_events["continuation_duration_seconds"] > 0
            ]
            metrics["continuation_probability"] = round(
                len(successful_continuations) / len(continuation_events), 2
            )

            # Expected continuation duration
            metrics["expected_continuation_minutes"] = round(
                continuation_events["continuation_duration_seconds"].mean() / 60, 1
            )
            metrics["median_continuation_minutes"] = round(
                continuation_events["continuation_duration_seconds"].median() / 60, 1
            )

            # Confidence interval for continuation duration
            ci_low, ci_high = self._calculate_confidence_interval(
                continuation_events["continuation_duration_seconds"].dropna()
            )
            metrics["continuation_ci_low_minutes"] = round(ci_low / 60, 1)
            metrics["continuation_ci_high_minutes"] = round(ci_high / 60, 1)

        else:
            metrics["continuation_probability"] = 0.0
            metrics["expected_continuation_minutes"] = 0.0

        # Reversal metrics
        if not reversal_events.empty:
            metrics["reversal_probability"] = round(
                len(reversal_events) / len(events), 2
            )

            # Expected reversal percentage
            metrics["expected_reversal_pct"] = round(
                reversal_events["reversal_percentage"].mean(), 2
            )
            metrics["median_reversal_pct"] = round(
                reversal_events["reversal_percentage"].median(), 2
            )

            # Expected reversal time
            metrics["expected_reversal_time_minutes"] = round(
                reversal_events["reversal_time_seconds"].mean() / 60, 1
            )
            metrics["median_reversal_time_minutes"] = round(
                reversal_events["reversal_time_seconds"].median() / 60, 1
            )

        else:
            metrics["reversal_probability"] = 0.0

        # Calculate overall confidence score
        metrics["confidence"] = self._calculate_prediction_confidence(events)

        return metrics

    def _calculate_confidence_interval(
        self, data: pd.Series, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for a dataset."""
        if len(data) < 2:
            mean = data.mean() if not data.empty else 0
            return (mean, mean)

        mean = data.mean()
        std_err = scipy_stats.sem(data)
        ci = scipy_stats.t.interval(
            confidence, len(data) - 1, loc=mean, scale=std_err
        )

        return ci

    def _calculate_prediction_confidence(self, events: pd.DataFrame) -> float:
        """
        Calculate confidence score for prediction (0-1).

        Based on sample size and data quality.
        """
        sample_size = len(events)

        # Sample size score (0-0.6)
        # Full score at 500+ samples
        size_score = min(sample_size / 500, 1.0) * 0.6

        # Data completeness score (0-0.4)
        # Percentage of events with continuation and reversal data
        continuation_completeness = events["continuation_duration_seconds"].notna().mean()
        reversal_completeness = events["reversal_percentage"].notna().mean()
        completeness_score = (continuation_completeness + reversal_completeness) / 2 * 0.4

        return round(size_score + completeness_score, 2)

    def _generate_recommendation(self, prediction: Dict) -> str:
        """
        Generate trading recommendation based on prediction metrics.

        Returns:
            'STRONG_ENTER', 'ENTER', 'WAIT', 'NO_ENTER', or 'INSUFFICIENT_DATA'
        """
        if prediction.get("confidence", 0) < 0.3:
            return "INSUFFICIENT_DATA"

        continuation_prob = prediction.get("continuation_probability", 0)
        expected_continuation = prediction.get("expected_continuation_minutes", 0)

        # Strong entry signal
        if continuation_prob >= 0.70 and expected_continuation >= 10:
            return "STRONG_ENTER"

        # Good entry signal
        if continuation_prob >= 0.60 and expected_continuation >= 5:
            return "ENTER"

        # Moderate signal - wait for better setup
        if continuation_prob >= 0.50:
            return "WAIT"

        # Weak signal - don't enter
        return "NO_ENTER"

    def calculate_risk_reward(
        self,
        entry_price: float,
        expected_continuation_pct: float,
        expected_reversal_pct: float,
        stop_loss_pct: float = 1.0,
    ) -> Dict:
        """
        Calculate risk/reward ratio for a trade.

        Args:
            entry_price: Entry price
            expected_continuation_pct: Expected continuation percentage
            expected_reversal_pct: Expected reversal percentage
            stop_loss_pct: Stop loss percentage

        Returns:
            Dictionary with risk/reward metrics
        """
        # Calculate target price (continuation)
        target_price = entry_price * (1 + expected_continuation_pct / 100)

        # Calculate stop loss price
        stop_loss_price = entry_price * (1 - stop_loss_pct / 100)

        # Calculate potential gain and loss
        potential_gain = target_price - entry_price
        potential_loss = entry_price - stop_loss_price

        # Risk/Reward ratio
        rr_ratio = potential_gain / potential_loss if potential_loss > 0 else 0

        return {
            "entry_price": round(entry_price, 2),
            "target_price": round(target_price, 2),
            "stop_loss_price": round(stop_loss_price, 2),
            "potential_gain": round(potential_gain, 2),
            "potential_loss": round(potential_loss, 2),
            "risk_reward_ratio": round(rr_ratio, 2),
            "expected_continuation_pct": expected_continuation_pct,
            "expected_reversal_pct": expected_reversal_pct,
        }

    def get_probability_distribution(
        self,
        symbol: str,
        timeframe: str = "5min",
        direction: Optional[str] = None,
        metric: str = "continuation_duration_seconds",
    ) -> Dict:
        """
        Get probability distribution for a specific metric.

        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            direction: Optional direction filter
            metric: Metric to analyze (e.g., 'continuation_duration_seconds')

        Returns:
            Dictionary with distribution statistics
        """
        with self.db.get_session() as session:
            query = session.query(MomentumEvent).filter(
                MomentumEvent.timeframe == timeframe
            )

            if direction:
                query = query.filter(MomentumEvent.direction == direction)

            df = pd.read_sql(query.statement, session.bind)

        if df.empty or metric not in df.columns:
            return {"error": "No data available"}

        data = df[df[metric].notna()][metric]

        if data.empty:
            return {"error": "No data for this metric"}

        # Calculate distribution statistics
        distribution = {
            "metric": metric,
            "count": len(data),
            "mean": round(float(data.mean()), 2),
            "median": round(float(data.median()), 2),
            "std": round(float(data.std()), 2),
            "min": round(float(data.min()), 2),
            "max": round(float(data.max()), 2),
            "percentiles": {
                "25th": round(float(data.quantile(0.25)), 2),
                "50th": round(float(data.quantile(0.50)), 2),
                "75th": round(float(data.quantile(0.75)), 2),
                "90th": round(float(data.quantile(0.90)), 2),
                "95th": round(float(data.quantile(0.95)), 2),
            },
        }

        return distribution
