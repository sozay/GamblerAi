#!/usr/bin/env python3
"""
Stock Scanner Strategy Comparison - 2019-2020 COVID Period
Tests all 8 stock selection strategies with Adaptive trading strategy

This simulation tests:
1. TOP_MOVERS - Select stocks with highest price moves
2. HIGH_VOLUME - Select stocks with unusually high volume
3. VOLATILITY_RANGE - Select stocks in optimal volatility range (15-35%)
4. RELATIVE_STRENGTH - Select stocks outperforming SPY
5. GAP_SCANNER - Select stocks with significant gaps
6. BEST_SETUPS - Select stocks with best risk/reward setups
7. SECTOR_LEADERS - Select sector leaders
8. MARKET_CAP_WEIGHTED - Prefer larger, more liquid stocks

Each scanner:
- Scans universe of stocks
- Selects top 3-5 stocks
- Trades ONLY using Adaptive strategy
- Re-scans every 20 trading days
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
from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType
from gambler_ai.analysis.stock_universe import StockUniverse


def generate_2019_2020_stock_data(
    symbols: List[str],
    include_covid_crash: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Generate simulated stock data for 2019-2020 including COVID crash.

    Simulates realistic market behavior:
    - Bull market: Jun 2019 - Feb 2020
    - COVID crash: Mar 2020 (-93% decline)
    - Recovery: Apr 2020 - Jun 2020
    """
    print(f"Generating {len(symbols)} stocks for 2019-2020 period...")

    # Stock characteristics
    stock_characteristics = {
        # Tech stocks - high beta, correlated, strong recovery
        "AAPL": {'beta': 1.2, 'volatility': 0.25, 'base': 150, 'covid_sensitivity': -0.5, 'recovery': 1.8},
        "MSFT": {'beta': 1.1, 'volatility': 0.22, 'base': 300, 'covid_sensitivity': -0.3, 'recovery': 1.6},
        "GOOGL": {'beta': 1.3, 'volatility': 0.26, 'base': 130, 'covid_sensitivity': -0.6, 'recovery': 1.5},
        "NVDA": {'beta': 1.8, 'volatility': 0.40, 'base': 200, 'covid_sensitivity': -0.7, 'recovery': 2.5},
        "AMD": {'beta': 1.7, 'volatility': 0.38, 'base': 50, 'covid_sensitivity': -0.8, 'recovery': 2.2},

        # TSLA - very high volatility, extreme moves
        "TSLA": {'beta': 2.0, 'volatility': 0.55, 'base': 80, 'covid_sensitivity': -1.0, 'recovery': 3.0},

        # Finance - hit hard by COVID, slow recovery
        "JPM": {'beta': 1.3, 'volatility': 0.28, 'base': 120, 'covid_sensitivity': -1.2, 'recovery': 0.8},
        "BAC": {'beta': 1.4, 'volatility': 0.32, 'base': 30, 'covid_sensitivity': -1.3, 'recovery': 0.7},
        "GS": {'beta': 1.5, 'volatility': 0.35, 'base': 200, 'covid_sensitivity': -1.4, 'recovery': 0.9},

        # Defensive - less affected by COVID
        "WMT": {'beta': 0.7, 'volatility': 0.15, 'base': 110, 'covid_sensitivity': -0.1, 'recovery': 1.1},
        "PG": {'beta': 0.6, 'volatility': 0.12, 'base': 120, 'covid_sensitivity': 0.0, 'recovery': 1.0},
        "JNJ": {'beta': 0.6, 'volatility': 0.12, 'base': 140, 'covid_sensitivity': -0.2, 'recovery': 1.2},

        # Healthcare - benefited from COVID
        "MRNA": {'beta': 2.5, 'volatility': 0.60, 'base': 20, 'covid_sensitivity': 0.5, 'recovery': 5.0},
        "PFE": {'beta': 0.8, 'volatility': 0.18, 'base': 35, 'covid_sensitivity': 0.3, 'recovery': 2.0},

        # SPY - market benchmark
        "SPY": {'beta': 1.0, 'volatility': 0.18, 'base': 290, 'covid_sensitivity': -0.8, 'recovery': 1.3},
    }

    all_stock_data = {}

    # Time periods
    bars_per_day = 20  # 5-minute bars

    # Jun 2019 - Feb 2020: 9 months bull market
    bull_days = 9 * 21  # 189 trading days

    # Mar 2020: 1 month crash
    crash_days = 21

    # Apr - Jun 2020: 3 months recovery
    recovery_days = 3 * 21  # 63 trading days

    total_days = bull_days + crash_days + recovery_days
    total_bars = total_days * bars_per_day

    # Generate timestamps
    start_date = datetime(2019, 6, 3, 9, 30)
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
        char = stock_characteristics.get(symbol, {
            'beta': 1.0, 'volatility': 0.20, 'base': 100,
            'covid_sensitivity': -0.8, 'recovery': 1.3
        })

        beta = char['beta']
        vol = char['volatility'] / np.sqrt(252 * bars_per_day)
        base_price = char['base']
        covid_sensitivity = char['covid_sensitivity']
        recovery_factor = char['recovery']

        # Generate returns for each period
        returns = []

        # Phase 1: Bull market (Jun 2019 - Feb 2020)
        bull_drift = 0.12 / 252 / bars_per_day * beta  # 12% annual
        for i in range(bull_days * bars_per_day):
            r = np.random.normal(bull_drift, vol)
            returns.append(r)

        # Phase 2: COVID crash (Mar 2020)
        crash_drift = -0.30 / 21 / bars_per_day * covid_sensitivity  # Adjusted by sensitivity
        crash_vol = vol * 3  # 3x volatility during crash
        for i in range(crash_days * bars_per_day):
            r = np.random.normal(crash_drift, crash_vol)
            returns.append(r)

        # Phase 3: Recovery (Apr - Jun 2020)
        recovery_drift = 0.40 / 63 / bars_per_day * recovery_factor
        recovery_vol = vol * 1.5
        for i in range(recovery_days * bars_per_day):
            r = np.random.normal(recovery_drift, recovery_vol)
            returns.append(r)

        # Generate price series
        price = base_price * np.exp(np.cumsum(returns))

        # Create OHLC
        high = price * (1 + np.abs(np.random.normal(0, vol/2, total_bars)))
        low = price * (1 - np.abs(np.random.normal(0, vol/2, total_bars)))
        open_price = np.roll(price, 1)
        open_price[0] = base_price

        # Generate volume (higher during crash)
        base_volume = 5_000_000 if symbol == "SPY" else 2_000_000
        volume = np.ones(total_bars) * base_volume

        # Increase volume during crash
        crash_start = bull_days * bars_per_day
        crash_end = crash_start + (crash_days * bars_per_day)
        volume[crash_start:crash_end] *= 3.0

        # Add volume spikes on large moves
        for i in range(1, total_bars):
            move = abs(price[i] - price[i-1]) / price[i-1]
            if move > 0.02:  # 2% move
                volume[i] *= (1 + move * 20)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume,
        })

        all_stock_data[symbol] = df

        # Print stock summary
        total_return = (price[-1] - price[0]) / price[0] * 100
        crash_return = (price[crash_end-1] - price[crash_start]) / price[crash_start] * 100
        print(f"  {symbol:6s}: ${price[0]:6.2f} -> ${price[-1]:6.2f} ({total_return:+6.1f}%) | Crash: {crash_return:+6.1f}%")

    return all_stock_data


def run_scanner_backtest(
    scanner_type: ScannerType,
    stock_data: Dict[str, pd.DataFrame],
    scan_frequency_days: int = 20,
    max_stocks: int = 3,
    initial_capital: float = 100000,
) -> Dict:
    """
    Run backtest using a specific scanner + adaptive strategy.
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
    strategy_usage = defaultdict(int)

    # Get total date range
    sample_df = list(stock_data.values())[0]
    total_bars = len(sample_df)
    bars_per_day = 20
    scan_frequency_bars = scan_frequency_days * bars_per_day

    # Simulate scanning at intervals
    current_bar = 200  # Start after enough data for indicators

    scan_count = 0

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

        scan_count += 1

        # Record scan
        scan_timestamp = sample_df['timestamp'].iloc[current_bar]
        scan_history.append({
            'timestamp': scan_timestamp,
            'stocks_selected': [r.symbol for r in scan_results],
            'scores': [r.score for r in scan_results],
            'regimes': [r.regime for r in scan_results],
        })

        # Allocate capital equally across selected stocks
        capital_per_stock = capital / len(scan_results)

        # Run adaptive strategy on each selected stock until next scan
        next_scan_bar = min(current_bar + scan_frequency_bars, total_bars)

        period_pnl = 0

        for result in scan_results:
            symbol = result.symbol
            stock_df = stock_data[symbol].iloc[current_bar:next_scan_bar].copy()

            if len(stock_df) < 10:
                continue

            # Use adaptive strategy selector
            strategy_name, strategy = adaptive_selector.select_strategy(stock_df)
            strategy_usage[strategy_name] += 1

            # Run backtest on this stock for this period
            engine = BacktestEngine(
                initial_capital=capital_per_stock,
                risk_per_trade=0.01,
                max_concurrent_trades=2,
            )

            # Run backtest
            trades = engine.run_backtest(stock_df, strategy)

            # Update capital
            final_capital = engine.trade_manager.current_capital
            period_pnl += (final_capital - capital_per_stock)

            # Record trades
            for trade in trades:
                trade.symbol = symbol
                trade.strategy_name = strategy_name
                all_trades.append(trade)

        # Update total capital
        capital += period_pnl

        # Record equity
        equity_curve.append({
            'timestamp': scan_timestamp,
            'equity': capital,
            'bar': current_bar,
        })

        # Move to next scan
        current_bar = next_scan_bar

    # Calculate metrics
    total_return = (capital - initial_capital) / initial_capital

    # Calculate by period
    bull_end_bar = 189 * bars_per_day
    crash_end_bar = bull_end_bar + (21 * bars_per_day)

    bull_equity = [e for e in equity_curve if e['bar'] <= bull_end_bar]
    crash_equity = [e for e in equity_curve if bull_end_bar < e['bar'] <= crash_end_bar]
    recovery_equity = [e for e in equity_curve if e['bar'] > crash_end_bar]

    bull_return = ((bull_equity[-1]['equity'] - initial_capital) / initial_capital) if bull_equity else 0

    crash_start_capital = bull_equity[-1]['equity'] if bull_equity else initial_capital
    crash_return = ((crash_equity[-1]['equity'] - crash_start_capital) / crash_start_capital) if crash_equity else 0

    recovery_start_capital = crash_equity[-1]['equity'] if crash_equity else crash_start_capital
    recovery_return = ((capital - recovery_start_capital) / recovery_start_capital) if recovery_equity else 0

    return {
        'scanner_type': scanner_type.value,
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_return': total_return,
        'bull_return': bull_return,
        'crash_return': crash_return,
        'recovery_return': recovery_return,
        'trades': all_trades,
        'scan_history': scan_history,
        'equity_curve': equity_curve,
        'total_scans': len(scan_history),
        'strategy_usage': dict(strategy_usage),
    }


def compare_scanner_strategies():
    """
    Compare all scanner strategies during 2019-2020 COVID period.
    """
    print("=" * 120)
    print("STOCK SCANNER STRATEGY COMPARISON - 2019-2020 COVID PERIOD")
    print("All scanners use ADAPTIVE STRATEGY for trading")
    print("=" * 120)
    print()

    # Define stock universe
    symbols = [
        "SPY",      # Benchmark
        "AAPL", "MSFT", "GOOGL", "NVDA", "AMD",  # Tech
        "TSLA",     # High volatility
        "JPM", "BAC", "GS",  # Finance (hard hit by COVID)
        "WMT", "PG", "JNJ",  # Defensive
        "MRNA", "PFE",  # Healthcare (benefited from COVID)
    ]

    # Generate data
    stock_data = generate_2019_2020_stock_data(symbols)

    # Calculate market (SPY) performance
    spy_data = stock_data['SPY']
    spy_total_return = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[0]) / spy_data['close'].iloc[0]

    # Calculate SPY by period
    bull_end = 189 * 20
    crash_end = bull_end + (21 * 20)

    spy_bull = (spy_data['close'].iloc[bull_end] - spy_data['close'].iloc[0]) / spy_data['close'].iloc[0]
    spy_crash = (spy_data['close'].iloc[crash_end] - spy_data['close'].iloc[bull_end]) / spy_data['close'].iloc[bull_end]
    spy_recovery = (spy_data['close'].iloc[-1] - spy_data['close'].iloc[crash_end]) / spy_data['close'].iloc[crash_end]

    print(f"\n📊 Market (SPY) Performance:")
    print(f"   Bull Market (Jun 2019 - Feb 2020): {spy_bull:+.1%}")
    print(f"   COVID Crash (Mar 2020):             {spy_crash:+.1%}")
    print(f"   Recovery (Apr - Jun 2020):          {spy_recovery:+.1%}")
    print(f"   TOTAL:                              {spy_total_return:+.1%}")
    print()

    # Test each scanner strategy
    scanner_types = [
        ScannerType.TOP_MOVERS,
        ScannerType.HIGH_VOLUME,
        ScannerType.VOLATILITY_RANGE,
        ScannerType.RELATIVE_STRENGTH,
        ScannerType.GAP_SCANNER,
        ScannerType.BEST_SETUPS,
        ScannerType.SECTOR_LEADERS,
        ScannerType.MARKET_CAP_WEIGHTED,
    ]

    results = {}

    print("Running scanner simulations...")
    for scanner_type in scanner_types:
        print(f"  Testing {scanner_type.value}...")
        result = run_scanner_backtest(
            scanner_type=scanner_type,
            stock_data=stock_data,
            scan_frequency_days=20,  # Re-scan every 20 days
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

    print(f"{'Scanner':<25}{'Total Return':<15}{'Bull':<12}{'Crash':<12}{'Recovery':<12}{'Trades':<10}{'Scans':<10}")
    print("-" * 120)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['total_return'], reverse=True)

    for i, (strategy_name, result) in enumerate(sorted_results, 1):
        rank_emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))

        print(
            f"{rank_emoji} {strategy_name:<23}{result['total_return']:>+12.2%}  "
            f"{result['bull_return']:>+9.1%}  {result['crash_return']:>+9.1%}  "
            f"{result['recovery_return']:>+9.1%}  {len(result['trades']):<10}"
            f"{result['total_scans']:<10}"
        )

    print("-" * 120)
    print(f"Benchmark (SPY):          {spy_total_return:>+12.2%}  {spy_bull:>+9.1%}  {spy_crash:>+9.1%}  {spy_recovery:>+9.1%}")
    print()

    # Show best scanner details
    best_strategy = sorted_results[0]
    best_scanner_name = best_strategy[0]
    best_result = best_strategy[1]

    print(f"=" * 120)
    print(f"BEST SCANNER: {best_scanner_name.upper()}")
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

    # Show strategy usage
    print(f"Adaptive Strategy Usage (Best Scanner):")
    print(f"{'Strategy':<30}{'Times Used':<20}{'Percentage':<20}")
    print("-" * 70)

    strategy_usage = best_result['strategy_usage']
    total_trades = sum(strategy_usage.values())

    for strategy, count in sorted(strategy_usage.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_trades * 100 if total_trades > 0 else 0
        print(f"{strategy:<30}{count:<20}{pct:>6.1f}%")

    print()

    # Key insights
    print(f"=" * 120)
    print("KEY INSIGHTS")
    print(f"=" * 120)
    print()

    winner = sorted_results[0]
    winner_name = winner[0]
    winner_result = winner[1]

    print(f"1. 🏆 Best Scanner: {winner_name}")
    print(f"   Total Return: {winner_result['total_return']:+.2%}")
    print(f"   Outperformance vs SPY: {(winner_result['total_return'] - spy_total_return):+.2%}")
    print()

    print(f"2. COVID Crash Performance:")
    crash_survivors = [(name, r) for name, r in results.items() if r['crash_return'] > 0]
    print(f"   Scanners with positive returns during crash: {len(crash_survivors)}/{len(results)}")
    if crash_survivors:
        best_crash = max(crash_survivors, key=lambda x: x[1]['crash_return'])
        print(f"   Best crash performer: {best_crash[0]} ({best_crash[1]['crash_return']:+.1%})")
    print()

    print(f"3. Recovery Performance:")
    best_recovery = max(results.items(), key=lambda x: x[1]['recovery_return'])
    print(f"   Best recovery: {best_recovery[0]} ({best_recovery[1]['recovery_return']:+.1%})")
    print()

    print(f"4. Most stocks selected overall:")
    all_selections = defaultdict(int)
    for result in results.values():
        for scan in result['scan_history']:
            for symbol in scan['stocks_selected']:
                all_selections[symbol] += 1

    top_selected = sorted(all_selections.items(), key=lambda x: x[1], reverse=True)[:5]
    for symbol, count in top_selected:
        total_possible = sum([r['total_scans'] for r in results.values()])
        pct = count / total_possible * 100
        print(f"   {symbol}: Selected {count} times ({pct:.1f}% of all scans)")
    print()

    print(f"5. Scanners beating SPY: {sum(1 for r in results.values() if r['total_return'] > spy_total_return)}/{len(results)}")
    print()

    print("=" * 120)
    print()

    return results


if __name__ == "__main__":
    compare_scanner_strategies()

    print("\n✅ Stock scanner strategy comparison complete!")
    print()
