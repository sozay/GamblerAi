"""
Stock Ranker

Ranks stocks based on multiple factors and market conditions.
"""

from typing import List, Dict
import pandas as pd

from .stock_screener import StockCandidate
from gambler_ai.analysis.regime_detector import RegimeDetector, MarketRegime
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)


class StockRanker:
    """
    Rank stocks based on current market regime and multiple factors.

    Ranking Logic:
    - BULL market: Favor momentum and breakout stocks
    - BEAR market: Favor mean reversion and quality
    - RANGE market: Favor mean reversion and volume
    """

    def __init__(self, regime_detector: RegimeDetector = None):
        """
        Initialize stock ranker.

        Args:
            regime_detector: Regime detector instance
        """
        self.regime_detector = regime_detector or RegimeDetector()

        # Weights for different regimes
        self.regime_weights = {
            'BULL': {
                'momentum': 0.40,
                'breakout': 0.30,
                'volume_surge': 0.20,
                'mean_reversion': 0.10,
            },
            'BEAR': {
                'mean_reversion': 0.50,
                'volume_surge': 0.25,
                'momentum': 0.15,
                'breakout': 0.10,
            },
            'RANGE': {
                'mean_reversion': 0.45,
                'volume_surge': 0.30,
                'breakout': 0.15,
                'momentum': 0.10,
            },
        }

    def rank_by_regime(
        self,
        candidates_by_strategy: Dict[str, List[StockCandidate]],
        market_df: pd.DataFrame,
    ) -> List[StockCandidate]:
        """
        Rank stocks based on current market regime.

        Args:
            candidates_by_strategy: Dict of strategy -> candidates
            market_df: Market data (SPY) for regime detection

        Returns:
            Ranked list of stocks
        """
        # Detect current regime
        regime, confidence = self.regime_detector.detect_regime_with_confidence(market_df)

        logger.info(f"Ranking stocks for {regime} market (confidence: {confidence:.2f})")

        # Get weights for this regime
        weights = self.regime_weights[regime]

        # Re-score candidates based on regime
        all_candidates = {}  # symbol -> candidate

        for strategy, candidates in candidates_by_strategy.items():
            strategy_weight = weights.get(strategy, 0.1)

            for candidate in candidates:
                symbol = candidate.symbol

                # Adjust score by regime weight
                adjusted_score = candidate.score * strategy_weight

                # If symbol already seen, take highest score
                if symbol not in all_candidates:
                    # Create new candidate with adjusted score
                    adjusted_candidate = StockCandidate(
                        symbol=symbol,
                        score=adjusted_score,
                        reason=f"{candidate.reason} | {regime}",
                        price=candidate.price,
                        volume=candidate.volume,
                        market_cap=candidate.market_cap,
                        sector=candidate.sector,
                        industry=candidate.industry,
                    )
                    all_candidates[symbol] = adjusted_candidate
                else:
                    # Add to existing score (stock appears in multiple strategies)
                    all_candidates[symbol].score += adjusted_score
                    all_candidates[symbol].reason += f" + {strategy}"

        # Sort by adjusted score
        ranked = sorted(all_candidates.values(), key=lambda x: x.score, reverse=True)

        logger.info(f"Ranked {len(ranked)} stocks for {regime} market")

        return ranked

    def rank_multi_factor(
        self,
        candidates: List[StockCandidate],
        factors: Dict[str, float] = None,
    ) -> List[StockCandidate]:
        """
        Rank stocks using multiple factors.

        Args:
            candidates: List of stock candidates
            factors: Dict of factor -> weight

        Returns:
            Re-ranked list
        """
        if factors is None:
            factors = {
                'score': 0.50,      # Strategy score
                'volume': 0.25,     # Volume importance
                'price': 0.25,      # Price action
            }

        # Normalize factors
        max_score = max(c.score for c in candidates) if candidates else 1
        max_volume = max(c.volume for c in candidates) if candidates else 1

        for candidate in candidates:
            # Multi-factor score
            multi_score = (
                (candidate.score / max_score) * factors.get('score', 0.5) +
                (candidate.volume / max_volume) * factors.get('volume', 0.25) +
                (1 if candidate.price > 50 else 0.5) * factors.get('price', 0.25)
            )

            candidate.score = multi_score * 100  # Scale back to 0-100

        # Re-sort
        candidates.sort(key=lambda x: x.score, reverse=True)

        return candidates

    def filter_by_criteria(
        self,
        candidates: List[StockCandidate],
        min_score: float = 10.0,
        min_volume: int = 1_000_000,
        max_price: float = 500.0,
    ) -> List[StockCandidate]:
        """
        Filter candidates by criteria.

        Args:
            candidates: List of candidates
            min_score: Minimum score required
            min_volume: Minimum volume
            max_price: Maximum price

        Returns:
            Filtered list
        """
        filtered = [
            c for c in candidates
            if c.score >= min_score
            and c.volume >= min_volume
            and c.price <= max_price
        ]

        logger.info(f"Filtered {len(candidates)} → {len(filtered)} candidates")

        return filtered
