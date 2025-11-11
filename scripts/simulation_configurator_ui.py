#!/usr/bin/env python3
"""
Simulation Configurator UI

Interactive dashboard to configure and run simulation races with custom parameters.
Allows users to set slippage and profit/loss target parameters.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.simulation_race_engine import SimulationRaceEngine

# Page configuration
st.set_page_config(
    page_title="GamblerAI Simulation Configurator",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .parameter-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main entry point."""

    # Header
    st.markdown('<div class="main-header">⚙️ GamblerAI Simulation Configurator ⚙️</div>', unsafe_allow_html=True)

    st.markdown("""
    ### Configure and Run Trading Simulations

    This tool allows you to run simulations with custom parameters for:
    - **Execution Slippage**: Simulate real-world order execution delays
    - **Profit/Loss Targets**: Set custom stop loss and take profit percentages
    """)

    # Create two columns for better layout
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("## 📊 Basic Configuration")

        # Basic parameters
        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=10000,
            max_value=1000000,
            value=100000,
            step=10000,
            help="Starting capital for each strategy combination"
        )

        lookback_days = st.slider(
            "Lookback Period (days)",
            min_value=30,
            max_value=365,
            value=365,
            step=30,
            help="Number of days to simulate (from today backwards)"
        )

        st.markdown("---")

        st.markdown("## 💰 Profit/Loss Targets")

        use_percentage_targets = st.checkbox(
            "Use Percentage Targets",
            value=True,
            help="Use percentage-based stop loss and take profit instead of fixed prices"
        )

        col_sl, col_tp = st.columns(2)

        with col_sl:
            stop_loss_pct = st.number_input(
                "Stop Loss (%)",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1,
                format="%.1f",
                help="Percentage loss to close position (e.g., 1.0 = 1% loss)"
            )

        with col_tp:
            take_profit_pct = st.number_input(
                "Take Profit (%)",
                min_value=0.1,
                max_value=20.0,
                value=2.0,
                step=0.1,
                format="%.1f",
                help="Percentage gain to close position (e.g., 2.0 = 2% gain)"
            )

        # Show Risk/Reward ratio
        risk_reward_ratio = take_profit_pct / stop_loss_pct
        st.metric(
            "Risk/Reward Ratio",
            f"1:{risk_reward_ratio:.2f}",
            help="Higher is better - you're risking $1 to make this much"
        )

    with col2:
        st.markdown("## 🔄 Execution Slippage")

        slippage_enabled = st.checkbox(
            "Enable Execution Slippage",
            value=True,
            help="Simulate realistic order execution delays"
        )

        if slippage_enabled:
            st.markdown("""
            <div class="warning-box">
            <strong>ℹ️ What is Slippage?</strong><br>
            In real trading, not all orders execute at the expected price. Slippage simulates
            scenarios where your order executes at the next bar's price instead of the current bar.
            </div>
            """, unsafe_allow_html=True)

            slippage_probability = st.slider(
                "Slippage Probability (%)",
                min_value=0,
                max_value=100,
                value=30,
                step=5,
                help="Percentage of orders that will experience slippage"
            ) / 100.0

            slippage_delay_bars = st.select_slider(
                "Execution Delay (bars)",
                options=[1, 2, 3, 4, 5],
                value=1,
                help="Number of bars to delay execution when slippage occurs"
            )

            # Show simulation example
            st.markdown("### Example Scenario")
            if slippage_probability > 0:
                st.info(
                    f"**{slippage_probability * 100:.0f}%** of your orders will execute "
                    f"**{slippage_delay_bars} bar(s) later** than expected, "
                    f"potentially at a different price."
                )

        else:
            slippage_probability = 0.0
            slippage_delay_bars = 0

        st.markdown("---")

        st.markdown("## 📈 Configuration Preview")

        st.markdown(f"""
        <div class="parameter-card">
        <h4>Your Simulation Settings:</h4>
        <ul>
            <li><strong>Capital:</strong> ${initial_capital:,}</li>
            <li><strong>Period:</strong> {lookback_days} days</li>
            <li><strong>Stop Loss:</strong> {stop_loss_pct}% loss</li>
            <li><strong>Take Profit:</strong> {take_profit_pct}% gain</li>
            <li><strong>Risk/Reward:</strong> 1:{risk_reward_ratio:.2f}</li>
            <li><strong>Slippage:</strong> {'Enabled' if slippage_enabled else 'Disabled'}</li>
            {f'<li><strong>Slippage Rate:</strong> {slippage_probability * 100:.0f}% of orders</li>' if slippage_enabled else ''}
            {f'<li><strong>Execution Delay:</strong> {slippage_delay_bars} bar(s)</li>' if slippage_enabled else ''}
        </ul>
        </div>
        """, unsafe_allow_html=True)

    # Run simulation button
    st.markdown("---")
    st.markdown("## 🚀 Run Simulation")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

    with col_btn2:
        run_simulation = st.button(
            "▶️ Run Simulation",
            type="primary",
            use_container_width=True,
            help="Start the simulation with current parameters"
        )

    if run_simulation:
        st.markdown("""
        <div class="success-box">
        <strong>✅ Simulation Started!</strong><br>
        This may take several minutes depending on the number of combinations.
        </div>
        """, unsafe_allow_html=True)

        # Create progress container
        progress_container = st.container()

        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Create and run simulation engine
            try:
                status_text.text("Initializing simulation engine...")

                engine = SimulationRaceEngine(
                    initial_capital=initial_capital,
                    lookback_days=lookback_days,
                    results_dir="simulation_results",
                    slippage_enabled=slippage_enabled,
                    slippage_probability=slippage_probability,
                    slippage_delay_bars=int(slippage_delay_bars),
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct,
                    use_percentage_targets=use_percentage_targets,
                )

                total_combos = len(engine.scanner_types) * len(engine.strategy_classes)

                status_text.text(f"Running {total_combos} strategy combinations...")
                progress_bar.progress(10)

                # Run simulation
                results = engine.run_simulation(save_progress=True)

                progress_bar.progress(100)
                status_text.text("✅ Simulation completed successfully!")

                # Display summary
                st.markdown("### 📊 Simulation Summary")

                col_s1, col_s2, col_s3, col_s4 = st.columns(4)

                with col_s1:
                    st.metric("Combinations Tested", len(results))

                with col_s2:
                    best_result = max(results.values(), key=lambda x: x.return_pct)
                    st.metric("Best Return", f"{best_result.return_pct:.2f}%")

                with col_s3:
                    avg_return = sum(r.return_pct for r in results.values()) / len(results)
                    st.metric("Average Return", f"{avg_return:.2f}%")

                with col_s4:
                    total_trades = sum(r.total_trades for r in results.values())
                    st.metric("Total Trades", total_trades)

                st.success(f"""
                **Simulation Complete!** 🎉

                Results have been saved to `simulation_results/` directory.

                **Next Steps:**
                1. View detailed results in the [Simulation Race UI](http://localhost:8501)
                2. Run `streamlit run scripts/simulation_race_ui.py` to visualize results
                """)

            except Exception as e:
                st.error(f"❌ Simulation failed: {str(e)}")
                import traceback
                with st.expander("Show Error Details"):
                    st.code(traceback.format_exc())

    # Information section
    st.markdown("---")
    st.markdown("## ℹ️ Understanding the Parameters")

    with st.expander("📖 Execution Slippage Explained"):
        st.markdown("""
        ### What is Slippage?

        In real-world trading, not all orders execute at the exact price you see when you place the order.
        **Slippage** occurs when your order is filled at a different price, often due to:

        - Market volatility
        - Order execution delays
        - Liquidity constraints
        - Network latency

        ### How We Simulate It

        When slippage is enabled:
        - A certain % of your orders (based on **Slippage Probability**) will experience delayed execution
        - These orders execute at the price N bars later (based on **Execution Delay**)
        - This creates a more realistic simulation of actual trading conditions

        ### Example

        - **Without Slippage**: Order to buy at $100 → Executes at $100
        - **With 30% Slippage, 1 bar delay**:
          - 70% of orders execute at $100 (no slippage)
          - 30% of orders execute at next bar's price (could be $100.50 or $99.50)
        """)

    with st.expander("📖 Profit/Loss Targets Explained"):
        st.markdown("""
        ### Stop Loss

        The **Stop Loss** is the maximum loss you're willing to take on a trade.

        - Set as a percentage from your entry price
        - Example: 1% stop loss on a $100 entry = exit at $99 (for long positions)
        - Protects your capital from large losses

        ### Take Profit

        The **Take Profit** is your profit target for each trade.

        - Set as a percentage from your entry price
        - Example: 2% take profit on a $100 entry = exit at $102 (for long positions)
        - Locks in profits when target is reached

        ### Risk/Reward Ratio

        The ratio between your potential profit and potential loss.

        - Formula: Take Profit % ÷ Stop Loss %
        - Example: 2% TP / 1% SL = 1:2 ratio
        - **Higher is better**: You're risking less to gain more
        - Professional traders typically target ratios of 1:2 or higher
        """)

    with st.expander("📖 Recommended Settings"):
        st.markdown("""
        ### Conservative (Low Risk)
        - Stop Loss: 0.5%
        - Take Profit: 1.0%
        - Slippage: 20%
        - **Use for**: Stable markets, high-frequency trading

        ### Balanced (Medium Risk)
        - Stop Loss: 1.0%
        - Take Profit: 2.0%
        - Slippage: 30%
        - **Use for**: Normal market conditions, swing trading

        ### Aggressive (High Risk)
        - Stop Loss: 2.0%
        - Take Profit: 6.0%
        - Slippage: 50%
        - **Use for**: Volatile markets, momentum trading

        ### Testing Extreme Slippage
        - Stop Loss: 1.0%
        - Take Profit: 2.0%
        - Slippage: 70-100%
        - **Use for**: Worst-case scenario testing, high volatility markets
        """)


if __name__ == "__main__":
    main()
