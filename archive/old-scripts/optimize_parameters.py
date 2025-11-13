"""
Optimize trading parameters for maximum returns
Tests different configurations to find the best settings for 1h data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from datetime import datetime
import json

print("="*80)
print("PARAMETER OPTIMIZATION FOR 1H DATA (2024-11-08 to 2025-11-07)")
print("="*80)
print()

# Load all available data
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD', 'NFLX', 'SPY']
data = {}

print("Loading data for all symbols...")
for symbol in symbols:
    file = Path(f'market_data_cache/{symbol}_1h_20241108_20251107.parquet')
    if file.exists():
        df = pd.read_parquet(file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        data[symbol] = df.sort_values('timestamp').reset_index(drop=True)
        print(f"  {symbol}: {len(df)} bars")

print(f"\nTotal symbols loaded: {len(data)}")
print()

# Test configurations
configs = [
    {
        'name': 'Current (Conservative)',
        'mean_reversion_z': -1.5,
        'momentum_return': 0.002,
        'momentum_volume': 1.1,
        'volatility_atr': 2.0,
        'hold_period': 8,
        'stop_loss': None,
        'take_profit': None,
    },
    {
        'name': 'Aggressive Entry',
        'mean_reversion_z': -1.2,
        'momentum_return': 0.0015,
        'momentum_volume': 1.05,
        'volatility_atr': 1.8,
        'hold_period': 8,
        'stop_loss': None,
        'take_profit': None,
    },
    {
        'name': 'With Stop Loss & Take Profit',
        'mean_reversion_z': -1.5,
        'momentum_return': 0.002,
        'momentum_volume': 1.1,
        'volatility_atr': 2.0,
        'hold_period': 15,
        'stop_loss': -0.02,  # -2%
        'take_profit': 0.03,  # +3%
    },
    {
        'name': 'Aggressive + Risk Management',
        'mean_reversion_z': -1.2,
        'momentum_return': 0.0015,
        'momentum_volume': 1.05,
        'volatility_atr': 1.8,
        'hold_period': 15,
        'stop_loss': -0.015,  # -1.5%
        'take_profit': 0.025,  # +2.5%
    },
    {
        'name': 'Very Aggressive',
        'mean_reversion_z': -1.0,
        'momentum_return': 0.001,
        'momentum_volume': 1.03,
        'volatility_atr': 1.5,
        'hold_period': 12,
        'stop_loss': -0.02,
        'take_profit': 0.04,
    },
    {
        'name': 'Longer Hold + Tight Stops',
        'mean_reversion_z': -1.5,
        'momentum_return': 0.002,
        'momentum_volume': 1.1,
        'volatility_atr': 2.0,
        'hold_period': 20,
        'stop_loss': -0.01,  # -1%
        'take_profit': 0.02,  # +2%
    },
]

def backtest_mean_reversion(df, config, position_size=10000):
    """Test mean reversion strategy"""
    df = df.copy()
    df['ma'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['z_score'] = (df['close'] - df['ma']) / df['std']

    trades = []
    for i in range(20, len(df) - config['hold_period'], 6):
        if df['z_score'].iloc[i] < config['mean_reversion_z']:
            entry_price = df['close'].iloc[i]

            # Simulate holding period with stop loss / take profit
            best_exit_price = entry_price
            exit_bar = i + config['hold_period']

            if config['stop_loss'] or config['take_profit']:
                for j in range(i+1, min(i + config['hold_period'] + 1, len(df))):
                    current_price = df['close'].iloc[j]
                    pnl_pct = (current_price - entry_price) / entry_price

                    # Check stop loss
                    if config['stop_loss'] and pnl_pct <= config['stop_loss']:
                        best_exit_price = current_price
                        exit_bar = j
                        break

                    # Check take profit
                    if config['take_profit'] and pnl_pct >= config['take_profit']:
                        best_exit_price = current_price
                        exit_bar = j
                        break

                    best_exit_price = current_price
                    exit_bar = j
            else:
                best_exit_price = df['close'].iloc[min(i + config['hold_period'], len(df)-1)]

            pnl = (best_exit_price - entry_price) / entry_price
            trades.append({
                'pnl_pct': pnl,
                'pnl_dollars': pnl * position_size
            })

    return trades

def backtest_momentum(df, config, position_size=10000):
    """Test momentum strategy"""
    df = df.copy()
    df['returns'] = df['close'].pct_change()
    df['ma_short'] = df['close'].rolling(window=5).mean()
    df['ma_long'] = df['close'].rolling(window=20).mean()
    df['volume_ma'] = df['volume'].rolling(window=20).mean()

    trades = []
    for i in range(20, len(df) - config['hold_period'], 6):
        if (df['ma_short'].iloc[i] > df['ma_long'].iloc[i] and
            df['returns'].iloc[i] > config['momentum_return'] and
            df['volume'].iloc[i] > df['volume_ma'].iloc[i] * config['momentum_volume']):

            entry_price = df['close'].iloc[i]

            # Simulate holding with risk management
            best_exit_price = entry_price

            if config['stop_loss'] or config['take_profit']:
                for j in range(i+1, min(i + config['hold_period'] + 1, len(df))):
                    current_price = df['close'].iloc[j]
                    pnl_pct = (current_price - entry_price) / entry_price

                    if config['stop_loss'] and pnl_pct <= config['stop_loss']:
                        best_exit_price = current_price
                        break

                    if config['take_profit'] and pnl_pct >= config['take_profit']:
                        best_exit_price = current_price
                        break

                    best_exit_price = current_price
            else:
                best_exit_price = df['close'].iloc[min(i + config['hold_period'], len(df)-1)]

            pnl = (best_exit_price - entry_price) / entry_price
            trades.append({
                'pnl_pct': pnl,
                'pnl_dollars': pnl * position_size
            })

    return trades

# Test each configuration
results = []

for config in configs:
    print(f"\nTesting: {config['name']}")
    print("-" * 60)

    all_mr_trades = []
    all_mom_trades = []

    for symbol, df in data.items():
        mr_trades = backtest_mean_reversion(df, config)
        mom_trades = backtest_momentum(df, config)
        all_mr_trades.extend(mr_trades)
        all_mom_trades.extend(mom_trades)

    # Calculate statistics
    mr_pnl = sum(t['pnl_dollars'] for t in all_mr_trades)
    mr_count = len(all_mr_trades)
    mr_win_rate = sum(1 for t in all_mr_trades if t['pnl_dollars'] > 0) / mr_count * 100 if mr_count > 0 else 0

    mom_pnl = sum(t['pnl_dollars'] for t in all_mom_trades)
    mom_count = len(all_mom_trades)
    mom_win_rate = sum(1 for t in all_mom_trades if t['pnl_dollars'] > 0) / mom_count * 100 if mom_count > 0 else 0

    total_pnl = mr_pnl + mom_pnl
    total_return = total_pnl / 100000 * 100  # % return on $100k

    print(f"  Mean Reversion: {mr_count} trades, {mr_win_rate:.1f}% win, ${mr_pnl:,.2f}")
    print(f"  Momentum: {mom_count} trades, {mom_win_rate:.1f}% win, ${mom_pnl:,.2f}")
    print(f"  TOTAL: ${total_pnl:,.2f} ({total_return:+.2f}% return)")

    results.append({
        'config': config,
        'mr_trades': mr_count,
        'mr_pnl': mr_pnl,
        'mr_win_rate': mr_win_rate,
        'mom_trades': mom_count,
        'mom_pnl': mom_pnl,
        'mom_win_rate': mom_win_rate,
        'total_pnl': total_pnl,
        'total_return': total_return
    })

# Show best configuration
print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80)

results.sort(key=lambda x: x['total_pnl'], reverse=True)

print("\nBest configurations by total P&L:")
for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['config']['name']}")
    print(f"   Total P&L: ${result['total_pnl']:,.2f} ({result['total_return']:+.2f}% return)")
    print(f"   Mean Reversion: {result['mr_trades']} trades, {result['mr_win_rate']:.1f}% win")
    print(f"   Momentum: {result['mom_trades']} trades, {result['mom_win_rate']:.1f}% win")

# Save best config
best = results[0]
print("\n" + "="*80)
print("RECOMMENDED CONFIGURATION")
print("="*80)
print(json.dumps(best['config'], indent=2))

# Save to file
with open('optimized_config.json', 'w') as f:
    json.dump(best['config'], f, indent=2)

print("\nSaved to: optimized_config.json")
