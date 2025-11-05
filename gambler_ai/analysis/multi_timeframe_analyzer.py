"""
Multi-Timeframe Confluence strategy analyzer.

Analyzes multiple timeframes for alignment to increase probability.

Entry Logic:
- Trend alignment across timeframes (all same direction)
- Price at key level (20 EMA) on entry timeframe
- Volume confirmation
- RSI alignment (momentum but not extreme)

Exit Logic:
- Target: Next major resistance/support from higher timeframe
- Stop: Below multi-timeframe support
- Time stop: 120 minutes
"""

from typing import Dict, List
import pandas as pd
import numpy as np

from gambler_ai.analysis.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_volume_ratio,
    calculate_vwap,
)


class MultiTimeframeAnalyzer:
    """Analyze multiple timeframes for confluence."""

    def __init__(
        self,
        trend_ma_period: int = 20,
        min_confluence_score: int = 3,
    ):
        """
        Initialize multi-timeframe analyzer.

        Args:
            trend_ma_period: Period for trend identification
            min_confluence_score: Minimum score to generate signal (0-5)
        """
        self.trend_ma_period = trend_ma_period
        self.min_confluence_score = min_confluence_score

    def detect_setups(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect multi-timeframe confluence setups.

        Note: This simplified version simulates multiple timeframes
        by using different moving average periods on the same data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of detected setups
        """
        df = df.copy()

        # Add indicators
        df = self._add_indicators(df)

        setups = []

        # Scan for confluence
        for i in range(50, len(df)):  # Need 50 bars for indicators
            row = df.iloc[i]

            # Skip if missing data
            if any(pd.isna(row[col]) for col in ['ema_20', 'ema_50', 'rsi', 'vwap']):
                continue

            # Calculate confluence score
            confluence = self._calculate_confluence(row)

            if confluence['score'] >= self.min_confluence_score:
                # Determine entry and targets
                direction = confluence['direction']

                if direction == 'LONG':
                    entry_price = float(row['close'])
                    stop_loss = float(row['ema_50'])  # Use 50 EMA as support
                    target = entry_price * 1.025  # 2.5% target

                    setup = {
                        'direction': 'LONG',
                        'timestamp': row.get('timestamp', i),
                        'entry_price': entry_price,
                        'confluence_score': confluence['score'],
                        'factors': confluence['factors'],
                        'target': target,
                        'stop_loss': stop_loss,
                        'ema_20': float(row['ema_20']),
                        'ema_50': float(row['ema_50']),
                        'rsi': float(row['rsi']),
                        'volume_ratio': float(row['volume_ratio']),
                    }
                    setups.append(setup)

                elif direction == 'SHORT':
                    entry_price = float(row['close'])
                    stop_loss = float(row['ema_50'])  # Use 50 EMA as resistance
                    target = entry_price * 0.975  # 2.5% target

                    setup = {
                        'direction': 'SHORT',
                        'timestamp': row.get('timestamp', i),
                        'entry_price': entry_price,
                        'confluence_score': confluence['score'],
                        'factors': confluence['factors'],
                        'target': target,
                        'stop_loss': stop_loss,
                        'ema_20': float(row['ema_20']),
                        'ema_50': float(row['ema_50']),
                        'rsi': float(row['rsi']),
                        'volume_ratio': float(row['volume_ratio']),
                    }
                    setups.append(setup)

        return setups

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add required indicators."""
        # EMAs for trend
        df['ema_20'] = calculate_ema(df['close'], 20)
        df['ema_50'] = calculate_ema(df['close'], 50)

        # RSI
        df['rsi'] = calculate_rsi(df['close'], 14)

        # Volume
        df['volume_ratio'] = calculate_volume_ratio(df['volume'], 20)

        # VWAP
        df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])

        # Price distance from EMAs
        df['distance_from_ema20'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100

        return df

    def _calculate_confluence(self, row: pd.Series) -> Dict:
        """
        Calculate confluence score (0-5).

        Factors:
        1. Trend alignment (price above/below both EMAs)
        2. Price at key level (close to 20 EMA)
        3. Volume confirmation
        4. RSI alignment (momentum but not extreme)
        5. VWAP alignment
        """
        score = 0
        factors = []
        direction = 'NEUTRAL'

        # Factor 1: Trend alignment
        if row['close'] > row['ema_20'] > row['ema_50']:
            score += 1
            factors.append('bullish_trend_alignment')
            direction = 'LONG'
        elif row['close'] < row['ema_20'] < row['ema_50']:
            score += 1
            factors.append('bearish_trend_alignment')
            direction = 'SHORT'

        # Factor 2: Price at key level (within 0.5% of 20 EMA)
        if abs(row['distance_from_ema20']) < 0.5:
            score += 1
            factors.append('at_key_level')

        # Factor 3: Volume confirmation (above average)
        if row['volume_ratio'] > 1.5:
            score += 1
            factors.append('volume_confirmation')

        # Factor 4: RSI alignment (not extreme)
        if 45 < row['rsi'] < 55:
            # Neutral RSI - good for continuation
            score += 1
            factors.append('rsi_neutral')
        elif direction == 'LONG' and 50 < row['rsi'] < 70:
            # Bullish momentum but not overbought
            score += 1
            factors.append('rsi_bullish')
        elif direction == 'SHORT' and 30 < row['rsi'] < 50:
            # Bearish momentum but not oversold
            score += 1
            factors.append('rsi_bearish')

        # Factor 5: VWAP alignment
        if direction == 'LONG' and row['close'] > row['vwap']:
            score += 1
            factors.append('above_vwap')
        elif direction == 'SHORT' and row['close'] < row['vwap']:
            score += 1
            factors.append('below_vwap')

        return {
            'score': score,
            'direction': direction if score >= self.min_confluence_score else 'NEUTRAL',
            'factors': factors,
        }

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "multi_timeframe"
