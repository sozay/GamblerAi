"""
Market Regime Detector

Detects whether the market is in a BULL, BEAR, or RANGE regime
using technical indicators and trend analysis.
"""

from typing import Literal
import pandas as pd
import numpy as np


MarketRegime = Literal['BULL', 'BEAR', 'RANGE']


class RegimeDetector:
    """
    Detect market regime using multiple methods.

    Primary method: 200 EMA (most reliable)
    Secondary: ADX for trend strength
    Tertiary: Price action patterns
    """

    def __init__(
        self,
        ema_period: int = 200,
        ema_bull_threshold: float = 1.02,  # 2% above EMA = bull
        ema_bear_threshold: float = 0.98,  # 2% below EMA = bear
        use_adx: bool = False,
        adx_threshold: float = 25.0,
    ):
        """
        Initialize regime detector.

        Args:
            ema_period: Period for trend EMA (default 200)
            ema_bull_threshold: Multiplier for bull threshold (1.02 = 2% above)
            ema_bear_threshold: Multiplier for bear threshold (0.98 = 2% below)
            use_adx: Whether to use ADX for trend strength confirmation
            adx_threshold: ADX value above which trend is considered strong
        """
        self.ema_period = ema_period
        self.ema_bull_threshold = ema_bull_threshold
        self.ema_bear_threshold = ema_bear_threshold
        self.use_adx = use_adx
        self.adx_threshold = adx_threshold

    def detect_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            'BULL', 'BEAR', or 'RANGE'
        """
        if len(df) < self.ema_period:
            # Not enough data, default to RANGE
            return 'RANGE'

        # Calculate 200 EMA
        ema_200 = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        current_price = df['close'].iloc[-1]
        current_ema = ema_200.iloc[-1]

        # Primary regime detection: Price vs EMA
        if current_price > current_ema * self.ema_bull_threshold:
            primary_regime = 'BULL'
        elif current_price < current_ema * self.ema_bear_threshold:
            primary_regime = 'BEAR'
        else:
            primary_regime = 'RANGE'

        # If ADX is enabled, confirm trend strength
        if self.use_adx:
            adx = self._calculate_adx(df)

            if adx is not None and adx < self.adx_threshold:
                # Weak trend = likely ranging
                return 'RANGE'

        return primary_regime

    def detect_regime_with_confidence(self, df: pd.DataFrame) -> tuple[MarketRegime, float]:
        """
        Detect regime with confidence score.

        Returns:
            Tuple of (regime, confidence) where confidence is 0-1
        """
        if len(df) < self.ema_period:
            return ('RANGE', 0.5)

        # Calculate indicators
        ema_200 = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        current_price = df['close'].iloc[-1]
        current_ema_200 = ema_200.iloc[-1]
        current_ema_50 = ema_50.iloc[-1]

        # Calculate distance from EMA (normalized)
        distance_from_ema = (current_price - current_ema_200) / current_ema_200

        # Determine regime
        if distance_from_ema > (self.ema_bull_threshold - 1):
            regime = 'BULL'
            # Confidence increases with distance from EMA
            confidence = min(abs(distance_from_ema) / 0.10, 1.0)  # Max at 10% distance
        elif distance_from_ema < -(1 - self.ema_bear_threshold):
            regime = 'BEAR'
            confidence = min(abs(distance_from_ema) / 0.10, 1.0)
        else:
            regime = 'RANGE'
            # Lower confidence when close to EMA
            confidence = 0.5 + (1 - min(abs(distance_from_ema) / 0.02, 1.0)) * 0.3

        # Boost confidence if EMA50 aligns with EMA200
        if len(df) >= 50:
            if regime == 'BULL' and current_ema_50 > current_ema_200:
                confidence = min(confidence * 1.2, 1.0)
            elif regime == 'BEAR' and current_ema_50 < current_ema_200:
                confidence = min(confidence * 1.2, 1.0)

        return (regime, confidence)

    def get_regime_history(self, df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
        """
        Get regime detection for historical data.

        Args:
            df: DataFrame with OHLCV data
            window: How many recent bars to analyze

        Returns:
            DataFrame with regime and confidence columns
        """
        regimes = []
        confidences = []

        start_idx = max(self.ema_period, len(df) - window)

        for i in range(start_idx, len(df)):
            subset = df.iloc[:i+1]
            regime, confidence = self.detect_regime_with_confidence(subset)
            regimes.append(regime)
            confidences.append(confidence)

        result_df = pd.DataFrame({
            'timestamp': df['timestamp'].iloc[start_idx:].values,
            'close': df['close'].iloc[start_idx:].values,
            'regime': regimes,
            'confidence': confidences,
        })

        return result_df

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average Directional Index (ADX).

        Returns:
            Current ADX value (0-100)
        """
        if len(df) < period + 1:
            return None

        high = df['high']
        low = df['low']
        close = df['close']

        # Calculate +DM and -DM
        high_diff = high.diff()
        low_diff = -low.diff()

        pos_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        neg_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Smooth the directional movements and TR
        atr = tr.rolling(window=period).mean()
        pos_di = 100 * (pos_dm.rolling(window=period).mean() / atr)
        neg_di = 100 * (neg_dm.rolling(window=period).mean() / atr)

        # Calculate DX and ADX
        dx = 100 * abs(pos_di - neg_di) / (pos_di + neg_di)
        adx = dx.rolling(window=period).mean()

        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else None

    def print_regime_summary(self, df: pd.DataFrame):
        """Print current regime information."""
        regime, confidence = self.detect_regime_with_confidence(df)

        ema_200 = df['close'].ewm(span=self.ema_period, adjust=False).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        distance = ((current_price - ema_200) / ema_200) * 100

        print(f"\n{'='*60}")
        print(f"MARKET REGIME ANALYSIS")
        print(f"{'='*60}")
        print(f"Current Regime:    {regime}")
        print(f"Confidence:        {confidence:.1%}")
        print(f"Current Price:     ${current_price:.2f}")
        print(f"200 EMA:           ${ema_200:.2f}")
        print(f"Distance from EMA: {distance:+.2f}%")

        if self.use_adx:
            adx = self._calculate_adx(df)
            if adx:
                print(f"ADX (Trend):       {adx:.1f}")
                print(f"Trend Strength:    {'Strong' if adx > self.adx_threshold else 'Weak'}")

        print(f"{'='*60}\n")

        # Interpretation
        if regime == 'BULL':
            print("📈 BULLISH REGIME: Use trend-following strategies")
            print("   Recommended: Multi-Timeframe, Momentum")
        elif regime == 'BEAR':
            print("📉 BEARISH REGIME: Use counter-trend or SHORT strategies")
            print("   Recommended: Mean Reversion, Momentum")
        else:
            print("📊 RANGING REGIME: Use mean-reversion strategies")
            print("   Recommended: Mean Reversion, Smart Money")

        print()


def detect_regime_simple(df: pd.DataFrame) -> MarketRegime:
    """
    Simple regime detection function (convenience wrapper).

    Args:
        df: DataFrame with OHLCV data

    Returns:
        'BULL', 'BEAR', or 'RANGE'
    """
    detector = RegimeDetector()
    return detector.detect_regime(df)
