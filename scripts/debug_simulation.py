"""
Debug simulation script to test specific scanner/strategy combinations.
Runs simulations for top_movers and high_volume scanners with Volatility Breakout strategy.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from scripts.real_data_simulator import RealDataSimulator
from gambler_ai.analysis.stock_scanner import ScannerType
import logging

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    # User-specified parameters
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD', 'NFLX', 'SPY']
    start_date = datetime(2024, 11, 8)
    end_date = datetime(2025, 11, 7)
    interval = '1h'
    initial_capital = 100000.0

    logger.info("="*80)
    logger.info("DEBUG SIMULATION - SPECIFIC COMBINATIONS")
    logger.info("="*80)
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Date Range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    logger.info(f"Testing combinations:")
    logger.info(f"  1. top_movers + Volatility Breakout")
    logger.info(f"  2. high_volume + Volatility Breakout")
    logger.info("="*80)

    # Initialize simulator
    simulator = RealDataSimulator(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        interval=interval,
        results_dir="debug_simulation_results"
    )

    # Check if data was loaded
    if not simulator.market_data:
        logger.error("NO DATA LOADED! Cannot run simulation.")
        logger.error("Please ensure data is downloaded for the specified symbols and date range.")
        return

    logger.info(f"\nData loaded for {len(simulator.market_data)} symbols:")
    for symbol, df in simulator.market_data.items():
        logger.info(f"  {symbol}: {len(df)} bars from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Test specific combinations
    scanners_to_test = [
        ScannerType.TOP_MOVERS,
        ScannerType.HIGH_VOLUME
    ]

    strategy_name = 'Volatility Breakout'

    logger.info("\n" + "="*80)
    logger.info("RUNNING SIMULATIONS")
    logger.info("="*80)

    results = {}

    for scanner_type in scanners_to_test:
        combo_name = f"{scanner_type.value}_{strategy_name.replace(' ', '_')}"

        logger.info(f"\n{'='*80}")
        logger.info(f"TESTING: {scanner_type.value} + {strategy_name}")
        logger.info(f"{'='*80}")

        weekly_results = []
        cumulative_pnl = 0
        total_trades = 0
        total_wins = 0

        # Simulate each week
        for week_num, (week_start, week_end) in enumerate(simulator.weekly_periods, 1):
            logger.info(f"\nWeek {week_num}: {week_start.date()} to {week_end.date()}")

            week_result = simulator._simulate_week(
                week_start, week_end, scanner_type, strategy_name
            )

            cumulative_pnl += week_result['pnl']
            total_trades += week_result['trades_count']

            if week_result['trades_count'] > 0:
                wins_this_week = int(
                    week_result['trades_count'] * week_result['win_rate'] / 100
                )
                total_wins += wins_this_week

            logger.info(f"  Trades: {week_result['trades_count']}")
            logger.info(f"  P&L: ${week_result['pnl']:,.2f}")
            logger.info(f"  Win Rate: {week_result['win_rate']:.1f}%")
            logger.info(f"  Cumulative P&L: ${cumulative_pnl:,.2f}")

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
        final_capital = initial_capital + cumulative_pnl
        return_pct = (cumulative_pnl / initial_capital) * 100
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        results[combo_name] = {
            'scanner': scanner_type.value,
            'strategy': strategy_name,
            'final_pnl': cumulative_pnl,
            'final_capital': final_capital,
            'return_pct': return_pct,
            'total_trades': total_trades,
            'win_rate': overall_win_rate,
            'weekly_results': weekly_results,
        }

        logger.info(f"\n{'='*80}")
        logger.info(f"FINAL RESULTS: {scanner_type.value} + {strategy_name}")
        logger.info(f"{'='*80}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"Final Capital:   ${final_capital:,.2f}")
        logger.info(f"Total P&L:       ${cumulative_pnl:,.2f}")
        logger.info(f"Return:          {return_pct:.2f}%")
        logger.info(f"Total Trades:    {total_trades}")
        logger.info(f"Win Rate:        {overall_win_rate:.1f}%")
        logger.info(f"{'='*80}")

    # Summary comparison
    logger.info("\n" + "="*80)
    logger.info("COMPARISON SUMMARY")
    logger.info("="*80)

    for combo_name, result in results.items():
        logger.info(f"\n{result['scanner']} + {result['strategy']}:")
        logger.info(f"  Return: {result['return_pct']:+.2f}%")
        logger.info(f"  P&L: ${result['final_pnl']:+,.2f}")
        logger.info(f"  Trades: {result['total_trades']}")
        logger.info(f"  Win Rate: {result['win_rate']:.1f}%")

    logger.info("\n" + "="*80)
    logger.info("DEBUG SIMULATION COMPLETE")
    logger.info("="*80)

    return results


if __name__ == "__main__":
    main()
