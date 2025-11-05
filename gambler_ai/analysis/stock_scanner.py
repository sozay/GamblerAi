"""
Stock Scanner Strategies

Different methods to scan and select stocks for trading.
"""

from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum


class ScannerType(Enum):
    """Types of stock scanners."""
    TOP_MOVERS = "top_movers"
    HIGH_VOLUME = "high_volume"
    VOLATILITY_RANGE = "volatility_range"
    RELATIVE_STRENGTH = "relative_strength"
    GAP_SCANNER = "gap_scanner"
    BEST_SETUPS = "best_setups"
    SECTOR_LEADERS = "sector_leaders"
    MARKET_CAP_WEIGHTED = "market_cap_weighted"


@dataclass
class ScanResult:
    """Result from scanning a stock."""
    symbol: str
    score: float
    setup_count: int
    regime: str
    volatility: float
    price_change_pct: float
    volume_ratio: float
    setups: List[Dict]
    reason: str  # Why this stock was selected


class StockScanner:
    """
    Scans multiple stocks and selects the best trading opportunities.
    """

    def __init__(
        self,
        scanner_type: ScannerType = ScannerType.BEST_SETUPS,
        max_stocks: int = 5,
        min_volume_ratio: float = 1.2,  # Lowered from 1.5 to 1.2 (20% above average)
        min_price_change: float = 0.5,  # Lowered from 1.0% to 0.5%
    ):
        """
        Initialize stock scanner.

        Args:
            scanner_type: Type of scanning strategy to use
            max_stocks: Maximum number of stocks to select
            min_volume_ratio: Minimum volume ratio vs average (1.5 = 50% above avg)
            min_price_change: Minimum price change % to consider
        """
        self.scanner_type = scanner_type
        self.max_stocks = max_stocks
        self.min_volume_ratio = min_volume_ratio
        self.min_price_change = min_price_change

    def scan_stocks(
        self,
        stock_data: Dict[str, pd.DataFrame],
        adaptive_selector,
        benchmark_data: pd.DataFrame = None,
    ) -> List[ScanResult]:
        """
        Scan multiple stocks and return best opportunities.

        Args:
            stock_data: Dictionary of {symbol: DataFrame} with OHLCV data
            adaptive_selector: AdaptiveStrategySelector instance
            benchmark_data: Optional benchmark (e.g., SPY) for relative strength

        Returns:
            List of ScanResult, sorted by score (best first)
        """
        results = []

        for symbol, df in stock_data.items():
            # Skip if not enough data
            if len(df) < 200:
                continue

            # Analyze this stock
            result = self._analyze_stock(symbol, df, adaptive_selector, benchmark_data)

            if result:
                results.append(result)

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        # Return top N stocks
        return results[:self.max_stocks]

    def _analyze_stock(
        self,
        symbol: str,
        df: pd.DataFrame,
        adaptive_selector,
        benchmark_data: pd.DataFrame,
    ) -> ScanResult:
        """Analyze a single stock."""

        # Get regime and strategy
        regime_info = adaptive_selector.get_regime_info(df)

        # Get setups from adaptive strategy
        setups = adaptive_selector.detect_setups(df)

        if not setups:
            return None

        # Calculate metrics
        price_change = self._calculate_price_change(df)
        volume_ratio = self._calculate_volume_ratio(df)
        volatility = regime_info['volatility_metrics'].get('historical_volatility', 0)

        # Apply scanner-specific logic
        score, reason = self._calculate_score(
            symbol=symbol,
            df=df,
            setups=setups,
            regime=regime_info['regime'],
            price_change=price_change,
            volume_ratio=volume_ratio,
            volatility=volatility,
            benchmark_data=benchmark_data,
        )

        if score <= 0:
            return None

        return ScanResult(
            symbol=symbol,
            score=score,
            setup_count=len(setups),
            regime=regime_info['regime'],
            volatility=volatility,
            price_change_pct=price_change,
            volume_ratio=volume_ratio,
            setups=setups,
            reason=reason,
        )

    def _calculate_score(
        self,
        symbol: str,
        df: pd.DataFrame,
        setups: List[Dict],
        regime: str,
        price_change: float,
        volume_ratio: float,
        volatility: float,
        benchmark_data: pd.DataFrame,
    ) -> Tuple[float, str]:
        """Calculate score based on scanner type."""

        if self.scanner_type == ScannerType.TOP_MOVERS:
            return self._score_top_movers(price_change, volume_ratio, setups)

        elif self.scanner_type == ScannerType.HIGH_VOLUME:
            return self._score_high_volume(volume_ratio, setups)

        elif self.scanner_type == ScannerType.VOLATILITY_RANGE:
            return self._score_volatility_range(volatility, setups)

        elif self.scanner_type == ScannerType.RELATIVE_STRENGTH:
            return self._score_relative_strength(df, benchmark_data, setups)

        elif self.scanner_type == ScannerType.GAP_SCANNER:
            return self._score_gap(df, setups)

        elif self.scanner_type == ScannerType.BEST_SETUPS:
            return self._score_best_setups(setups, regime, volatility)

        elif self.scanner_type == ScannerType.SECTOR_LEADERS:
            return self._score_sector_leader(symbol, price_change, setups)

        elif self.scanner_type == ScannerType.MARKET_CAP_WEIGHTED:
            return self._score_market_cap(symbol, setups)

        else:
            return (len(setups), "default")

    def _score_top_movers(self, price_change: float, volume_ratio: float, setups: List) -> Tuple[float, str]:
        """Score based on price movement."""
        if abs(price_change) < self.min_price_change:
            return (0, "insufficient_move")

        if volume_ratio < self.min_volume_ratio:
            return (0, "low_volume")

        score = abs(price_change) * volume_ratio * len(setups)
        return (score, f"top_mover: {price_change:+.1f}% move on {volume_ratio:.1f}x volume")

    def _score_high_volume(self, volume_ratio: float, setups: List) -> Tuple[float, str]:
        """Score based on volume."""
        if volume_ratio < self.min_volume_ratio:
            return (0, "low_volume")

        score = volume_ratio * len(setups) * 10
        return (score, f"high_volume: {volume_ratio:.1f}x average volume")

    def _score_volatility_range(self, volatility: float, setups: List) -> Tuple[float, str]:
        """Score based on volatility being in optimal range."""
        # Optimal volatility: 15-35% (not too low, not too high)
        if volatility is None:
            return (0, "no_volatility_data")

        if volatility < 0.10 or volatility > 0.50:
            return (0, "volatility_out_of_range")

        # Score highest around 25% volatility
        optimal = 0.25
        distance = abs(volatility - optimal)
        score = (1 - distance / optimal) * len(setups) * 100

        return (max(score, 0), f"optimal_volatility: {volatility:.1%}")

    def _score_relative_strength(
        self,
        df: pd.DataFrame,
        benchmark_data: pd.DataFrame,
        setups: List,
    ) -> Tuple[float, str]:
        """Score based on relative strength vs benchmark."""
        if benchmark_data is None or len(benchmark_data) < 20:
            return (0, "no_benchmark_data")

        # Calculate 20-day returns
        stock_return = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]
        benchmark_return = (benchmark_data['close'].iloc[-1] - benchmark_data['close'].iloc[-20]) / benchmark_data['close'].iloc[-20]

        relative_strength = stock_return - benchmark_return

        if relative_strength < 0:
            return (0, "underperforming_market")

        score = relative_strength * 100 * len(setups)
        return (score, f"relative_strength: {relative_strength:+.1%} vs SPY")

    def _score_gap(self, df: pd.DataFrame, setups: List) -> Tuple[float, str]:
        """
        Score based on significant price gaps.

        For intraday data, looks for gaps >0.5% between any consecutive bars
        (simulates overnight gaps).
        """
        if len(df) < 20:
            return (0, "insufficient_data")

        # Look for any significant gap in last 20 bars
        # Gap = difference between open and previous close
        max_gap = 0
        for i in range(-20, -1):
            try:
                current_open = df['open'].iloc[i]
                previous_close = df['close'].iloc[i-1]
                gap_pct = abs((current_open - previous_close) / previous_close * 100)

                if gap_pct > abs(max_gap):
                    max_gap = gap_pct if (current_open > previous_close) else -gap_pct
            except:
                continue

        if abs(max_gap) < 0.3:  # Minimum 0.3% gap (lowered for intraday)
            return (0, "no_significant_gap")

        score = abs(max_gap) * len(setups) * 10
        return (score, f"gap: {max_gap:+.1f}% detected")

    def _score_best_setups(
        self,
        setups: List[Dict],
        regime: str,
        volatility: float,
    ) -> Tuple[float, str]:
        """Score based on setup quality."""
        if not setups:
            return (0, "no_setups")

        # Calculate average risk/reward
        total_rr = 0
        for setup in setups:
            entry = setup['entry_price']
            target = setup.get('target', entry * 1.02)
            stop = setup.get('stop_loss', entry * 0.98)

            risk = abs(entry - stop)
            reward = abs(target - entry)

            if risk > 0:
                rr = reward / risk
                total_rr += rr

        avg_rr = total_rr / len(setups)

        # Score: # setups * avg risk/reward * 10
        score = len(setups) * avg_rr * 10

        return (score, f"best_setups: {len(setups)} setups, {avg_rr:.1f}:1 R/R")

    def _score_sector_leader(
        self,
        symbol: str,
        price_change: float,
        setups: List,
    ) -> Tuple[float, str]:
        """Score if stock is sector leader."""
        # This would require sector performance data
        # For now, score by price change + setups
        if price_change < 0:
            return (0, "negative_performance")

        score = price_change * len(setups) * 5
        return (score, f"sector_performance: {price_change:+.1f}%")

    def _score_market_cap(self, symbol: str, setups: List) -> Tuple[float, str]:
        """Score based on market cap (prefer larger, more liquid stocks)."""
        from gambler_ai.analysis.stock_universe import StockUniverse

        stock_info = StockUniverse.get_stock_info(symbol)

        if stock_info is None:
            return (len(setups), "unknown_stock")

        # Score: market cap * setups
        # Larger market cap = higher score (more liquid, less risky)
        score = (stock_info.market_cap / 100) * len(setups)

        return (score, f"market_cap: ${stock_info.market_cap:.0f}B")

    def _calculate_price_change(self, df: pd.DataFrame, periods: int = 20) -> float:
        """Calculate recent price change percentage."""
        if len(df) < periods:
            periods = len(df)

        start_price = df['close'].iloc[-periods]
        end_price = df['close'].iloc[-1]

        return (end_price - start_price) / start_price * 100

    def _calculate_volume_ratio(self, df: pd.DataFrame, lookback_recent: int = 20, lookback_baseline: int = 100) -> float:
        """
        Calculate PEAK volume in recent period vs baseline average.

        Args:
            lookback_recent: Recent period to find max volume (default: 20 bars)
            lookback_baseline: Baseline period for average (default: 100 bars)

        Returns:
            Ratio of peak recent volume to baseline average
        """
        total_needed = lookback_baseline + lookback_recent
        if len(df) < total_needed:
            return 1.0

        # Baseline: Average volume from older bars
        baseline_volume = df['volume'].iloc[-(lookback_baseline + lookback_recent):-lookback_recent].mean()

        # Recent: MAXIMUM volume in recent bars (catches spikes)
        recent_max_volume = df['volume'].iloc[-lookback_recent:].max()

        if baseline_volume == 0:
            return 1.0

        return recent_max_volume / baseline_volume

    def print_scan_results(self, results: List[ScanResult]):
        """Print scan results in a formatted table."""
        if not results:
            print("No stocks found matching criteria.")
            return

        print(f"\n{'='*120}")
        print(f"STOCK SCANNER RESULTS - {self.scanner_type.value.upper()}")
        print(f"{'='*120}\n")

        print(f"{'Rank':<6}{'Symbol':<10}{'Score':<10}{'Setups':<10}{'Regime':<10}{'Change':<12}{'Volume':<12}{'Reason':<50}")
        print("-" * 120)

        for i, result in enumerate(results, 1):
            emoji = "🟢" if result.price_change_pct > 0 else "🔴"

            print(
                f"{i:<6}{result.symbol:<10}{result.score:<10.1f}{result.setup_count:<10}"
                f"{result.regime:<10}{emoji} {result.price_change_pct:>6.1f}%  "
                f"{result.volume_ratio:>6.1f}x    {result.reason:<50}"
            )

        print("-" * 120)
        print(f"\nTotal stocks scanned: {len(results)}")
        print(f"Top {min(self.max_stocks, len(results))} selected\n")


def create_scanner(scanner_type: str, max_stocks: int = 5) -> StockScanner:
    """
    Factory function to create a stock scanner.

    Args:
        scanner_type: Type of scanner (top_movers, high_volume, best_setups, etc.)
        max_stocks: Maximum stocks to return

    Returns:
        Configured StockScanner
    """
    scanner_enum = ScannerType(scanner_type)
    return StockScanner(scanner_type=scanner_enum, max_stocks=max_stocks)
