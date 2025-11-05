"""
Stock Screener

Scans universe of stocks and selects the best candidates for trading
based on various criteria.
"""

from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import pandas as pd
import requests
from dataclasses import dataclass

from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StockCandidate:
    """A stock candidate from screening."""
    symbol: str
    score: float
    reason: str
    price: float
    volume: int
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class StockScreener:
    """
    Screen stocks based on multiple criteria.

    Screening Strategies:
    1. Momentum - Find stocks with strong price momentum
    2. Mean Reversion - Find oversold stocks ready to bounce
    3. Breakout - Find stocks breaking out of consolidation
    4. Volume - Find stocks with unusual volume
    5. Sector - Find strongest sectors/industries
    """

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        min_price: float = 5.0,
        max_price: float = 500.0,
        min_volume: int = 1_000_000,
        min_market_cap: float = 1_000_000_000,  # $1B
    ):
        """
        Initialize stock screener.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            min_price: Minimum stock price
            max_price: Maximum stock price
            min_volume: Minimum average daily volume
            min_market_cap: Minimum market cap
        """
        self.api_key = api_key or "PKJUPGKDCCIMZKPDXUFXHM3E4D"
        self.api_secret = api_secret or "CcXV59Li9bQC4K3yfmNXVsZ3GYwrEFrGfECGbRjaVb3H"
        self.base_url = "https://data.alpaca.markets"

        self.min_price = min_price
        self.max_price = max_price
        self.min_volume = min_volume
        self.min_market_cap = min_market_cap

        # Trading universe (can be expanded)
        self.universe = self._get_default_universe()

        # Session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        })

    def _get_default_universe(self) -> List[str]:
        """Get default trading universe."""
        # Start with major ETFs and liquid stocks
        return [
            # Major ETFs
            "SPY", "QQQ", "IWM", "DIA",

            # Tech
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "NFLX",

            # Finance
            "JPM", "BAC", "WFC", "GS", "MS",

            # Healthcare
            "JNJ", "UNH", "PFE", "ABBV", "TMO",

            # Consumer
            "WMT", "HD", "MCD", "NKE", "SBUX",

            # Energy
            "XOM", "CVX", "COP",

            # Industrials
            "BA", "CAT", "GE",

            # Communication
            "T", "VZ", "DIS",
        ]

    def screen_momentum(
        self,
        lookback_days: int = 20,
        min_gain_pct: float = 10.0,
        top_n: int = 10,
    ) -> List[StockCandidate]:
        """
        Screen for momentum stocks.

        Finds stocks with:
        - Strong price momentum (>10% gain)
        - Increasing volume
        - Above average volume

        Args:
            lookback_days: Period to calculate momentum
            min_gain_pct: Minimum % gain required
            top_n: Number of top candidates to return

        Returns:
            List of StockCandidate objects
        """
        logger.info(f"Screening for momentum stocks (lookback={lookback_days}d, min_gain={min_gain_pct}%)")

        candidates = []

        for symbol in self.universe:
            try:
                # Get historical data
                bars = self._get_bars(symbol, lookback_days)

                if bars is None or len(bars) < lookback_days:
                    continue

                # Calculate momentum
                start_price = bars['close'].iloc[0]
                current_price = bars['close'].iloc[-1]
                gain_pct = ((current_price - start_price) / start_price) * 100

                # Calculate volume trend
                avg_volume = bars['volume'].mean()
                recent_volume = bars['volume'].tail(5).mean()
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0

                # Filter criteria
                if (gain_pct >= min_gain_pct and
                    volume_ratio >= 1.2 and
                    current_price >= self.min_price and
                    current_price <= self.max_price):

                    score = gain_pct * volume_ratio  # Combined score

                    candidates.append(StockCandidate(
                        symbol=symbol,
                        score=score,
                        reason=f"Momentum: +{gain_pct:.1f}%, Vol: {volume_ratio:.1f}x",
                        price=current_price,
                        volume=int(recent_volume),
                    ))

            except Exception as e:
                logger.debug(f"Error screening {symbol}: {e}")
                continue

        # Sort by score and return top N
        candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(candidates)} momentum candidates")
        return candidates[:top_n]

    def screen_mean_reversion(
        self,
        lookback_days: int = 20,
        oversold_threshold: float = -10.0,
        top_n: int = 10,
    ) -> List[StockCandidate]:
        """
        Screen for mean reversion opportunities.

        Finds stocks that are:
        - Oversold (down >10%)
        - Near support levels
        - With strong fundamentals

        Args:
            lookback_days: Period to look for pullback
            oversold_threshold: Maximum % loss to consider
            top_n: Number of top candidates

        Returns:
            List of StockCandidate objects
        """
        logger.info(f"Screening for mean reversion stocks (oversold<{oversold_threshold}%)")

        candidates = []

        for symbol in self.universe:
            try:
                bars = self._get_bars(symbol, lookback_days)

                if bars is None or len(bars) < lookback_days:
                    continue

                # Calculate pullback
                high_price = bars['high'].max()
                current_price = bars['close'].iloc[-1]
                pullback_pct = ((current_price - high_price) / high_price) * 100

                # Calculate RSI (simple version)
                rsi = self._calculate_rsi(bars['close'])

                # Recent volume
                avg_volume = bars['volume'].mean()
                recent_volume = bars['volume'].tail(5).mean()

                # Filter: oversold stocks with decent volume
                if (pullback_pct <= oversold_threshold and
                    pullback_pct >= -30.0 and  # Not too oversold (might be broken)
                    rsi < 35 and  # RSI oversold
                    current_price >= self.min_price and
                    current_price <= self.max_price and
                    avg_volume >= self.min_volume):

                    # Score: More oversold = higher score, but penalize if too extreme
                    score = abs(pullback_pct) * (1 if rsi < 30 else 0.8)

                    candidates.append(StockCandidate(
                        symbol=symbol,
                        score=score,
                        reason=f"Pullback: {pullback_pct:.1f}%, RSI: {rsi:.0f}",
                        price=current_price,
                        volume=int(recent_volume),
                    ))

            except Exception as e:
                logger.debug(f"Error screening {symbol}: {e}")
                continue

        candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(candidates)} mean reversion candidates")
        return candidates[:top_n]

    def screen_breakout(
        self,
        lookback_days: int = 60,
        consolidation_days: int = 20,
        top_n: int = 10,
    ) -> List[StockCandidate]:
        """
        Screen for breakout candidates.

        Finds stocks that:
        - Consolidated in tight range
        - Breaking out with volume
        - Near all-time or 52-week highs

        Args:
            lookback_days: Period to analyze
            consolidation_days: Days of consolidation required
            top_n: Number of candidates

        Returns:
            List of StockCandidate objects
        """
        logger.info("Screening for breakout stocks")

        candidates = []

        for symbol in self.universe:
            try:
                bars = self._get_bars(symbol, lookback_days)

                if bars is None or len(bars) < lookback_days:
                    continue

                current_price = bars['close'].iloc[-1]

                # Check recent consolidation
                recent = bars.tail(consolidation_days)
                high = recent['high'].max()
                low = recent['low'].min()
                range_pct = ((high - low) / low) * 100

                # Check if breaking out
                period_high = bars['high'].max()
                is_breakout = current_price >= period_high * 0.99  # Within 1% of high

                # Volume surge
                avg_volume = bars['volume'].head(-5).mean()
                recent_volume = bars['volume'].tail(5).mean()
                volume_surge = recent_volume / avg_volume if avg_volume > 0 else 0

                # Tight consolidation + breakout + volume = good signal
                if (range_pct < 15 and  # Tight range
                    is_breakout and
                    volume_surge > 1.5 and
                    current_price >= self.min_price and
                    current_price <= self.max_price):

                    score = volume_surge * (20 - range_pct)  # Higher score for tighter range + more volume

                    candidates.append(StockCandidate(
                        symbol=symbol,
                        score=score,
                        reason=f"Breakout: Range {range_pct:.1f}%, Vol: {volume_surge:.1f}x",
                        price=current_price,
                        volume=int(recent_volume),
                    ))

            except Exception as e:
                logger.debug(f"Error screening {symbol}: {e}")
                continue

        candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(candidates)} breakout candidates")
        return candidates[:top_n]

    def screen_volume_surge(
        self,
        lookback_days: int = 20,
        min_volume_ratio: float = 3.0,
        top_n: int = 10,
    ) -> List[StockCandidate]:
        """
        Screen for unusual volume activity.

        Finds stocks with:
        - Volume significantly above average
        - Price movement accompanying volume
        - Recent volume surge

        Args:
            lookback_days: Period to calculate average volume
            min_volume_ratio: Minimum volume vs average
            top_n: Number of candidates

        Returns:
            List of StockCandidate objects
        """
        logger.info(f"Screening for volume surge (min_ratio={min_volume_ratio}x)")

        candidates = []

        for symbol in self.universe:
            try:
                bars = self._get_bars(symbol, lookback_days)

                if bars is None or len(bars) < lookback_days:
                    continue

                # Calculate volume metrics
                avg_volume = bars['volume'].head(-1).mean()  # Exclude today
                current_volume = bars['volume'].iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

                # Price movement
                prev_close = bars['close'].iloc[-2]
                current_price = bars['close'].iloc[-1]
                price_change_pct = ((current_price - prev_close) / prev_close) * 100

                # Filter
                if (volume_ratio >= min_volume_ratio and
                    abs(price_change_pct) > 2.0 and  # Significant price move
                    current_price >= self.min_price and
                    current_price <= self.max_price):

                    score = volume_ratio * abs(price_change_pct)

                    candidates.append(StockCandidate(
                        symbol=symbol,
                        score=score,
                        reason=f"Volume: {volume_ratio:.1f}x, Price: {price_change_pct:+.1f}%",
                        price=current_price,
                        volume=int(current_volume),
                    ))

            except Exception as e:
                logger.debug(f"Error screening {symbol}: {e}")
                continue

        candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(f"Found {len(candidates)} volume surge candidates")
        return candidates[:top_n]

    def screen_all(self, top_n_per_strategy: int = 5) -> Dict[str, List[StockCandidate]]:
        """
        Run all screening strategies.

        Args:
            top_n_per_strategy: Number of candidates per strategy

        Returns:
            Dictionary with strategy name -> candidates
        """
        logger.info("Running comprehensive stock screening...")

        results = {
            "momentum": self.screen_momentum(top_n=top_n_per_strategy),
            "mean_reversion": self.screen_mean_reversion(top_n=top_n_per_strategy),
            "breakout": self.screen_breakout(top_n=top_n_per_strategy),
            "volume_surge": self.screen_volume_surge(top_n=top_n_per_strategy),
        }

        # Log summary
        total = sum(len(candidates) for candidates in results.values())
        logger.info(f"Screening complete: {total} candidates across 4 strategies")

        return results

    def get_combined_top_picks(
        self,
        strategies: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[StockCandidate]:
        """
        Get top picks combining multiple strategies.

        Args:
            strategies: List of strategy names to use (None = all)
            top_n: Number of top picks to return

        Returns:
            Combined and deduplicated list of top candidates
        """
        if strategies is None:
            strategies = ["momentum", "mean_reversion", "breakout", "volume_surge"]

        all_candidates = []

        if "momentum" in strategies:
            all_candidates.extend(self.screen_momentum(top_n=top_n))

        if "mean_reversion" in strategies:
            all_candidates.extend(self.screen_mean_reversion(top_n=top_n))

        if "breakout" in strategies:
            all_candidates.extend(self.screen_breakout(top_n=top_n))

        if "volume_surge" in strategies:
            all_candidates.extend(self.screen_volume_surge(top_n=top_n))

        # Deduplicate by symbol, keeping highest score
        seen = {}
        for candidate in all_candidates:
            if candidate.symbol not in seen or candidate.score > seen[candidate.symbol].score:
                seen[candidate.symbol] = candidate

        # Sort by score
        top_picks = sorted(seen.values(), key=lambda x: x.score, reverse=True)

        logger.info(f"Combined top {len(top_picks)} picks from {len(strategies)} strategies")

        return top_picks[:top_n]

    def _get_bars(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """Get historical bars for a symbol."""
        try:
            end = datetime.now()
            start = end - timedelta(days=days + 10)  # Extra days for weekends

            response = self.session.get(
                f"{self.base_url}/v2/stocks/{symbol}/bars",
                params={
                    "timeframe": "1Day",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "limit": days,
                }
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if 'bars' not in data or not data['bars']:
                return None

            df = pd.DataFrame(data['bars'])
            df['timestamp'] = pd.to_datetime(df['t'])
            df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            logger.debug(f"Error getting bars for {symbol}: {e}")
            return None

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        try:
            deltas = prices.diff()
            gain = deltas.where(deltas > 0, 0).rolling(window=period).mean()
            loss = -deltas.where(deltas < 0, 0).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return rsi.iloc[-1]

        except:
            return 50.0  # Neutral if calculation fails
