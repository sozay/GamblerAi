"""
Interactive Simulation UI

Simplified version:
- Select date ranges and interval
- Choose scanners and strategies
- Data is downloaded automatically if needed
- View results in real-time
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.data_downloader import DataDownloader
from scripts.simulation_race_live import LiveSimulationRace
from gambler_ai.analysis.stock_scanner import ScannerType

st.set_page_config(
    page_title="Interactive Simulator",
    page_icon="🎮",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #667eea;
        color: white;
        font-size: 1.2rem;
        padding: 0.8rem;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #764ba2;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None


def check_data_availability(start_date: datetime, end_date: datetime, interval: str, requested_symbols: list = None):
    """Check if data exists for the requested period, interval, and symbols."""
    cache_dir = Path("market_data_cache")

    if not cache_dir.exists():
        return False, [], []

    # Check for parquet files with the specified interval
    pattern = f"*_{interval}_*.parquet"
    files = list(cache_dir.glob(pattern))

    if not files:
        return False, [], []

    # Extract symbols that have data covering the requested period
    available_symbols = []

    for file in files:
        try:
            df = pd.read_parquet(file)
            # Check for timestamp column (use 'Datetime' as fallback for Yahoo data)
            timestamp_col = 'timestamp' if 'timestamp' in df.columns else ('Datetime' if 'Datetime' in df.columns else None)

            if timestamp_col:
                df['timestamp'] = pd.to_datetime(df[timestamp_col])
                file_start = df['timestamp'].min()
                file_end = df['timestamp'].max()

                # Remove timezone for comparison
                if pd.api.types.is_datetime64tz_dtype(df['timestamp']):
                    file_start = file_start.tz_localize(None)
                    file_end = file_end.tz_localize(None)

                # Check if file overlaps with our requested range
                # File is useful if: file_start is before/at requested_end AND file_end is after/at requested_start
                requested_start = pd.Timestamp(start_date)
                requested_end = pd.Timestamp(end_date)

                if file_start <= requested_end and file_end >= requested_start:
                    # Extract symbol from filename (format: AAPL_1h_20241108_20251107.parquet)
                    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else file.name.split('_')[0]
                    if symbol and symbol not in available_symbols:
                        available_symbols.append(symbol)
        except:
            continue

    # If specific symbols were requested, check if all are available
    if requested_symbols:
        missing_symbols = [s for s in requested_symbols if s not in available_symbols]
        all_available = len(missing_symbols) == 0
        return all_available, available_symbols, missing_symbols
    else:
        # No specific symbols requested, just report what's available
        data_exists = len(available_symbols) > 0
        return data_exists, available_symbols, []


def simulation_config_section():
    """Simulation configuration section."""
    st.markdown("## ⚙️ Configure Simulation")

    # Date range and interval selection
    st.markdown("### 📅 Select Date Range and Interval")

    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input(
            "📍 Start Date",
            value=datetime.now().date() - timedelta(days=30),
            max_value=datetime.now().date(),
            help="Select the start date for your simulation"
        )

    with col2:
        end_date = st.date_input(
            "📍 End Date",
            value=datetime.now().date(),
            max_value=datetime.now().date(),
            help="Select the end date for your simulation"
        )

    with col3:
        interval = st.selectbox(
            "⏱️ Data Interval",
            ["1m", "5m", "15m", "1h", "1d"],
            index=1,
            help="1m=1 minute, 5m=5 minutes, 1h=1 hour, 1d=1 day"
        )

    # Show selected period and validate
    days_selected = (end_date - start_date).days
    st.info(f"📊 Selected period: **{start_date}** to **{end_date}** ({days_selected} days, ~{days_selected//7} weeks)")

    # Validate data availability based on interval and date range
    is_intraday = interval in ["1m", "5m", "15m", "1h"]
    if is_intraday and days_selected > 60:
        st.warning(f"⚠️ **Yahoo Finance Limitation:** Intraday data ({interval}) is limited to 60 days, but you selected {days_selected} days.")
        st.info("💡 **Solution:** Alpaca API credentials are required for periods > 60 days. Make sure ALPACA_API_SECRET environment variable is set.")
    elif interval == "1m" and days_selected > 7:
        st.info("ℹ️ For 1-minute data > 7 days, Alpaca API will be used (Yahoo Finance limit: 7 days)")

    # Symbols selection
    symbols_input = st.text_input(
        "📊 Symbols (comma-separated)",
        "AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,AMD,NFLX,SPY",
        help="Enter stock symbols separated by commas"
    )
    symbols = [s.strip().upper() for s in symbols_input.split(',')]

    # Scanner selection
    st.markdown("### 🔍 Select Stock Scanners")

    scanner_options = {
        "Top Movers": ScannerType.TOP_MOVERS,
        "High Volume": ScannerType.HIGH_VOLUME,
        "Best Setups": ScannerType.BEST_SETUPS,
        "Relative Strength": ScannerType.RELATIVE_STRENGTH,
        "Gap Scanner": ScannerType.GAP_SCANNER,
        "Volatility Range": ScannerType.VOLATILITY_RANGE,
        "Sector Leaders": ScannerType.SECTOR_LEADERS,
        "Market Cap Weighted": ScannerType.MARKET_CAP_WEIGHTED,
    }

    selected_scanners = st.multiselect(
        "Choose scanners to test",
        list(scanner_options.keys()),
        default=["Top Movers", "High Volume", "Best Setups"]
    )

    # Strategy selection
    st.markdown("### 📈 Select Trading Strategies")

    strategy_options = [
        "Momentum",
        "Mean Reversion",
        "Volatility Breakout",
    ]

    selected_strategies = st.multiselect(
        "Choose strategies to test",
        strategy_options,
        default=["Momentum", "Mean Reversion"]
    )

    # Additional parameters
    st.markdown("### 💰 Capital & Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=10000,
            max_value=1000000,
            value=100000,
            step=10000
        )

    with col2:
        position_size_pct = st.slider(
            "Position Size (% of Capital)",
            min_value=10,
            max_value=100,
            value=30,
            step=5,
            help="Percentage of available capital to use per trade. 30% is conservative, 100% is all-in aggressive."
        )

    with col3:
        update_interval = st.slider(
            "Chart Update Speed (seconds)",
            min_value=0.1,
            max_value=2.0,
            value=0.5,
            step=0.1
        )

    # Return configuration
    return {
        'start_date': datetime.combine(start_date, datetime.min.time()),
        'end_date': datetime.combine(end_date, datetime.max.time()),
        'interval': interval,
        'symbols': symbols,
        'scanners': [scanner_options[s] for s in selected_scanners],
        'strategies': selected_strategies,
        'initial_capital': initial_capital,
        'position_size_pct': position_size_pct / 100.0,  # Convert percentage to decimal
        'update_interval': update_interval
    }


def run_simulation_section(config):
    """Run simulation section."""
    if not config:
        return

    st.markdown("## 🚀 Run Simulation")

    total_combinations = len(config['scanners']) * len(config['strategies'])
    days = (config['end_date'] - config['start_date']).days
    weeks = days // 7

    # Check if data exists for all requested symbols
    data_exists, available_symbols, missing_symbols = check_data_availability(
        config['start_date'],
        config['end_date'],
        config['interval'],
        config['symbols']
    )

    if data_exists:
        st.success(f"✅ Data available for all {len(available_symbols)} symbols at {config['interval']} interval")
    elif len(available_symbols) > 0:
        st.info(f"ℹ️ Data available for {len(available_symbols)}/{len(config['symbols'])} symbols. Missing: {', '.join(missing_symbols)}")
        st.info(f"💾 Missing symbols will be downloaded automatically when you start the simulation")
    else:
        st.info(f"ℹ️ Data will be downloaded automatically when you start the simulation")

    st.info(f"""
    **Simulation Summary:**
    - Period: {config['start_date'].date()} to {config['end_date'].date()} ({weeks} weeks)
    - Interval: {config['interval']}
    - Symbols: {len(config['symbols'])}
    - Combinations: {total_combinations} ({len(config['scanners'])} scanners × {len(config['strategies'])} strategies)
    - Initial Capital: ${config['initial_capital']:,}
    """)

    if st.button("🎮 START SIMULATION", type="primary", disabled=st.session_state.simulation_running):
        st.session_state.simulation_running = True

        # Create progress placeholder
        progress_bar = st.progress(0)
        status_text = st.empty()
        chart_placeholder = st.empty()

        try:
            # Check and download data if needed
            if not data_exists:
                # Only download missing symbols
                symbols_to_download = missing_symbols if missing_symbols else config['symbols']

                if symbols_to_download:
                    status_text.markdown(f"### 📥 Downloading data for {len(symbols_to_download)} symbol(s)...")
                    if len(symbols_to_download) < len(config['symbols']):
                        status_text.markdown(f"**Downloading:** {', '.join(symbols_to_download)}")
                        status_text.markdown(f"**Using cached:** {', '.join(available_symbols)}")

                    progress_bar.progress(10)

                    from scripts.enhanced_data_downloader import EnhancedDataDownloader

                    downloader = EnhancedDataDownloader()
                    data = downloader.download_auto(
                        symbols=symbols_to_download,
                        start_date=config['start_date'],
                        end_date=config['end_date'],
                        interval=config['interval']
                    )
                else:
                    data = True  # All data already exists

                if not data:
                    is_intraday = config['interval'] in ["1m", "5m", "15m", "1h"]
                    days = (config['end_date'] - config['start_date']).days

                    st.error("❌ Failed to download data")

                    if is_intraday and days > 60:
                        st.error(f"**Yahoo Finance Limitation:** Cannot download {config['interval']} data for {days} days (limit: 60 days)")
                        st.info("**💡 Solutions:**")
                        st.info("1. Set ALPACA_API_SECRET environment variable to use Alpaca API")
                        st.info(f"2. Reduce the period to 60 days or less")
                        st.info("3. Use daily (1d) interval instead (no limit)")
                    elif config['interval'] == "1m" and days > 7:
                        st.error(f"**Yahoo Finance Limitation:** Cannot download 1m data for {days} days (limit: 7 days)")
                        st.info("**💡 Solutions:**")
                        st.info("1. Set ALPACA_API_SECRET environment variable")
                        st.info("2. Reduce the period to 7 days or less")
                        st.info("3. Use 5m, 15m, 1h, or 1d interval instead")
                    else:
                        st.info("💡 Check your Alpaca credentials or try a shorter period")

                    st.session_state.simulation_running = False
                    return

                if data and symbols_to_download:
                    st.success(f"✅ Downloaded {config['interval']} data for {len(data)} symbol(s)!")
                progress_bar.progress(30)

            # Use REAL DATA SIMULATOR - NO synthetic data!
            # Force reload to get latest code changes
            import importlib
            import sys
            if 'scripts.real_data_simulator' in sys.modules:
                import scripts.real_data_simulator
                importlib.reload(scripts.real_data_simulator)

            from scripts.real_data_simulator import RealDataSimulator

            # Create simulator with REAL market data
            simulator = RealDataSimulator(
                symbols=config['symbols'],
                start_date=config['start_date'],
                end_date=config['end_date'],
                initial_capital=config['initial_capital'],
                interval=config['interval'],  # Pass the selected interval!
                position_size_pct=config['position_size_pct'],  # Pass position size %!
                results_dir="simulation_results_real"
            )

            # Clear any old results first
            st.session_state.simulation_results = None

            # Calculate actual weeks
            actual_weeks = simulator.total_weeks

            # Show clear status message
            status_text.markdown(f"""
            ### Running Simulation with REAL Market Data...

            **Period:** {config['start_date'].date()} to {config['end_date'].date()}

            **Total weeks to simulate:** {actual_weeks}

            **Data Source:** Real Yahoo Finance data (NO synthetic data!)

            **This will take approximately {max(1, actual_weeks // 10)}-{max(2, actual_weeks // 5)} minutes.**

            The simulation is analyzing real price movements and generating actual trading signals.
            Please wait for completion - results will appear automatically below.

            You can monitor progress in the terminal/console output.
            """)

            progress_bar.progress(0)
            progress_bar.empty()  # Remove progress bar since we can't track real progress

            # Run the actual simulation with REAL DATA
            simulator.run_simulation()

            # Load the newly generated results
            results_file = Path("simulation_results_real/live_results.json")
            if results_file.exists():
                with open(results_file, 'r') as f:
                    results = json.load(f)

                # Add metadata about the simulation config
                results['_config'] = {
                    'start_date': config['start_date'].isoformat(),
                    'end_date': config['end_date'].isoformat(),
                    'selected_scanners': [s.value for s in config['scanners']],
                    'selected_strategies': config['strategies'],
                }

                st.session_state.simulation_results = results
                st.success(f"✅ Simulation complete! Simulated from {config['start_date'].date()} to {config['end_date'].date()}")

        except Exception as e:
            st.error(f"❌ Simulation failed: {e}")

        finally:
            st.session_state.simulation_running = False
            progress_bar.empty()
            status_text.empty()


def results_section():
    """Display results section."""
    if st.session_state.simulation_results is None:
        return

    st.markdown("## 📊 Simulation Results")

    results = st.session_state.simulation_results

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Weeks Simulated", results['weeks_completed'])
    col2.metric("Combinations", len(results['combinations']))

    # Find best performer
    best = max(results['combinations'].items(), key=lambda x: x[1]['return_pct'])
    col3.metric("Best Return", f"{best[1]['return_pct']:.2f}%")
    col4.metric("Best P&L", f"${best[1]['final_pnl']:,.0f}")

    st.markdown("---")

    # Create tabs for results
    tab1, tab2 = st.tabs(["📈 Performance Chart", "🏆 Rankings"])

    with tab1:
        # Line chart
        fig = go.Figure()

        sorted_combos = sorted(
            results['combinations'].items(),
            key=lambda x: x[1]['return_pct'],
            reverse=True
        )[:10]  # Top 10

        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
                  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788']

        for idx, (combo_name, combo_data) in enumerate(sorted_combos):
            if 'cumulative_pnl' not in combo_data:
                continue

            weeks = list(range(1, len(combo_data['cumulative_pnl']) + 1))
            display_name = f"{combo_data['scanner']} + {combo_data['strategy']}"

            fig.add_trace(go.Scatter(
                x=weeks,
                y=combo_data['cumulative_pnl'],
                mode='lines',
                name=display_name,
                line=dict(width=2, color=colors[idx % len(colors)]),
            ))

        fig.update_layout(
            height=600,
            hovermode='x unified',
            xaxis_title="Week",
            yaxis_title="Cumulative P&L ($)",
        )

        st.plotly_chart(fig, use_container_width=True)  # Will update to width='stretch' in future

    with tab2:
        # Rankings table
        rankings = []
        for combo_name, combo_data in results['combinations'].items():
            rankings.append({
                'Scanner': combo_data['scanner'],
                'Strategy': combo_data['strategy'],
                'Return %': f"{combo_data['return_pct']:.2f}%",
                'Final P&L': f"${combo_data['final_pnl']:,.2f}",
                'Trades': combo_data['total_trades'],
                'Win Rate': f"{combo_data['win_rate']:.1f}%"
            })

        df = pd.DataFrame(rankings)
        df = df.sort_values('Return %', ascending=False)
        df.insert(0, 'Rank', range(1, len(df) + 1))

        st.dataframe(df, width='stretch', hide_index=True)


def main():
    """Main UI."""
    st.markdown('<div class="main-header">🎮 Interactive Simulation Platform</div>', unsafe_allow_html=True)

    st.markdown("""
    **Welcome to the Simplified Interactive Simulator!**

    This tool allows you to:
    - Select date ranges and data interval
    - Choose which scanners and strategies to test
    - Data is downloaded automatically if needed
    - Run simulations and see results in real-time
    """)

    st.markdown("---")

    # Configuration
    config = simulation_config_section()

    st.markdown("---")

    # Run Simulation
    if config:
        run_simulation_section(config)

    # Results
    if st.session_state.simulation_results:
        st.markdown("---")
        results_section()


if __name__ == "__main__":
    main()
