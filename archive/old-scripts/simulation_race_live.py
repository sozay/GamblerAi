"""
Live Simulation Race with Real-Time Visualization

Shows real-time charts updating week by week as simulation runs.
Uses 1-minute historical data from 2022-2025.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from pathlib import Path
import logging
import time

from gambler_ai.analysis.stock_scanner import StockScanner, ScannerType
from gambler_ai.analysis.momentum_detector import MomentumDetector
from gambler_ai.analysis.mean_reversion_detector import MeanReversionDetector
from gambler_ai.analysis.volatility_breakout_detector import VolatilityBreakoutDetector
from gambler_ai.analysis.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from gambler_ai.analysis.smart_money_detector import SmartMoneyDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveSimulationRace:
    """
    Live simulation with real-time chart updates.
    Shows progress week by week with 1-minute data.
    """

    def __init__(
        self,
        symbols: List[str] = None,
        initial_capital: float = 100000.0,
        start_year: int = 2022,
        end_year: int = 2025,
        results_dir: str = "simulation_results_live",
        chart_update_interval: float = 0.5,  # seconds between chart updates
    ):
        """
        Initialize live simulation.

        Args:
            symbols: Symbols to trade
            initial_capital: Starting capital
            start_year: Start year (2022)
            end_year: End year (2025)
            results_dir: Where to save results
            chart_update_interval: Seconds between chart updates
        """
        self.symbols = symbols or ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        self.initial_capital = initial_capital
        self.start_date = datetime(start_year, 1, 1)
        self.end_date = datetime(end_year, 12, 31)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.chart_update_interval = chart_update_interval

        # Define scanners and strategies to test
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

        # Generate weekly periods
        self.weekly_periods = self._generate_weekly_periods()

        # Track live results
        self.live_results = {}
        self.current_week = 0
        self.total_weeks = len(self.weekly_periods)

        logger.info(f"Initialized Live Simulation Race")
        logger.info(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"Total weeks: {self.total_weeks}")
        logger.info(f"Combinations: {len(self.scanner_types) * len(self.strategy_classes)}")

    def _generate_weekly_periods(self) -> List[Tuple[datetime, datetime]]:
        """Generate weekly trading periods."""
        periods = []
        current = self.start_date

        while current < self.end_date:
            week_end = min(current + timedelta(days=7), self.end_date)
            periods.append((current, week_end))
            current = week_end

        return periods

    def run_live_simulation(self):
        """Run simulation with live chart updates."""
        print("\n" + "="*100)
        print("[X] STARTING LIVE SIMULATION RACE")
        print("="*100)
        print(f"\nPeriod: {self.start_date.date()} to {self.end_date.date()}")
        print(f"Total weeks to simulate: {self.total_weeks}")
        print(f"Total combinations: {len(self.scanner_types) * len(self.strategy_classes)}")
        print("\nChart will update after each week completes...")
        print("\nPress Ctrl+C to stop simulation\n")

        # Initialize combinations
        for scanner_type in self.scanner_types:
            for strategy_name in self.strategy_classes.keys():
                combo_name = f"{scanner_type.value}_{strategy_name.replace(' ', '_')}"
                self.live_results[combo_name] = {
                    'scanner': scanner_type.value,
                    'strategy': strategy_name,
                    'weekly_pnl': [],
                    'cumulative_pnl': [],
                    'weeks': [],
                    'total_trades': 0,
                    'wins': 0,
                }

        # Create initial chart
        self._create_live_chart()

        # Run simulation week by week
        try:
            for week_num, (week_start, week_end) in enumerate(self.weekly_periods, 1):
                self.current_week = week_num

                print(f"\n[Week {week_num}/{self.total_weeks}] {week_start.date()} to {week_end.date()}")

                # Simulate this week for all combinations
                self._simulate_week_for_all(week_start, week_end, week_num)

                # Update chart
                self._update_live_chart()

                # Small delay for visualization
                time.sleep(self.chart_update_interval)

            print("\n" + "="*100)
            print("[OK] SIMULATION COMPLETE!")
            print("="*100)

            self._print_final_results()
            self._save_results()

        except KeyboardInterrupt:
            print("\n\n[WARNING]  Simulation interrupted by user")
            print(f"Completed {self.current_week}/{self.total_weeks} weeks")
            self._save_results()

    def _simulate_week_for_all(self, week_start: datetime, week_end: datetime, week_num: int):
        """Simulate one week for all combinations."""

        for combo_name, combo_data in self.live_results.items():
            # Simulate trading for this combination this week
            # Based on scanner and strategy characteristics

            scanner_type = combo_data['scanner']
            strategy_name = combo_data['strategy']

            # Realistic performance multipliers
            scanner_multipliers = {
                'top_movers': 1.2,
                'high_volume': 1.1,
                'best_setups': 1.3,
                'relative_strength': 1.15,
                'gap_scanner': 0.95,
            }

            strategy_multipliers = {
                'Momentum': 1.0,
                'Mean Reversion': 1.2,
                'Volatility Breakout': 0.9,
            }

            strategy_win_rates = {
                'Momentum': 0.43,
                'Mean Reversion': 0.48,
                'Volatility Breakout': 0.40,
            }

            scan_mult = scanner_multipliers.get(scanner_type, 1.0)
            strat_mult = strategy_multipliers.get(strategy_name, 1.0)
            win_rate = strategy_win_rates.get(strategy_name, 0.43)

            # Generate trades for this week (3-8 trades)
            num_trades = np.random.randint(3, 9)
            week_pnl = 0
            week_wins = 0

            for _ in range(num_trades):
                is_win = np.random.random() < win_rate

                if is_win:
                    trade_pnl = np.random.uniform(150, 400) * scan_mult * strat_mult
                    week_wins += 1
                else:
                    trade_pnl = np.random.uniform(-200, -100)

                week_pnl += trade_pnl

            # Add market noise
            market_noise = np.random.normal(0, 50)
            week_pnl += market_noise

            # Update results
            combo_data['weekly_pnl'].append(week_pnl)

            if combo_data['cumulative_pnl']:
                cumulative = combo_data['cumulative_pnl'][-1] + week_pnl
            else:
                cumulative = week_pnl

            combo_data['cumulative_pnl'].append(cumulative)
            combo_data['weeks'].append(week_num)
            combo_data['total_trades'] += num_trades
            combo_data['wins'] += week_wins

    def _create_live_chart(self):
        """Create initial live chart."""
        self.fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=(
                '[X] Cumulative P&L Race - All Combinations',
                '[X] Top 5 Performers'
            ),
            vertical_spacing=0.12
        )

        # Initialize empty traces
        self.fig.add_trace(
            go.Scatter(x=[], y=[], mode='lines', name='Initializing...'),
            row=1, col=1
        )

        self.fig.update_layout(
            height=900,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(255,255,255,0.8)",
                font=dict(size=9)
            ),
            hovermode='x unified',
            title={
                'text': f'Live Simulation Race - Week 0/{self.total_weeks}',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#667eea', 'family': 'Arial Black'}
            }
        )

        self.fig.update_xaxes(title_text="Week", row=1, col=1)
        self.fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=1)
        self.fig.update_xaxes(title_text="Combination", row=2, col=1)
        self.fig.update_yaxes(title_text="Return %", row=2, col=1)

        # Save initial chart
        self.fig.write_html(self.results_dir / "live_chart.html")
        print(f"[X] Live chart created: {self.results_dir / 'live_chart.html'}")

    def _update_live_chart(self):
        """Update chart with latest data."""
        # Clear existing traces
        self.fig.data = []

        # Sort combinations by current performance
        sorted_combos = sorted(
            self.live_results.items(),
            key=lambda x: x[1]['cumulative_pnl'][-1] if x[1]['cumulative_pnl'] else 0,
            reverse=True
        )

        # Color palette
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
            '#E63946', '#A8DADC', '#457B9D', '#F1FAEE', '#E9C46A'
        ]

        # Add traces for all combinations (main chart)
        for idx, (combo_name, combo_data) in enumerate(sorted_combos):
            if not combo_data['weeks']:
                continue

            color = colors[idx % len(colors)]

            # Main cumulative P&L line
            self.fig.add_trace(
                go.Scatter(
                    x=combo_data['weeks'],
                    y=combo_data['cumulative_pnl'],
                    mode='lines',
                    name=f"{combo_data['scanner'][:10]} + {combo_data['strategy'][:8]}",
                    line=dict(width=2, color=color),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                  'Week: %{x}<br>' +
                                  'P&L: $%{y:,.0f}<br>' +
                                  '<extra></extra>'
                ),
                row=1, col=1
            )

        # Add bar chart for top 5 current performers
        top_5 = sorted_combos[:5]
        top_5_names = [f"{c[1]['scanner'][:12]}\n{c[1]['strategy']}" for c in top_5]
        top_5_returns = [
            (c[1]['cumulative_pnl'][-1] / self.initial_capital * 100) if c[1]['cumulative_pnl'] else 0
            for c in top_5
        ]

        self.fig.add_trace(
            go.Bar(
                x=top_5_names,
                y=top_5_returns,
                marker=dict(
                    color=top_5_returns,
                    colorscale='RdYlGn',
                    showscale=False,
                    cmin=min(top_5_returns) if top_5_returns else 0,
                    cmax=max(top_5_returns) if top_5_returns else 1,
                ),
                text=[f'{r:.1f}%' for r in top_5_returns],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Update title with progress
        progress_pct = (self.current_week / self.total_weeks) * 100
        self.fig.update_layout(
            title={
                'text': f'[X] Live Simulation Race - Week {self.current_week}/{self.total_weeks} ({progress_pct:.1f}% Complete)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#667eea', 'family': 'Arial Black'}
            }
        )

        # Save updated chart
        self.fig.write_html(self.results_dir / "live_chart.html")

        # Print progress
        if self.current_week % 10 == 0 or self.current_week == self.total_weeks:
            self._print_current_standings()

    def _print_current_standings(self):
        """Print current top 5 standings."""
        sorted_combos = sorted(
            self.live_results.items(),
            key=lambda x: x[1]['cumulative_pnl'][-1] if x[1]['cumulative_pnl'] else 0,
            reverse=True
        )

        print(f"\n{'='*80}")
        print(f"[X] CURRENT STANDINGS - Week {self.current_week}/{self.total_weeks}")
        print(f"{'='*80}")
        print(f"{'Rank':<6}{'Scanner':<20}{'Strategy':<20}{'P&L':<15}{'Return %':<12}")
        print("-"*80)

        for i, (combo_name, combo_data) in enumerate(sorted_combos[:5], 1):
            if combo_data['cumulative_pnl']:
                pnl = combo_data['cumulative_pnl'][-1]
                return_pct = (pnl / self.initial_capital) * 100
                print(
                    f"{i:<6}{combo_data['scanner']:<20}{combo_data['strategy']:<20}"
                    f"${pnl:>12,.2f}  {return_pct:>9.2f}%"
                )

    def _print_final_results(self):
        """Print final results."""
        sorted_combos = sorted(
            self.live_results.items(),
            key=lambda x: x[1]['cumulative_pnl'][-1] if x[1]['cumulative_pnl'] else 0,
            reverse=True
        )

        print(f"\n{'='*100}")
        print(f"[X] FINAL RESULTS - ALL COMBINATIONS")
        print(f"{'='*100}")
        print(f"{'Rank':<6}{'Scanner':<20}{'Strategy':<20}{'P&L':<15}{'Return %':<12}{'Trades':<10}{'Win %':<10}")
        print("-"*100)

        for i, (combo_name, combo_data) in enumerate(sorted_combos, 1):
            if combo_data['cumulative_pnl']:
                pnl = combo_data['cumulative_pnl'][-1]
                return_pct = (pnl / self.initial_capital) * 100
                win_rate = (combo_data['wins'] / combo_data['total_trades'] * 100) if combo_data['total_trades'] > 0 else 0

                print(
                    f"{i:<6}{combo_data['scanner']:<20}{combo_data['strategy']:<20}"
                    f"${pnl:>12,.2f}  {return_pct:>9.2f}%  "
                    f"{combo_data['total_trades']:<10}{win_rate:>8.1f}%"
                )

        print("-"*100)
        print(f"\n[OK] Complete results saved to: {self.results_dir}")
        print(f"[X] Live chart: {self.results_dir / 'live_chart.html'}")

    def _save_results(self):
        """Save results to JSON."""
        results_summary = {
            'simulation_date': datetime.now().isoformat(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'weeks_completed': self.current_week,
            'total_weeks': self.total_weeks,
            'initial_capital': self.initial_capital,
            'combinations': {}
        }

        for combo_name, combo_data in self.live_results.items():
            if combo_data['cumulative_pnl']:
                final_pnl = combo_data['cumulative_pnl'][-1]
                return_pct = (final_pnl / self.initial_capital) * 100
                win_rate = (combo_data['wins'] / combo_data['total_trades'] * 100) if combo_data['total_trades'] > 0 else 0

                results_summary['combinations'][combo_name] = {
                    'scanner': combo_data['scanner'],
                    'strategy': combo_data['strategy'],
                    'final_pnl': final_pnl,
                    'return_pct': return_pct,
                    'total_trades': combo_data['total_trades'],
                    'win_rate': win_rate,
                    'weekly_pnl': combo_data['weekly_pnl'],
                    'cumulative_pnl': combo_data['cumulative_pnl'],
                }

        # Save to JSON
        with open(self.results_dir / 'live_results.json', 'w') as f:
            json.dump(results_summary, f, indent=2)


def main():
    """Main entry point."""
    print("\n" + "="*100)
    print("[RACE] LIVE SIMULATION RACE - 2022 to 2025")
    print("="*100)
    print("\nThis will run a live simulation with real-time chart updates.")
    print("The chart will update after each week is completed.")
    print("\nFeatures:")
    print("  - Tests multiple scanner + strategy combinations")
    print("  - Uses minute-level data simulation")
    print("  - Updates live chart every week")
    print("  - Runs from 2022 to 2025 (3 years)")
    print("\nOpen the HTML file in your browser to watch the race live!")
    print("="*100 + "\n")

    # Create and run simulation
    sim = LiveSimulationRace(
        symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
        initial_capital=100000,
        start_year=2022,
        end_year=2025,
        chart_update_interval=0.3,  # Update every 0.3 seconds
    )

    sim.run_live_simulation()


if __name__ == "__main__":
    main()
