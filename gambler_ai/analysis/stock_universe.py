"""
Stock Universe Definitions

Defines pools of stocks to scan and trade.
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class StockInfo:
    """Information about a stock."""
    symbol: str
    name: str
    sector: str
    market_cap: float  # in billions
    avg_volume: int
    is_liquid: bool = True


class StockUniverse:
    """
    Defines and manages stock universes for scanning.
    """

    # Common liquid stocks for day trading
    LIQUID_STOCKS = [
        # Mega Cap Tech (FAANG+)
        StockInfo("AAPL", "Apple Inc.", "Technology", 3000, 50_000_000),
        StockInfo("MSFT", "Microsoft Corp.", "Technology", 2800, 20_000_000),
        StockInfo("GOOGL", "Alphabet Inc.", "Technology", 1800, 20_000_000),
        StockInfo("AMZN", "Amazon.com Inc.", "Consumer", 1500, 45_000_000),
        StockInfo("META", "Meta Platforms", "Technology", 900, 15_000_000),
        StockInfo("NVDA", "NVIDIA Corp.", "Technology", 1200, 40_000_000),
        StockInfo("TSLA", "Tesla Inc.", "Automotive", 800, 90_000_000),

        # Other Tech
        StockInfo("AMD", "Advanced Micro Devices", "Technology", 200, 50_000_000),
        StockInfo("NFLX", "Netflix Inc.", "Technology", 180, 6_000_000),
        StockInfo("CRM", "Salesforce Inc.", "Technology", 220, 5_000_000),
        StockInfo("ORCL", "Oracle Corp.", "Technology", 280, 8_000_000),
        StockInfo("ADBE", "Adobe Inc.", "Technology", 240, 3_000_000),

        # Finance
        StockInfo("JPM", "JPMorgan Chase", "Finance", 450, 10_000_000),
        StockInfo("BAC", "Bank of America", "Finance", 300, 40_000_000),
        StockInfo("GS", "Goldman Sachs", "Finance", 120, 2_500_000),
        StockInfo("MS", "Morgan Stanley", "Finance", 150, 7_000_000),

        # Consumer
        StockInfo("WMT", "Walmart Inc.", "Retail", 400, 7_000_000),
        StockInfo("HD", "Home Depot", "Retail", 350, 3_000_000),
        StockInfo("NKE", "Nike Inc.", "Consumer", 160, 6_000_000),
        StockInfo("SBUX", "Starbucks Corp.", "Consumer", 110, 7_000_000),

        # Healthcare
        StockInfo("JNJ", "Johnson & Johnson", "Healthcare", 400, 6_000_000),
        StockInfo("UNH", "UnitedHealth Group", "Healthcare", 500, 3_000_000),
        StockInfo("PFE", "Pfizer Inc.", "Healthcare", 160, 30_000_000),

        # Energy
        StockInfo("XOM", "Exxon Mobil", "Energy", 400, 20_000_000),
        StockInfo("CVX", "Chevron Corp.", "Energy", 280, 7_000_000),

        # ETFs (Index tracking)
        StockInfo("SPY", "S&P 500 ETF", "ETF", 400, 80_000_000),
        StockInfo("QQQ", "Nasdaq 100 ETF", "ETF", 200, 40_000_000),
        StockInfo("IWM", "Russell 2000 ETF", "ETF", 60, 30_000_000),
        StockInfo("DIA", "Dow Jones ETF", "ETF", 30, 3_000_000),
    ]

    # High-volatility stocks (popular for day trading)
    HIGH_VOLATILITY_STOCKS = [
        "TSLA", "AMD", "NVDA", "PLTR", "SOFI",
        "RIVN", "LCID", "NIO", "PLUG", "SPCE",
        "AMC", "GME", "BB", "WISH", "CLOV",
    ]

    # Popular meme stocks
    MEME_STOCKS = [
        "GME", "AMC", "BB", "BBBY", "WISH",
        "CLOV", "SPCE", "PLTR", "COIN", "HOOD",
    ]

    @staticmethod
    def get_universe(name: str) -> List[str]:
        """
        Get a stock universe by name.

        Args:
            name: Universe name (liquid, tech, volatile, meme, all)

        Returns:
            List of stock symbols
        """
        if name == "liquid":
            return [s.symbol for s in StockUniverse.LIQUID_STOCKS]

        elif name == "tech":
            return [s.symbol for s in StockUniverse.LIQUID_STOCKS if s.sector == "Technology"]

        elif name == "volatile":
            return StockUniverse.HIGH_VOLATILITY_STOCKS

        elif name == "meme":
            return StockUniverse.MEME_STOCKS

        elif name == "etf":
            return [s.symbol for s in StockUniverse.LIQUID_STOCKS if s.sector == "ETF"]

        elif name == "all":
            return [s.symbol for s in StockUniverse.LIQUID_STOCKS]

        else:
            raise ValueError(f"Unknown universe: {name}")

    @staticmethod
    def get_stock_info(symbol: str) -> StockInfo:
        """Get info for a specific stock."""
        for stock in StockUniverse.LIQUID_STOCKS:
            if stock.symbol == symbol:
                return stock
        return None

    @staticmethod
    def filter_by_sector(sector: str) -> List[str]:
        """Get stocks in a specific sector."""
        return [s.symbol for s in StockUniverse.LIQUID_STOCKS if s.sector == sector]

    @staticmethod
    def filter_by_volume(min_volume: int) -> List[str]:
        """Get stocks with minimum average volume."""
        return [s.symbol for s in StockUniverse.LIQUID_STOCKS if s.avg_volume >= min_volume]

    @staticmethod
    def filter_by_market_cap(min_cap: float, max_cap: float = float('inf')) -> List[str]:
        """Get stocks within market cap range (in billions)."""
        return [
            s.symbol for s in StockUniverse.LIQUID_STOCKS
            if min_cap <= s.market_cap <= max_cap
        ]
