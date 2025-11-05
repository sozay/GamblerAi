"""
Backtesting framework for strategy simulation.
"""

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.backtesting.trade import Trade, TradeManager
from gambler_ai.backtesting.performance import PerformanceMetrics

__all__ = [
    "BacktestEngine",
    "Trade",
    "TradeManager",
    "PerformanceMetrics",
]
