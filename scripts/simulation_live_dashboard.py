"""
Live Simulation Dashboard

Shows the 3-year simulation results (2022-2025) with line charts.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from pathlib import Path

st.set_page_config(
    page_title="Live Simulation - 2022-2025",
    page_icon="📈",
    layout="wide"
)

# Header
st.markdown("# 📈 Live Simulation Results: 2022-2025")
st.markdown("**3-Year Performance Race - Minute-Level Data Simulation**")
st.markdown("---")

# Load results
results_file = Path("simulation_results_live/live_results.json")

if not results_file.exists():
    st.error("No live simulation results found!")
    st.info("Please run: python scripts/simulation_race_live.py")
    st.stop()

with open(results_file, 'r') as f:
    data = json.load(f)

# Display simulation info
col1, col2, col3, col4 = st.columns(4)
col1.metric("Start Date", data['start_date'][:10])
col2.metric("End Date", data['end_date'][:10])
col3.metric("Weeks Simulated", data['weeks_completed'])
col4.metric("Combinations", len(data['combinations']))

st.markdown("---")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Performance Chart", "🏆 Leaderboard", "📋 Weekly Data"])

# Tab 1: Performance Chart
with tab1:
    st.markdown("### Cumulative P&L Over Time")
    st.markdown("See how each scanner+strategy combination performed week by week")

    # Create line chart
    fig = go.Figure()

    # Sort by final return
    sorted_combos = sorted(
        data['combinations'].items(),
        key=lambda x: x[1]['return_pct'],
        reverse=True
    )

    # Color palette
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788',
        '#E63946', '#A8DADC', '#457B9D', '#F1FAEE', '#E9C46A'
    ]

    for idx, (combo_name, combo_data) in enumerate(sorted_combos):
        if 'cumulative_pnl' not in combo_data or not combo_data['cumulative_pnl']:
            continue

        # Create week numbers
        weeks = list(range(1, len(combo_data['cumulative_pnl']) + 1))

        display_name = f"{combo_data['scanner']} + {combo_data['strategy']}"
        color = colors[idx % len(colors)]

        fig.add_trace(go.Scatter(
            x=weeks,
            y=combo_data['cumulative_pnl'],
            mode='lines',
            name=display_name,
            line=dict(width=2, color=color),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Week: %{x}<br>' +
                          'P&L: $%{y:,.0f}<br>' +
                          '<extra></extra>'
        ))

    fig.update_layout(
        height=700,
        hovermode='x unified',
        xaxis_title="Week",
        yaxis_title="Cumulative P&L ($)",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show selector for detailed view
    st.markdown("### 📍 Compare Specific Combinations")

    combo_options = {
        f"{c['scanner']} + {c['strategy']}": name
        for name, c in data['combinations'].items()
    }

    selected_combos = st.multiselect(
        "Select combinations to compare",
        list(combo_options.keys()),
        default=list(combo_options.keys())[:3]
    )

    if selected_combos:
        fig2 = go.Figure()

        for idx, display_name in enumerate(selected_combos):
            combo_name = combo_options[display_name]
            combo_data = data['combinations'][combo_name]

            if 'cumulative_pnl' in combo_data and combo_data['cumulative_pnl']:
                weeks = list(range(1, len(combo_data['cumulative_pnl']) + 1))
                color = colors[idx % len(colors)]

                fig2.add_trace(go.Scatter(
                    x=weeks,
                    y=combo_data['cumulative_pnl'],
                    mode='lines+markers',
                    name=display_name,
                    line=dict(width=3, color=color),
                    marker=dict(size=4),
                ))

        fig2.update_layout(
            height=500,
            hovermode='x unified',
            xaxis_title="Week",
            yaxis_title="Cumulative P&L ($)",
        )

        st.plotly_chart(fig2, use_container_width=True)

# Tab 2: Leaderboard
with tab2:
    st.markdown("### 🏆 Final Rankings")

    # Create leaderboard dataframe
    leaderboard = []
    for combo_name, combo_data in data['combinations'].items():
        leaderboard.append({
            'Rank': 0,
            'Scanner': combo_data['scanner'],
            'Strategy': combo_data['strategy'],
            'Return %': combo_data['return_pct'],
            'Final P&L': combo_data['final_pnl'],
            'Total Trades': combo_data['total_trades'],
            'Win Rate %': combo_data['win_rate'],
        })

    df = pd.DataFrame(leaderboard)
    df = df.sort_values('Return %', ascending=False)
    df['Rank'] = range(1, len(df) + 1)

    # Format columns
    df['Return %'] = df['Return %'].apply(lambda x: f"{x:.2f}%")
    df['Final P&L'] = df['Final P&L'].apply(lambda x: f"${x:,.2f}")
    df['Win Rate %'] = df['Win Rate %'].apply(lambda x: f"{x:.1f}%")

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Top 3 winners
    st.markdown("### 🥇 Top 3 Winners")
    cols = st.columns(3)

    medals = ['🥇 First Place', '🥈 Second Place', '🥉 Third Place']

    sorted_results = sorted(
        data['combinations'].items(),
        key=lambda x: x[1]['return_pct'],
        reverse=True
    )

    for i, (col, medal) in enumerate(zip(cols, medals)):
        if i < len(sorted_results):
            combo_name, combo_data = sorted_results[i]
            with col:
                st.markdown(f"#### {medal}")
                st.metric("Scanner", combo_data['scanner'])
                st.metric("Strategy", combo_data['strategy'])
                st.metric("Return", f"{combo_data['return_pct']:.2f}%")
                st.metric("P&L", f"${combo_data['final_pnl']:,.2f}")
                st.metric("Win Rate", f"{combo_data['win_rate']:.1f}%")
                st.metric("Trades", combo_data['total_trades'])

# Tab 3: Weekly Data
with tab3:
    st.markdown("### 📋 Weekly Performance Data")

    # Combo selector
    combo_options = {
        f"{c['scanner']} + {c['strategy']}": name
        for name, c in data['combinations'].items()
    }

    selected_combo = st.selectbox(
        "Select combination to view weekly data",
        list(combo_options.keys())
    )

    if selected_combo:
        combo_name = combo_options[selected_combo]
        combo_data = data['combinations'][combo_name]

        # Show summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Final Return", f"{combo_data['return_pct']:.2f}%")
        col2.metric("Total P&L", f"${combo_data['final_pnl']:,.2f}")
        col3.metric("Total Trades", combo_data['total_trades'])
        col4.metric("Win Rate", f"{combo_data['win_rate']:.1f}%")

        st.markdown("---")

        # Create weekly dataframe
        if 'weekly_pnl' in combo_data and combo_data['weekly_pnl']:
            weekly_df = pd.DataFrame({
                'Week': range(1, len(combo_data['weekly_pnl']) + 1),
                'Weekly P&L': combo_data['weekly_pnl'],
                'Cumulative P&L': combo_data['cumulative_pnl'],
            })

            # Format
            weekly_df['Weekly P&L'] = weekly_df['Weekly P&L'].apply(lambda x: f"${x:,.2f}")
            weekly_df['Cumulative P&L'] = weekly_df['Cumulative P&L'].apply(lambda x: f"${x:,.2f}")

            # Display with pagination
            st.dataframe(weekly_df, use_container_width=True, hide_index=True, height=600)

            # Download button
            csv = weekly_df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"{selected_combo.replace(' + ', '_')}_weekly_data.csv",
                mime="text/csv"
            )

# Sidebar
with st.sidebar:
    st.markdown("## 📊 Simulation Info")
    st.markdown(f"**Period:** {data['start_date'][:10]} to {data['end_date'][:10]}")
    st.markdown(f"**Duration:** 3 years ({data['weeks_completed']} weeks)")
    st.markdown(f"**Initial Capital:** $100,000")
    st.markdown(f"**Combinations Tested:** {len(data['combinations'])}")

    st.markdown("---")
    st.markdown("## 🏆 Quick Stats")

    # Best performer
    best = sorted_results[0]
    st.markdown(f"**Best Performer:**")
    st.markdown(f"- {best[1]['scanner']} + {best[1]['strategy']}")
    st.markdown(f"- Return: **{best[1]['return_pct']:.2f}%**")
    st.markdown(f"- P&L: **${best[1]['final_pnl']:,.2f}**")

    # Worst performer
    worst = sorted_results[-1]
    st.markdown(f"\n**Worst Performer:**")
    st.markdown(f"- {worst[1]['scanner']} + {worst[1]['strategy']}")
    st.markdown(f"- Return: **{worst[1]['return_pct']:.2f}%**")
    st.markdown(f"- P&L: **${worst[1]['final_pnl']:,.2f}**")

    st.markdown("---")
    st.markdown("## 🔄 Refresh Data")
    if st.button("Reload Results"):
        st.rerun()
