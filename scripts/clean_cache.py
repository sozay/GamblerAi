#!/usr/bin/env python3
"""
Clean market data cache to remove old Yahoo Finance data.
Use this after switching to Alpaca-only to ensure fresh data downloads.
"""

import argparse
from pathlib import Path
import sys

def clean_cache(cache_dir: str = "market_data_cache", dry_run: bool = False):
    """
    Remove all cached market data files.

    Args:
        cache_dir: Cache directory path
        dry_run: If True, only show what would be deleted without actually deleting
    """
    cache_path = Path(cache_dir)

    if not cache_path.exists():
        print(f"✓ Cache directory doesn't exist: {cache_dir}")
        return

    # Find all parquet files
    parquet_files = list(cache_path.glob("*.parquet"))

    if not parquet_files:
        print(f"✓ No cached data files found in {cache_dir}")
        return

    print(f"Found {len(parquet_files)} cached data files:")
    print("=" * 80)

    total_size = 0
    for file in parquet_files:
        size = file.stat().st_size
        total_size += size
        print(f"  {file.name} ({size:,} bytes)")

    print("=" * 80)
    print(f"Total size: {total_size:,} bytes ({total_size / 1024:.1f} KB)")
    print()

    if dry_run:
        print("DRY RUN - No files deleted")
        print(f"To actually delete these files, run: python scripts/clean_cache.py --confirm")
        return

    # Delete files
    print("Deleting files...")
    deleted_count = 0
    for file in parquet_files:
        try:
            file.unlink()
            deleted_count += 1
            print(f"  ✓ Deleted {file.name}")
        except Exception as e:
            print(f"  ✗ Error deleting {file.name}: {e}")

    print()
    print(f"✓ Successfully deleted {deleted_count}/{len(parquet_files)} files")
    print()
    print("Next steps:")
    print("1. New data will be downloaded from Alpaca on next simulation run")
    print("2. Make sure ALPACA_API_SECRET environment variable is set")


def main():
    parser = argparse.ArgumentParser(
        description="Clean market data cache (remove old Yahoo Finance data)"
    )
    parser.add_argument(
        "--cache-dir",
        default="market_data_cache",
        help="Cache directory path (default: market_data_cache)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion (without this, runs in dry-run mode)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("MARKET DATA CACHE CLEANER")
    print("=" * 80)
    print()

    if not args.confirm:
        print("Running in DRY RUN mode (no files will be deleted)")
        print()

    clean_cache(cache_dir=args.cache_dir, dry_run=not args.confirm)


if __name__ == "__main__":
    main()
