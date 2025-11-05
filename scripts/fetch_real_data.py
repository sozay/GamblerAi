#!/usr/bin/env python3
"""
Fetch real historical data and save to CSV for backtesting.

Uses yfinance with retry logic and multiple data sources.
"""

import argparse
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import time
from pathlib import Path


def fetch_with_retry(symbol, start_date, end_date, interval="1d", max_retries=3):
    """Fetch data with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}/{max_retries} for {symbol}...")

            ticker = yf.Ticker(symbol)

            # For intraday data, we need to chunk it due to Yahoo limitations
            if interval in ["1m", "2m", "5m", "15m", "30m", "60m", "90m"]:
                # Yahoo limits: 1m = 7 days, 5m/15m/30m/60m = 60 days
                chunk_days = 7 if interval == "1m" else 60

                all_data = []
                current_start = start_date

                while current_start < end_date:
                    current_end = min(current_start + timedelta(days=chunk_days), end_date)

                    print(f"    Fetching {current_start.date()} to {current_end.date()}...")

                    df = ticker.history(
                        start=current_start.strftime("%Y-%m-%d"),
                        end=current_end.strftime("%Y-%m-%d"),
                        interval=interval,
                        actions=False,
                        auto_adjust=True,
                        back_adjust=False,
                        repair=True,
                    )

                    if not df.empty:
                        all_data.append(df)
                        time.sleep(0.5)  # Rate limiting

                    current_start = current_end

                if all_data:
                    result = pd.concat(all_data)
                    result = result[~result.index.duplicated(keep='first')]
                    return result
                else:
                    return pd.DataFrame()
            else:
                # For daily or longer intervals
                df = ticker.history(
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    interval=interval,
                    actions=False,
                    auto_adjust=True,
                    back_adjust=False,
                    repair=True,
                )
                return df

        except Exception as e:
            print(f"    Error: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"    Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"    Failed after {max_retries} attempts")
                return pd.DataFrame()

    return pd.DataFrame()


def save_data(df, symbol, interval, output_dir="data"):
    """Save data to CSV."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    if df.empty:
        print(f"  ✗ No data to save for {symbol}")
        return None

    # Prepare dataframe
    df = df.reset_index()
    df.columns = [col.lower() for col in df.columns]

    # Rename date/datetime column to timestamp
    if 'date' in df.columns:
        df.rename(columns={'date': 'timestamp'}, inplace=True)
    elif 'datetime' in df.columns:
        df.rename(columns={'datetime': 'timestamp'}, inplace=True)

    # Save to CSV
    filename = output_path / f"{symbol}_{interval}_{df['timestamp'].min().strftime('%Y%m%d')}_{df['timestamp'].max().strftime('%Y%m%d')}.csv"
    df.to_csv(filename, index=False)

    print(f"  ✓ Saved {len(df)} bars to {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="Fetch real historical data")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--interval", default="1d", help="Data interval (1d, 1h, 5m, etc)")
    parser.add_argument("--output-dir", default="data", help="Output directory")

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    print("=" * 80)
    print("FETCHING REAL HISTORICAL DATA")
    print("=" * 80)
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Interval: {args.interval}")
    print("=" * 80 + "\n")

    results = {}

    for symbol in symbols:
        print(f"Fetching {symbol}...")
        df = fetch_with_retry(symbol, start_date, end_date, args.interval)

        if not df.empty:
            filename = save_data(df, symbol, args.interval, args.output_dir)
            results[symbol] = {
                'bars': len(df),
                'filename': filename,
                'start': df.index.min(),
                'end': df.index.max(),
            }
        else:
            results[symbol] = None

        print()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for symbol, result in results.items():
        if result:
            print(f"{symbol:8s}: {result['bars']:6d} bars, {result['start']} to {result['end']}")
        else:
            print(f"{symbol:8s}: FAILED")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
