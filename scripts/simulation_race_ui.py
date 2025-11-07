"""
Simulation Race UI

Interactive dashboard to visualize the simulation race results.
Shows performance of all scanner+strategy combinations over time.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="GamblerAI Simulation Race",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better visuals
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
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)


class SimulationRaceUI:
    """Interactive UI for simulation race results."""

    def __init__(self, results_dir: str = "simulation_results"):
        """Initialize UI with results directory."""
        self.results_dir = Path(results_dir)
        self.data = None
        self.weekly_data = None

    def load_data(self):
        """Load simulation results."""
        all_results_file = self.results_dir / "all_results.json"

        if not all_results_file.exists():
            st.error(f"No results found at {all_results_file}")
            st.info("Please run the simulation first: `python scripts/simulation_race_engine.py`")
            return False

        with open(all_results_file, 'r') as f:
            self.data = json.load(f)

        # Load detailed weekly data for each combination
        self.weekly_data = {}
        for combo_name in self.data['combinations'].keys():
            combo_file = self.results_dir / f"{combo_name}.json"
            if combo_file.exists():
                with open(combo_file, 'r') as f:
                    self.weekly_data[combo_name] = json.load(f)

        return True

    def render(self):
        """Render the main UI."""

        # Header
        st.markdown('<div class="main-header">🏁 GamblerAI Simulation Race 🏁</div>', unsafe_allow_html=True)

        if not self.load_data():
            return

        # Sidebar filters
        self._render_sidebar()

        # Main content
        tab1, tab2, tab3, tab4 = st.tabs([
            "🏁 Race View",
            "📊 Leaderboard",
            "📈 Performance Charts",
            "🔍 Detailed Analysis"
        ])

        with tab1:
            self._render_race_view()

        with tab2:
            self._render_leaderboard()

        with tab3:
            self._render_performance_charts()

        with tab4:
            self._render_detailed_analysis()

    def _render_sidebar(self):
        """Render sidebar with filters and info."""
        st.sidebar.title("🎯 Filters & Controls")

        # Simulation info
        st.sidebar.markdown("### Simulation Info")
        st.sidebar.metric("Start Date", self.data['start_date'][:10])
        st.sidebar.metric("End Date", self.data['end_date'][:10])
        st.sidebar.metric("Initial Capital", f"${self.data['initial_capital']:,.0f}")
        st.sidebar.metric("Total Weeks", self.data['total_weeks'])
        st.sidebar.metric("Combinations", len(self.data['combinations']))

        st.sidebar.markdown("---")

        # Filters
        st.sidebar.markdown("### Filter Combinations")

        # Scanner filter
        all_scanners = sorted(set(c['scanner_type'] for c in self.data['combinations'].values()))
        selected_scanners = st.sidebar.multiselect(
            "Stock Scanners",
            all_scanners,
            default=all_scanners
        )

        # Strategy filter
        all_strategies = sorted(set(c['strategy_name'] for c in self.data['combinations'].values()))
        selected_strategies = st.sidebar.multiselect(
            "Trading Strategies",
            all_strategies,
            default=all_strategies
        )

        # Store in session state
        st.session_state['selected_scanners'] = selected_scanners
        st.session_state['selected_strategies'] = selected_strategies

        st.sidebar.markdown("---")

        # Display controls
        st.sidebar.markdown("### Display Controls")
        st.session_state['show_top_n'] = st.sidebar.slider(
            "Show Top N Combinations",
            min_value=5,
            max_value=40,
            value=10,
            step=5
        )

        st.session_state['animation_speed'] = st.sidebar.slider(
            "Animation Speed (ms per week)",
            min_value=50,
            max_value=500,
            value=200,
            step=50
        )

    def _get_filtered_combinations(self):
        """Get combinations matching current filters."""
        selected_scanners = st.session_state.get('selected_scanners', [])
        selected_strategies = st.session_state.get('selected_strategies', [])

        filtered = {}
        for name, combo in self.data['combinations'].items():
            if (not selected_scanners or combo['scanner_type'] in selected_scanners) and \
               (not selected_strategies or combo['strategy_name'] in selected_strategies):
                filtered[name] = combo

        return filtered

    def _render_race_view(self):
        """Render the animated race view."""
        st.markdown("## 🏁 Performance Race Over Time")
        st.markdown("Watch how different scanner+strategy combinations perform week by week!")

        filtered_combos = self._get_filtered_combinations()

        if not filtered_combos:
            st.warning("No combinations match the current filters.")
            return

        # Sort by final return and get top N
        top_n = st.session_state.get('show_top_n', 10)
        sorted_combos = sorted(
            filtered_combos.items(),
            key=lambda x: x[1]['return_pct'],
            reverse=True
        )[:top_n]

        # Create animated race chart
        fig = self._create_race_chart(sorted_combos)
        st.plotly_chart(fig, use_container_width=True)

        # Week selector for static view
        st.markdown("### 📅 View Specific Week")
        max_weeks = self.data['total_weeks']
        selected_week = st.slider("Select Week", 1, max_weeks, max_weeks)

        # Show standings at selected week
        standings_df = self._get_standings_at_week(sorted_combos, selected_week)
        st.dataframe(standings_df, use_container_width=True)

    def _create_race_chart(self, combinations):
        """Create animated race chart using Plotly."""
        # Prepare data for animation
        all_frames = []
        combo_names = [name for name, _ in combinations]

        # Get max weeks
        max_weeks = max(
            len(self.weekly_data[name]['weekly_results'])
            for name, _ in combinations
            if name in self.weekly_data
        )

        # Create frames for each week
        for week in range(1, max_weeks + 1):
            frame_data = []

            for combo_name, combo_info in combinations:
                if combo_name not in self.weekly_data:
                    continue

                weekly_results = self.weekly_data[combo_name]['weekly_results']

                if week <= len(weekly_results):
                    cumulative_pnl = weekly_results[week - 1]['cumulative_pnl']
                else:
                    cumulative_pnl = weekly_results[-1]['cumulative_pnl']

                # Create display name
                display_name = f"{combo_info['scanner_type'][:15]}\n{combo_info['strategy_name']}"

                frame_data.append({
                    'combination': display_name,
                    'cumulative_pnl': cumulative_pnl,
                    'week': week
                })

            frame_df = pd.DataFrame(frame_data)
            frame_df = frame_df.sort_values('cumulative_pnl', ascending=True)

            all_frames.append(frame_df)

        # Create the figure with the last frame
        final_frame = all_frames[-1]

        fig = go.Figure(
            data=[go.Bar(
                x=final_frame['cumulative_pnl'],
                y=final_frame['combination'],
                orientation='h',
                marker=dict(
                    color=final_frame['cumulative_pnl'],
                    colorscale='RdYlGn',
                    showscale=True,
                    cmin=final_frame['cumulative_pnl'].min(),
                    cmax=final_frame['cumulative_pnl'].max(),
                ),
                text=final_frame['cumulative_pnl'].apply(lambda x: f'${x:,.0f}'),
                textposition='outside',
            )]
        )

        # Create frames for animation
        frames = []
        for week, frame_df in enumerate(all_frames, 1):
            frames.append(go.Frame(
                data=[go.Bar(
                    x=frame_df['cumulative_pnl'],
                    y=frame_df['combination'],
                    orientation='h',
                    marker=dict(
                        color=frame_df['cumulative_pnl'],
                        colorscale='RdYlGn',
                        cmin=all_frames[-1]['cumulative_pnl'].min(),
                        cmax=all_frames[-1]['cumulative_pnl'].max(),
                    ),
                    text=frame_df['cumulative_pnl'].apply(lambda x: f'${x:,.0f}'),
                    textposition='outside',
                )],
                name=f'Week {week}',
                layout=go.Layout(title_text=f"Week {week} of {max_weeks}")
            ))

        fig.frames = frames

        # Add animation buttons
        fig.update_layout(
            title=f"Cumulative P&L Race - Week {max_weeks}",
            xaxis_title="Cumulative P&L ($)",
            yaxis_title="Combination",
            height=600,
            updatemenus=[{
                'type': 'buttons',
                'showactive': True,
                'buttons': [
                    {
                        'label': '▶ Play',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': st.session_state.get('animation_speed', 200)},
                            'fromcurrent': True,
                            'mode': 'immediate',
                        }]
                    },
                    {
                        'label': '⏸ Pause',
                        'method': 'animate',
                        'args': [[None], {
                            'frame': {'duration': 0},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }]
                    }
                ],
                'x': 0.1,
                'y': 1.15,
            }],
            sliders=[{
                'active': max_weeks - 1,
                'steps': [
                    {
                        'args': [[f'Week {w}'], {
                            'frame': {'duration': 0},
                            'mode': 'immediate'
                        }],
                        'label': f'W{w}',
                        'method': 'animate'
                    }
                    for w in range(1, max_weeks + 1)
                ],
                'x': 0.1,
                'y': 0,
                'currentvalue': {'prefix': 'Week: '},
            }]
        )

        return fig

    def _get_standings_at_week(self, combinations, week: int):
        """Get standings at a specific week."""
        standings = []

        for combo_name, combo_info in combinations:
            if combo_name not in self.weekly_data:
                continue

            weekly_results = self.weekly_data[combo_name]['weekly_results']

            if week <= len(weekly_results):
                week_data = weekly_results[week - 1]
                standings.append({
                    'Scanner': combo_info['scanner_type'],
                    'Strategy': combo_info['strategy_name'],
                    'Cumulative P&L': f"${week_data['cumulative_pnl']:,.2f}",
                    'Week P&L': f"${week_data['pnl']:,.2f}",
                    'Total Trades': week_data['trades_count'],
                    'Week Win Rate': f"{week_data['win_rate']:.1f}%",
                })

        df = pd.DataFrame(standings)
        return df.sort_values('Cumulative P&L', ascending=False)

    def _render_leaderboard(self):
        """Render leaderboard table."""
        st.markdown("## 🏆 Final Leaderboard")

        filtered_combos = self._get_filtered_combinations()

        # Create leaderboard dataframe
        leaderboard = []
        for name, combo in filtered_combos.items():
            leaderboard.append({
                'Rank': 0,  # Will be filled after sorting
                'Scanner': combo['scanner_type'],
                'Strategy': combo['strategy_name'],
                'Return %': combo['return_pct'],
                'Total P&L': combo['total_pnl'],
                'Final Capital': combo['final_capital'],
                'Trades': combo['total_trades'],
                'Win Rate %': combo['win_rate'],
                'Sharpe Ratio': combo['sharpe_ratio'],
                'Max DD %': combo['max_drawdown'],
            })

        df = pd.DataFrame(leaderboard)
        df = df.sort_values('Return %', ascending=False)
        df['Rank'] = range(1, len(df) + 1)

        # Format columns
        df['Return %'] = df['Return %'].apply(lambda x: f"{x:.2f}%")
        df['Total P&L'] = df['Total P&L'].apply(lambda x: f"${x:,.2f}")
        df['Final Capital'] = df['Final Capital'].apply(lambda x: f"${x:,.2f}")
        df['Win Rate %'] = df['Win Rate %'].apply(lambda x: f"{x:.1f}%")
        df['Sharpe Ratio'] = df['Sharpe Ratio'].apply(lambda x: f"{x:.2f}")
        df['Max DD %'] = df['Max DD %'].apply(lambda x: f"{x:.1f}%")

        # Display with styling
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # Top 3 winners
        st.markdown("### 🥇 Top 3 Winners")
        cols = st.columns(3)

        medals = ['🥇', '🥈', '🥉']
        for i, (col, medal) in enumerate(zip(cols, medals)):
            if i < len(leaderboard):
                winner = sorted(leaderboard, key=lambda x: x['Return %'], reverse=True)[i]
                with col:
                    st.markdown(f"### {medal} Rank {i+1}")
                    st.metric("Scanner", winner['Scanner'])
                    st.metric("Strategy", winner['Strategy'])
                    st.metric("Return", winner['Return %'])
                    st.metric("P&L", winner['Total P&L'])

    def _render_performance_charts(self):
        """Render performance comparison charts."""
        st.markdown("## 📈 Performance Analysis")

        filtered_combos = self._get_filtered_combinations()

        # Create tabs for different chart types
        chart_tab1, chart_tab2, chart_tab3 = st.tabs([
            "Returns Distribution",
            "Risk vs Return",
            "Weekly Performance"
        ])

        with chart_tab1:
            self._render_returns_distribution(filtered_combos)

        with chart_tab2:
            self._render_risk_return_scatter(filtered_combos)

        with chart_tab3:
            self._render_weekly_performance(filtered_combos)

    def _render_returns_distribution(self, combinations):
        """Render returns distribution chart."""
        st.markdown("### 📊 Returns Distribution")

        returns = [c['return_pct'] for c in combinations.values()]

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=returns,
            nbinsx=20,
            marker_color='#667eea',
            opacity=0.75
        ))

        fig.update_layout(
            title="Distribution of Returns Across All Combinations",
            xaxis_title="Return %",
            yaxis_title="Count",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mean Return", f"{np.mean(returns):.2f}%")
        col2.metric("Median Return", f"{np.median(returns):.2f}%")
        col3.metric("Best Return", f"{max(returns):.2f}%")
        col4.metric("Worst Return", f"{min(returns):.2f}%")

    def _render_risk_return_scatter(self, combinations):
        """Render risk vs return scatter plot."""
        st.markdown("### 🎯 Risk vs Return Analysis")

        data = []
        for name, combo in combinations.items():
            data.append({
                'name': f"{combo['scanner_type'][:10]}+{combo['strategy_name'][:10]}",
                'return': combo['return_pct'],
                'risk': combo['max_drawdown'],
                'sharpe': combo['sharpe_ratio'],
                'scanner': combo['scanner_type'],
                'strategy': combo['strategy_name'],
            })

        df = pd.DataFrame(data)

        fig = px.scatter(
            df,
            x='risk',
            y='return',
            size='sharpe',
            color='strategy',
            hover_data=['scanner', 'strategy', 'sharpe'],
            title="Risk (Max Drawdown) vs Return",
            labels={'risk': 'Max Drawdown %', 'return': 'Return %'}
        )

        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    def _render_weekly_performance(self, combinations):
        """Render weekly performance for top combinations."""
        st.markdown("### 📅 Weekly Performance Trends")

        # Get top 5 combinations
        top_combos = sorted(
            combinations.items(),
            key=lambda x: x[1]['return_pct'],
            reverse=True
        )[:5]

        fig = go.Figure()

        for combo_name, combo_info in top_combos:
            if combo_name not in self.weekly_data:
                continue

            weekly_results = self.weekly_data[combo_name]['weekly_results']
            weeks = [w['week_number'] for w in weekly_results]
            cumulative_pnl = [w['cumulative_pnl'] for w in weekly_results]

            display_name = f"{combo_info['scanner_type'][:12]} + {combo_info['strategy_name']}"

            fig.add_trace(go.Scatter(
                x=weeks,
                y=cumulative_pnl,
                mode='lines+markers',
                name=display_name,
                line=dict(width=2),
            ))

        fig.update_layout(
            title="Cumulative P&L Over Time (Top 5 Combinations)",
            xaxis_title="Week",
            yaxis_title="Cumulative P&L ($)",
            height=500,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_detailed_analysis(self):
        """Render detailed analysis section."""
        st.markdown("## 🔍 Detailed Combination Analysis")

        filtered_combos = self._get_filtered_combinations()

        # Combination selector
        combo_options = {
            f"{c['scanner_type']} + {c['strategy_name']}": name
            for name, c in filtered_combos.items()
        }

        selected_display = st.selectbox(
            "Select Combination to Analyze",
            list(combo_options.keys())
        )

        combo_name = combo_options[selected_display]
        combo_info = filtered_combos[combo_name]

        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Return", f"{combo_info['return_pct']:.2f}%")
        col2.metric("Total P&L", f"${combo_info['total_pnl']:,.2f}")
        col3.metric("Win Rate", f"{combo_info['win_rate']:.1f}%")
        col4.metric("Sharpe Ratio", f"{combo_info['sharpe_ratio']:.2f}")
        col5.metric("Max Drawdown", f"{combo_info['max_drawdown']:.1f}%")

        # Weekly details table
        if combo_name in self.weekly_data:
            st.markdown("### 📊 Weekly Performance Details")

            weekly_results = self.weekly_data[combo_name]['weekly_results']
            df = pd.DataFrame(weekly_results)

            # Format columns
            df['pnl'] = df['pnl'].apply(lambda x: f"${x:,.2f}")
            df['cumulative_pnl'] = df['cumulative_pnl'].apply(lambda x: f"${x:,.2f}")
            df['win_rate'] = df['win_rate'].apply(lambda x: f"{x:.1f}%")

            df = df.rename(columns={
                'week_number': 'Week',
                'start_date': 'Start',
                'end_date': 'End',
                'pnl': 'P&L',
                'cumulative_pnl': 'Cumulative P&L',
                'trades_count': 'Trades',
                'win_rate': 'Win Rate'
            })

            st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    """Main entry point."""
    ui = SimulationRaceUI(results_dir="simulation_results")
    ui.render()


if __name__ == "__main__":
    main()
