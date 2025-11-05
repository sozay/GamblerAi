"""
Adaptive Strategy Selector

Automatically selects the best strategy based on detected market regime.
"""

from typing import Dict, List, Optional
import pandas as pd

from gambler_ai.analysis.regime_detector import RegimeDetector, MarketRegime
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from gambler_ai.analysis.smart_money_detector import SmartMoneyDetector


class AdaptiveStrategySelector:
    """
    Automatically selects and switches strategies based on market regime.

    Strategy Selection:
    - BULL: Multi-Timeframe (best bull performer: +98.7%)
    - BEAR: Mean Reversion (best bear performer: +74.4%)
    - RANGE: Mean Reversion (works well in ranges)
    """

    def __init__(
        self,
        regime_detector: Optional[RegimeDetector] = None,
        use_momentum_always: bool = False,
    ):
        """
        Initialize adaptive strategy selector.

        Args:
            regime_detector: Custom regime detector (uses default if None)
            use_momentum_always: If True, adds Momentum as secondary strategy in all regimes
        """
        self.regime_detector = regime_detector or RegimeDetector()
        self.use_momentum_always = use_momentum_always

        # Initialize all strategies
        self.strategies = {
            'Momentum': MomentumDetector(use_db=False),
            'Mean Reversion': MeanReversionDetector(),
            'Volatility Breakout': VolatilityBreakoutDetector(),
            'Multi-Timeframe': MultiTimeframeAnalyzer(),
            'Smart Money': SmartMoneyDetector(),
        }

        # Strategy selection rules
        self.regime_strategy_map = {
            'BULL': 'Multi-Timeframe',
            'BEAR': 'Mean Reversion',
            'RANGE': 'Mean Reversion',
        }

        # Track current regime and strategy
        self.current_regime = None
        self.current_strategy_name = None
        self.regime_changes = 0

    def select_strategy(self, df: pd.DataFrame) -> tuple[str, object]:
        """
        Select best strategy for current market regime.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (strategy_name, strategy_object)
        """
        # Detect current regime
        regime, confidence = self.regime_detector.detect_regime_with_confidence(df)

        # Track regime changes
        if self.current_regime != regime:
            self.current_regime = regime
            self.regime_changes += 1

        # Select strategy based on regime
        strategy_name = self.regime_strategy_map[regime]
        strategy = self.strategies[strategy_name]

        self.current_strategy_name = strategy_name

        return (strategy_name, strategy)

    def get_strategy_allocation(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Get capital allocation across strategies based on regime.

        Returns:
            Dictionary of {strategy_name: allocation_pct}
        """
        regime, confidence = self.regime_detector.detect_regime_with_confidence(df)

        if regime == 'BULL':
            if confidence > 0.8:
                # High confidence bull - go all-in on Multi-Timeframe
                return {
                    'Multi-Timeframe': 1.0,
                }
            else:
                # Lower confidence - split with Momentum
                return {
                    'Multi-Timeframe': 0.7,
                    'Momentum': 0.3,
                }

        elif regime == 'BEAR':
            if confidence > 0.8:
                # High confidence bear - go all-in on Mean Reversion
                return {
                    'Mean Reversion': 1.0,
                }
            else:
                # Lower confidence - split with Momentum
                return {
                    'Mean Reversion': 0.7,
                    'Momentum': 0.3,
                }

        else:  # RANGE
            # In ranging markets, use Mean Reversion with some Smart Money
            return {
                'Mean Reversion': 0.7,
                'Smart Money': 0.3,
            }

    def detect_setups(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect setups using the selected strategy.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of detected setups from the appropriate strategy
        """
        strategy_name, strategy = self.select_strategy(df)
        setups = strategy.detect_setups(df)

        # Add regime info to each setup
        regime, confidence = self.regime_detector.detect_regime_with_confidence(df)
        for setup in setups:
            setup['regime'] = regime
            setup['regime_confidence'] = confidence
            setup['strategy_used'] = strategy_name

        return setups

    def get_regime_info(self, df: pd.DataFrame) -> Dict:
        """
        Get current regime information.

        Returns:
            Dictionary with regime details
        """
        regime, confidence = self.regime_detector.detect_regime_with_confidence(df)
        strategy_name, _ = self.select_strategy(df)
        allocation = self.get_strategy_allocation(df)

        return {
            'regime': regime,
            'confidence': confidence,
            'selected_strategy': strategy_name,
            'allocation': allocation,
            'regime_changes': self.regime_changes,
        }

    def print_status(self, df: pd.DataFrame):
        """Print current strategy selection status."""
        info = self.get_regime_info(df)

        print(f"\n{'='*70}")
        print(f"ADAPTIVE STRATEGY STATUS")
        print(f"{'='*70}")
        print(f"Market Regime:        {info['regime']} ({info['confidence']:.1%} confidence)")
        print(f"Selected Strategy:    {info['selected_strategy']}")
        print(f"Regime Changes:       {info['regime_changes']}")
        print(f"\nCapital Allocation:")
        for strategy, pct in info['allocation'].items():
            print(f"  {strategy:<20} {pct:.1%}")
        print(f"{'='*70}\n")


class AdaptivePortfolio:
    """
    Portfolio that adapts strategy selection over time based on regime changes.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        rebalance_frequency: str = 'daily',
    ):
        """
        Initialize adaptive portfolio.

        Args:
            initial_capital: Starting capital
            rebalance_frequency: How often to check and rebalance ('daily', 'weekly')
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.rebalance_frequency = rebalance_frequency

        self.selector = AdaptiveStrategySelector()
        self.regime_history = []
        self.strategy_history = []

    def update(self, df: pd.DataFrame):
        """
        Update portfolio based on current market conditions.

        Args:
            df: DataFrame with current market data
        """
        info = self.selector.get_regime_info(df)

        self.regime_history.append({
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df else None,
            'regime': info['regime'],
            'confidence': info['confidence'],
            'strategy': info['selected_strategy'],
        })

    def get_performance_by_regime(self) -> Dict:
        """
        Analyze performance attribution by regime.

        Returns:
            Dictionary with performance stats by regime
        """
        if not self.regime_history:
            return {}

        regime_stats = {}

        for entry in self.regime_history:
            regime = entry['regime']

            if regime not in regime_stats:
                regime_stats[regime] = {
                    'count': 0,
                    'strategies_used': [],
                }

            regime_stats[regime]['count'] += 1
            regime_stats[regime]['strategies_used'].append(entry['strategy'])

        return regime_stats


def create_adaptive_strategy() -> AdaptiveStrategySelector:
    """
    Factory function to create a configured adaptive strategy selector.

    Returns:
        Configured AdaptiveStrategySelector
    """
    return AdaptiveStrategySelector()
