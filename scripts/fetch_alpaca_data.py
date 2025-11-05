#!/usr/bin/env python3
"""
Fetch real historical data from Alpaca using direct REST API calls.

Alpaca provides free historical data API - no authentication needed for basic data.
Uses the Data API v2 which provides free historical stock data.
"""

import argparse
from datetime import datetime, timedelta
import pandas as pd
import requests
import time
from pathlib import Path


class AlpacaDataFetcher:
    """Fetch historical data from Alpaca Data API."""

    def __init__(self, api_key=None, api_secret=None):
        """
        Initialize Alpaca data fetcher.

        For free tier historical data, you can use paper trading credentials
        or even without authentication for limited data.
        """
        self.base_url = "https://data.alpaca.markets/v2"
        self.headers = {
            'accept': 'application/json',
        }

        # Add authentication if provided
        if api_key and api_secret:
            self.headers['APCA-API-KEY-ID'] = api_key
            self.headers['APCA-API-SECRET-KEY'] = api_secret

    def fetch_bars(self, symbol, start_date, end_date, timeframe='1Day', limit=10000):
        """
        Fetch historical bars from Alpaca.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            limit: Max bars per request (max 10000)
        """
        print(f"  Fetching {symbol} from Alpaca...")

        # Format dates for API
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # API endpoint
        url = f"{self.base_url}/stocks/{symbol}/bars"

        params = {
            'start': start_str,
            'end': end_str,
            'timeframe': timeframe,
            'limit': limit,
            'adjustment': 'split',  # Adjust for splits
            'feed': 'iex',  # Use IEX feed (free tier)
        }

        all_bars = []
        page_token = None

        try:
            while True:
                if page_token:
                    params['page_token'] = page_token

                response = requests.get(url, headers=self.headers, params=params)

                if response.status_code == 200:
                    data = response.json()

                    if 'bars' in data and data['bars']:
                        all_bars.extend(data['bars'])
                        print(f"    Retrieved {len(data['bars'])} bars...")

                        # Check for next page
                        if 'next_page_token' in data and data['next_page_token']:
                            page_token = data['next_page_token']
                            time.sleep(0.2)  # Rate limiting
                        else:
                            break
                    else:
                        break

                elif response.status_code == 429:
                    print("    Rate limited, waiting 60 seconds...")
                    time.sleep(60)
                    continue

                else:
                    print(f"    Error {response.status_code}: {response.text}")
                    break

            if all_bars:
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
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                df = df.sort_values('timestamp')

                print(f"  ✓ Fetched {len(df)} bars for {symbol}")
                return df
            else:
                print(f"  ✗ No data returned for {symbol}")
                return pd.DataFrame()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return pd.DataFrame()

    def save_data(self, df, symbol, timeframe, output_dir="real_data"):
        """Save data to CSV."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        if df.empty:
            return None

        filename = output_path / f"{symbol}_{timeframe}_{df['timestamp'].min().strftime('%Y%m%d')}_{df['timestamp'].max().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False)

        print(f"  ✓ Saved to {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description="Fetch real data from Alpaca")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--timeframe", default="1Day", help="Timeframe: 1Min, 5Min, 15Min, 1Hour, 1Day")
    parser.add_argument("--api-key", help="Alpaca API key (optional for free data)")
    parser.add_argument("--api-secret", help="Alpaca API secret (optional for free data)")
    parser.add_argument("--output-dir", default="real_data", help="Output directory")

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    print("=" * 80)
    print("FETCHING REAL DATA FROM ALPACA")
    print("=" * 80)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Timeframe: {args.timeframe}")
    print("=" * 80 + "\n")

    fetcher = AlpacaDataFetcher(args.api_key, args.api_secret)

    results = {}

    for symbol in symbols:
        df = fetcher.fetch_bars(symbol, start_date, end_date, args.timeframe)

        if not df.empty:
            filename = fetcher.save_data(df, symbol, args.timeframe, args.output_dir)
            results[symbol] = {
                'bars': len(df),
                'filename': filename,
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max(),
                'price_range': f"${df['low'].min():.2f} - ${df['high'].max():.2f}"
            }
        else:
            results[symbol] = None

        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for symbol, result in results.items():
        if result:
            print(f"{symbol:8s}: {result['bars']:6d} bars")
            print(f"           {result['start']} to {result['end']}")
            print(f"           Price range: {result['price_range']}")
            print(f"           File: {result['filename']}")
        else:
            print(f"{symbol:8s}: FAILED")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
