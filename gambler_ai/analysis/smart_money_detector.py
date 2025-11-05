"""
Smart Money Tracker strategy detector.

Detects institutional order flow patterns and follows smart money.

Entry Logic:
- Large volume anomaly (>5x average) indicating institutional activity
- Price absorption (high volume, low price movement)
- VWAP reclaim or level defense

Exit Logic:
- Target: Previous swing high/low
- Stop: Below accumulation zone
- Time stop: 90 minutes
"""

from typing import Dict, List
import pandas as pd
import numpy as np

from gambler_ai.analysis.indicators import (
    calculate_volume_ratio,
    calculate_vwap,
    calculate_ema,
)


class SmartMoneyDetector:
    """Detect smart money (institutional) activity."""

    def __init__(
        self,
        volume_anomaly_threshold: float = 5.0,
        absorption_efficiency_threshold: float = 0.5,
        level_test_min: int = 2,
    ):
        """
        Initialize smart money detector.

        Args:
            volume_anomaly_threshold: Volume spike threshold (5x = institutional)
            absorption_efficiency_threshold: Price/volume efficiency for absorption
            level_test_min: Minimum level tests for support/resistance
        """
        self.volume_anomaly_threshold = volume_anomaly_threshold
        self.absorption_efficiency_threshold = absorption_efficiency_threshold
        self.level_test_min = level_test_min

    def detect_setups(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect smart money patterns.

        Patterns:
        1. Absorption: High volume, narrow spread (institutions accumulating)
        2. VWAP Reclaim: Price reclaims VWAP after breakdown
        3. Level Defense: Multiple tests of support with decreasing range

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of detected setups
        """
        df = df.copy()

        # Add indicators
        df = self._add_indicators(df)

        setups = []

        # Detect absorption patterns
        absorptions = self._detect_absorption(df)
        setups.extend(absorptions)

        # Detect VWAP reclaims
        vwap_setups = self._detect_vwap_reclaim(df)
        setups.extend(vwap_setups)

        # Detect level defense patterns
        level_defense = self._detect_level_defense(df)
        setups.extend(level_defense)

        return setups

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add required indicators."""
        # Volume
        df['volume_ratio'] = calculate_volume_ratio(df['volume'], 20)
        df['avg_volume'] = df['volume'].rolling(20).mean()

        # VWAP
        df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])

        # Price spread
        df['spread'] = df['high'] - df['low']
        df['spread_pct'] = (df['spread'] / df['open']) * 100

        # EMA for swing points
        df['ema_20'] = calculate_ema(df['close'], 20)

        return df

    def _detect_absorption(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect volume absorption patterns.

        Absorption = High volume but price doesn't move proportionally.
        This indicates large orders being absorbed (accumulation/distribution).
        """
        setups = []

        for i in range(20, len(df)):
            row = df.iloc[i]

            # Check for volume anomaly
            if row['volume_ratio'] < self.volume_anomaly_threshold:
                continue

            # Calculate spread efficiency
            # Expected: high volume should cause large price movement
            # Absorption: high volume but small movement
            avg_spread = df.iloc[i-20:i]['spread_pct'].mean()

            if avg_spread == 0:
                continue

            spread_efficiency = row['spread_pct'] / avg_spread

            # Absorption detected if spread is much smaller than expected
            if spread_efficiency < self.absorption_efficiency_threshold:
                # Determine direction from close position in bar
                close_position = (row['close'] - row['low']) / row['spread']

                if close_position > 0.6:  # Close near high = bullish
                    direction = 'LONG'
                    target = row['close'] * 1.02  # 2% target
                    stop_loss = row['low'] * 0.99  # Below low
                elif close_position < 0.4:  # Close near low = bearish
                    direction = 'SHORT'
                    target = row['close'] * 0.98  # 2% target
                    stop_loss = row['high'] * 1.01  # Above high
                else:
                    continue  # Inconclusive

                setup = {
                    'direction': direction,
                    'pattern': 'absorption',
                    'timestamp': row.get('timestamp', i),
                    'entry_price': float(row['close']),
                    'volume_ratio': float(row['volume_ratio']),
                    'spread_efficiency': float(spread_efficiency),
                    'target': float(target),
                    'stop_loss': float(stop_loss),
                }
                setups.append(setup)

        return setups

    def _detect_vwap_reclaim(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect VWAP reclaim patterns.

        When price breaks below VWAP then quickly reclaims it,
        often indicates institutional support (stop hunt + reversal).
        """
        setups = []

        for i in range(5, len(df)):
            current = df.iloc[i]
            prev_bars = df.iloc[i-5:i]

            # Check if previous bars were below VWAP
            was_below_vwap = (prev_bars['close'] < prev_bars['vwap']).any()

            # Check if current bar reclaims VWAP
            reclaims_vwap = (
                current['close'] > current['vwap'] and
                current['low'] < current['vwap']  # Tested and reclaimed
            )

            if was_below_vwap and reclaims_vwap:
                setup = {
                    'direction': 'LONG',
                    'pattern': 'vwap_reclaim',
                    'timestamp': current.get('timestamp', i),
                    'entry_price': float(current['close']),
                    'vwap': float(current['vwap']),
                    'volume_ratio': float(current['volume_ratio']),
                    'target': float(current['close'] * 1.025),  # 2.5% target
                    'stop_loss': float(current['low'] * 0.995),  # Below low
                }
                setups.append(setup)

        return setups

    def _detect_level_defense(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect level defense patterns (Wyckoff Spring).

        Multiple tests of support with decreasing spread indicates
        accumulation at a level.
        """
        setups = []

        # Look for support levels being tested multiple times
        for i in range(20, len(df) - 5):
            window = df.iloc[i-20:i]

            # Find potential support level (lowest low in window)
            support_level = window['low'].min()

            # Count touches of support (within 0.5%)
            touches = (
                (window['low'] <= support_level * 1.005) &
                (window['low'] >= support_level * 0.995)
            ).sum()

            if touches >= self.level_test_min:
                # Check for breakout above support
                next_bars = df.iloc[i:i+5]

                for j, row in enumerate(next_bars.iterrows()):
                    idx, bar = row

                    # Breakout with volume
                    if (
                        bar['close'] > support_level * 1.01 and
                        bar['volume_ratio'] > 2.0
                    ):
                        setup = {
                            'direction': 'LONG',
                            'pattern': 'level_defense',
                            'timestamp': bar.get('timestamp', i + j),
                            'entry_price': float(bar['close']),
                            'support_level': float(support_level),
                            'num_touches': int(touches),
                            'volume_ratio': float(bar['volume_ratio']),
                            'target': float(bar['close'] * 1.03),  # 3% target
                            'stop_loss': float(support_level * 0.99),  # Below support
                        }
                        setups.append(setup)
                        break

        return setups

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "smart_money"
