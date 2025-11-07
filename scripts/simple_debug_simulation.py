"""
Simplified debug simulation script - loads cached data directly.
Tests top_movers and high_volume with Volatility Breakout strategy.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import logging

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_cached_data(symbols: List[str], interval: str, start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
    """Load cached market data."""
    logger.info("="*80)
    logger.info("LOADING CACHED DATA")
    logger.info("="*80)

    cache_dir = Path("market_data_cache")
    market_data = {}

    for symbol in symbols:
        pattern = f"{symbol}_{interval}_*.parquet"
        cache_files = list(cache_dir.glob(pattern))

        if not cache_files:
            logger.warning(f"No cached data for {symbol}")
            continue

        # Load parquet file
        for cache_file in cache_files:
            try:
                df = pd.read_parquet(cache_file)

                # Ensure timestamp column
                if 'timestamp' not in df.columns:
                    for col in df.columns:
                        if 'date' in col.lower() or 'time' in col.lower():
                            df['timestamp'] = pd.to_datetime(df[col])
                            break

                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Normalize timezone
                if not pd.api.types.is_datetime64tz_dtype(df['timestamp']):
                    df['timestamp'] = df['timestamp'].dt.tz_localize('America/New_York')
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')

                # Filter to date range
                start_utc = pd.Timestamp(start_date).tz_localize('America/New_York').tz_convert('UTC')
                end_utc = pd.Timestamp(end_date).tz_localize('America/New_York').tz_convert('UTC')

                df = df[(df['timestamp'] >= start_utc) & (df['timestamp'] <= end_utc)]

                if len(df) > 0:
                    market_data[symbol] = df
                    logger.info(f"✓ {symbol}: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")

            except Exception as e:
                logger.error(f"Error loading {cache_file}: {e}")

    logger.info(f"Loaded data for {len(market_data)} symbols")
    return market_data


def calculate_volatility_breakout_signals(data: pd.DataFrame, position_size: float) -> List[Dict]:
    """Calculate Volatility Breakout trading signals."""
    if data is None or len(data) < 20:
        return []

    trades = []

    # Optimized parameters from real_data_simulator.py
    min_bars_between_trades = 6
    max_hold_bars = 15
    stop_loss_pct = 0.02
    take_profit_pct = 0.04

    # Calculate indicators
    data = data.copy()
    data['volatility'] = data['close'].rolling(window=20).std()
    data['high_low_range'] = data['high'] - data['low']
    data['atr'] = data['high_low_range'].rolling(window=14).mean()

    # Generate signals
    for i in range(20, len(data) - max_hold_bars, min_bars_between_trades):
        # Breakout condition: high-low range > 1.5x ATR
        if data['high_low_range'].iloc[i] > data['atr'].iloc[i] * 1.5:
            entry_price = data['close'].iloc[i]
            entry_time = data['timestamp'].iloc[i]

            # Simulate holding with stop loss and take profit
            hold_period = min(12, max_hold_bars)
            best_exit_price = None
            exit_idx = i + hold_period
            exit_time = None

            # Check each bar for stop loss or take profit
            for j in range(i + 1, min(i + hold_period + 1, len(data))):
                current_price = data['close'].iloc[j]
                pnl_pct = (current_price - entry_price) / entry_price

                # Stop loss
                if pnl_pct <= -stop_loss_pct:
                    best_exit_price = current_price
                    exit_idx = j
                    exit_time = data['timestamp'].iloc[j]
                    break

                # Take profit
                if pnl_pct >= take_profit_pct:
                    best_exit_price = current_price
                    exit_idx = j
                    exit_time = data['timestamp'].iloc[j]
                    break

            # If no stop/profit hit, exit at hold period
            if best_exit_price is None:
                exit_idx = min(i + hold_period, len(data) - 1)
                best_exit_price = data['close'].iloc[exit_idx]
                exit_time = data['timestamp'].iloc[exit_idx]

            pnl = (best_exit_price - entry_price) / entry_price
            trades.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': best_exit_price,
                'pnl_pct': pnl,
                'pnl_dollars': pnl * position_size
            })

    return trades


def select_stocks_by_scanner(
    market_data: Dict[str, pd.DataFrame],
    scanner_name: str,
    week_start: datetime,
    week_end: datetime,
    max_stocks: int = 3
) -> List[str]:
    """
    Select top stocks based on scanner type for the week.

    Args:
        market_data: All market data
        scanner_name: Scanner type name
        week_start: Start of week
        week_end: End of week
        max_stocks: Maximum number of stocks to select

    Returns:
        List of selected stock symbols
    """
    stock_scores = []

    for symbol, df in market_data.items():
        # Filter to week
        start_utc = pd.Timestamp(week_start).tz_localize('America/New_York').tz_convert('UTC')
        end_utc = pd.Timestamp(week_end).tz_localize('America/New_York').tz_convert('UTC')
        week_df = df[(df['timestamp'] >= start_utc) & (df['timestamp'] <= end_utc)].copy()

        if len(week_df) < 20:
            continue

        try:
            # Calculate metrics
            price_change = (week_df['close'].iloc[-1] - week_df['close'].iloc[0]) / week_df['close'].iloc[0] * 100

            # Volume ratio
            if len(week_df) >= 40:
                baseline_volume = week_df['volume'].iloc[:len(week_df)//2].mean()
                recent_volume = week_df['volume'].iloc[len(week_df)//2:].max()
            else:
                baseline_volume = week_df['volume'].mean()
                recent_volume = week_df['volume'].max()

            volume_ratio = recent_volume / baseline_volume if baseline_volume > 0 else 1.0

            # Volatility
            volatility = week_df['close'].pct_change().std()

            # Score based on scanner type
            score = 0

            if scanner_name == 'top_movers':
                # Score by absolute price movement and volume
                if abs(price_change) >= 0.5 and volume_ratio >= 1.2:
                    score = abs(price_change) * volume_ratio

            elif scanner_name == 'high_volume':
                # Score by volume ratio
                if volume_ratio >= 1.2:
                    score = volume_ratio * 10

            elif scanner_name == 'best_setups':
                # Score by balanced metrics
                if volatility is not None and 0.10 <= volatility <= 0.50:
                    score = volatility * volume_ratio * (1 + abs(price_change) / 10)

            if score > 0:
                stock_scores.append((symbol, score, price_change, volume_ratio))

        except Exception as e:
            continue

    # Sort by score and select top N
    stock_scores.sort(key=lambda x: x[1], reverse=True)
    selected = [symbol for symbol, _, _, _ in stock_scores[:max_stocks]]

    if selected and stock_scores:
        logger.debug(f"{scanner_name}: Selected {selected} from {len(stock_scores)} candidates")
        for symbol, score, pc, vr in stock_scores[:max_stocks]:
            logger.debug(f"  {symbol}: score={score:.1f}, price_change={pc:+.1f}%, volume_ratio={vr:.1f}x")

    return selected


def simulate_combination(
    market_data: Dict[str, pd.DataFrame],
    scanner_name: str,
    strategy_name: str,
    initial_capital: float,
    start_date: datetime,
    end_date: datetime
) -> Dict:
    """Simulate one scanner + strategy combination."""

    logger.info(f"\n{'='*80}")
    logger.info(f"SIMULATING: {scanner_name} + {strategy_name}")
    logger.info(f"{'='*80}")

    all_trades = []
    position_size = initial_capital * 1.0  # 100% capital deployment

    # Generate weekly periods
    periods = []
    current = start_date
    while current < end_date:
        week_end = min(current + timedelta(days=7), end_date)
        periods.append((current, week_end))
        current = week_end

    # Simulate each week
    for week_num, (week_start, week_end) in enumerate(periods, 1):
        logger.info(f"\nWeek {week_num}: {week_start.date()} to {week_end.date()}")

        week_trades = []

        # Select stocks based on scanner type
        selected_symbols = select_stocks_by_scanner(
            market_data, scanner_name, week_start, week_end, max_stocks=3
        )

        if not selected_symbols:
            logger.info(f"  No stocks selected by {scanner_name}")
            continue

        logger.info(f"  Selected: {', '.join(selected_symbols)}")

        # Process only selected symbols
        for symbol in selected_symbols:
            df = market_data[symbol]

            # Filter to week
            start_utc = pd.Timestamp(week_start).tz_localize('America/New_York').tz_convert('UTC')
            end_utc = pd.Timestamp(week_end).tz_localize('America/New_York').tz_convert('UTC')
            week_df = df[(df['timestamp'] >= start_utc) & (df['timestamp'] <= end_utc)].copy()

            if len(week_df) < 20:
                continue

            # Calculate signals
            if strategy_name == 'Volatility Breakout':
                trades = calculate_volatility_breakout_signals(week_df, position_size)
                week_trades.extend(trades)

        # Week statistics
        week_pnl = sum(t['pnl_dollars'] for t in week_trades)
        wins = sum(1 for t in week_trades if t['pnl_dollars'] > 0)
        win_rate = (wins / len(week_trades) * 100) if week_trades else 0

        logger.info(f"  Trades: {len(week_trades)}")
        logger.info(f"  P&L: ${week_pnl:,.2f}")
        logger.info(f"  Win Rate: {win_rate:.1f}%")

        all_trades.extend(week_trades)

    # Final statistics
    total_pnl = sum(t['pnl_dollars'] for t in all_trades)
    final_capital = initial_capital + total_pnl
    return_pct = (total_pnl / initial_capital) * 100
    total_wins = sum(1 for t in all_trades if t['pnl_dollars'] > 0)
    overall_win_rate = (total_wins / len(all_trades) * 100) if all_trades else 0

    logger.info(f"\n{'='*80}")
    logger.info(f"FINAL RESULTS: {scanner_name} + {strategy_name}")
    logger.info(f"{'='*80}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    logger.info(f"Final Capital:   ${final_capital:,.2f}")
    logger.info(f"Total P&L:       ${total_pnl:,.2f}")
    logger.info(f"Return:          {return_pct:+.2f}%")
    logger.info(f"Total Trades:    {len(all_trades)}")
    logger.info(f"Win Rate:        {overall_win_rate:.1f}%")
    logger.info(f"{'='*80}")

    return {
        'scanner': scanner_name,
        'strategy': strategy_name,
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'total_pnl': total_pnl,
        'return_pct': return_pct,
        'total_trades': len(all_trades),
        'win_rate': overall_win_rate,
        'trades': all_trades
    }


def main():
    # User-specified parameters
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD', 'NFLX', 'SPY']
    start_date = datetime(2024, 11, 8)
    end_date = datetime(2025, 11, 7)
    interval = '1h'
    initial_capital = 100000.0

    logger.info("="*80)
    logger.info("DEBUG SIMULATION - VOLATILITY BREAKOUT")
    logger.info("="*80)
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Date Range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    logger.info("="*80)

    # Load cached data
    market_data = load_cached_data(symbols, interval, start_date, end_date)

    if not market_data:
        logger.error("NO DATA LOADED! Cannot run simulation.")
        return

    # Run simulations for both scanners
    scanners = ['top_movers', 'high_volume']
    strategy = 'Volatility Breakout'

    results = {}
    for scanner in scanners:
        result = simulate_combination(
            market_data, scanner, strategy, initial_capital, start_date, end_date
        )
        results[f"{scanner}_{strategy.replace(' ', '_')}"] = result

    # Comparison summary
    logger.info("\n" + "="*80)
    logger.info("COMPARISON SUMMARY")
    logger.info("="*80)

    for name, result in results.items():
        logger.info(f"\n{result['scanner']} + {result['strategy']}:")
        logger.info(f"  Return:      {result['return_pct']:+.2f}%")
        logger.info(f"  P&L:         ${result['total_pnl']:+,.2f}")
        logger.info(f"  Trades:      {result['total_trades']}")
        logger.info(f"  Win Rate:    {result['win_rate']:.1f}%")

        # Show sample trades
        if result['trades']:
            logger.info(f"\n  Sample trades (first 5):")
            for i, trade in enumerate(result['trades'][:5], 1):
                logger.info(f"    {i}. Entry: ${trade['entry_price']:.2f} @ {trade['entry_time']} -> "
                           f"Exit: ${trade['exit_price']:.2f} @ {trade['exit_time']} = "
                           f"{trade['pnl_pct']*100:+.2f}% (${trade['pnl_dollars']:+,.2f})")

    logger.info("\n" + "="*80)
    logger.info("SIMULATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
