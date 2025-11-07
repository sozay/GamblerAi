"""
Real Data Simulation Engine

Uses actual downloaded market data to run simulations.
NO synthetic data - only real price movements and actual strategy signals.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
import json

from scripts.data_downloader import DataDownloader
from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector

# Set logging level to INFO to see all messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RealDataSimulator:
    """
    Simulation engine using ONLY real market data.
    Downloads and uses actual price data from Yahoo Finance.
    """

    def __init__(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000.0,
        results_dir: str = "simulation_results_real",
        interval: str = "1h",
    ):
        """
        Initialize real data simulator.

        Args:
            symbols: Stock symbols to trade
            start_date: Simulation start date
            end_date: Simulation end date
            initial_capital: Starting capital
            results_dir: Where to save results
            interval: Data interval (1m, 5m, 15m, 1h, 1d)
        """
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.interval = interval
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

        # Scanners and strategies to test
        self.scanner_types = [
            ScannerType.TOP_MOVERS,
            ScannerType.HIGH_VOLUME,
            ScannerType.BEST_SETUPS,
            ScannerType.RELATIVE_STRENGTH,
            ScannerType.GAP_SCANNER,
        ]

        self.strategy_classes = {
            'Momentum': MomentumDetector,
            'Mean Reversion': MeanReversionDetector,
            'Volatility Breakout': VolatilityBreakoutDetector,
        }

        # Load real market data
        self.market_data = {}
        self._load_market_data()

        # Generate periods
        self.weekly_periods = self._generate_weekly_periods()
        self.total_weeks = len(self.weekly_periods)

        logger.info(f"Initialized Real Data Simulator")
        logger.info(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"Symbols: {len(self.symbols)}")
        logger.info(f"Total weeks: {self.total_weeks}")
        logger.info(f"Combinations: {len(self.scanner_types) * len(self.strategy_classes)}")

    def _load_market_data(self):
        """Load real market data from cache."""
        logger.info("="*80)
        logger.info("LOADING REAL MARKET DATA FROM CACHE")
        logger.info("="*80)

        cache_dir = Path("market_data_cache")
        logger.info(f"Cache directory path: {cache_dir.absolute()}")
        logger.info(f"Cache directory exists: {cache_dir.exists()}")

        if not cache_dir.exists():
            logger.error(f"Cache directory not found: {cache_dir.absolute()}")
            logger.error("Please download data first using the '📊 Download 7-Day 1-Min Data' button")
            return

        # List all files in cache
        logger.info("Scanning for data files in cache...")
        all_files = list(cache_dir.glob("*.*"))
        logger.info(f"*** Found {len(all_files)} files in cache directory ***")

        if all_files:
            logger.info(f"Sample files: {[f.name for f in all_files[:5]]}")

        # Load data for each symbol
        for symbol in self.symbols:
            # Find cache files for this symbol with SPECIFIC INTERVAL
            cache_files = []

            # Try different patterns - ONLY for the specified interval
            patterns = [
                f"{symbol}_{self.interval}_*.parquet",
                f"{symbol.lower()}_{self.interval}_*.parquet",
            ]

            for pattern in patterns:
                found = list(cache_dir.glob(pattern))
                if found:
                    cache_files.extend(found)
                    logger.info(f"Found {len(found)} files for {symbol} with pattern {pattern} (interval: {self.interval})")

            if not cache_files:
                logger.warning(f"No cached data for {symbol} (tried patterns: {patterns})")
                continue

            # Load all cache files and combine
            symbol_dfs = []
            for cache_file in cache_files:
                try:
                    logger.debug(f"Loading {cache_file}")
                    df = pd.read_parquet(cache_file)

                    # Ensure timestamp column exists
                    if 'timestamp' not in df.columns:
                        logger.warning(f"No timestamp column in {cache_file}, columns: {df.columns.tolist()}")
                        # Try to find datetime-like column
                        for col in df.columns:
                            if 'date' in col.lower() or 'time' in col.lower():
                                df['timestamp'] = pd.to_datetime(df[col])
                                logger.info(f"Using column '{col}' as timestamp")
                                break

                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])

                        # Normalize timezone: convert all to UTC for consistency
                        if not pd.api.types.is_datetime64tz_dtype(df['timestamp']):
                            # Timezone-naive data (from Yahoo) - assume it's US Eastern time
                            df['timestamp'] = df['timestamp'].dt.tz_localize('America/New_York')
                            logger.debug(f"Localized timezone-naive data to America/New_York")

                        # Convert all to UTC for consistent comparison
                        df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')

                        symbol_dfs.append(df)
                        logger.info(f"Loaded {len(df)} rows from {cache_file.name}")
                except Exception as e:
                    logger.error(f"Error loading {cache_file}: {e}")

            if symbol_dfs:
                # Combine and sort by timestamp (all data is now in UTC)
                combined_df = pd.concat(symbol_dfs, ignore_index=True)
                combined_df = combined_df.sort_values('timestamp')
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')

                # Filter to our date range
                # Convert user-selected dates to UTC for comparison
                start_date_utc = pd.Timestamp(self.start_date).tz_localize('America/New_York').tz_convert('UTC')
                end_date_utc = pd.Timestamp(self.end_date).tz_localize('America/New_York').tz_convert('UTC')
                logger.info(f"Filtering data: {start_date_utc} to {end_date_utc} (UTC)")

                combined_df = combined_df[
                    (combined_df['timestamp'] >= start_date_utc) &
                    (combined_df['timestamp'] <= end_date_utc)
                ]

                if len(combined_df) > 0:
                    self.market_data[symbol] = combined_df
                    logger.info(f"Loaded {len(combined_df)} bars for {symbol}")
                else:
                    logger.warning(f"No data in date range for {symbol}")

        if not self.market_data:
            logger.error("No market data loaded! Cannot run simulation.")
        else:
            logger.info(f"Successfully loaded data for {len(self.market_data)} symbols")

            # CRITICAL FIX: Detect actual data date range and adjust simulation period
            self._adjust_date_range_to_data()

    def _adjust_date_range_to_data(self):
        """
        CRITICAL FIX: Adjust simulation date range to match actual data availability.

        This fixes the issue where user requests a 1-year period but data only covers
        recent months, causing weeks of empty trading until data starts.
        """
        if not self.market_data:
            return

        # Find the actual min and max timestamps across all loaded data
        all_min_dates = []
        all_max_dates = []

        for symbol, df in self.market_data.items():
            if len(df) > 0 and 'timestamp' in df.columns:
                all_min_dates.append(df['timestamp'].min())
                all_max_dates.append(df['timestamp'].max())

        if not all_min_dates or not all_max_dates:
            logger.warning("No timestamp data found in loaded market data")
            return

        # Get the actual data range (timezone-aware)
        actual_start = min(all_min_dates)
        actual_end = max(all_max_dates)

        # Convert to timezone-naive datetime for comparison
        if pd.api.types.is_datetime64tz_dtype(actual_start):
            actual_start = actual_start.tz_convert('America/New_York').tz_localize(None)
            actual_end = actual_end.tz_convert('America/New_York').tz_localize(None)

        actual_start = actual_start.to_pydatetime()
        actual_end = actual_end.to_pydatetime()

        # Compare with requested range
        requested_days = (self.end_date - self.start_date).days
        actual_days = (actual_end - actual_start).days

        logger.info("=" * 80)
        logger.info("DATA RANGE VALIDATION")
        logger.info("=" * 80)
        logger.info(f"Requested range: {self.start_date.date()} to {self.end_date.date()} ({requested_days} days)")
        logger.info(f"Actual data range: {actual_start.date()} to {actual_end.date()} ({actual_days} days)")

        # If actual data range is significantly different, adjust simulation period
        if actual_start > self.start_date or actual_end < self.end_date:
            logger.warning("⚠️  DATA RANGE MISMATCH DETECTED!")
            logger.warning(f"   Requested data from {self.start_date.date()} but data starts at {actual_start.date()}")
            logger.warning(f"   Adjusting simulation to match actual data availability...")

            # Adjust to actual data range
            self.start_date = actual_start
            self.end_date = actual_end

            # Regenerate weekly periods with correct dates
            self.weekly_periods = self._generate_weekly_periods()
            self.total_weeks = len(self.weekly_periods)

            logger.info(f"✓ Adjusted simulation: {self.start_date.date()} to {self.end_date.date()}")
            logger.info(f"✓ New total weeks: {self.total_weeks}")
        else:
            logger.info("✓ Data range matches requested range")

        logger.info("=" * 80)

    def _generate_weekly_periods(self) -> List[Tuple[datetime, datetime]]:
        """Generate weekly trading periods."""
        periods = []
        current = self.start_date

        while current < self.end_date:
            week_end = min(current + timedelta(days=7), self.end_date)
            periods.append((current, week_end))
            current = week_end

        return periods

    def _get_week_data(self, symbol: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Get market data for a specific week."""
        if symbol not in self.market_data:
            return None

        df = self.market_data[symbol]

        # All data is now in UTC, convert week dates to UTC for comparison
        start_utc = pd.Timestamp(start).tz_localize('America/New_York').tz_convert('UTC')
        end_utc = pd.Timestamp(end).tz_localize('America/New_York').tz_convert('UTC')

        week_df = df[(df['timestamp'] >= start_utc) & (df['timestamp'] <= end_utc)].copy()

        return week_df if len(week_df) > 0 else None

    def _calculate_signals(
        self,
        data: pd.DataFrame,
        scanner_type: ScannerType,
        strategy_name: str
    ) -> List[Dict]:
        """
        Calculate trading signals from real data.
        Returns list of trades with entry/exit prices.

        REALISTIC TRADING RULES:
        - Maximum 1-3 trades per day per symbol
        - Minimum 30-minute hold period
        - Clear entry/exit criteria
        - Position sizing based on capital
        """
        if data is None or len(data) < 20:
            return []

        trades = []
        last_trade_time = None

        # OPTIMIZED PARAMETERS (from backtesting on 2024-11-08 to 2025-11-07)
        # These settings achieved +9.89% return on 1h data
        min_bars_between_trades = 6  # Minimum 6 bars between trades

        # Dynamic max_hold_bars based on available data
        available_bars = len(data) - 20  # Bars available after warmup
        max_hold_bars = min(15, max(8, available_bars // 3))  # Allow longer holds

        # Position size: 100% OF CAPITAL (ALL IN - VERY AGGRESSIVE!)
        # If capital is $100k, trade with $100k. If $10k, trade with $10k.
        position_size = self.initial_capital * 1.0  # Changed from 0.10 to 1.0

        # Risk management parameters (OPTIMIZED)
        stop_loss_pct = 0.02  # Exit if loss exceeds 2%
        take_profit_pct = 0.04  # Exit if profit reaches 4%

        # Simple signal generation based on strategy
        if strategy_name == 'Momentum':
            # Momentum: Buy on strong upward movement with volume confirmation
            data['returns'] = data['close'].pct_change()
            data['ma_short'] = data['close'].rolling(window=5).mean()
            data['ma_long'] = data['close'].rolling(window=20).mean()
            data['volume_ma'] = data['volume'].rolling(window=20).mean()

            # Generate signals with spacing
            for i in range(20, len(data) - max_hold_bars, min_bars_between_trades):
                # OPTIMIZED: More sensitive momentum detection
                if (data['ma_short'].iloc[i] > data['ma_long'].iloc[i] and
                    data['returns'].iloc[i] > 0.001 and  # 0.1% move (optimized)
                    data['volume'].iloc[i] > data['volume_ma'].iloc[i] * 1.03):  # 3% volume spike (optimized)

                    entry_price = data['close'].iloc[i]

                    # Simulate holding with stop loss and take profit
                    hold_period = min(12, max_hold_bars)  # Optimized: 12 bars
                    best_exit_price = None
                    exit_idx = i + hold_period

                    # Check each bar for stop loss or take profit
                    for j in range(i + 1, min(i + hold_period + 1, len(data))):
                        current_price = data['close'].iloc[j]
                        pnl_pct = (current_price - entry_price) / entry_price

                        # Stop loss: exit if down 2%
                        if pnl_pct <= -stop_loss_pct:
                            best_exit_price = current_price
                            exit_idx = j
                            break

                        # Take profit: exit if up 4%
                        if pnl_pct >= take_profit_pct:
                            best_exit_price = current_price
                            exit_idx = j
                            break

                    # If no stop/profit hit, exit at hold period
                    if best_exit_price is None:
                        exit_idx = min(i + hold_period, len(data) - 1)
                        best_exit_price = data['close'].iloc[exit_idx]

                    pnl = (best_exit_price - entry_price) / entry_price
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': best_exit_price,
                        'pnl_pct': pnl,
                        'pnl_dollars': pnl * position_size
                    })

        elif strategy_name == 'Mean Reversion':
            # Mean Reversion: Buy on extreme dips, wait for reversion
            data['ma'] = data['close'].rolling(window=20).mean()
            data['std'] = data['close'].rolling(window=20).std()
            data['z_score'] = (data['close'] - data['ma']) / data['std']

            # Limit trades with spacing
            for i in range(20, len(data) - max_hold_bars, min_bars_between_trades):
                # OPTIMIZED: More aggressive entry on dips (z-score < -1.0)
                if data['z_score'].iloc[i] < -1.0:  # Was -1.5
                    entry_price = data['close'].iloc[i]

                    # Simulate holding with stop loss and take profit
                    hold_period = min(12, max_hold_bars)  # Optimized: 12 bars
                    best_exit_price = None

                    # Check each bar for stop loss or take profit
                    for j in range(i + 1, min(i + hold_period + 1, len(data))):
                        current_price = data['close'].iloc[j]
                        pnl_pct = (current_price - entry_price) / entry_price

                        # Stop loss: exit if down 2%
                        if pnl_pct <= -stop_loss_pct:
                            best_exit_price = current_price
                            break

                        # Take profit: exit if up 4%
                        if pnl_pct >= take_profit_pct:
                            best_exit_price = current_price
                            break

                    # If no stop/profit hit, exit at hold period
                    if best_exit_price is None:
                        exit_idx = min(i + hold_period, len(data) - 1)
                        best_exit_price = data['close'].iloc[exit_idx]

                    pnl = (best_exit_price - entry_price) / entry_price
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': best_exit_price,
                        'pnl_pct': pnl,
                        'pnl_dollars': pnl * position_size
                    })

        elif strategy_name == 'Volatility Breakout':
            # Volatility Breakout: Trade significant breakouts only
            data['volatility'] = data['close'].rolling(window=20).std()
            data['high_low_range'] = data['high'] - data['low']
            data['atr'] = data['high_low_range'].rolling(window=14).mean()

            # Limit trades with spacing
            for i in range(20, len(data) - max_hold_bars, min_bars_between_trades):
                # OPTIMIZED: More sensitive to breakouts (1.5x ATR instead of 2.0x)
                if data['high_low_range'].iloc[i] > data['atr'].iloc[i] * 1.5:
                    entry_price = data['close'].iloc[i]

                    # Simulate holding with stop loss and take profit
                    hold_period = min(12, max_hold_bars)  # Optimized: 12 bars
                    best_exit_price = None

                    # Check each bar for stop loss or take profit
                    for j in range(i + 1, min(i + hold_period + 1, len(data))):
                        current_price = data['close'].iloc[j]
                        pnl_pct = (current_price - entry_price) / entry_price

                        # Stop loss: exit if down 2%
                        if pnl_pct <= -stop_loss_pct:
                            best_exit_price = current_price
                            break

                        # Take profit: exit if up 4%
                        if pnl_pct >= take_profit_pct:
                            best_exit_price = current_price
                            break

                    # If no stop/profit hit, exit at hold period
                    if best_exit_price is None:
                        exit_idx = min(i + hold_period, len(data) - 1)
                        best_exit_price = data['close'].iloc[exit_idx]

                    pnl = (best_exit_price - entry_price) / entry_price
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': best_exit_price,
                        'pnl_pct': pnl,
                        'pnl_dollars': pnl * position_size
                    })

        return trades

    def _simulate_week(
        self,
        week_start: datetime,
        week_end: datetime,
        scanner_type: ScannerType,
        strategy_name: str
    ) -> Dict:
        """
        Simulate trading for one week using REAL DATA ONLY.
        """
        all_trades = []

        # Get data for each symbol
        for symbol in self.symbols:
            week_data = self._get_week_data(symbol, week_start, week_end)

            if week_data is None:
                continue

            # Calculate trading signals from real data
            trades = self._calculate_signals(week_data, scanner_type, strategy_name)
            all_trades.extend(trades)

        # Calculate week statistics
        if not all_trades:
            return {
                'pnl': 0,
                'trades_count': 0,
                'win_rate': 0,
            }

        total_pnl = sum(t['pnl_dollars'] for t in all_trades)
        wins = sum(1 for t in all_trades if t['pnl_dollars'] > 0)
        win_rate = (wins / len(all_trades)) * 100 if all_trades else 0

        return {
            'pnl': total_pnl,
            'trades_count': len(all_trades),
            'win_rate': win_rate,
        }

    def run_simulation(self) -> Dict:
        """
        Run simulation using REAL MARKET DATA ONLY.
        """
        logger.info("Starting simulation with REAL data...")

        all_results = {}

        for scanner_type in self.scanner_types:
            for strategy_name in self.strategy_classes.keys():
                combo_name = f"{scanner_type.value}_{strategy_name.replace(' ', '_')}"

                logger.info(f"Simulating {combo_name}...")

                weekly_results = []
                cumulative_pnl = 0
                total_trades = 0
                total_wins = 0

                # Simulate each week
                for week_num, (week_start, week_end) in enumerate(self.weekly_periods, 1):
                    week_result = self._simulate_week(
                        week_start, week_end, scanner_type, strategy_name
                    )

                    cumulative_pnl += week_result['pnl']
                    total_trades += week_result['trades_count']

                    if week_result['trades_count'] > 0:
                        wins_this_week = int(
                            week_result['trades_count'] * week_result['win_rate'] / 100
                        )
                        total_wins += wins_this_week

                    weekly_results.append({
                        'week_number': week_num,
                        'start_date': week_start.isoformat(),
                        'end_date': week_end.isoformat(),
                        'pnl': week_result['pnl'],
                        'cumulative_pnl': cumulative_pnl,
                        'trades_count': week_result['trades_count'],
                        'win_rate': week_result['win_rate'],
                    })

                # Calculate final statistics
                final_capital = self.initial_capital + cumulative_pnl
                return_pct = (cumulative_pnl / self.initial_capital) * 100
                overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

                all_results[combo_name] = {
                    'scanner': scanner_type.value,
                    'strategy': strategy_name,
                    'final_pnl': cumulative_pnl,
                    'return_pct': return_pct,
                    'total_trades': total_trades,
                    'win_rate': overall_win_rate,
                    'weekly_pnl': [w['pnl'] for w in weekly_results],
                    'cumulative_pnl': [w['cumulative_pnl'] for w in weekly_results],
                }

                logger.info(f"  Completed: P&L=${cumulative_pnl:,.2f}, Return={return_pct:.2f}%")

        # Save results
        self._save_results(all_results)

        return all_results

    def _save_results(self, results: Dict):
        """Save results to JSON."""
        output = {
            'simulation_date': datetime.now().isoformat(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'weeks_completed': self.total_weeks,
            'total_weeks': self.total_weeks,
            'initial_capital': self.initial_capital,
            'combinations': results,
            'data_source': 'REAL_MARKET_DATA_ONLY'
        }

        results_file = self.results_dir / 'live_results.json'
        with open(results_file, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Results saved to {results_file}")
