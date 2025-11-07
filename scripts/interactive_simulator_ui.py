"""
Interactive Simulation UI - Simplified

Simple workflow:
1. User selects dates and interval
2. If data exists, use it; if not, download it
3. Run simulation and show results
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enhanced_data_downloader import EnhancedDataDownloader
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


def check_data_exists(symbols: list, start_date: datetime, end_date: datetime, interval: str) -> bool:
    """Check if data exists for the given parameters."""
    cache_dir = Path("market_data_cache")
    if not cache_dir.exists():
        return False

    # Check if parquet files exist for all symbols
    for symbol in symbols:
        pattern = f"{symbol}_{interval}_*.parquet"
        files = list(cache_dir.glob(pattern))

        if not files:
            return False

        # Check if any file covers the date range
        has_coverage = False
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
                        has_coverage = True
                        break
            except Exception:
                continue

        if not has_coverage:
            return False

    return True


def download_data(symbols: list, start_date: datetime, end_date: datetime, interval: str) -> bool:
    """Download data for the given parameters."""
    try:
        downloader = EnhancedDataDownloader()
        data = downloader.download_auto(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )
        return data is not None and len(data) > 0
    except Exception as e:
        st.error(f"Error downloading data: {e}")
        return False


def main():
    """Main UI."""
    st.markdown('<div class="main-header">🎮 Interactive Simulation Platform</div>', unsafe_allow_html=True)

    st.markdown("""
    **Simple Simulation Workflow:**
    1. Select your date range and interval
    2. Choose symbols to simulate (or use defaults)
    3. Click "Run Simulation" - data will be downloaded if needed
    4. View results
    """)

    st.markdown("---")

    # ========== STEP 1: Date and Interval Selection ==========
    st.markdown("## 📅 Select Simulation Period")

    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            max_value=datetime.now().date()
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now().date(),
            max_value=datetime.now().date()
        )

    with col3:
        interval = st.selectbox(
            "Interval",
            ["1m", "5m", "15m", "1h", "1d"],
            index=4,  # Default to 1d
            help="Note: 1m data limited to 7 days by Yahoo Finance"
        )

    # Show period info
    days_selected = (end_date - start_date).days
    st.info(f"📊 Selected period: {days_selected} days (~{days_selected//7} weeks)")

    # Validate for 1m interval
    if interval == "1m" and days_selected > 7:
        st.warning("⚠️ Yahoo Finance limits 1-minute data to 7 days. Will attempt to use Alpaca (requires API key) or reduce date range.")

    # ========== STEP 2: Symbol Selection ==========
    st.markdown("## 📈 Select Symbols")

    symbols_input = st.text_input(
        "Symbols (comma-separated)",
        "AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA,META,AMD,NFLX,SPY",
        help="Enter stock symbols separated by commas"
    )
    symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]

    st.info(f"Will simulate {len(symbols)} symbols: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")

    # ========== STEP 3: Optional Configuration ==========
    with st.expander("⚙️ Advanced Options (Optional)"):
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
            st.markdown("**Scanners & Strategies**")
            st.caption("Currently using default scanners and strategies")
            st.caption("Top Movers, High Volume, Best Setups")
            st.caption("Momentum, Mean Reversion, Volatility Breakout")

    st.markdown("---")

    # ========== STEP 4: Run Simulation ==========
    st.markdown("## 🚀 Run Simulation")

    # Check if data exists
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    data_exists = check_data_exists(symbols, start_datetime, end_datetime, interval)

    if data_exists:
        st.success("✅ Data exists in cache - will use existing data")
    else:
        st.info("ℹ️ Data not found in cache - will download when you run simulation")

    if st.button("🎮 RUN SIMULATION", type="primary", disabled=st.session_state.simulation_running):
        st.session_state.simulation_running = True
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        try:
            # Check/download data
            if not data_exists:
                status_placeholder.info("📥 Downloading data...")
                progress_placeholder.progress(0.1)

                success = download_data(symbols, start_datetime, end_datetime, interval)

                if not success:
                    st.error("❌ Failed to download data. Check credentials or try different date range.")
                    st.session_state.simulation_running = False
                    return

                status_placeholder.success("✅ Data downloaded successfully!")
                progress_placeholder.progress(0.3)
            else:
                progress_placeholder.progress(0.3)

            # Run simulation
            status_placeholder.info("🔄 Running simulation with real market data...")

            # Force reload simulator
            import importlib
            if 'scripts.real_data_simulator' in sys.modules:
                import scripts.real_data_simulator
                importlib.reload(scripts.real_data_simulator)

            from scripts.real_data_simulator import RealDataSimulator

            # Create and run simulator
            simulator = RealDataSimulator(
                symbols=symbols,
                start_date=start_datetime,
                end_date=end_datetime,
                initial_capital=initial_capital,
                results_dir="simulation_results_real"
            )

            progress_placeholder.progress(0.5)

            # Run the simulation
            simulator.run_simulation()

            progress_placeholder.progress(0.9)

            # Load results
            results_file = Path("simulation_results_real/live_results.json")
            if results_file.exists():
                with open(results_file, 'r') as f:
                    results = json.load(f)

                # Add config metadata
                results['_config'] = {
                    'start_date': start_datetime.isoformat(),
                    'end_date': end_datetime.isoformat(),
                    'interval': interval,
                    'symbols': symbols,
                    'initial_capital': initial_capital
                }

                st.session_state.simulation_results = results
                progress_placeholder.progress(1.0)
                status_placeholder.success(f"✅ Simulation complete! Analyzed {days_selected} days of data.")
            else:
                st.error("❌ Results file not found")

        except Exception as e:
            st.error(f"❌ Simulation failed: {e}")
            import traceback
            st.code(traceback.format_exc())

        finally:
            st.session_state.simulation_running = False
            progress_placeholder.empty()
            status_placeholder.empty()

    # ========== STEP 5: Display Results ==========
    if st.session_state.simulation_results:
        st.markdown("---")
        st.markdown("## 📊 Simulation Results")

        results = st.session_state.simulation_results

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Weeks Simulated", results.get('weeks_completed', 0))
        col2.metric("Combinations", len(results.get('combinations', {})))

        # Find best performer
        if results.get('combinations'):
            best = max(results['combinations'].items(), key=lambda x: x[1].get('return_pct', 0))
            col3.metric("Best Return", f"{best[1].get('return_pct', 0):.2f}%")
            col4.metric("Best P&L", f"${best[1].get('final_pnl', 0):,.0f}")

        st.markdown("---")

        # Create tabs for results
        tab1, tab2 = st.tabs(["📈 Performance Chart", "🏆 Rankings"])

        with tab1:
            # Line chart
            fig = go.Figure()

            if results.get('combinations'):
                sorted_combos = sorted(
                    results['combinations'].items(),
                    key=lambda x: x[1].get('return_pct', 0),
                    reverse=True
                )[:10]  # Top 10

                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
                          '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788']

                for idx, (combo_name, combo_data) in enumerate(sorted_combos):
                    if 'cumulative_pnl' not in combo_data:
                        continue

                    weeks = list(range(1, len(combo_data['cumulative_pnl']) + 1))
                    display_name = f"{combo_data.get('scanner', 'Unknown')} + {combo_data.get('strategy', 'Unknown')}"

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

                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            # Rankings table
            if results.get('combinations'):
                rankings = []
                for combo_name, combo_data in results['combinations'].items():
                    rankings.append({
                        'Scanner': combo_data.get('scanner', 'Unknown'),
                        'Strategy': combo_data.get('strategy', 'Unknown'),
                        'Return %': f"{combo_data.get('return_pct', 0):.2f}%",
                        'Final P&L': f"${combo_data.get('final_pnl', 0):,.2f}",
                        'Trades': combo_data.get('total_trades', 0),
                        'Win Rate': f"{combo_data.get('win_rate', 0):.1f}%"
                    })

                df = pd.DataFrame(rankings)
                df = df.sort_values('Return %', ascending=False)
                df.insert(0, 'Rank', range(1, len(df) + 1))

                st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
