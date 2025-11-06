"""
Detailed $10,000 backtest showing exact gains, losses, and trade counts.
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


def generate_2024_data(num_bars: int = 5000) -> pd.DataFrame:
    """Generate realistic 2024 market data."""
    np.random.seed(2024)

    prices = []
    volumes = []
    timestamps = []

    current_price = 185.0
    current_time = datetime(2024, 1, 2, 9, 30)

    regimes = [
        {'bars': 1200, 'drift': 0.0001, 'volatility': 0.010},
        {'bars': 1200, 'drift': 0.0008, 'volatility': 0.008},
        {'bars': 1200, 'drift': -0.0003, 'volatility': 0.012},
        {'bars': 1400, 'drift': 0.0010, 'volatility': 0.009},
    ]

    for regime in regimes:
        for _ in range(regime['bars']):
            if np.random.random() < 0.01:
                current_volatility = regime['volatility'] * np.random.uniform(1.5, 3.0)
            else:
                current_volatility = regime['volatility']

            change = regime['drift'] + np.random.normal(0, current_volatility)
            current_price = current_price * (1 + change)

            intrabar_vol = current_volatility * 0.5
            high = current_price * (1 + abs(np.random.normal(0, intrabar_vol)))
            low = current_price * (1 - abs(np.random.normal(0, intrabar_vol)))
            open_price = current_price * (1 + np.random.normal(0, intrabar_vol * 0.3))
            close = current_price

            high = max(high, open_price, close)
            low = min(low, open_price, close)

            base_volume = 1500000
            volume_multiplier = 1.0
            if current_volatility > regime['volatility'] * 1.2:
                volume_multiplier = np.random.uniform(2.0, 4.0)

            volume = int(base_volume * np.random.uniform(0.7, 1.3) * volume_multiplier)

            prices.append({'open': open_price, 'high': high, 'low': low, 'close': close})
            volumes.append(volume)
            timestamps.append(current_time)

            current_time += timedelta(minutes=5)
            if current_time.hour >= 16:
                current_time = current_time.replace(hour=9, minute=30)
                current_time += timedelta(days=1)
                while current_time.weekday() >= 5:
                    current_time += timedelta(days=1)

    df = pd.DataFrame(prices)
    df['volume'] = volumes
    df['timestamp'] = timestamps
    return df


def simulate_momentum(df: pd.DataFrame, capital: float) -> List[Trade]:
    """Simulate momentum strategy."""
    trade_manager = TradeManager(initial_capital=capital, risk_per_trade=0.01)

    df['returns'] = df['close'].pct_change() * 100
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    for i in range(20, len(df) - 60):
        row = df.iloc[i]
        if pd.isna(row['volume_ratio']):
            continue

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
                symbol='AAPL', direction=direction, entry_time=row['timestamp'],
                entry_price=entry_price, stop_loss=stop_loss, target=target,
                strategy_name='momentum',
            )

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


def simulate_strategy(strategy_name: str, setups: List[Dict], df: pd.DataFrame, capital: float) -> List[Trade]:
    """Simulate generic strategy."""
    trade_manager = TradeManager(initial_capital=capital, risk_per_trade=0.01)

    for setup in setups:
        if not trade_manager.can_open_trade(3):
            continue

        direction = TradeDirection.LONG if setup['direction'] == 'LONG' else TradeDirection.SHORT
        entry_time = setup['timestamp']
        entry_price = setup['entry_price']
        target = setup.get('target', entry_price * 1.02 if direction == TradeDirection.LONG else entry_price * 0.98)
        stop_loss = setup.get('stop_loss', entry_price * 0.99 if direction == TradeDirection.LONG else entry_price * 1.01)

        trade = trade_manager.open_trade(
            symbol='AAPL', direction=direction, entry_time=entry_time,
            entry_price=entry_price, stop_loss=stop_loss, target=target,
            strategy_name=strategy_name, setup_data=setup,
        )

        entry_idx = df[df['timestamp'] == entry_time].index
        if len(entry_idx) == 0:
            continue

        entry_idx = entry_idx[0]
        end_idx = min(entry_idx + 60, len(df))

        for i in range(entry_idx + 1, end_idx):
            row = df.iloc[i]
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
            last_row = df.iloc[end_idx - 1]
            trade.close(last_row['timestamp'], last_row['close'], 'time_stop')
            trade_manager.close_trade(trade)

    return trade_manager.closed_trades


def run_detailed_backtest():
    """Run detailed backtest with $10,000."""

    STARTING_CAPITAL = 10000.0

    print("="*90)
    print(" "*25 + "2024 BACKTEST - $10,000 STARTING CAPITAL")
    print("="*90)
    print()

    # Generate data
    df = generate_2024_data(5000)
    print(f"✓ Generated {len(df)} bars of 2024 market data")
    print(f"  Price: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f}")
    print()

    results = []

    # Momentum
    print("Running Momentum...")
    momentum_trades = simulate_momentum(df, STARTING_CAPITAL)
    if momentum_trades:
        total_pnl = sum(t.pnl for t in momentum_trades)
        largest_win = max([t.pnl for t in momentum_trades if t.pnl > 0], default=0)
        largest_loss = min([t.pnl for t in momentum_trades if t.pnl < 0], default=0)
        results.append({
            'strategy': 'Momentum',
            'trades': len(momentum_trades),
            'total_gain': total_pnl,
            'final_capital': STARTING_CAPITAL + total_pnl,
            'return_pct': (total_pnl / STARTING_CAPITAL) * 100,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'win_rate': len([t for t in momentum_trades if t.pnl > 0]) / len(momentum_trades) * 100,
        })

    # Mean Reversion
    print("Running Mean Reversion...")
    mr_detector = MeanReversionDetector()
    mr_setups = mr_detector.detect_setups(df)
    if mr_setups:
        mr_trades = simulate_strategy('mean_reversion', mr_setups, df, STARTING_CAPITAL)
        if mr_trades:
            total_pnl = sum(t.pnl for t in mr_trades)
            largest_win = max([t.pnl for t in mr_trades if t.pnl > 0], default=0)
            largest_loss = min([t.pnl for t in mr_trades if t.pnl < 0], default=0)
            results.append({
                'strategy': 'Mean Reversion',
                'trades': len(mr_trades),
                'total_gain': total_pnl,
                'final_capital': STARTING_CAPITAL + total_pnl,
                'return_pct': (total_pnl / STARTING_CAPITAL) * 100,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'win_rate': len([t for t in mr_trades if t.pnl > 0]) / len(mr_trades) * 100,
            })

    # Volatility Breakout
    print("Running Volatility Breakout...")
    vb_detector = VolatilityBreakoutDetector()
    vb_setups = vb_detector.detect_setups(df)
    if vb_setups:
        vb_trades = simulate_strategy('volatility_breakout', vb_setups, df, STARTING_CAPITAL)
        if vb_trades:
            total_pnl = sum(t.pnl for t in vb_trades)
            largest_win = max([t.pnl for t in vb_trades if t.pnl > 0], default=0)
            largest_loss = min([t.pnl for t in vb_trades if t.pnl < 0], default=0)
            results.append({
                'strategy': 'Volatility Breakout',
                'trades': len(vb_trades),
                'total_gain': total_pnl,
                'final_capital': STARTING_CAPITAL + total_pnl,
                'return_pct': (total_pnl / STARTING_CAPITAL) * 100,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'win_rate': len([t for t in vb_trades if t.pnl > 0]) / len(vb_trades) * 100,
            })

    # Multi-Timeframe
    print("Running Multi-Timeframe...")
    mtf_analyzer = MultiTimeframeAnalyzer()
    mtf_setups = mtf_analyzer.detect_setups(df)
    if mtf_setups:
        mtf_trades = simulate_strategy('multi_timeframe', mtf_setups, df, STARTING_CAPITAL)
        if mtf_trades:
            total_pnl = sum(t.pnl for t in mtf_trades)
            largest_win = max([t.pnl for t in mtf_trades if t.pnl > 0], default=0)
            largest_loss = min([t.pnl for t in mtf_trades if t.pnl < 0], default=0)
            results.append({
                'strategy': 'Multi-Timeframe',
                'trades': len(mtf_trades),
                'total_gain': total_pnl,
                'final_capital': STARTING_CAPITAL + total_pnl,
                'return_pct': (total_pnl / STARTING_CAPITAL) * 100,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'win_rate': len([t for t in mtf_trades if t.pnl > 0]) / len(mtf_trades) * 100,
            })

    # Smart Money
    print("Running Smart Money...")
    sm_detector = SmartMoneyDetector()
    sm_setups = sm_detector.detect_setups(df)
    if sm_setups:
        sm_trades = simulate_strategy('smart_money', sm_setups, df, STARTING_CAPITAL)
        if sm_trades:
            total_pnl = sum(t.pnl for t in sm_trades)
            largest_win = max([t.pnl for t in sm_trades if t.pnl > 0], default=0)
            largest_loss = min([t.pnl for t in sm_trades if t.pnl < 0], default=0)
            results.append({
                'strategy': 'Smart Money',
                'trades': len(sm_trades),
                'total_gain': total_pnl,
                'final_capital': STARTING_CAPITAL + total_pnl,
                'return_pct': (total_pnl / STARTING_CAPITAL) * 100,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'win_rate': len([t for t in sm_trades if t.pnl > 0]) / len(sm_trades) * 100,
            })

    print()
    print("="*90)
    print(" "*30 + "DETAILED RESULTS TABLE")
    print("="*90)
    print()

    # Print table
    print("┌" + "─"*88 + "┐")
    print("│" + " "*30 + "Starting Capital: $10,000" + " "*32 + "│")
    print("├" + "─"*18 + "┬" + "─"*13 + "┬" + "─"*13 + "┬" + "─"*13 + "┬" + "─"*13 + "┬" + "─"*13 + "┤")
    print(f"│ {'Strategy':<16} │ {'Total Gain':<11} │ {'Final $':<11} │ {'Biggest Win':<11} │ {'Biggest Loss':<11} │ {'# Trades':<11} │")
    print("├" + "─"*18 + "┼" + "─"*13 + "┼" + "─"*13 + "┼" + "─"*13 + "┼" + "─"*13 + "┼" + "─"*13 + "┤")

    for r in results:
        print(
            f"│ {r['strategy']:<16} │ "
            f"${r['total_gain']:>10,.0f} │ "
            f"${r['final_capital']:>10,.0f} │ "
            f"${r['largest_win']:>10,.0f} │ "
            f"${r['largest_loss']:>10,.0f} │ "
            f"{r['trades']:>11} │"
        )

    print("└" + "─"*18 + "┴" + "─"*13 + "┴" + "─"*13 + "┴" + "─"*13 + "┴" + "─"*13 + "┴" + "─"*13 + "┘")
    print()

    # Additional info
    print("ADDITIONAL METRICS:")
    print("─" * 90)
    for r in results:
        print(f"\n{r['strategy']}:")
        print(f"  Return: {r['return_pct']:.2f}%")
        print(f"  Win Rate: {r['win_rate']:.1f}%")
        print(f"  Average per trade: ${r['total_gain']/r['trades']:.2f}")

    print()
    print("="*90)

    # Best strategy
    if results:
        best = max(results, key=lambda x: x['total_gain'])
        print(f"\n🏆 BEST PERFORMER: {best['strategy']}")
        print(f"   Turned $10,000 into ${best['final_capital']:,.0f} ({best['return_pct']:.1f}% gain)")
        print(f"   Total profit: ${best['total_gain']:,.0f}")
        print()


if __name__ == "__main__":
    run_detailed_backtest()
