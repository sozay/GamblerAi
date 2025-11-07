"""
Historical Data Downloader

Downloads 10 years of real market data for simulation.
Saves to local cache for fast access.
"""

import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataDownloader:
    """Downloads and caches historical market data."""

    def __init__(self, cache_dir: str = "market_data_cache"):
        """
        Initialize data downloader.

        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"Data cache directory: {self.cache_dir}")

    def download_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1m"
    ) -> pd.DataFrame:
        """
        Download data for a single symbol.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            interval: Data interval (1m, 5m, 15m, 1h, 1d)

        Returns:
            DataFrame with OHLCV data
        """
        cache_file = self.cache_dir / f"{symbol}_{interval}_{start_date.date()}_{end_date.date()}.parquet"

        # Check cache first
        if cache_file.exists():
            logger.info(f"Loading {symbol} from cache: {cache_file}")
            try:
                df = pd.read_parquet(cache_file)
                return df
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, re-downloading...")

        # Download from Yahoo Finance
        logger.info(f"Downloading {symbol} from {start_date.date()} to {end_date.date()}")

        try:
            ticker = yf.Ticker(symbol)

            # Note: yfinance only provides last 7 days of 1-minute data
            # For longer periods, use daily data
            if interval == "1m":
                # For minute data, we can only get last 7 days
                max_days = 7
                if (end_date - start_date).days > max_days:
                    logger.warning(f"Minute data limited to last {max_days} days, adjusting...")
                    start_date = end_date - timedelta(days=max_days)

            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True
            )

            if df.empty:
                logger.error(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Standardize column names
            df.columns = [col.lower() for col in df.columns]
            df.reset_index(inplace=True)

            # Ensure we have timestamp column
            if 'datetime' in df.columns:
                df.rename(columns={'datetime': 'timestamp'}, inplace=True)
            elif 'date' in df.columns:
                df.rename(columns={'date': 'timestamp'}, inplace=True)

            df['symbol'] = symbol

            # Save to cache
            df.to_parquet(cache_file)
            logger.info(f"Saved {len(df)} rows to cache for {symbol}")

            return df

        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return pd.DataFrame()

    def download_multiple_symbols(
        self,
        symbols: list,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> dict:
        """
        Download data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            interval: Data interval

        Returns:
            Dictionary of {symbol: DataFrame}
        """
        data = {}

        for symbol in symbols:
            logger.info(f"Downloading {symbol}...")
            df = self.download_symbol(symbol, start_date, end_date, interval)

            if not df.empty:
                data[symbol] = df
            else:
                logger.warning(f"Failed to download {symbol}")

        logger.info(f"Successfully downloaded {len(data)}/{len(symbols)} symbols")
        return data

    def get_available_date_range(self, symbol: str) -> dict:
        """
        Get the available date range for a symbol in cache.

        Returns:
            Dictionary with 'start' and 'end' dates
        """
        cache_files = list(self.cache_dir.glob(f"{symbol}_*.parquet"))

        if not cache_files:
            return {'start': None, 'end': None}

        # Parse dates from filenames
        dates = []
        for file in cache_files:
            parts = file.stem.split('_')
            if len(parts) >= 4:
                try:
                    start = datetime.strptime(parts[2], '%Y-%m-%d')
                    end = datetime.strptime(parts[3], '%Y-%m-%d')
                    dates.extend([start, end])
                except:
                    continue

        if dates:
            return {
                'start': min(dates),
                'end': max(dates)
            }

        return {'start': None, 'end': None}

    def download_full_dataset(
        self,
        symbols: list = None,
        years: int = 10,
        interval: str = "1d"
    ):
        """
        Download full historical dataset.

        Args:
            symbols: List of symbols (default: major stocks)
            years: Number of years to download
            interval: Data interval (1d recommended for long periods)
        """
        if symbols is None:
            symbols = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
                'NVDA', 'META', 'AMD', 'NFLX', 'SPY'
            ]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)

        logger.info(f"\n{'='*80}")
        logger.info(f"DOWNLOADING {years}-YEAR DATASET")
        logger.info(f"{'='*80}")
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Interval: {interval}")
        logger.info(f"{'='*80}\n")

        data = self.download_multiple_symbols(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        # Save metadata
        metadata = {
            'symbols': symbols,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'interval': interval,
            'download_timestamp': datetime.now().isoformat(),
            'data_summary': {
                symbol: {
                    'rows': len(df),
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat()
                }
                for symbol, df in data.items()
            }
        }

        metadata_file = self.cache_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"\n{'='*80}")
        logger.info(f"DOWNLOAD COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total symbols: {len(data)}")
        logger.info(f"Metadata saved to: {metadata_file}")
        logger.info(f"Cache directory: {self.cache_dir}")

        return data


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("HISTORICAL DATA DOWNLOADER")
    print("="*80)
    print("\nThis will download 10 years of historical data for major stocks.")
    print("Data will be cached locally for fast access.\n")

    downloader = DataDownloader()

    # Download 10 years of daily data
    print("Downloading 10 years of DAILY data...")
    print("(Note: Minute data is only available for last 7 days via Yahoo Finance)\n")

    data = downloader.download_full_dataset(
        years=10,
        interval="1d"
    )

    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)

    for symbol, df in data.items():
        print(f"{symbol}: {len(df)} rows, {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")

    print("\n" + "="*80)
    print("Data ready for simulation!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
