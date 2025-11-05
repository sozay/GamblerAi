"""
Technical indicators for trading strategies.

Provides commonly used technical analysis indicators:
- Bollinger Bands
- RSI (Relative Strength Index)
- ATR (Average True Range)
- VWAP (Volume Weighted Average Price)
- Moving Averages (SMA, EMA)
"""

import numpy as np
import pandas as pd
from typing import Tuple


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.

    Args:
        data: Price data series
        period: Number of periods

    Returns:
        SMA series
    """
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Args:
        data: Price data series
        period: Number of periods

    Returns:
        EMA series
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_bollinger_bands(
    data: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Args:
        data: Price data series (typically close prices)
        period: Rolling window period
        std_dev: Number of standard deviations

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle_band = calculate_sma(data, period)
    std = data.rolling(window=period).std()

    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return upper_band, middle_band, lower_band


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        data: Price data series (typically close prices)
        period: RSI period (default 14)

    Returns:
        RSI series (0-100)
    """
    # Calculate price changes
    delta = data.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Calculate average gains and losses
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()

    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period

    Returns:
        ATR series
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Calculate ATR as moving average of TR
    atr = tr.rolling(window=period).mean()

    return atr


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).

    Typically calculated from market open, so this assumes
    data is for a single trading day or you want cumulative VWAP.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume

    Returns:
        VWAP series
    """
    # Typical price
    typical_price = (high + low + close) / 3

    # VWAP = Cumulative(typical_price * volume) / Cumulative(volume)
    vwap = (typical_price * volume).cumsum() / volume.cumsum()

    return vwap


def calculate_vwap_by_day(
    df: pd.DataFrame,
    high_col: str = 'high',
    low_col: str = 'low',
    close_col: str = 'close',
    volume_col: str = 'volume',
    timestamp_col: str = 'timestamp'
) -> pd.Series:
    """
    Calculate VWAP reset daily.

    Args:
        df: DataFrame with OHLCV data
        high_col: Name of high price column
        low_col: Name of low price column
        close_col: Name of close price column
        volume_col: Name of volume column
        timestamp_col: Name of timestamp column

    Returns:
        VWAP series
    """
    df = df.copy()

    # Extract date for grouping
    df['date'] = pd.to_datetime(df[timestamp_col]).dt.date

    # Calculate typical price
    typical_price = (df[high_col] + df[low_col] + df[close_col]) / 3

    # Calculate VWAP per day
    vwap = (
        (typical_price * df[volume_col]).groupby(df['date']).cumsum() /
        df[volume_col].groupby(df['date']).cumsum()
    )

    return vwap


def calculate_bollinger_width(
    upper_band: pd.Series,
    lower_band: pd.Series,
    middle_band: pd.Series
) -> pd.Series:
    """
    Calculate Bollinger Band Width.

    Width = (Upper - Lower) / Middle

    Used to identify volatility compression.

    Args:
        upper_band: Upper Bollinger Band
        lower_band: Lower Bollinger Band
        middle_band: Middle Bollinger Band

    Returns:
        Band width series
    """
    return (upper_band - lower_band) / middle_band


def calculate_volatility_percentile(
    data: pd.Series,
    current_period: int = 14,
    lookback_period: int = 252
) -> pd.Series:
    """
    Calculate where current volatility ranks historically.

    Args:
        data: Price data
        current_period: Period for current volatility calculation
        lookback_period: Historical lookback period

    Returns:
        Percentile series (0-100)
    """
    # Calculate rolling standard deviation (volatility)
    volatility = data.rolling(window=current_period).std()

    # Calculate percentile rank
    percentile = volatility.rolling(window=lookback_period).apply(
        lambda x: (x < x[-1]).sum() / len(x) * 100,
        raw=True
    )

    return percentile


def calculate_volume_ratio(
    volume: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Calculate volume ratio vs average.

    Args:
        volume: Volume series
        period: Period for average calculation

    Returns:
        Volume ratio (current / average)
    """
    avg_volume = volume.rolling(window=period).mean()
    return volume / avg_volume


def detect_support_resistance(
    high: pd.Series,
    low: pd.Series,
    window: int = 10,
    num_touches: int = 2
) -> dict:
    """
    Detect support and resistance levels.

    A level is considered support/resistance if price touches
    it multiple times without breaking through.

    Args:
        high: High prices
        low: Low prices
        window: Window for local extrema
        num_touches: Minimum touches to confirm level

    Returns:
        Dictionary with 'support' and 'resistance' lists
    """
    # Find local highs (resistance candidates)
    local_highs = high.rolling(window=window, center=True).max()
    resistance_candidates = high[high == local_highs].dropna()

    # Find local lows (support candidates)
    local_lows = low.rolling(window=window, center=True).min()
    support_candidates = low[low == local_lows].dropna()

    # Group similar levels (within 0.5% of each other)
    def cluster_levels(levels, tolerance=0.005):
        if len(levels) == 0:
            return []

        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if (level - current_cluster[0]) / current_cluster[0] <= tolerance:
                current_cluster.append(level)
            else:
                if len(current_cluster) >= num_touches:
                    clusters.append(np.mean(current_cluster))
                current_cluster = [level]

        if len(current_cluster) >= num_touches:
            clusters.append(np.mean(current_cluster))

        return clusters

    resistance_levels = cluster_levels(resistance_candidates.tolist())
    support_levels = cluster_levels(support_candidates.tolist())

    return {
        'support': support_levels,
        'resistance': resistance_levels
    }


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all common indicators to a dataframe.

    Expects OHLCV columns: open, high, low, close, volume

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with added indicator columns
    """
    df = df.copy()

    # Moving averages
    df['sma_20'] = calculate_sma(df['close'], 20)
    df['sma_50'] = calculate_sma(df['close'], 50)
    df['ema_20'] = calculate_ema(df['close'], 20)

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'], 20, 2.0)
    df['bb_upper'] = bb_upper
    df['bb_middle'] = bb_middle
    df['bb_lower'] = bb_lower
    df['bb_width'] = calculate_bollinger_width(bb_upper, bb_lower, bb_middle)

    # RSI
    df['rsi'] = calculate_rsi(df['close'], 14)

    # ATR
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)
    df['atr_avg'] = df['atr'].rolling(20).mean()

    # Volume
    df['volume_ratio'] = calculate_volume_ratio(df['volume'], 20)
    df['avg_volume'] = df['volume'].rolling(20).mean()

    # VWAP
    if 'timestamp' in df.columns:
        df['vwap'] = calculate_vwap_by_day(df)
    else:
        df['vwap'] = calculate_vwap(df['high'], df['low'], df['close'], df['volume'])

    return df
