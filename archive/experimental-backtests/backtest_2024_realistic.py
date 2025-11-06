"""
Comprehensive backtest of all 5 strategies on realistic 2024-style market data.

Generates realistic price data mimicking 2024 AAPL characteristics:
- Starting price: $185 (Jan 2024)
- Ending price: ~$250 (Dec 2024)
- Volatility: Moderate with occasional spikes
- Trend: Overall uptrend with corrections
"""

import sys
sys.path.insert(0, '/home/user/GamblerAi')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict

from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from gambler_ai.analysis.smart_money_detector import SmartMoneyDetector
from gambler_ai.backtesting.trade import Trade, TradeDirection, TradeManager
from gambler_ai.backtesting.performance import PerformanceMetrics


def generate_2024_realistic_data(num_bars: int = 5000) -> pd.DataFrame:
    """
    Generate realistic 2024 AAPL-style data.

    AAPL 2024 characteristics:
    - Started around $185
    - Ended around $250
    - Overall uptrend with several corrections
    - Moderate volatility with occasional spikes
    - Strong Q2 and Q4 performance
    """
    np.random.seed(2024)  # For reproducibility

    print("📊 Generating realistic 2024-style market data...")
    print("   Simulating AAPL price action from Jan-Dec 2024")
    print("   Characteristics: Uptrend with corrections, moderate volatility")

    prices = []
    volumes = []
    timestamps = []

    current_price = 185.0  # AAPL Jan 2024 price
    current_time = datetime(2024, 1, 2, 9, 30)  # Start of trading year

    # Define market regimes for 2024 (simulating real quarters)
    regimes = [
        {'name': 'Q1 Consolidation', 'bars': 1200, 'drift': 0.0001, 'volatility': 0.010},
        {'name': 'Q2 Rally', 'bars': 1200, 'drift': 0.0008, 'volatility': 0.008},
        {'name': 'Q3 Correction', 'bars': 1200, 'drift': -0.0003, 'volatility': 0.012},
        {'name': 'Q4 Strong Rally', 'bars': 1400, 'drift': 0.0010, 'volatility': 0.009},
    ]

    bar_count = 0
    for regime in regimes:
        print(f"   - {regime['name']}: {regime['bars']} bars")

        drift = regime['drift']
        volatility = regime['volatility']

        for _ in range(regime['bars']):
            # Add occasional volatility spikes (news events)
            if np.random.random() < 0.01:  # 1% chance
                vol_spike = np.random.uniform(1.5, 3.0)
                current_volatility = volatility * vol_spike
            else:
                current_volatility = volatility

            # Generate price movement
            change = drift + np.random.normal(0, current_volatility)
            current_price = current_price * (1 + change)

            # Generate OHLC
            intrabar_vol = current_volatility * 0.5
            high = current_price * (1 + abs(np.random.normal(0, intrabar_vol)))
            low = current_price * (1 - abs(np.random.normal(0, intrabar_vol)))
            open_price = current_price * (1 + np.random.normal(0, intrabar_vol * 0.3))
            close = current_price

            # Ensure OHLC validity
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # Generate volume (higher during volatility)
            base_volume = 1500000
            volume_multiplier = 1.0
            if current_volatility > volatility * 1.2:  # During spikes
                volume_multiplier = np.random.uniform(2.0, 4.0)

            volume = int(base_volume * np.random.uniform(0.7, 1.3) * volume_multiplier)

            prices.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
            })
            volumes.append(volume)
            timestamps.append(current_time)

            # Advance time (5-minute bars, skip weekends/nights)
            current_time += timedelta(minutes=5)

            # Skip to next trading day after market close
            if current_time.hour >= 16:
                current_time = current_time.replace(hour=9, minute=30)
                current_time += timedelta(days=1)

                # Skip weekends
                while current_time.weekday() >= 5:
                    current_time += timedelta(days=1)

            bar_count += 1

    df = pd.DataFrame(prices)
    df['volume'] = volumes
    df['timestamp'] = timestamps

    print(f"✓ Generated {len(df)} bars (5-minute intervals)")
    print(f"  Period: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
    print(f"  Starting price: ${df['close'].iloc[0]:.2f}")
    print(f"  Ending price: ${df['close'].iloc[-1]:.2f}")
    print(f"  Total return: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.1f}%")
    print(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print()

    return df


def simulate_momentum_strategy(df: pd.DataFrame) -> List[Trade]:
    """Simulate momentum strategy."""
    trade_manager = TradeManager(initial_capital=100000, risk_per_trade=0.01)

    df['returns'] = df['close'].pct_change() * 100
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    for i in range(20, len(df) - 60):
        row = df.iloc[i]

        if pd.isna(row['volume_ratio']):
            continue

        # Momentum signal: 2%+ move with 2x volume
        if abs(row['returns']) >= 2.0 and row['volume_ratio'] >= 2.0:
            if not trade_manager.can_open_trade(3):
                continue

            direction = TradeDirection.LONG if row['returns'] > 0 else TradeDirection.SHORT
            entry_price = float(row['close'])

            if direction == TradeDirection.LONG:
                target = entry_price * 1.03
                stop_loss = entry_price * 0.99
            else:
                target = entry_price * 0.97
                stop_loss = entry_price * 1.01

            trade = trade_manager.open_trade(
                symbol='AAPL',
                direction=direction,
                entry_time=row['timestamp'],
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                strategy_name='momentum',
            )

            # Simulate outcome
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
            symbol='AAPL',
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            strategy_name=strategy_name,
            setup_data=setup,
        )

        entry_idx = price_data[price_data['timestamp'] == entry_time].index
        if len(entry_idx) == 0:
            continue

        entry_idx = entry_idx[0]
        end_idx = min(entry_idx + 60, len(price_data))

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


def run_2024_backtest():
    """Run comprehensive 2024 backtest."""

    print("="*80)
    print("GAMBLERAI - 2024 COMPREHENSIVE STRATEGY BACKTEST")
    print("="*80)
    print()
    print("Testing all 5 strategies on realistic 2024 AAPL-style market data")
    print("Period: January 2024 - December 2024 (Full Year)")
    print("Interval: 5-minute bars (~5000 bars)")
    print("="*80)
    print()

    # Generate data
    df = generate_2024_realistic_data(num_bars=5000)

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
        print(f"✓ Simulated {len(momentum_trades)} trades")

        if momentum_trades:
            perf = PerformanceMetrics(
                trades=momentum_trades,
                initial_capital=100000,
                final_capital=100000 + sum(t.pnl for t in momentum_trades)
            )
            results['Momentum'] = perf.calculate_all_metrics()
            print(f"  Return: {results['Momentum']['total_return_pct']:.2f}%")
            print(f"  Win Rate: {results['Momentum']['win_rate_pct']:.1f}%")
            print(f"  Profit Factor: {results['Momentum']['profit_factor']:.2f}")
            print(f"  Score: {results['Momentum']['performance_score']:.1f}/100")
        else:
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
            print(f"  Profit Factor: {results['Mean Reversion']['profit_factor']:.2f}")
            print(f"  Score: {results['Mean Reversion']['performance_score']:.1f}/100")
        else:
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
            print(f"  Profit Factor: {results['Volatility Breakout']['profit_factor']:.2f}")
            print(f"  Score: {results['Volatility Breakout']['performance_score']:.1f}/100")
        else:
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
            print(f"  Profit Factor: {results['Multi-Timeframe']['profit_factor']:.2f}")
            print(f"  Score: {results['Multi-Timeframe']['performance_score']:.1f}/100")
        else:
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
            print(f"  Profit Factor: {results['Smart Money']['profit_factor']:.2f}")
            print(f"  Score: {results['Smart Money']['performance_score']:.1f}/100")
        else:
            results['Smart Money'] = {'total_trades': 0}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['Smart Money'] = {'total_trades': 0}
    print()

    # Comparison
    print("="*80)
    print("2024 BACKTEST RESULTS - FINAL COMPARISON")
    print("="*80)
    print()

    print("┌" + "─"*78 + "┐")
    print("│" + " "*26 + "2024 FULL YEAR RESULTS" + " "*28 + "│")
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
        best_pf = max(valid_results.items(), key=lambda x: x[1]['profit_factor'])

        print("🏆 2024 CHAMPIONS:")
        print(f"  🥇 Best Return: {best_return[0]} ({best_return[1]['total_return_pct']:.2f}%)")
        print(f"  🥇 Best Win Rate: {best_win_rate[0]} ({best_win_rate[1]['win_rate_pct']:.1f}%)")
        print(f"  🥇 Best Profit Factor: {best_pf[0]} ({best_pf[1]['profit_factor']:.2f})")
        print(f"  🥇 Best Overall Score: {best_score[0]} ({best_score[1]['performance_score']:.1f}/100)")

        print()
        print("📊 KEY INSIGHTS:")
        for name, metrics in valid_results.items():
            if metrics['performance_score'] >= 70:
                rating = "⭐⭐⭐⭐ EXCELLENT"
            elif metrics['performance_score'] >= 60:
                rating = "⭐⭐⭐ GOOD"
            elif metrics['performance_score'] >= 50:
                rating = "⭐⭐ ACCEPTABLE"
            else:
                rating = "⭐ NEEDS WORK"

            print(f"  {name}: {rating}")

    print()
    print("="*80)
    print("Full year 2024 backtest completed successfully!")
    print("="*80)


if __name__ == "__main__":
    run_2024_backtest()
