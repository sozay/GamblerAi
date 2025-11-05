"""
Pattern analyzer for classifying and analyzing momentum event patterns.
"""

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import and_, func

from gambler_ai.storage import MomentumEvent, PatternStatistic, get_timeseries_db
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class PatternAnalyzer:
    """Analyze and classify momentum event patterns."""

    def __init__(self):
        """Initialize the pattern analyzer."""
        self.db = get_timeseries_db()
        self.config = get_config()

        # Load thresholds from config
        self.strong_continuation_threshold = self.config.get(
            "analysis.pattern_analysis.continuation_thresholds.strong", 0.70
        )
        self.moderate_continuation_threshold = self.config.get(
            "analysis.pattern_analysis.continuation_thresholds.moderate", 0.40
        )

    def analyze_patterns(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        min_samples: int = 100,
    ) -> List[Dict]:
        """
        Analyze patterns from detected momentum events.

        Args:
            symbol: Optionally filter by symbol (None = all symbols)
            timeframe: Optionally filter by timeframe
            min_samples: Minimum number of samples required for analysis

        Returns:
            List of pattern analysis results
        """
        logger.info(f"Analyzing patterns for symbol={symbol}, timeframe={timeframe}")

        # Fetch momentum events
        events_df = self._fetch_events(symbol, timeframe)

        if events_df.empty:
            logger.warning("No events found for analysis")
            return []

        logger.info(f"Analyzing {len(events_df)} momentum events")

        # Classify events
        events_df = self._classify_events(events_df)

        # Group by pattern type, timeframe, and direction
        patterns = []

        for (pattern_type, tf, direction), group in events_df.groupby(
            ["pattern_type", "timeframe", "direction"]
        ):
            if len(group) < min_samples:
                logger.debug(
                    f"Skipping {pattern_type}/{tf}/{direction}: "
                    f"only {len(group)} samples (min {min_samples})"
                )
                continue

            pattern_stats = self._calculate_pattern_statistics(
                group, pattern_type, tf, direction
            )
            patterns.append(pattern_stats)

        logger.info(f"Identified {len(patterns)} significant patterns")

        return patterns

    def _fetch_events(
        self,
        symbol: Optional[str],
        timeframe: Optional[str],
    ) -> pd.DataFrame:
        """Fetch momentum events from database."""
        with self.db.get_session() as session:
            query = session.query(MomentumEvent)

            if symbol:
                query = query.filter(MomentumEvent.symbol == symbol)
            if timeframe:
                query = query.filter(MomentumEvent.timeframe == timeframe)

            df = pd.read_sql(query.statement, session.bind)

        return df

    def _classify_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify events into pattern types based on continuation behavior."""

        def classify_event(row):
            """Classify a single event."""
            if pd.isna(row["continuation_duration_seconds"]):
                return "unknown"

            # Calculate continuation ratio
            # (How much of the initial move continued?)
            continuation_seconds = row["continuation_duration_seconds"] or 0
            initial_duration = row["duration_seconds"]

            if initial_duration > 0:
                continuation_ratio = continuation_seconds / initial_duration
            else:
                continuation_ratio = 0

            # Classify based on thresholds
            if continuation_ratio >= self.strong_continuation_threshold:
                return "strong_continuation"
            elif continuation_ratio >= self.moderate_continuation_threshold:
                return "moderate_continuation"
            else:
                return "weak_continuation"

        df["pattern_type"] = df.apply(classify_event, axis=1)

        return df

    def _calculate_pattern_statistics(
        self,
        group: pd.DataFrame,
        pattern_type: str,
        timeframe: str,
        direction: str,
    ) -> Dict:
        """Calculate statistical metrics for a pattern group."""

        # Filter out None values
        continuation_data = group[group["continuation_duration_seconds"].notna()][
            "continuation_duration_seconds"
        ]
        reversal_pct_data = group[group["reversal_percentage"].notna()][
            "reversal_percentage"
        ]
        reversal_time_data = group[group["reversal_time_seconds"].notna()][
            "reversal_time_seconds"
        ]

        stats = {
            "pattern_type": pattern_type,
            "timeframe": timeframe,
            "direction": direction,
            "sample_size": len(group),
            # Continuation statistics
            "avg_continuation_duration": (
                int(continuation_data.mean()) if not continuation_data.empty else None
            ),
            "median_continuation_duration": (
                int(continuation_data.median()) if not continuation_data.empty else None
            ),
            "std_continuation_duration": (
                float(continuation_data.std()) if not continuation_data.empty else None
            ),
            # Reversal percentage statistics
            "avg_reversal_percentage": (
                float(reversal_pct_data.mean()) if not reversal_pct_data.empty else None
            ),
            "median_reversal_percentage": (
                float(reversal_pct_data.median()) if not reversal_pct_data.empty else None
            ),
            "std_reversal_percentage": (
                float(reversal_pct_data.std()) if not reversal_pct_data.empty else None
            ),
            # Reversal timing statistics
            "avg_reversal_time": (
                int(reversal_time_data.mean()) if not reversal_time_data.empty else None
            ),
            "median_reversal_time": (
                int(reversal_time_data.median()) if not reversal_time_data.empty else None
            ),
            "std_reversal_time": (
                float(reversal_time_data.std()) if not reversal_time_data.empty else None
            ),
            # Initial move statistics
            "avg_initial_move_pct": float(group["max_move_percentage"].mean()),
            "median_initial_move_pct": float(group["max_move_percentage"].median()),
            # Confidence metrics
            "confidence_score": self._calculate_confidence_score(group),
            "win_rate": self._calculate_win_rate(group),
        }

        return stats

    def _calculate_confidence_score(self, group: pd.DataFrame) -> float:
        """
        Calculate confidence score based on sample size and consistency.

        Score is 0-1, with 1 being most confident.
        """
        sample_size = len(group)

        # Sample size score (0-0.5)
        # Give full score at 1000+ samples
        size_score = min(sample_size / 1000, 1.0) * 0.5

        # Consistency score (0-0.5)
        # Based on coefficient of variation of continuation duration
        continuation_data = group[group["continuation_duration_seconds"].notna()][
            "continuation_duration_seconds"
        ]

        if not continuation_data.empty and continuation_data.mean() > 0:
            cv = continuation_data.std() / continuation_data.mean()
            # Lower CV = higher consistency = higher score
            consistency_score = max(0, 1 - cv) * 0.5
        else:
            consistency_score = 0.0

        return round(size_score + consistency_score, 2)

    def _calculate_win_rate(self, group: pd.DataFrame) -> float:
        """
        Calculate win rate (percentage of events with profitable continuation).

        A "win" is defined as continuation duration > initial duration.
        """
        wins = group[
            (group["continuation_duration_seconds"].notna())
            & (
                group["continuation_duration_seconds"]
                > group["duration_seconds"]
            )
        ]

        if len(group) > 0:
            return round(len(wins) / len(group), 2)
        return 0.0

    def save_pattern_statistics(self, patterns: List[Dict]) -> None:
        """Save pattern statistics to database."""
        try:
            with self.db.get_session() as session:
                for pattern_data in patterns:
                    # Check if pattern exists, update if yes
                    existing = (
                        session.query(PatternStatistic)
                        .filter(
                            and_(
                                PatternStatistic.pattern_type
                                == pattern_data["pattern_type"],
                                PatternStatistic.timeframe == pattern_data["timeframe"],
                                PatternStatistic.direction == pattern_data["direction"],
                            )
                        )
                        .first()
                    )

                    if existing:
                        # Update existing record
                        for key, value in pattern_data.items():
                            if key not in ["pattern_type", "timeframe", "direction"]:
                                setattr(existing, key, value)
                        existing.last_updated = datetime.now()
                    else:
                        # Create new record
                        pattern = PatternStatistic(**pattern_data)
                        session.add(pattern)

            logger.info(f"✓ Saved {len(patterns)} pattern statistics to database")

        except Exception as e:
            logger.error(f"Error saving pattern statistics: {e}", exc_info=True)
            raise

    def get_pattern_statistics(
        self,
        pattern_type: Optional[str] = None,
        timeframe: Optional[str] = None,
        direction: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[PatternStatistic]:
        """
        Retrieve pattern statistics from database with optional filters.

        Args:
            pattern_type: Filter by pattern type
            timeframe: Filter by timeframe
            direction: Filter by direction
            min_confidence: Minimum confidence score

        Returns:
            List of PatternStatistic objects
        """
        with self.db.get_session() as session:
            query = session.query(PatternStatistic)

            if pattern_type:
                query = query.filter(PatternStatistic.pattern_type == pattern_type)
            if timeframe:
                query = query.filter(PatternStatistic.timeframe == timeframe)
            if direction:
                query = query.filter(PatternStatistic.direction == direction)
            if min_confidence > 0:
                query = query.filter(PatternStatistic.confidence_score >= min_confidence)

            patterns = query.order_by(
                PatternStatistic.confidence_score.desc(),
                PatternStatistic.sample_size.desc(),
            ).all()

        return patterns

    def generate_pattern_report(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> Dict:
        """
        Generate a comprehensive pattern analysis report.

        Args:
            symbol: Filter by symbol
            timeframe: Filter by timeframe

        Returns:
            Dictionary with report data
        """
        logger.info(f"Generating pattern report for {symbol or 'all symbols'}")

        # Analyze patterns
        patterns = self.analyze_patterns(symbol, timeframe)

        if not patterns:
            return {
                "error": "No patterns found for analysis",
                "symbol": symbol,
                "timeframe": timeframe,
            }

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(patterns)

        report = {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_patterns": len(patterns),
            "total_samples": int(df["sample_size"].sum()),
            "patterns_by_type": df.groupby("pattern_type")["sample_size"]
            .sum()
            .to_dict(),
            "patterns_by_direction": df.groupby("direction")["sample_size"]
            .sum()
            .to_dict(),
            "highest_confidence_patterns": df.nlargest(5, "confidence_score")[
                ["pattern_type", "direction", "confidence_score", "sample_size"]
            ].to_dict("records"),
            "best_win_rates": df.nlargest(5, "win_rate")[
                ["pattern_type", "direction", "win_rate", "sample_size"]
            ].to_dict("records"),
            "avg_continuation_duration_seconds": float(
                df[df["avg_continuation_duration"].notna()][
                    "avg_continuation_duration"
                ].mean()
            ),
            "avg_reversal_percentage": float(
                df[df["avg_reversal_percentage"].notna()][
                    "avg_reversal_percentage"
                ].mean()
            ),
        }

        logger.info(f"Report generated with {len(patterns)} patterns")

        return report
