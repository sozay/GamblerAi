#!/usr/bin/env python3
"""
Stock Scanner Strategy Comparison - Multi-Year Testing
Tests all stock selection strategies across multiple years with different market conditions
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

from gambler_ai.backtesting.backtest_engine import BacktestEngine
from gambler_ai.analysis.adaptive_strategy import AdaptiveStrategySelector
from gambler_ai.analysis.regime_detector import RegimeDetector
from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType


def generate_year_stock_data(year: int, symbols: List[str], market_type: str = "bull") -> Dict[str, pd.DataFrame]:
    """
    Generate stock data for a specific year with market characteristics.

    Args:
        year: Year to simulate
        symbols: List of stock symbols
        market_type: "bull", "bear", "choppy", or "crash"
    """
    print(f"\nGenerating {len(symbols)} stocks for {year} ({market_type} market)...")

    stock_chars = {
        "SPY": {'beta': 1.0, 'volatility': 0.18, 'base': 400, 'sector': 'market'},
        "AAPL": {'beta': 1.2, 'volatility': 0.25, 'base': 150, 'sector': 'tech'},
        "MSFT": {'beta': 1.1, 'volatility': 0.22, 'base': 300, 'sector': 'tech'},
        "GOOGL": {'beta': 1.3, 'volatility': 0.26, 'base': 130, 'sector': 'tech'},
        "NVDA": {'beta': 1.8, 'volatility': 0.40, 'base': 200, 'sector': 'tech'},
        "TSLA": {'beta': 2.0, 'volatility': 0.55, 'base': 200, 'sector': 'auto'},
        "JPM": {'beta': 1.3, 'volatility': 0.28, 'base': 140, 'sector': 'finance'},
        "WMT": {'beta': 0.7, 'volatility': 0.15, 'base': 140, 'sector': 'retail'},
        "MRNA": {'beta': 2.5, 'volatility': 0.60, 'base': 150, 'sector': 'pharma'},
        "AMD": {'beta': 1.7, 'volatility': 0.38, 'base': 80, 'sector': 'tech'},
    }

    # Market characteristics by type
    if market_type == "bull":
        drift = 0.20 / 252  # 20% annual
        vol_multiplier = 1.0
    elif market_type == "bear":
        drift = -0.30 / 252  # -30% annual
        vol_multiplier = 2.0
    elif market_type == "choppy":
        drift = 0.05 / 252  # 5% annual
        vol_multiplier = 1.8
    elif market_type == "crash":
        drift = -0.40 / 252  # -40% annual
        vol_multiplier = 3.0
    else:
        drift = 0.10 / 252
        vol_multiplier = 1.0

    bars_per_day = 20
    trading_days = 252
    total_bars = trading_days * bars_per_day

    # Generate timestamps
    start_date = datetime(year, 1, 3, 9, 30)
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

    all_stock_data = {}

    for symbol in symbols:
        char = stock_chars.get(symbol, {'beta': 1.0, 'volatility': 0.20, 'base': 100, 'sector': 'other'})

        beta = char['beta']
        vol = char['volatility'] / np.sqrt(252 * bars_per_day) * vol_multiplier
        base_price = char['base']

        # Generate returns
        stock_drift = drift * beta
        returns = np.random.normal(stock_drift, vol, total_bars)

        # Add trends and reversals
        for i in range(0, total_bars, 500):
            trend_length = min(250, total_bars - i)
            if np.random.random() > 0.5:
                returns[i:i+trend_length] += np.random.uniform(0.0001, 0.0003)

        # Generate prices
        price = base_price * np.exp(np.cumsum(returns))

        # OHLC
        high = price * (1 + np.abs(np.random.normal(0, vol/2, total_bars)))
        low = price * (1 - np.abs(np.random.normal(0, vol/2, total_bars)))
        open_price = np.roll(price, 1)
        open_price[0] = base_price

        # Volume with spikes
        base_volume = 2_000_000
        volume = base_volume * (1 + np.abs(returns) * 50)

        # Add volume spikes on large moves
        for i in range(1, total_bars):
            if abs(returns[i]) > vol * 2:
                volume[i] *= 3.0

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume,
        })

        all_stock_data[symbol] = df

        total_return = (price[-1] - price[0]) / price[0] * 100
        print(f"  {symbol:6s}: ${price[0]:7.2f} -> ${price[-1]:7.2f} ({total_return:+7.1f}%)")

    return all_stock_data


def run_scanner_backtest_fast(
    scanner_type: ScannerType,
    stock_data: Dict[str, pd.DataFrame],
    initial_capital: float = 100000,
) -> Dict:
    """Fast backtest for scanner comparison."""
    scanner = StockScanner(scanner_type=scanner_type, max_stocks=3)
    adaptive_selector = AdaptiveStrategySelector(
        regime_detector=RegimeDetector(),
        use_volatility_filter=True,
    )

    benchmark_data = stock_data.get('SPY')
    capital = initial_capital
    all_trades = []
    scan_history = []

    sample_df = list(stock_data.values())[0]
    total_bars = len(sample_df)
    scan_frequency_bars = 20 * 20  # Every 20 days

    current_bar = 200

    while current_bar < total_bars:
        current_stock_data = {symbol: df.iloc[:current_bar].copy() for symbol, df in stock_data.items()}

        scan_results = scanner.scan_stocks(
            stock_data=current_stock_data,
            adaptive_selector=adaptive_selector,
            benchmark_data=benchmark_data.iloc[:current_bar] if benchmark_data is not None else None,
        )

        if not scan_results:
            current_bar += scan_frequency_bars
            continue

        scan_history.append({
            'stocks': [r.symbol for r in scan_results],
            'scores': [r.score for r in scan_results],
        })

        capital_per_stock = capital / len(scan_results)
        next_scan_bar = min(current_bar + scan_frequency_bars, total_bars)

        for result in scan_results:
            symbol = result.symbol
            stock_df = stock_data[symbol].iloc[current_bar:next_scan_bar].copy()

            if len(stock_df) < 10:
                continue

            strategy_name, strategy = adaptive_selector.select_strategy(stock_df)

            engine = BacktestEngine(
                initial_capital=capital_per_stock,
                risk_per_trade=0.01,
                max_concurrent_trades=2,
            )

            trades = engine.run_backtest(stock_df, strategy)
            final_capital = engine.trade_manager.current_capital
            capital += (final_capital - capital_per_stock)

            for trade in trades:
                trade.symbol = symbol
                all_trades.append(trade)

        current_bar = next_scan_bar

    total_return = (capital - initial_capital) / initial_capital

    return {
        'scanner': scanner_type.value,
        'initial': initial_capital,
        'final': capital,
        'return': total_return,
        'trades': len(all_trades),
        'scans': len(scan_history),
    }


def test_year(year: int, market_type: str):
    """Test all scanners for a specific year."""
    print(f"\n{'='*120}")
    print(f"TESTING {year} - {market_type.upper()} MARKET")
    print(f"{'='*120}")

    symbols = ["SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "JPM", "WMT", "MRNA", "AMD"]
    stock_data = generate_year_stock_data(year, symbols, market_type)

    spy_return = (stock_data['SPY']['close'].iloc[-1] - stock_data['SPY']['close'].iloc[0]) / stock_data['SPY']['close'].iloc[0]
    print(f"\n📊 Market (SPY): {spy_return:+.1%}")

    scanner_types = [
        ScannerType.VOLATILITY_RANGE,
        ScannerType.HIGH_VOLUME,
        ScannerType.TOP_MOVERS,
        ScannerType.BEST_SETUPS,
        ScannerType.RELATIVE_STRENGTH,
        ScannerType.SECTOR_LEADERS,
        ScannerType.MARKET_CAP_WEIGHTED,
    ]

    print(f"\nRunning {len(scanner_types)} scanner tests...")
    results = {}

    for scanner_type in scanner_types:
        result = run_scanner_backtest_fast(scanner_type, stock_data)
        results[scanner_type.value] = result
        print(f"  ✓ {scanner_type.value:25s}: {result['return']:>+8.1%} ({result['trades']:4d} trades)")

    print(f"\n{'='*120}")
    print(f"RESULTS - {year}")
    print(f"{'='*120}\n")

    print(f"{'Scanner':<25}{'Return':<12}{'Final $':<15}{'Trades':<10}{'vs SPY':<12}")
    print("-" * 120)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['return'], reverse=True)

    for i, (name, r) in enumerate(sorted_results, 1):
        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        vs_spy = r['return'] - spy_return

        print(f"{emoji} {name:<23}{r['return']:>+10.1%}  ${r['final']:>12,.0f}  {r['trades']:<10}{vs_spy:>+10.1%}")

    print("-" * 120)
    print(f"SPY Benchmark:          {spy_return:>+10.1%}")
    print()

    beats_spy = sum(1 for r in results.values() if r['return'] > spy_return)
    print(f"Scanners beating SPY: {beats_spy}/{len(results)}")
    print()

    return {
        'year': year,
        'market_type': market_type,
        'spy_return': spy_return,
        'results': results,
        'best': sorted_results[0] if sorted_results else None,
    }


def compare_multi_year():
    """Compare scanner performance across multiple years."""
    print("="*120)
    print("MULTI-YEAR STOCK SCANNER TESTING")
    print("Testing stock selection + adaptive strategy across different market conditions")
    print("="*120)

    # Test different market types
    tests = [
        (2021, "bull"),      # Bull market
        (2022, "bear"),      # Bear market
        (2023, "choppy"),    # Choppy/range market
        (2024, "bull"),      # Bull market
    ]

    all_results = []

    for year, market_type in tests:
        result = test_year(year, market_type)
        all_results.append(result)

    # Summary across all years
    print("\n" + "="*120)
    print("MULTI-YEAR SUMMARY")
    print("="*120)
    print()

    # Calculate average performance per scanner
    scanner_totals = defaultdict(lambda: {'returns': [], 'trades': []})

    for year_result in all_results:
        for scanner_name, scanner_result in year_result['results'].items():
            scanner_totals[scanner_name]['returns'].append(scanner_result['return'])
            scanner_totals[scanner_name]['trades'].append(scanner_result['trades'])

    print(f"{'Scanner':<25}{'Avg Return':<15}{'Best Year':<15}{'Worst Year':<15}{'Avg Trades':<12}")
    print("-" * 120)

    scanner_avgs = []
    for scanner_name, data in scanner_totals.items():
        avg_return = np.mean(data['returns'])
        best_return = max(data['returns'])
        worst_return = min(data['returns'])
        avg_trades = np.mean(data['trades'])

        scanner_avgs.append((scanner_name, avg_return, best_return, worst_return, avg_trades))

    scanner_avgs.sort(key=lambda x: x[1], reverse=True)

    for i, (name, avg, best, worst, trades) in enumerate(scanner_avgs, 1):
        emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"{emoji} {name:<23}{avg:>+13.1%}  {best:>+13.1%}  {worst:>+13.1%}  {trades:>10.0f}")

    print()

    # Best scanner by market type
    print("\nBest Scanner by Market Type:")
    print("-" * 80)
    for year_result in all_results:
        if year_result['best']:
            best_name, best_data = year_result['best']
            print(f"  {year_result['year']} ({year_result['market_type']:8s}): {best_name:25s} {best_data['return']:>+8.1%}")

    print()
    print("="*120)
    print()

    return all_results


if __name__ == "__main__":
    results = compare_multi_year()
    print("✅ Multi-year stock scanner testing complete!")
