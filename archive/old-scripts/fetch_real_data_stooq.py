#!/usr/bin/env python3
"""
Fetch real historical data using pandas_datareader with Stooq.
Stooq is a free data source that doesn't require authentication.
"""

import argparse
from datetime import datetime
import pandas as pd
import pandas_datareader.data as web
from pathlib import Path


def fetch_stooq_data(symbol, start_date, end_date):
    """Fetch data from Stooq."""
    try:
        print(f"  Fetching {symbol} from Stooq...")

        # Stooq uses lowercase symbols
        df = web.DataReader(
            symbol.lower(),
            'stooq',
            start=start_date,
            end=end_date
        )

        # Stooq returns data in reverse chronological order, so reverse it
        df = df.sort_index()

        print(f"  ✓ Fetched {len(df)} bars for {symbol}")
        return df

    except Exception as e:
        print(f"  ✗ Error fetching {symbol}: {e}")
        return pd.DataFrame()


def save_data(df, symbol, output_dir="real_data"):
    """Save data to CSV."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    if df.empty:
        print(f"  ✗ No data to save for {symbol}")
        return None

    # Prepare dataframe
    df = df.reset_index()
    df.columns = [col.lower() for col in df.columns]

    # Rename date column to timestamp
    df.rename(columns={'date': 'timestamp'}, inplace=True)

    # Save to CSV
    filename = output_path / f"{symbol}_daily_{df['timestamp'].min().strftime('%Y%m%d')}_{df['timestamp'].max().strftime('%Y%m%d')}.csv"
    df.to_csv(filename, index=False)

    print(f"  ✓ Saved to {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="Fetch real historical data from Stooq")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default="real_data", help="Output directory")

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    print("=" * 80)
    print("FETCHING REAL HISTORICAL DATA FROM STOOQ")
    print("=" * 80)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Interval: Daily")
    print("=" * 80 + "\n")

    results = {}

    for symbol in symbols:
        df = fetch_stooq_data(symbol, start_date, end_date)

        if not df.empty:
            filename = save_data(df, symbol, args.output_dir)
            results[symbol] = {
                'bars': len(df),
                'filename': filename,
                'start': df.index.min() if hasattr(df.index, 'min') else df.iloc[0]['timestamp'],
                'end': df.index.max() if hasattr(df.index, 'max') else df.iloc[-1]['timestamp'],
            }
        else:
            results[symbol] = None

        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for symbol, result in results.items():
        if result:
            print(f"{symbol:8s}: {result['bars']:6d} bars from {result['start']} to {result['end']}")
            print(f"           File: {result['filename']}")
        else:
            print(f"{symbol:8s}: FAILED")

    print("=" * 80 + "\n")

    return results


if __name__ == "__main__":
    main()
