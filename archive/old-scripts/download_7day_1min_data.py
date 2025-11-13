#!/usr/bin/env python3
"""
Download 7 Days of 1-Minute Real Data

Downloads real 1-minute market data for the last 7 days using Yahoo Finance.
This is the maximum period available for 1-minute data.
"""

import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealDataDownloader:
    """Download real 1-minute data for simulation."""

    def __init__(self, cache_dir: str = "real_data_1min"):
        """Initialize downloader with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"Cache directory: {self.cache_dir}")

    def download_1min_data(
        self,
        symbols: list,
        days: int = 7
    ) -> dict:
        """
        Download 1-minute data for specified symbols.

        Args:
            symbols: List of stock symbols
            days: Number of days (max 7 for 1-minute data)

        Returns:
            Dictionary of {symbol: DataFrame}
        """
        if days > 7:
            logger.warning("Yahoo Finance only provides 7 days of 1-minute data. Using 7 days.")
            days = 7

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logger.info(f"\n{'='*80}")
        logger.info(f"DOWNLOADING {days}-DAY 1-MINUTE DATA")
        logger.info(f"{'='*80}")
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Interval: 1-minute")
        logger.info(f"{'='*80}\n")

        data = {}

        for symbol in symbols:
            logger.info(f"Downloading {symbol}...")

            cache_file = self.cache_dir / f"{symbol}_1m_{start_date.date()}_{end_date.date()}.parquet"

            try:
                ticker = yf.Ticker(symbol)

                # Download 1-minute data
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval="1m",
                    auto_adjust=True
                )

                if df.empty:
                    logger.error(f"  ✗ No data returned for {symbol}")
                    continue

                # Standardize columns
                df.columns = [col.lower() for col in df.columns]
                df.reset_index(inplace=True)

                # Ensure timestamp column exists
                if 'datetime' in df.columns:
                    df.rename(columns={'datetime': 'timestamp'}, inplace=True)
                elif 'date' in df.columns:
                    df.rename(columns={'date': 'timestamp'}, inplace=True)

                df['symbol'] = symbol

                # Save to cache
                df.to_parquet(cache_file)

                data[symbol] = df

                logger.info(f"  ✓ Downloaded {len(df):,} bars for {symbol}")
                logger.info(f"     Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

            except Exception as e:
                logger.error(f"  ✗ Error downloading {symbol}: {e}")

        logger.info(f"\n{'='*80}")
        logger.info(f"DOWNLOAD COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Successfully downloaded {len(data)}/{len(symbols)} symbols")
        logger.info(f"Total bars: {sum(len(df) for df in data.values()):,}")
        logger.info(f"Cache directory: {self.cache_dir}")
        logger.info(f"{'='*80}\n")

        return data

    def load_cached_data(self, symbol: str) -> pd.DataFrame:
        """Load cached data for a symbol."""
        cache_files = list(self.cache_dir.glob(f"{symbol}_*.parquet"))

        if not cache_files:
            logger.warning(f"No cached data found for {symbol}")
            return pd.DataFrame()

        # Use most recent cache file
        latest_file = sorted(cache_files, key=lambda x: x.stat().st_mtime)[-1]

        logger.info(f"Loading cached data from {latest_file}")
        return pd.read_parquet(latest_file)

    def load_all_cached_data(self) -> dict:
        """Load all cached data."""
        cache_files = list(self.cache_dir.glob("*_1m_*.parquet"))

        data = {}

        for cache_file in cache_files:
            try:
                symbol = cache_file.stem.split('_')[0]
                df = pd.read_parquet(cache_file)
                data[symbol] = df
                logger.info(f"Loaded {len(df):,} bars for {symbol}")
            except Exception as e:
                logger.error(f"Error loading {cache_file}: {e}")

        return data


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Download 7 days of 1-minute real data")
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,GOOGL,TSLA,NVDA,AMD,META,AMZN,SPY,QQQ",
        help="Comma-separated stock symbols"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to download (max 7)"
    )
    parser.add_argument(
        "--cache-dir",
        default="real_data_1min",
        help="Cache directory"
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    downloader = RealDataDownloader(cache_dir=args.cache_dir)
    data = downloader.download_1min_data(symbols=symbols, days=args.days)

    if data:
        print("\n✓ Data download complete!")
        print(f"\nData Summary:")
        for symbol, df in data.items():
            print(f"  {symbol}: {len(df):,} bars ({df['timestamp'].min()} to {df['timestamp'].max()})")
        print(f"\nData saved to: {downloader.cache_dir}")
        print("\nYou can now run the simulation with this real data!")
    else:
        print("\n✗ No data downloaded")


if __name__ == "__main__":
    main()
