"""
Live Scanner Runner

Fetches real-time market data and runs stock scanner to select best trading opportunities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import time

from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType, ScanResult
from gambler_ai.analysis.stock_universe import StockUniverse
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector


class LiveScannerRunner:
    """
    Runs stock scanner on live market data.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        scanner_type: ScannerType = ScannerType.TOP_MOVERS,
        max_stocks: int = 3,
        universe: str = "liquid",
    ):
        """
        Initialize live scanner runner.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            scanner_type: Type of scanner to use
            max_stocks: Maximum stocks to select
            universe: Stock universe to scan
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.scanner_type = scanner_type
        self.max_stocks = max_stocks
        self.universe = universe

        # Alpaca endpoints
        self.base_url = "https://paper-api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"

        self.headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret,
            'accept': 'application/json',
        }

        # Create scanner
        self.scanner = StockScanner(
            scanner_type=scanner_type,
            max_stocks=max_stocks,
        )

        # Create adaptive selector for analysis
        self.adaptive_selector = AdaptiveStrategySelector(use_volatility_filter=True)

        print(f"✓ LiveScannerRunner initialized")
        print(f"  Scanner: {scanner_type.value}")
        print(f"  Universe: {universe} ({len(self.get_symbols())} stocks)")
        print(f"  Max stocks: {max_stocks}")

    def get_symbols(self) -> List[str]:
        """Get list of symbols to scan."""
        return StockUniverse.get_universe(self.universe)

    def fetch_market_data(self, symbol: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """
        Fetch real-time market data from Alpaca.

        Args:
            symbol: Stock symbol
            limit: Number of bars to fetch

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            # Get bars (5-minute timeframe)
            url = f"{self.data_url}/v2/stocks/{symbol}/bars"
            params = {
                'timeframe': '5Min',
                'limit': limit,
                'feed': 'iex',  # Use IEX for free tier
            }

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()

            if 'bars' not in data or not data['bars']:
                return None

            # Convert to DataFrame
            bars = data['bars']
            df = pd.DataFrame(bars)

            # Rename columns to match our format
            df['timestamp'] = pd.to_datetime(df['t'])
            df = df.rename(columns={
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
            })

            # Select required columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            print(f"⚠ Error fetching data for {symbol}: {e}")
            return None

    def scan_market(self) -> List[ScanResult]:
        """
        Scan entire market and return best stocks.

        Returns:
            List of ScanResult objects
        """
        print(f"\n{'='*80}")
        print(f"SCANNING MARKET - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        symbols = self.get_symbols()
        print(f"Fetching data for {len(symbols)} stocks...")

        # Fetch data for all symbols
        stock_data = {}
        for i, symbol in enumerate(symbols, 1):
            print(f"  [{i}/{len(symbols)}] {symbol}...", end=" ")

            df = self.fetch_market_data(symbol)

            if df is not None and len(df) >= 200:
                stock_data[symbol] = df
                print("✓")
            else:
                print("✗ (insufficient data)")

            # Rate limiting (Alpaca free tier: 200 requests/minute)
            time.sleep(0.3)

        print(f"\n✓ Fetched data for {len(stock_data)}/{len(symbols)} stocks")

        if not stock_data:
            print("⚠ No data available for scanning")
            return []

        # Get benchmark (SPY) for relative strength
        benchmark_data = stock_data.get('SPY')

        # Run scanner
        print(f"\nRunning {self.scanner_type.value} scanner...")
        results = self.scanner.scan_stocks(
            stock_data=stock_data,
            adaptive_selector=self.adaptive_selector,
            benchmark_data=benchmark_data,
        )

        # Print results
        print()
        self.scanner.print_scan_results(results)

        return results

    def get_selected_symbols(self) -> List[str]:
        """
        Run scan and return just the selected symbols.

        Returns:
            List of stock symbols
        """
        results = self.scan_market()
        return [r.symbol for r in results]

    def get_scan_details(self) -> Dict[str, Dict]:
        """
        Run scan and return detailed information about each selected stock.

        Returns:
            Dictionary of {symbol: {regime, setups, score, etc.}}
        """
        results = self.scan_market()

        details = {}
        for result in results:
            details[result.symbol] = {
                'score': result.score,
                'regime': result.regime,
                'setups': result.setups,
                'setup_count': result.setup_count,
                'price_change_pct': result.price_change_pct,
                'volume_ratio': result.volume_ratio,
                'volatility': result.volatility,
                'reason': result.reason,
            }

        return details


def create_live_scanner(
    api_key: str,
    api_secret: str,
    scanner_type: str = "top_movers",
    max_stocks: int = 3,
    universe: str = "liquid",
) -> LiveScannerRunner:
    """
    Factory function to create a live scanner.

    Args:
        api_key: Alpaca API key
        api_secret: Alpaca API secret
        scanner_type: Scanner type (top_movers, high_volume, etc.)
        max_stocks: Maximum stocks to select
        universe: Stock universe (liquid, tech, volatile, etc.)

    Returns:
        Configured LiveScannerRunner
    """
    scanner_enum = ScannerType(scanner_type)
    return LiveScannerRunner(
        api_key=api_key,
        api_secret=api_secret,
        scanner_type=scanner_enum,
        max_stocks=max_stocks,
        universe=universe,
    )
