#!/usr/bin/env python3
"""
Enhanced Data Downloader with Alpaca Integration

Downloads historical market data from multiple sources:
- Yahoo Finance: Free, but limited to 7 days for 1-minute data
- Alpaca: Requires API credentials, supports years of 1-minute data

Data is saved to market_data_cache/ directory in parquet format.
"""

import os
import yaml
import pandas as pd
import requests
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import yfinance as yf

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # python-dotenv not installed, will use environment variables only

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class EnhancedDataDownloader:
    """Download historical data from Yahoo Finance or Alpaca."""

    def __init__(self, cache_dir: str = "market_data_cache"):
        """
        Initialize downloader.

        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Load Alpaca credentials from config
        self.alpaca_config = self._load_alpaca_config()

        # Initialize Alpaca headers if credentials available
        self.alpaca_headers = None
        if self.alpaca_config.get('api_key') and self.alpaca_config.get('api_secret'):
            self.alpaca_headers = {
                'accept': 'application/json',
                'APCA-API-KEY-ID': self.alpaca_config['api_key'],
                'APCA-API-SECRET-KEY': self.alpaca_config['api_secret']
            }
            logger.info("✓ Alpaca credentials loaded successfully")
        else:
            logger.warning("⚠ Alpaca credentials not found - only Yahoo Finance will be available")

    def _load_alpaca_config(self) -> dict:
        """Load Alpaca configuration from config.yaml and environment."""
        config = {
            'api_key': None,
            'api_secret': None,
            'base_url': 'https://data.alpaca.markets/v2'
        }

        # Try to load from config.yaml
        config_path = Path('config.yaml')
        if config_path.exists():
            try:
                with open(config_path) as f:
                    yaml_config = yaml.safe_load(f)
                    alpaca_config = yaml_config.get('data_sources', {}).get('alpaca', {})

                    # Get API key
                    api_key = alpaca_config.get('api_key', '')
                    # Remove ${ALPACA_API_KEY:...} template and extract default
                    if api_key.startswith('${'):
                        # Extract default value after colon
                        api_key = api_key.split(':')[1].rstrip('}')
                    config['api_key'] = api_key

                    # Get API secret from environment or config
                    config['api_secret'] = os.environ.get('ALPACA_API_SECRET', alpaca_config.get('api_secret', ''))

                    # Get data URL
                    data_url = alpaca_config.get('data_url', config['base_url'])
                    if data_url:
                        config['base_url'] = data_url

            except Exception as e:
                logger.error(f"Error loading config.yaml: {e}")

        # Override with environment variables if set
        if os.environ.get('ALPACA_API_KEY'):
            config['api_key'] = os.environ.get('ALPACA_API_KEY')
        if os.environ.get('ALPACA_API_SECRET'):
            config['api_secret'] = os.environ.get('ALPACA_API_SECRET')

        return config

    def download_yahoo(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1m"
    ) -> dict:
        """
        Download data from Yahoo Finance.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            interval: Data interval (1m, 5m, 15m, 1h, 1d)

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        logger.info("=" * 80)
        logger.info("DOWNLOADING DATA FROM YAHOO FINANCE")
        logger.info("=" * 80)
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Interval: {interval}")
        logger.info("=" * 80)

        results = {}

        for symbol in symbols:
            try:
                logger.info(f"Downloading {symbol}...")

                # Download data
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True
                )

                if df.empty:
                    logger.warning(f"No data returned for {symbol}")
                    continue

                # Reset index to get datetime as column
                df.reset_index(inplace=True)

                # Standardize column names
                df.columns = [col.lower() for col in df.columns]

                # Ensure timestamp column
                timestamp_col = None
                for possible_name in ['datetime', 'date', 'timestamp', 'index']:
                    if possible_name in df.columns:
                        timestamp_col = possible_name
                        break

                if timestamp_col and timestamp_col != 'timestamp':
                    df.rename(columns={timestamp_col: 'timestamp'}, inplace=True)

                if 'timestamp' not in df.columns:
                    logger.error(f"Could not find timestamp column for {symbol}")
                    continue

                # Ensure timestamp is datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Keep only OHLCV columns
                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                df = df[[col for col in required_cols if col in df.columns]]

                # Save to cache
                cache_file = self.cache_dir / f"{symbol}_{interval}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet"
                df.to_parquet(cache_file, index=False)

                results[symbol] = df
                logger.info(f"✓ Downloaded {len(df)} bars for {symbol} -> {cache_file.name}")

            except Exception as e:
                logger.error(f"✗ Error downloading {symbol}: {e}")

        logger.info(f"\nSuccessfully downloaded data for {len(results)}/{len(symbols)} symbols")
        return results

    def download_alpaca(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1Min"
    ) -> dict:
        """
        Download data from Alpaca.

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            timeframe: Data timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        if not self.alpaca_headers:
            logger.error("Alpaca credentials not configured!")
            logger.error("Please set ALPACA_API_SECRET environment variable")
            return {}

        logger.info("=" * 80)
        logger.info("DOWNLOADING DATA FROM ALPACA")
        logger.info("=" * 80)
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Timeframe: {timeframe}")
        logger.info("=" * 80)

        results = {}

        for symbol in symbols:
            try:
                logger.info(f"Downloading {symbol}...")

                # Fetch bars from Alpaca
                df = self._fetch_alpaca_bars(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe
                )

                if df.empty:
                    logger.warning(f"No data returned for {symbol}")
                    continue

                # Save to cache
                # Convert timeframe to Yahoo-style interval for filename consistency
                interval_map = {
                    '1Min': '1m',
                    '5Min': '5m',
                    '15Min': '15m',
                    '1Hour': '1h',
                    '1Day': '1d'
                }
                interval = interval_map.get(timeframe, timeframe.lower())

                cache_file = self.cache_dir / f"{symbol}_{interval}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet"
                df.to_parquet(cache_file, index=False)

                results[symbol] = df
                logger.info(f"✓ Downloaded {len(df)} bars for {symbol} -> {cache_file.name}")

            except Exception as e:
                logger.error(f"✗ Error downloading {symbol}: {e}")

        logger.info(f"\nSuccessfully downloaded data for {len(results)}/{len(symbols)} symbols")
        return results

    def _fetch_alpaca_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1Min",
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        Fetch historical bars from Alpaca API with pagination.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            limit: Max bars per request (max 10000)

        Returns:
            DataFrame with OHLCV data
        """
        # Format dates for API
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # API endpoint
        url = f"{self.alpaca_config['base_url']}/stocks/{symbol}/bars"

        params = {
            'start': start_str,
            'end': end_str,
            'timeframe': timeframe,
            'limit': limit,
            'adjustment': 'split',  # Adjust for splits
            'feed': 'iex',  # Use IEX feed
        }

        all_bars = []
        page_token = None
        page_count = 0

        while True:
            if page_token:
                params['page_token'] = page_token

            response = requests.get(url, headers=self.alpaca_headers, params=params)

            if response.status_code == 200:
                data = response.json()

                if 'bars' in data and data['bars']:
                    all_bars.extend(data['bars'])
                    page_count += 1
                    logger.debug(f"  Page {page_count}: Retrieved {len(data['bars'])} bars")

                    # Check for next page
                    if 'next_page_token' in data and data['next_page_token']:
                        page_token = data['next_page_token']
                        time.sleep(0.2)  # Rate limiting
                    else:
                        break
                else:
                    break

            elif response.status_code == 429:
                logger.warning("  Rate limited, waiting 60 seconds...")
                time.sleep(60)
                continue

            else:
                logger.error(f"  API Error {response.status_code}: {response.text}")
                break

        if not all_bars:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(all_bars)
        df['t'] = pd.to_datetime(df['t'])
        df = df.rename(columns={
            't': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
        })

        # Keep only OHLCV columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('timestamp')

        return df

    def download_auto(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1m"
    ) -> dict:
        """
        Automatically choose best data source based on date range and availability.

        Rules:
        - Yahoo Finance: Used for 7 days or less of 1-minute data
        - Alpaca: Used for longer periods or when Yahoo fails

        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            interval: Data interval (1m, 5m, 15m, 1h, 1d)

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        days = (end_date - start_date).days

        # Determine best source
        if interval == "1m" and days > 7:
            # Need Alpaca for more than 7 days of 1-minute data
            if self.alpaca_headers:
                logger.info(f"Using Alpaca for {days}-day period with 1-minute data")
                # Convert interval to Alpaca timeframe
                timeframe = "1Min"
                return self.download_alpaca(symbols, start_date, end_date, timeframe)
            else:
                logger.warning(f"Yahoo Finance only supports 7 days of 1-minute data, but {days} days requested")
                logger.warning("Using Yahoo Finance anyway - data may be limited")
                return self.download_yahoo(symbols, start_date, end_date, interval)
        else:
            # Yahoo Finance is sufficient
            logger.info(f"Using Yahoo Finance for {days}-day period")
            return self.download_yahoo(symbols, start_date, end_date, interval)


def main():
    """Test the enhanced downloader."""
    import argparse

    parser = argparse.ArgumentParser(description="Download market data")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", default="1m", help="Data interval (1m, 5m, 15m, 1h, 1d)")
    parser.add_argument("--source", choices=['yahoo', 'alpaca', 'auto'], default='auto',
                        help="Data source to use")

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    downloader = EnhancedDataDownloader()

    if args.source == 'yahoo':
        results = downloader.download_yahoo(symbols, start_date, end_date, args.interval)
    elif args.source == 'alpaca':
        # Convert interval to Alpaca timeframe
        interval_map = {'1m': '1Min', '5m': '5Min', '15m': '15Min', '1h': '1Hour', '1d': '1Day'}
        timeframe = interval_map.get(args.interval, args.interval)
        results = downloader.download_alpaca(symbols, start_date, end_date, timeframe)
    else:
        results = downloader.download_auto(symbols, start_date, end_date, args.interval)

    print(f"\n✓ Downloaded data for {len(results)} symbols")


if __name__ == "__main__":
    main()
