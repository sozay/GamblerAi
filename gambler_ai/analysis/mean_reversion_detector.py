"""
Mean Reversion strategy detector.

Detects overextended price moves that are likely to revert to the mean.

Entry Logic:
- Price touches/exceeds outer Bollinger Band (2.5σ)
- RSI < 30 (oversold) for LONG or RSI > 70 (overbought) for SHORT
- Volume spike (>3x average) indicating climax/exhaustion

Exit Logic:
- Target: Middle Bollinger Band (return to mean)
- Stop: 1% beyond entry
- Time stop: 30 minutes
"""

from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

from gambler_ai.analysis.indicators import (
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_volume_ratio,
)


class MeanReversionDetector:
    """Detect mean reversion trading opportunities."""

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.5,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        volume_multiplier: float = 3.0,
    ):
        """
        Initialize mean reversion detector.

        Args:
            bb_period: Bollinger Band period
            bb_std: Bollinger Band standard deviations
            rsi_period: RSI period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            volume_multiplier: Volume spike threshold
        """
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.volume_multiplier = volume_multiplier

    def detect_setups(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect mean reversion setups in price data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of detected setups
        """
        df = df.copy()

        # Calculate indicators
        df = self._add_indicators(df)

        setups = []

        # Scan for setups
        for i in range(self.bb_period + self.rsi_period, len(df)):
            row = df.iloc[i]

            # Skip if missing data
            if pd.isna(row['bb_upper']) or pd.isna(row['rsi']):
                continue

            # Check for LONG setup (oversold)
            if self._is_long_setup(row):
                setup = {
                    'direction': 'LONG',
                    'timestamp': row.get('timestamp', i),
                    'entry_price': float(row['close']),
                    'bb_distance_pct': float(
                        (row['bb_middle'] - row['close']) / row['close'] * 100
                    ),
                    'rsi': float(row['rsi']),
                    'volume_ratio': float(row['volume_ratio']),
                    'target': float(row['bb_middle']),
                    'stop_loss': float(row['close'] * 0.99),  # 1% below
                }
                setups.append(setup)

            # Check for SHORT setup (overbought)
            elif self._is_short_setup(row):
                setup = {
                    'direction': 'SHORT',
                    'timestamp': row.get('timestamp', i),
                    'entry_price': float(row['close']),
                    'bb_distance_pct': float(
                        (row['close'] - row['bb_middle']) / row['close'] * 100
                    ),
                    'rsi': float(row['rsi']),
                    'volume_ratio': float(row['volume_ratio']),
                    'target': float(row['bb_middle']),
                    'stop_loss': float(row['close'] * 1.01),  # 1% above
                }
                setups.append(setup)

        return setups

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add required indicators to dataframe."""
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            df['close'], self.bb_period, self.bb_std
        )
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower

        # RSI
        df['rsi'] = calculate_rsi(df['close'], self.rsi_period)

        # Volume ratio
        df['volume_ratio'] = calculate_volume_ratio(df['volume'], 20)

        return df

    def _is_long_setup(self, row: pd.Series) -> bool:
        """
        Check if row represents a LONG setup.
        Requires at least 2 out of 3 conditions for more flexibility.
        """
        conditions_met = 0

        # Condition 1: Price at/below lower BB
        if row['close'] <= row['bb_lower']:
            conditions_met += 1

        # Condition 2: RSI oversold
        if row['rsi'] < self.rsi_oversold:
            conditions_met += 1

        # Condition 3: Volume spike
        if row['volume_ratio'] > self.volume_multiplier:
            conditions_met += 1

        # Also accept if price is very close to BB (within 0.5%) and one other condition
        if conditions_met < 2 and row['close'] <= row['bb_lower'] * 1.005:
            if row['rsi'] < self.rsi_oversold * 1.2 or row['volume_ratio'] > self.volume_multiplier * 0.7:
                conditions_met = 2

        return conditions_met >= 2

    def _is_short_setup(self, row: pd.Series) -> bool:
        """
        Check if row represents a SHORT setup.
        Requires at least 2 out of 3 conditions for more flexibility.
        """
        conditions_met = 0

        # Condition 1: Price at/above upper BB
        if row['close'] >= row['bb_upper']:
            conditions_met += 1

        # Condition 2: RSI overbought
        if row['rsi'] > self.rsi_overbought:
            conditions_met += 1

        # Condition 3: Volume spike
        if row['volume_ratio'] > self.volume_multiplier:
            conditions_met += 1

        # Also accept if price is very close to BB (within 0.5%) and one other condition
        if conditions_met < 2 and row['close'] >= row['bb_upper'] * 0.995:
            if row['rsi'] > self.rsi_overbought * 0.8 or row['volume_ratio'] > self.volume_multiplier * 0.7:
                conditions_met = 2

        return conditions_met >= 2

    def calculate_target_distance(self, entry_price: float, target: float) -> float:
        """Calculate distance to target in percentage."""
        return abs(target - entry_price) / entry_price * 100

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "mean_reversion"
