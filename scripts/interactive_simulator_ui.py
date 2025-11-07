"""
Interactive Simulation UI

Allows users to:
- Select date ranges
- Choose scanners and strategies
- Run simulations on-demand
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
if 'data_downloaded' not in st.session_state:
    st.session_state.data_downloaded = False


def check_data_availability():
    """Check if historical data is available."""
    cache_dir = Path("market_data_cache")
    metadata_file = cache_dir / "metadata.json"

    if not metadata_file.exists():
        return None

    with open(metadata_file, 'r') as f:
        metadata = json.load(f)

    return metadata


def check_existing_data(days: int, interval: str) -> bool:
    """Check if data already exists for the requested period."""
    from datetime import datetime, timedelta

    cache_dir = Path("market_data_cache")
    if not cache_dir.exists():
        return False

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Check for any parquet files in the date range
    pattern = f"*_{interval}_*.parquet"
    files = list(cache_dir.glob(pattern))

    if not files:
        return False

    # Check if files cover the requested date range
    for file in files:
        try:
            df = pd.read_parquet(file)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                file_start = df['timestamp'].min()
                file_end = df['timestamp'].max()

                # Remove timezone for comparison
                if pd.api.types.is_datetime64tz_dtype(df['timestamp']):
                    file_start = file_start.tz_localize(None)
                    file_end = file_end.tz_localize(None)

                # Check if file covers our range
                if file_start <= pd.Timestamp(start_date) and file_end >= pd.Timestamp(end_date):
                    return True
        except:
            continue

    return False


def download_data_section():
    """Data download section."""
    st.markdown("## 📥 Step 1: Download Historical Data")

    metadata = check_data_availability()

    if metadata:
        st.success("✅ Historical data available! Scroll down to Step 2 to select your custom date range.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Symbols", len(metadata['symbols']))
        col2.metric("Data Available From", metadata['start_date'][:10])
        col3.metric("Data Available To", metadata['end_date'][:10])

        with st.expander("📊 View Data Summary"):
            summary_data = []
            for symbol, info in metadata['data_summary'].items():
                summary_data.append({
                    'Symbol': symbol,
                    'Rows': info['rows'],
                    'Start': info['start'][:10],
                    'End': info['end'][:10]
                })

            df = pd.DataFrame(summary_data)
            st.dataframe(df, width='stretch', hide_index=True)

        st.markdown("### 📥 Download More Data")

    # Simple unified download form
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        days = st.number_input("Days of history", min_value=1, max_value=365, value=30, step=1,
                               help="Number of days to download (1-365)")

    with col2:
        interval = st.selectbox(
            "Interval",
            ["1m", "5m", "15m", "1h", "1d"],
            index=0,
            help="1m=1 minute, 5m=5 minutes, 1h=1 hour, 1d=1 day"
        )

    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        download_clicked = st.button("📥 Download", type="primary")

    # Get symbols from metadata or use default
    if metadata:
        symbols = metadata['symbols']
    else:
        symbols_input = st.text_input(
            "Symbols (comma-separated)",
            "AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,AMD,NFLX,SPY"
        )
        symbols = [s.strip().upper() for s in symbols_input.split(',')]

    # Download data
    if download_clicked:
        # Check if data already exists
        if check_existing_data(days, interval):
            st.info(f"ℹ️ Data for {days} days at {interval} interval already exists. Skipping download.")
        else:
            with st.spinner(f"Downloading {days} days of {interval} data for {len(symbols)} symbols..."):
                from datetime import datetime, timedelta
                from scripts.enhanced_data_downloader import EnhancedDataDownloader

                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # Use enhanced downloader with auto source selection
                downloader = EnhancedDataDownloader()
                data = downloader.download_auto(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval
                )

                if data:
                    st.success(f"✅ Downloaded {interval} data for {len(data)} symbols!")
                    st.info(f"📅 Period: {start_date.date()} to {end_date.date()}")
                    st.rerun()
                else:
                    st.error("❌ Failed to download data. Check your Alpaca credentials or try a shorter period.")
                    st.info("💡 Tip: For Alpaca data, set ALPACA_API_SECRET environment variable")


def simulation_config_section():
    """Simulation configuration section."""
    st.markdown("## ⚙️ Step 2: Configure Simulation")

    metadata = check_data_availability()

    if not metadata:
        st.warning("⚠️ Please download data first")
        return None

    # Date range selection
    st.markdown("### 📅 Select Time Period for Your Simulation")
    st.markdown(f"**Available data range:** {metadata['start_date'][:10]} to {metadata['end_date'][:10]}")

    min_date = datetime.fromisoformat(metadata['start_date'])
    max_date = datetime.fromisoformat(metadata['end_date'])

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "📍 Simulation Start Date",
            value=max_date - timedelta(days=365),  # Default: last 1 year
            min_value=min_date.date(),
            max_value=max_date.date(),
            help=f"Select any date from {min_date.date()} to {max_date.date()}"
        )

    with col2:
        end_date = st.date_input(
            "📍 Simulation End Date",
            value=max_date.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
            help=f"Select any date from {min_date.date()} to {max_date.date()}"
        )

    # Show selected period
    days_selected = (end_date - start_date).days
    st.info(f"📊 Selected period: **{start_date}** to **{end_date}** ({days_selected} days, ~{days_selected//7} weeks)")

    # Quick date range buttons
    st.markdown("**Quick Select:**")
    col1, col2, col3, col4, col5 = st.columns(5)

    if col1.button("Last 1 Year"):
        st.session_state.start_date = max_date - timedelta(days=365)
        st.session_state.end_date = max_date

    if col2.button("Last 2 Years"):
        st.session_state.start_date = max_date - timedelta(days=730)
        st.session_state.end_date = max_date

    if col3.button("Last 3 Years"):
        st.session_state.start_date = max_date - timedelta(days=1095)
        st.session_state.end_date = max_date

    if col4.button("Last 5 Years"):
        st.session_state.start_date = max_date - timedelta(days=1825)
        st.session_state.end_date = max_date

    if col5.button("Full Period"):
        st.session_state.start_date = min_date
        st.session_state.end_date = max_date

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

    col1, col2 = st.columns(2)

    with col1:
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=10000,
            max_value=1000000,
            value=100000,
            step=10000
        )

    with col2:
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
        'scanners': [scanner_options[s] for s in selected_scanners],
        'strategies': selected_strategies,
        'initial_capital': initial_capital,
        'update_interval': update_interval,
        'metadata': metadata
    }


def run_simulation_section(config):
    """Run simulation section."""
    if not config:
        return

    st.markdown("## 🚀 Step 3: Run Simulation")

    total_combinations = len(config['scanners']) * len(config['strategies'])
    days = (config['end_date'] - config['start_date']).days
    weeks = days // 7

    st.info(f"""
    **Simulation Summary:**
    - Period: {config['start_date'].date()} to {config['end_date'].date()} ({weeks} weeks)
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
            # Use REAL DATA SIMULATOR - NO synthetic data!
            # Force reload to get latest code changes
            import importlib
            import sys
            if 'scripts.real_data_simulator' in sys.modules:
                import scripts.real_data_simulator
                importlib.reload(scripts.real_data_simulator)

            from scripts.real_data_simulator import RealDataSimulator

            # Get symbols from metadata
            symbols = config['metadata']['symbols']

            # Create simulator with REAL market data
            simulator = RealDataSimulator(
                symbols=symbols,
                start_date=config['start_date'],
                end_date=config['end_date'],
                initial_capital=config['initial_capital'],
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
    **Welcome to the Interactive Simulator!**

    This tool allows you to:
    - Download real historical market data (up to 10 years)
    - Select custom date ranges for backtesting
    - Choose which scanners and strategies to test
    - Run simulations on-demand and see results in real-time
    """)

    st.markdown("---")

    # Section 1: Data Download
    download_data_section()

    st.markdown("---")

    # Section 2: Configuration
    config = simulation_config_section()

    st.markdown("---")

    # Section 3: Run Simulation
    if config:
        run_simulation_section(config)

    # Section 4: Results
    if st.session_state.simulation_results:
        st.markdown("---")
        results_section()


if __name__ == "__main__":
    main()
