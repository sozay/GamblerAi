#!/usr/bin/env python3
"""
Multi-Stock Scanner Backtest

Compares different stock scanning strategies over multiple years.

Tests:
1. Top Movers - Select stocks with highest % moves
2. High Volume - Select stocks with unusually high volume
3. Volatility Range - Select stocks in optimal volatility range
4. Best Setups - Select stocks with best risk/reward setups
5. Market Cap Weighted - Prefer larger, more liquid stocks
6. Relative Strength - Select stocks outperforming market

Each scanner selects top 3-5 stocks, then runs adaptive strategy on those stocks.
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType, create_scanner
from gambler_ai.analysis.stock_universe import StockUniverse


def generate_multi_stock_data(
    symbols: List[str],
    start_year: int,
    end_year: int,
    bars_per_day: int = 20,
) -> Dict[str, pd.DataFrame]:
    """
    Generate simulated market data for multiple stocks.

    Simulates:
    - Different stocks with different characteristics
    - Correlation with market (some follow SPY, some diverge)
    - Varying volatility levels
    - Sector rotations

    Args:
        symbols: List of stock symbols
        start_year: Start year
        end_year: End year
        bars_per_day: Bars per trading day

    Returns:
        Dictionary of {symbol: DataFrame}
    """
    print(f"Generating {len(symbols)} stocks from {start_year} to {end_year}...")

    # Define stock characteristics
    stock_characteristics = {
        # Tech stocks - high beta, correlated
        "AAPL": {'beta': 1.2, 'volatility': 0.25, 'base': 150, 'sector_strength': 1.3},
        "MSFT": {'beta': 1.1, 'volatility': 0.22, 'base': 300, 'sector_strength': 1.3},
        "GOOGL": {'beta': 1.3, 'volatility': 0.26, 'base': 130, 'sector_strength': 1.3},
        "NVDA": {'beta': 1.8, 'volatility': 0.40, 'base': 400, 'sector_strength': 1.5},
        "AMD": {'beta': 1.7, 'volatility': 0.38, 'base': 100, 'sector_strength': 1.4},

        # TSLA - very high volatility
        "TSLA": {'beta': 2.0, 'volatility': 0.55, 'base': 200, 'sector_strength': 1.2},

        # Finance - moderate beta
        "JPM": {'beta': 1.1, 'volatility': 0.20, 'base': 140, 'sector_strength': 1.0},
        "BAC": {'beta': 1.2, 'volatility': 0.24, 'base': 30, 'sector_strength': 1.0},

        # Defensive - low beta
        "WMT": {'beta': 0.7, 'volatility': 0.15, 'base': 140, 'sector_strength': 0.8},
        "JNJ": {'beta': 0.6, 'volatility': 0.12, 'base': 160, 'sector_strength': 0.7},

        # SPY - market benchmark
        "SPY": {'beta': 1.0, 'volatility': 0.18, 'base': 400, 'sector_strength': 1.0},
    }

    all_stock_data = {}

    # Generate market factor (SPY-like returns)
    total_years = end_year - start_year + 1
    trading_days = 252 * total_years
    total_bars = trading_days * bars_per_day

    # Market returns (bull market with occasional corrections)
    market_drift = 0.10 / 252 / bars_per_day  # 10% annual return
    market_vol = 0.18 / np.sqrt(252 * bars_per_day)

    market_returns = np.random.normal(market_drift, market_vol, total_bars)

    # Add market regimes (bull/bear cycles)
    for i in range(total_bars):
        year_progress = (i / total_bars) * total_years

        # Simulate bear market every ~3-4 years
        if 1.5 < year_progress < 2.0:  # Year 1.5-2: Bear market
            market_returns[i] -= 0.001  # Extra downward drift
        elif 3.5 < year_progress < 4.0:  # Year 3.5-4: Another correction
            market_returns[i] -= 0.0005

    # Generate timestamps
    start_date = datetime(start_year, 1, 1, 9, 30)
    timestamps = []
    current_time = start_date
    bar_minutes = 390 // bars_per_day

    for i in range(total_bars):
        timestamps.append(current_time)
        current_time += timedelta(minutes=bar_minutes)

        if current_time.hour >= 16:
            current_time = current_time.replace(hour=9, minute=30)
            current_time += timedelta(days=1)
            while current_time.weekday() >= 5:
                current_time += timedelta(days=1)

    # Generate each stock
    for symbol in symbols:
        char = stock_characteristics.get(symbol, {'beta': 1.0, 'volatility': 0.20, 'base': 100, 'sector_strength': 1.0})

        beta = char['beta']
        vol = char['volatility'] / np.sqrt(252 * bars_per_day)
        base_price = char['base']
        sector_strength = char['sector_strength']

        # Stock returns = beta * market + idiosyncratic
        idiosyncratic_vol = vol * 0.5  # Stock-specific volatility
        idiosyncratic_returns = np.random.normal(0, idiosyncratic_vol, total_bars)

        stock_returns = (beta * market_returns * sector_strength) + idiosyncratic_returns

        # Generate price series
        price = base_price * np.exp(np.cumsum(stock_returns))

        # Create OHLC
        high = price * (1 + np.abs(np.random.normal(0, vol/2, total_bars)))
        low = price * (1 - np.abs(np.random.normal(0, vol/2, total_bars)))
        open_price = np.roll(price, 1)
        open_price[0] = base_price

        # Generate volume
        base_volume = 10_000_000 if symbol == "SPY" else 5_000_000
        volume_multiplier = 1 + np.abs(stock_returns) * 50
        volume = base_volume * volume_multiplier

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume,
        })

        all_stock_data[symbol] = df

    return all_stock_data


def run_scanner_backtest(
    scanner_type: ScannerType,
    stock_data: Dict[str, pd.DataFrame],
    scan_frequency_days: int = 5,
    max_stocks: int = 3,
    initial_capital: float = 100000,
) -> Dict:
    """
    Run backtest using a specific scanner strategy.

    Args:
        scanner_type: Scanner strategy to use
        stock_data: Dict of {symbol: DataFrame}
        scan_frequency_days: How often to re-scan stocks (days)
        max_stocks: Maximum stocks to hold at once
        initial_capital: Starting capital

    Returns:
        Dictionary with results
    """
    # Create scanner
    scanner = StockScanner(scanner_type=scanner_type, max_stocks=max_stocks)

    # Create adaptive selector
    regime_detector = RegimeDetector(high_volatility_threshold=0.012)
    adaptive_selector = AdaptiveStrategySelector(
        regime_detector=regime_detector,
        use_volatility_filter=True,
    )

    # Get benchmark (SPY)
    benchmark_data = stock_data.get('SPY')

    # Track performance
    capital = initial_capital
    all_trades = []
    scan_history = []
    equity_curve = []

    # Get total date range
    sample_df = list(stock_data.values())[0]
    total_bars = len(sample_df)
    bars_per_day = 20  # Assuming this
    scan_frequency_bars = scan_frequency_days * bars_per_day

    # Simulate scanning at intervals
    current_bar = 200  # Start after enough data for indicators

    while current_bar < total_bars:
        # Get data up to current point for all stocks
        current_stock_data = {}
        for symbol, df in stock_data.items():
            current_stock_data[symbol] = df.iloc[:current_bar].copy()

        # Scan stocks
        scan_results = scanner.scan_stocks(
            stock_data=current_stock_data,
            adaptive_selector=adaptive_selector,
            benchmark_data=benchmark_data.iloc[:current_bar] if benchmark_data is not None else None,
        )

        if not scan_results:
            current_bar += scan_frequency_bars
            continue

        # Record scan
        scan_timestamp = sample_df['timestamp'].iloc[current_bar]
        scan_history.append({
            'timestamp': scan_timestamp,
            'stocks_selected': [r.symbol for r in scan_results],
            'scores': [r.score for r in scan_results],
        })

        # Allocate capital equally across selected stocks
        capital_per_stock = capital / len(scan_results)

        # Run strategy on each selected stock until next scan
        next_scan_bar = min(current_bar + scan_frequency_bars, total_bars)

        for result in scan_results:
            symbol = result.symbol
            stock_df = stock_data[symbol].iloc[current_bar:next_scan_bar].copy()

            if len(stock_df) < 10:
                continue

            # Run backtest on this stock for this period
            engine = BacktestEngine(
                initial_capital=capital_per_stock,
                risk_per_trade=0.01,
            )

            # Get strategy
            _, strategy = adaptive_selector.select_strategy(stock_df)

            # Run backtest
            trades = engine.run_backtest(stock_df, strategy)

            # Update capital
            final_capital = engine.trade_manager.current_capital
            capital += (final_capital - capital_per_stock)

            # Record trades
            for trade in trades:
                trade.symbol = symbol
                all_trades.append(trade)

        # Record equity
        equity_curve.append({
            'timestamp': scan_timestamp,
            'equity': capital,
        })

        # Move to next scan
        current_bar = next_scan_bar

    # Calculate metrics
    total_return = (capital - initial_capital) / initial_capital

    return {
        'scanner_type': scanner_type.value,
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_return': total_return,
        'trades': all_trades,
        'scan_history': scan_history,
        'equity_curve': equity_curve,
        'total_scans': len(scan_history),
    }


def compare_scanner_strategies(
    start_year: int = 2020,
    end_year: int = 2024,
):
    """
    Compare all scanner strategies over multi-year period.
    """
    print("=" * 120)
    print("MULTI-STOCK SCANNER STRATEGY COMPARISON")
    print(f"Testing Period: {start_year} - {end_year}")
    print("=" * 120)
    print()

    # Define stock universe
    symbols = ["SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "TSLA", "JPM", "BAC", "WMT", "JNJ"]

    # Generate data
    stock_data = generate_multi_stock_data(symbols, start_year, end_year)

    # Calculate market (SPY) performance
    spy_return = (stock_data['SPY']['close'].iloc[-1] - stock_data['SPY']['close'].iloc[0]) / stock_data['SPY']['close'].iloc[0]

    print(f"\nMarket (SPY) Performance: {spy_return:+.1%}")
    print()

    # Test each scanner strategy
    scanner_types = [
        ScannerType.TOP_MOVERS,
        ScannerType.HIGH_VOLUME,
        ScannerType.VOLATILITY_RANGE,
        ScannerType.BEST_SETUPS,
        ScannerType.MARKET_CAP_WEIGHTED,
    ]

    results = {}

    for scanner_type in scanner_types:
        print(f"Testing {scanner_type.value}...")
        result = run_scanner_backtest(
            scanner_type=scanner_type,
            stock_data=stock_data,
            scan_frequency_days=5,
            max_stocks=3,
            initial_capital=100000,
        )
        results[scanner_type.value] = result

    # Display results
    print()
    print("=" * 120)
    print("SCANNER STRATEGY COMPARISON RESULTS")
    print("=" * 120)
    print()

    print(f"{'Strategy':<25}{'Return':<15}{'Final Capital':<20}{'Trades':<12}{'Scans':<12}{'Avg Stocks':<12}")
    print("-" * 120)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['total_return'], reverse=True)

    for strategy_name, result in sorted_results:
        avg_stocks_per_scan = sum(len(s['stocks_selected']) for s in result['scan_history']) / len(result['scan_history']) if result['scan_history'] else 0

        rank_emoji = "🥇" if result == sorted_results[0][1] else ("🥈" if result == sorted_results[1][1] else ("🥉" if result == sorted_results[2][1] else ""))

        print(
            f"{rank_emoji} {strategy_name:<23}{result['total_return']:>+12.2%}  "
            f"${result['final_capital']:>15,.0f}   {len(result['trades']):<12}"
            f"{result['total_scans']:<12}{avg_stocks_per_scan:<12.1f}"
        )

    print("-" * 120)
    print(f"\nBenchmark (SPY Buy & Hold): {spy_return:+.2%}")
    print()

    # Show which stocks were selected most often by best strategy
    best_strategy = sorted_results[0]
    best_scanner_name = best_strategy[0]
    best_result = best_strategy[1]

    print(f"=" * 120)
    print(f"BEST STRATEGY: {best_scanner_name.upper()}")
    print(f"=" * 120)
    print()

    # Count stock selections
    stock_selections = defaultdict(int)
    for scan in best_result['scan_history']:
        for symbol in scan['stocks_selected']:
            stock_selections[symbol] += 1

    print(f"Stock Selection Frequency:")
    print(f"{'Symbol':<12}{'Times Selected':<20}{'Pct of Scans':<20}")
    print("-" * 60)

    sorted_stocks = sorted(stock_selections.items(), key=lambda x: x[1], reverse=True)
    total_scans = best_result['total_scans']

    for symbol, count in sorted_stocks:
        pct = count / total_scans * 100
        print(f"{symbol:<12}{count:<20}{pct:>6.1f}%")

    print()

    # Show equity curve comparison
    print(f"=" * 120)
    print("KEY INSIGHTS")
    print(f"=" * 120)
    print()

    winner = sorted_results[0]
    winner_name = winner[0]
    winner_return = winner[1]['total_return']

    print(f"1. 🏆 Best Scanner: {winner_name}")
    print(f"   Return: {winner_return:+.2%}")
    print(f"   Outperformance vs SPY: {(winner_return - spy_return):+.2%}")
    print()

    print(f"2. Scanner Performance Range:")
    best_return = sorted_results[0][1]['total_return']
    worst_return = sorted_results[-1][1]['total_return']
    print(f"   Best: {best_return:+.2%}")
    print(f"   Worst: {worst_return:+.2%}")
    print(f"   Spread: {(best_return - worst_return):.2%}")
    print()

    print(f"3. Stock Selection Analysis:")
    if stock_selections:
        most_selected = sorted_stocks[0]
        least_selected = sorted_stocks[-1]
        print(f"   Most selected: {most_selected[0]} ({most_selected[1]} times)")
        print(f"   Least selected: {least_selected[0]} ({least_selected[1]} times)")
    print()

    beats_spy = sum(1 for r in results.values() if r['total_return'] > spy_return)
    print(f"4. Strategies beating SPY: {beats_spy}/{len(results)}")
    print()

    print("=" * 120)


if __name__ == "__main__":
    compare_scanner_strategies(start_year=2020, end_year=2024)

    print("\n✅ Multi-stock scanner comparison complete!")
    print()
