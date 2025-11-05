"""
Volatility Breakout strategy detector.

Detects breakouts from volatility compression (tight ranges).

Entry Logic:
- ATR compressed to <50% of 20-period average
- Price consolidation for 20+ bars
- Breakout from range with volume confirmation (>2x)

Exit Logic:
- Target: 1.5x the consolidation range
- Stop: Opposite side of range
- Time stop: 90 minutes
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from gambler_ai.analysis.indicators import calculate_atr, calculate_volume_ratio


class VolatilityBreakoutDetector:
    """Detect volatility breakout opportunities."""

    def __init__(
        self,
        atr_period: int = 14,
        atr_compression_ratio: float = 0.5,
        consolidation_min_bars: int = 20,
        breakout_threshold_pct: float = 0.5,
        volume_multiplier: float = 2.0,
    ):
        """
        Initialize volatility breakout detector.

        Args:
            atr_period: ATR calculation period
            atr_compression_ratio: ATR compression threshold (0.5 = 50% of average)
            consolidation_min_bars: Minimum bars in consolidation
            breakout_threshold_pct: Breakout confirmation threshold
            volume_multiplier: Volume spike threshold
        """
        self.atr_period = atr_period
        self.atr_compression_ratio = atr_compression_ratio
        self.consolidation_min_bars = consolidation_min_bars
        self.breakout_threshold_pct = breakout_threshold_pct
        self.volume_multiplier = volume_multiplier

    def detect_setups(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect volatility breakout setups.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of detected setups
        """
        df = df.copy()

        # Calculate indicators
        df = self._add_indicators(df)

        # Detect consolidation ranges
        ranges = self._detect_consolidation_ranges(df)

        # Detect breakouts from ranges
        setups = []
        for range_data in ranges:
            breakout = self._detect_breakout(df, range_data)
            if breakout:
                setups.append(breakout)

        return setups

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add required indicators."""
        # ATR
        df['atr'] = calculate_atr(df['high'], df['low'], df['close'], self.atr_period)
        df['atr_avg'] = df['atr'].rolling(20).mean()
        df['atr_ratio'] = df['atr'] / df['atr_avg']

        # Volume ratio
        df['volume_ratio'] = calculate_volume_ratio(df['volume'], 20)

        return df

    def _detect_consolidation_ranges(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect consolidation ranges where volatility is compressed.

        Returns:
            List of consolidation periods with range data
        """
        ranges = []
        in_range = False
        range_start_idx = None
        range_high = None
        range_low = None

        for i in range(len(df)):
            row = df.iloc[i]

            # Skip if missing ATR data
            if pd.isna(row['atr_ratio']):
                continue

            # Check if volatility is compressed
            is_compressed = row['atr_ratio'] < self.atr_compression_ratio

            if is_compressed and not in_range:
                # Start new consolidation range
                in_range = True
                range_start_idx = i
                range_high = row['high']
                range_low = row['low']

            elif is_compressed and in_range:
                # Extend range
                range_high = max(range_high, row['high'])
                range_low = min(range_low, row['low'])

            elif not is_compressed and in_range:
                # Range ended
                range_duration = i - range_start_idx

                if range_duration >= self.consolidation_min_bars:
                    range_size_pct = (range_high - range_low) / range_low * 100

                    ranges.append({
                        'start_idx': range_start_idx,
                        'end_idx': i - 1,
                        'duration': range_duration,
                        'high': range_high,
                        'low': range_low,
                        'size_pct': range_size_pct,
                        'middle': (range_high + range_low) / 2,
                    })

                in_range = False

        return ranges

    def _detect_breakout(
        self,
        df: pd.DataFrame,
        range_data: Dict
    ) -> Optional[Dict]:
        """
        Detect breakout from consolidation range.

        Args:
            df: Price data
            range_data: Consolidation range information

        Returns:
            Breakout setup or None
        """
        end_idx = range_data['end_idx']
        range_high = range_data['high']
        range_low = range_data['low']
        range_size_pct = range_data['size_pct']

        # Look for breakout in next 10 bars
        for i in range(end_idx + 1, min(end_idx + 11, len(df))):
            row = df.iloc[i]

            breakout_threshold_price_up = range_high * (1 + self.breakout_threshold_pct / 100)
            breakout_threshold_price_down = range_low * (1 - self.breakout_threshold_pct / 100)

            # Bullish breakout
            if (
                row['close'] > breakout_threshold_price_up and
                row['volume_ratio'] > self.volume_multiplier
            ):
                # Calculate target: 1.5x range size
                target_distance = range_size_pct * 1.5
                target = row['close'] * (1 + target_distance / 100)

                return {
                    'direction': 'LONG',
                    'timestamp': row.get('timestamp', i),
                    'entry_price': float(row['close']),
                    'range_high': float(range_high),
                    'range_low': float(range_low),
                    'range_size_pct': float(range_size_pct),
                    'consolidation_duration': range_data['duration'],
                    'volume_ratio': float(row['volume_ratio']),
                    'target': float(target),
                    'stop_loss': float(range_low),  # Below range
                }

            # Bearish breakout
            elif (
                row['close'] < breakout_threshold_price_down and
                row['volume_ratio'] > self.volume_multiplier
            ):
                # Calculate target: 1.5x range size
                target_distance = range_size_pct * 1.5
                target = row['close'] * (1 - target_distance / 100)

                return {
                    'direction': 'SHORT',
                    'timestamp': row.get('timestamp', i),
                    'entry_price': float(row['close']),
                    'range_high': float(range_high),
                    'range_low': float(range_low),
                    'range_size_pct': float(range_size_pct),
                    'consolidation_duration': range_data['duration'],
                    'volume_ratio': float(row['volume_ratio']),
                    'target': float(target),
                    'stop_loss': float(range_high),  # Above range
                }

        return None

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "volatility_breakout"
