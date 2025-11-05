"""
Comprehensive backtest of all 5 strategies on real 2024 market data.

Downloads actual historical data from Yahoo Finance and runs full backtests
for all strategies: Momentum, Mean Reversion, Volatility Breakout,
Multi-Timeframe Confluence, and Smart Money Tracker.
"""

import sys
sys.path.insert(0, '/home/user/GamblerAi')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

# Import strategy detectors
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from gambler_ai.analysis.smart_money_detector import SmartMoneyDetector
from gambler_ai.backtesting.trade import Trade, TradeDirection, TradeManager
from gambler_ai.backtesting.performance import PerformanceMetrics


def download_2024_data(symbol: str, interval: str = '5m') -> pd.DataFrame:
    """
    Download real 2024 market data from Yahoo Finance.

    Args:
        symbol: Stock ticker
        interval: Data interval (1m, 5m, 15m, 1h, 1d)

    Returns:
        DataFrame with OHLCV data
    """
    try:
        import yfinance as yf
    except ImportError:
        print("Installing yfinance...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "yfinance"])
        import yfinance as yf

    print(f"📥 Downloading {symbol} data from 2024...")

    # Yahoo Finance limits for intraday data:
    # 1m: last 7 days, 5m: last 60 days, 15m: last 60 days, 1h: last 730 days

    if interval in ['1m', '5m', '15m']:
        # For intraday, get last 60 days max
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
    else:
        # For hourly/daily, can get full year
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval=interval)

        if df.empty:
            print(f"⚠️  No data available for {symbol}")
            return pd.DataFrame()

        # Rename columns to match our format
        df = df.reset_index()
        df.columns = [col.lower() for col in df.columns]

        # Rename datetime column
        if 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        elif 'date' in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)

        # Keep only OHLCV columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        print(f"✓ Downloaded {len(df)} bars")
        print(f"  Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

        return df

    except Exception as e:
        print(f"❌ Error downloading data: {e}")
        return pd.DataFrame()


def simulate_momentum_strategy(df: pd.DataFrame) -> List[Trade]:
    """Simulate momentum strategy (simplified without database)."""
    trades = []
    trade_manager = TradeManager(initial_capital=100000, risk_per_trade=0.01)

    # Simple momentum detection: look for 2%+ moves with volume
    df['returns'] = df['close'].pct_change() * 100
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    for i in range(20, len(df) - 60):
        row = df.iloc[i]

        # Skip if missing data
        if pd.isna(row['volume_ratio']):
            continue

        # Detect momentum: 2%+ move with 2x volume
        if abs(row['returns']) >= 2.0 and row['volume_ratio'] >= 2.0:

            if not trade_manager.can_open_trade(3):
                continue

            direction = TradeDirection.LONG if row['returns'] > 0 else TradeDirection.SHORT
            entry_price = float(row['close'])

            # Set targets
            if direction == TradeDirection.LONG:
                target = entry_price * 1.03  # 3% target
                stop_loss = entry_price * 0.99  # 1% stop
            else:
                target = entry_price * 0.97
                stop_loss = entry_price * 1.01

            trade = trade_manager.open_trade(
                symbol='TEST',
                direction=direction,
                entry_time=row['timestamp'],
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                strategy_name='momentum',
            )

            # Simulate trade outcome (next 60 bars)
            for j in range(i + 1, min(i + 61, len(df))):
                bar = df.iloc[j]
                trade.update_excursions(bar['close'])

                if direction == TradeDirection.LONG:
                    if bar['low'] <= stop_loss:
                        trade.close(bar['timestamp'], stop_loss, 'stop_loss')
                        trade_manager.close_trade(trade)
                        break
                    elif bar['high'] >= target:
                        trade.close(bar['timestamp'], target, 'target')
                        trade_manager.close_trade(trade)
                        break
                else:
                    if bar['high'] >= stop_loss:
                        trade.close(bar['timestamp'], stop_loss, 'stop_loss')
                        trade_manager.close_trade(trade)
                        break
                    elif bar['low'] <= target:
                        trade.close(bar['timestamp'], target, 'target')
                        trade_manager.close_trade(trade)
                        break

            # Time stop
            if trade.status.value == 'OPEN':
                last_bar = df.iloc[min(i + 60, len(df) - 1)]
                trade.close(last_bar['timestamp'], last_bar['close'], 'time_stop')
                trade_manager.close_trade(trade)

    return trade_manager.closed_trades


def simulate_strategy_trades(
    strategy_name: str,
    setups: List[Dict],
    price_data: pd.DataFrame,
) -> List[Trade]:
    """Simulate trades for a strategy."""
    trade_manager = TradeManager(initial_capital=100000, risk_per_trade=0.01)

    for setup in setups:
        if not trade_manager.can_open_trade(3):
            continue

        direction = TradeDirection.LONG if setup['direction'] == 'LONG' else TradeDirection.SHORT
        entry_time = setup['timestamp']
        entry_price = setup['entry_price']
        target = setup.get('target', entry_price * 1.02 if direction == TradeDirection.LONG else entry_price * 0.98)
        stop_loss = setup.get('stop_loss', entry_price * 0.99 if direction == TradeDirection.LONG else entry_price * 1.01)

        trade = trade_manager.open_trade(
            symbol='TEST',
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            strategy_name=strategy_name,
            setup_data=setup,
        )

        # Find entry index
        entry_idx = price_data[price_data['timestamp'] == entry_time].index
        if len(entry_idx) == 0:
            continue

        entry_idx = entry_idx[0]
        end_idx = min(entry_idx + 60, len(price_data))

        # Simulate
        for i in range(entry_idx + 1, end_idx):
            row = price_data.iloc[i]
            trade.update_excursions(row['close'])

            if direction == TradeDirection.LONG:
                if row['low'] <= stop_loss:
                    trade.close(row['timestamp'], stop_loss, 'stop_loss')
                    trade_manager.close_trade(trade)
                    break
                elif row['high'] >= target:
                    trade.close(row['timestamp'], target, 'target')
                    trade_manager.close_trade(trade)
                    break
            else:
                if row['high'] >= stop_loss:
                    trade.close(row['timestamp'], stop_loss, 'stop_loss')
                    trade_manager.close_trade(trade)
                    break
                elif row['low'] <= target:
                    trade.close(row['timestamp'], target, 'target')
                    trade_manager.close_trade(trade)
                    break

        if trade.status.value == 'OPEN':
            last_row = price_data.iloc[end_idx - 1]
            trade.close(last_row['timestamp'], last_row['close'], 'time_stop')
            trade_manager.close_trade(trade)

    return trade_manager.closed_trades


def run_comprehensive_backtest(symbol: str = 'AAPL', interval: str = '5m'):
    """Run comprehensive backtest on 2024 data."""

    print("="*80)
    print("GAMBLERAI - 2024 COMPREHENSIVE STRATEGY BACKTEST")
    print("="*80)
    print(f"\nSymbol: {symbol}")
    print(f"Interval: {interval}")
    print(f"Period: 2024 (last 60 days for intraday data)")
    print("="*80)
    print()

    # Download data
    df = download_2024_data(symbol, interval)

    if df.empty:
        print("❌ Failed to download data. Exiting.")
        return

    print()
    print("="*80)
    print("RUNNING ALL STRATEGIES")
    print("="*80)
    print()

    results = {}

    # Strategy 1: Momentum
    print("📈 STRATEGY 1: MOMENTUM CONTINUATION")
    print("-" * 80)
    try:
        momentum_trades = simulate_momentum_strategy(df)
        print(f"✓ Detected and simulated {len(momentum_trades)} trades")

        if momentum_trades:
            perf = PerformanceMetrics(
                trades=momentum_trades,
                initial_capital=100000,
                final_capital=100000 + sum(t.pnl for t in momentum_trades)
            )
            results['Momentum'] = perf.calculate_all_metrics()
            print(f"  Return: {results['Momentum']['total_return_pct']:.2f}%")
            print(f"  Win Rate: {results['Momentum']['win_rate_pct']:.1f}%")
            print(f"  Score: {results['Momentum']['performance_score']:.1f}/100")
        else:
            print("  ⚠️  No trades detected")
            results['Momentum'] = {'total_trades': 0}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['Momentum'] = {'total_trades': 0}
    print()

    # Strategy 2: Mean Reversion
    print("📉 STRATEGY 2: MEAN REVERSION")
    print("-" * 80)
    try:
        mr_detector = MeanReversionDetector()
        mr_setups = mr_detector.detect_setups(df)
        print(f"✓ Detected {len(mr_setups)} setups")

        if mr_setups:
            mr_trades = simulate_strategy_trades('mean_reversion', mr_setups, df)
            print(f"✓ Simulated {len(mr_trades)} trades")

            perf = PerformanceMetrics(
                trades=mr_trades,
                initial_capital=100000,
                final_capital=100000 + sum(t.pnl for t in mr_trades)
            )
            results['Mean Reversion'] = perf.calculate_all_metrics()
            print(f"  Return: {results['Mean Reversion']['total_return_pct']:.2f}%")
            print(f"  Win Rate: {results['Mean Reversion']['win_rate_pct']:.1f}%")
            print(f"  Score: {results['Mean Reversion']['performance_score']:.1f}/100")
        else:
            print("  ⚠️  No setups detected")
            results['Mean Reversion'] = {'total_trades': 0}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['Mean Reversion'] = {'total_trades': 0}
    print()

    # Strategy 3: Volatility Breakout
    print("💥 STRATEGY 3: VOLATILITY BREAKOUT")
    print("-" * 80)
    try:
        vb_detector = VolatilityBreakoutDetector()
        vb_setups = vb_detector.detect_setups(df)
        print(f"✓ Detected {len(vb_setups)} setups")

        if vb_setups:
            vb_trades = simulate_strategy_trades('volatility_breakout', vb_setups, df)
            print(f"✓ Simulated {len(vb_trades)} trades")

            perf = PerformanceMetrics(
                trades=vb_trades,
                initial_capital=100000,
                final_capital=100000 + sum(t.pnl for t in vb_trades)
            )
            results['Volatility Breakout'] = perf.calculate_all_metrics()
            print(f"  Return: {results['Volatility Breakout']['total_return_pct']:.2f}%")
            print(f"  Win Rate: {results['Volatility Breakout']['win_rate_pct']:.1f}%")
            print(f"  Score: {results['Volatility Breakout']['performance_score']:.1f}/100")
        else:
            print("  ⚠️  No setups detected")
            results['Volatility Breakout'] = {'total_trades': 0}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['Volatility Breakout'] = {'total_trades': 0}
    print()

    # Strategy 4: Multi-Timeframe
    print("🎯 STRATEGY 4: MULTI-TIMEFRAME CONFLUENCE")
    print("-" * 80)
    try:
        mtf_analyzer = MultiTimeframeAnalyzer()
        mtf_setups = mtf_analyzer.detect_setups(df)
        print(f"✓ Detected {len(mtf_setups)} setups")

        if mtf_setups:
            mtf_trades = simulate_strategy_trades('multi_timeframe', mtf_setups, df)
            print(f"✓ Simulated {len(mtf_trades)} trades")

            perf = PerformanceMetrics(
                trades=mtf_trades,
                initial_capital=100000,
                final_capital=100000 + sum(t.pnl for t in mtf_trades)
            )
            results['Multi-Timeframe'] = perf.calculate_all_metrics()
            print(f"  Return: {results['Multi-Timeframe']['total_return_pct']:.2f}%")
            print(f"  Win Rate: {results['Multi-Timeframe']['win_rate_pct']:.1f}%")
            print(f"  Score: {results['Multi-Timeframe']['performance_score']:.1f}/100")
        else:
            print("  ⚠️  No setups detected")
            results['Multi-Timeframe'] = {'total_trades': 0}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['Multi-Timeframe'] = {'total_trades': 0}
    print()

    # Strategy 5: Smart Money
    print("💰 STRATEGY 5: SMART MONEY TRACKER")
    print("-" * 80)
    try:
        sm_detector = SmartMoneyDetector()
        sm_setups = sm_detector.detect_setups(df)
        print(f"✓ Detected {len(sm_setups)} setups")

        if sm_setups:
            sm_trades = simulate_strategy_trades('smart_money', sm_setups, df)
            print(f"✓ Simulated {len(sm_trades)} trades")

            perf = PerformanceMetrics(
                trades=sm_trades,
                initial_capital=100000,
                final_capital=100000 + sum(t.pnl for t in sm_trades)
            )
            results['Smart Money'] = perf.calculate_all_metrics()
            print(f"  Return: {results['Smart Money']['total_return_pct']:.2f}%")
            print(f"  Win Rate: {results['Smart Money']['win_rate_pct']:.1f}%")
            print(f"  Score: {results['Smart Money']['performance_score']:.1f}/100")
        else:
            print("  ⚠️  No setups detected")
            results['Smart Money'] = {'total_trades': 0}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['Smart Money'] = {'total_trades': 0}
    print()

    # Generate comparison
    print("="*80)
    print("FINAL COMPARISON - 2024 BACKTEST RESULTS")
    print("="*80)
    print()

    # Comparison table
    print("┌" + "─"*78 + "┐")
    print("│" + " "*28 + "2024 BACKTEST RESULTS" + " "*29 + "│")
    print("├" + "─"*20 + "┬" + "─"*11 + "┬" + "─"*11 + "┬" + "─"*13 + "┬" + "─"*12 + "┬" + "─"*7 + "┤")
    print(f"│ {'Strategy':<18} │ {'Return %':>9} │ {'Win Rate':>9} │ {'Profit Fact':>11} │ {'Score/100':>10} │ {'Trades':>5} │")
    print("├" + "─"*20 + "┼" + "─"*11 + "┼" + "─"*11 + "┼" + "─"*13 + "┼" + "─"*12 + "┼" + "─"*7 + "┤")

    for strategy_name, metrics in results.items():
        if metrics.get('total_trades', 0) > 0:
            print(
                f"│ {strategy_name:<18} │ "
                f"{metrics['total_return_pct']:>8.2f}% │ "
                f"{metrics['win_rate_pct']:>8.1f}% │ "
                f"{metrics['profit_factor']:>11.2f} │ "
                f"{metrics['performance_score']:>10.1f} │ "
                f"{metrics['total_trades']:>5} │"
            )
        else:
            print(f"│ {strategy_name:<18} │ {'N/A':>9} │ {'N/A':>9} │ {'N/A':>11} │ {'N/A':>10} │ {'0':>5} │")

    print("└" + "─"*20 + "┴" + "─"*11 + "┴" + "─"*11 + "┴" + "─"*13 + "┴" + "─"*12 + "┴" + "─"*7 + "┘")
    print()

    # Winners
    valid_results = {k: v for k, v in results.items() if v.get('total_trades', 0) > 0}

    if valid_results:
        best_return = max(valid_results.items(), key=lambda x: x[1]['total_return_pct'])
        best_win_rate = max(valid_results.items(), key=lambda x: x[1]['win_rate_pct'])
        best_score = max(valid_results.items(), key=lambda x: x[1]['performance_score'])

        print("🏆 2024 CHAMPIONS:")
        print(f"  🥇 Best Return: {best_return[0]} ({best_return[1]['total_return_pct']:.2f}%)")
        print(f"  🥇 Best Win Rate: {best_win_rate[0]} ({best_win_rate[1]['win_rate_pct']:.1f}%)")
        print(f"  🥇 Best Overall Score: {best_score[0]} ({best_score[1]['performance_score']:.1f}/100)")
    else:
        print("⚠️  No strategies generated profitable trades")

    print()
    print("="*80)
    print(f"Backtest completed on {symbol} {interval} data from 2024")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Backtest all strategies on 2024 data')
    parser.add_argument('--symbol', '-s', default='AAPL', help='Stock symbol (default: AAPL)')
    parser.add_argument('--interval', '-i', default='5m', help='Data interval: 5m, 15m, 1h (default: 5m)')

    args = parser.parse_args()

    run_comprehensive_backtest(args.symbol, args.interval)
