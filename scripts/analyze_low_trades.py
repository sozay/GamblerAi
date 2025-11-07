"""
Analyze why simulation has so few trades.
Check scanner selection and signal generation separately.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_data(symbols: List[str], interval: str, start_date: datetime, end_date: datetime):
    """Load cached market data."""
    cache_dir = Path("market_data_cache")
    market_data = {}

    for symbol in symbols:
        pattern = f"{symbol}_{interval}_*.parquet"
        cache_files = list(cache_dir.glob(pattern))

        if cache_files:
            df = pd.read_parquet(cache_files[0])
            if 'timestamp' not in df.columns:
                for col in df.columns:
                    if 'date' in col.lower() or 'time' in col.lower():
                        df['timestamp'] = pd.to_datetime(df[col])
                        break

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if not pd.api.types.is_datetime64tz_dtype(df['timestamp']):
                df['timestamp'] = df['timestamp'].dt.tz_localize('America/New_York')
            df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')

            start_utc = pd.Timestamp(start_date).tz_localize('America/New_York').tz_convert('UTC')
            end_utc = pd.Timestamp(end_date).tz_localize('America/New_York').tz_convert('UTC')
            df = df[(df['timestamp'] >= start_utc) & (df['timestamp'] <= end_utc)]

            if len(df) > 0:
                market_data[symbol] = df

    return market_data


def count_breakout_signals(df: pd.DataFrame) -> int:
    """Count how many volatility breakout signals would be generated."""
    if len(df) < 20:
        return 0

    df = df.copy()
    df['high_low_range'] = df['high'] - df['low']
    df['atr'] = df['high_low_range'].rolling(window=14).mean()

    signals = 0
    min_bars_between = 6

    for i in range(20, len(df) - 15, min_bars_between):
        if df['high_low_range'].iloc[i] > df['atr'].iloc[i] * 1.5:
            signals += 1

    return signals


def main():
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD', 'NFLX', 'SPY']
    start_date = datetime(2024, 11, 8)
    end_date = datetime(2025, 11, 7)
    interval = '1h'

    logger.info("="*80)
    logger.info("ANALYZING LOW TRADE COUNT")
    logger.info("="*80)

    market_data = load_data(symbols, interval, start_date, end_date)

    # Analyze full year data for each stock
    logger.info("\n" + "="*80)
    logger.info("SIGNAL POTENTIAL PER STOCK (Full Year)")
    logger.info("="*80)

    total_signals = 0
    for symbol, df in market_data.items():
        signals = count_breakout_signals(df)
        total_signals += signals

        # Calculate ATR info
        df['high_low_range'] = df['high'] - df['low']
        df['atr'] = df['high_low_range'].rolling(window=14).mean()
        avg_atr = df['atr'].mean()
        avg_range = df['high_low_range'].mean()

        logger.info(f"{symbol:6s}: {signals:3d} potential signals | "
                   f"Avg ATR: ${avg_atr:.2f} | Avg Range: ${avg_range:.2f} | "
                   f"Range/ATR: {avg_range/avg_atr:.2f}x")

    logger.info(f"\nTOTAL potential signals across all stocks: {total_signals}")

    # Test week-by-week selection
    logger.info("\n" + "="*80)
    logger.info("WEEK-BY-WEEK ANALYSIS (First 10 Weeks)")
    logger.info("="*80)

    current = start_date
    for week_num in range(1, 11):
        week_end = min(current + timedelta(days=7), end_date)

        logger.info(f"\nWeek {week_num}: {current.date()} to {week_end.date()}")

        # Count stocks that qualify for top_movers
        qualifiers = []
        for symbol, df in market_data.items():
            start_utc = pd.Timestamp(current).tz_localize('America/New_York').tz_convert('UTC')
            end_utc = pd.Timestamp(week_end).tz_localize('America/New_York').tz_convert('UTC')
            week_df = df[(df['timestamp'] >= start_utc) & (df['timestamp'] <= end_utc)].copy()

            if len(week_df) < 20:
                continue

            price_change = (week_df['close'].iloc[-1] - week_df['close'].iloc[0]) / week_df['close'].iloc[0] * 100

            if len(week_df) >= 40:
                baseline_vol = week_df['volume'].iloc[:len(week_df)//2].mean()
                recent_vol = week_df['volume'].iloc[len(week_df)//2:].max()
            else:
                baseline_vol = week_df['volume'].mean()
                recent_vol = week_df['volume'].max()

            volume_ratio = recent_vol / baseline_vol if baseline_vol > 0 else 1.0

            # top_movers criteria
            if abs(price_change) >= 0.5 and volume_ratio >= 1.2:
                signals = count_breakout_signals(week_df)
                qualifiers.append((symbol, price_change, volume_ratio, signals))

        qualifiers.sort(key=lambda x: abs(x[1]) * x[2], reverse=True)

        if qualifiers:
            logger.info(f"  Qualified stocks: {len(qualifiers)}")
            for i, (sym, pc, vr, sigs) in enumerate(qualifiers[:3], 1):
                logger.info(f"    {i}. {sym}: {pc:+.1f}%, vol:{vr:.1f}x, signals:{sigs}")
        else:
            logger.info(f"  NO stocks qualified (need ≥0.5% move + ≥1.2x volume)")

        current = week_end

    # Check if thresholds are too strict
    logger.info("\n" + "="*80)
    logger.info("THRESHOLD SENSITIVITY ANALYSIS")
    logger.info("="*80)

    test_week_df = market_data['TSLA'].iloc[:168]  # ~1 week of hourly data

    logger.info("\nTesting TSLA first week with different ATR multipliers:")
    for multiplier in [1.0, 1.2, 1.5, 1.8, 2.0]:
        df = test_week_df.copy()
        df['high_low_range'] = df['high'] - df['low']
        df['atr'] = df['high_low_range'].rolling(window=14).mean()

        signals = 0
        for i in range(20, len(df) - 15, 6):
            if df['high_low_range'].iloc[i] > df['atr'].iloc[i] * multiplier:
                signals += 1

        logger.info(f"  ATR * {multiplier:.1f}: {signals} signals")

    logger.info("\n" + "="*80)
    logger.info("RECOMMENDATION")
    logger.info("="*80)

    if total_signals < 100:
        logger.info("⚠️  VERY LOW signal potential detected!")
        logger.info("   Consider:")
        logger.info("   1. Lower ATR multiplier from 1.5 to 1.2")
        logger.info("   2. Relax scanner criteria (0.3% move instead of 0.5%)")
        logger.info("   3. Use 5-minute data instead of 1-hour for more opportunities")
    else:
        logger.info("✓ Signal potential looks good. Issue may be in selection logic.")


if __name__ == "__main__":
    main()
