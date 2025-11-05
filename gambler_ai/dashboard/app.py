"""
Streamlit dashboard for GamblerAI momentum analysis.
"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gambler_ai.analysis import MomentumDetector, PatternAnalyzer, StatisticsEngine
from gambler_ai.data_ingestion import DataValidator
from gambler_ai.utils.config import get_config
from gambler_ai.utils.logging import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="GamblerAI - Momentum Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("📈 GamblerAI - Stock Momentum Analysis Dashboard")
st.markdown("---")


# Sidebar
def render_sidebar():
    """Render sidebar with controls."""
    st.sidebar.title("Controls")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Momentum Events",
            "Pattern Analysis",
            "Predictions",
            "Data Quality",
        ],
    )

    st.sidebar.markdown("---")

    # Common filters
    st.sidebar.subheader("Filters")

    symbol = st.sidebar.text_input("Symbol", value="AAPL").upper()
    timeframe = st.sidebar.selectbox("Timeframe", ["5min", "15min", "1hour", "1day"])

    # Date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    date_range = st.sidebar.date_input(
        "Date Range", value=(start_date, end_date), max_value=datetime.now()
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range[0]
        end_date = datetime.now()

    return page, symbol, timeframe, start_date, end_date


page, symbol, timeframe, start_date, end_date = render_sidebar()


# Page: Overview
if page == "Overview":
    st.header("📊 Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Symbol", symbol)

    with col2:
        st.metric("Timeframe", timeframe)

    with col3:
        st.metric(
            "Date Range",
            f"{(end_date - start_date).days} days",
        )

    with col4:
        st.metric("Status", "Active", delta="Running")

    st.markdown("---")

    # Fetch recent momentum events
    detector = MomentumDetector()

    with st.spinner("Loading momentum events..."):
        events = detector.get_events(
            symbol=symbol,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            timeframe=timeframe,
        )

    if events:
        st.subheader(f"📈 Recent Momentum Events ({len(events)})")

        # Convert to DataFrame
        events_data = []
        for event in events[:50]:  # Limit to 50 most recent
            events_data.append({
                "Start Time": event.start_time,
                "Direction": event.direction,
                "Move %": float(event.max_move_percentage) if event.max_move_percentage else 0,
                "Initial Price": float(event.initial_price) if event.initial_price else 0,
                "Peak Price": float(event.peak_price) if event.peak_price else 0,
                "Continuation (min)": event.continuation_duration_seconds / 60 if event.continuation_duration_seconds else 0,
                "Reversal %": float(event.reversal_percentage) if event.reversal_percentage else None,
            })

        df = pd.DataFrame(events_data)

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            up_events = len([e for e in events if e.direction == "UP"])
            st.metric("UP Events", up_events)

        with col2:
            down_events = len([e for e in events if e.direction == "DOWN"])
            st.metric("DOWN Events", down_events)

        with col3:
            avg_move = df["Move %"].mean()
            st.metric("Avg Move", f"{avg_move:.2f}%")

        with col4:
            avg_cont = df["Continuation (min)"].mean()
            st.metric("Avg Continuation", f"{avg_cont:.1f} min")

        # Chart: Move distribution
        fig = px.histogram(
            df,
            x="Move %",
            color="Direction",
            nbins=30,
            title="Distribution of Price Moves",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Table: Recent events
        st.dataframe(
            df.sort_values("Start Time", ascending=False),
            use_container_width=True,
        )

    else:
        st.info(f"No momentum events found for {symbol} in the selected date range.")


# Page: Momentum Events
elif page == "Momentum Events":
    st.header("🎯 Momentum Events")

    direction_filter = st.selectbox("Direction", ["All", "UP", "DOWN"])

    detector = MomentumDetector()

    with st.spinner("Loading events..."):
        events = detector.get_events(
            symbol=symbol,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            direction=direction_filter if direction_filter != "All" else None,
            timeframe=timeframe,
        )

    if events:
        st.success(f"Found {len(events)} events")

        # Convert to DataFrame
        events_data = []
        for event in events:
            events_data.append({
                "ID": event.id,
                "Start Time": event.start_time,
                "Direction": event.direction,
                "Initial Price": float(event.initial_price) if event.initial_price else 0,
                "Peak Price": float(event.peak_price) if event.peak_price else 0,
                "Move %": float(event.max_move_percentage) if event.max_move_percentage else 0,
                "Duration (min)": event.duration_seconds / 60 if event.duration_seconds else 0,
                "Continuation (min)": event.continuation_duration_seconds / 60 if event.continuation_duration_seconds else 0,
                "Reversal %": float(event.reversal_percentage) if event.reversal_percentage else None,
                "Reversal Time (min)": event.reversal_time_seconds / 60 if event.reversal_time_seconds else None,
            })

        df = pd.DataFrame(events_data)

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            # Scatter plot: Move vs Continuation
            fig = px.scatter(
                df,
                x="Move %",
                y="Continuation (min)",
                color="Direction",
                title="Price Move vs Continuation Duration",
                hover_data=["Start Time"],
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Box plot: Continuation by direction
            fig = px.box(
                df,
                x="Direction",
                y="Continuation (min)",
                title="Continuation Duration by Direction",
            )
            st.plotly_chart(fig, use_container_width=True)

        # Table
        st.dataframe(
            df.sort_values("Start Time", ascending=False),
            use_container_width=True,
        )

    else:
        st.warning("No events found")


# Page: Pattern Analysis
elif page == "Pattern Analysis":
    st.header("🔍 Pattern Analysis")

    analyzer = PatternAnalyzer()

    if st.button("Run Pattern Analysis"):
        with st.spinner("Analyzing patterns..."):
            patterns = analyzer.analyze_patterns(
                symbol=symbol, timeframe=timeframe, min_samples=50
            )

            if patterns:
                analyzer.save_pattern_statistics(patterns)
                st.success(f"Found {len(patterns)} patterns")

                # Convert to DataFrame
                df = pd.DataFrame(patterns)

                # Display metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    total_samples = df["sample_size"].sum()
                    st.metric("Total Samples", total_samples)

                with col2:
                    avg_win_rate = df["win_rate"].mean()
                    st.metric("Avg Win Rate", f"{avg_win_rate:.1%}")

                with col3:
                    avg_confidence = df["confidence_score"].mean()
                    st.metric("Avg Confidence", f"{avg_confidence:.2f}")

                # Charts
                col1, col2 = st.columns(2)

                with col1:
                    # Bar chart: Pattern types
                    pattern_counts = df.groupby("pattern_type")["sample_size"].sum()
                    fig = px.bar(
                        x=pattern_counts.index,
                        y=pattern_counts.values,
                        title="Samples by Pattern Type",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # Bar chart: Win rates by pattern
                    fig = px.bar(
                        df,
                        x="pattern_type",
                        y="win_rate",
                        color="direction",
                        title="Win Rates by Pattern Type",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Table
                st.subheader("Pattern Statistics")
                display_df = df[[
                    "pattern_type",
                    "direction",
                    "sample_size",
                    "avg_continuation_duration",
                    "avg_reversal_percentage",
                    "win_rate",
                    "confidence_score",
                ]]
                st.dataframe(display_df, use_container_width=True)

            else:
                st.warning("No patterns found. Try collecting more data.")

    # Show existing patterns
    st.markdown("---")
    st.subheader("Saved Pattern Statistics")

    patterns = analyzer.get_pattern_statistics(timeframe=timeframe)

    if patterns:
        patterns_data = []
        for p in patterns:
            patterns_data.append({
                "Pattern Type": p.pattern_type,
                "Direction": p.direction,
                "Samples": p.sample_size,
                "Avg Continuation (s)": p.avg_continuation_duration,
                "Avg Reversal %": float(p.avg_reversal_percentage) if p.avg_reversal_percentage else None,
                "Win Rate": float(p.win_rate) if p.win_rate else None,
                "Confidence": float(p.confidence_score) if p.confidence_score else None,
            })

        df = pd.DataFrame(patterns_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No saved patterns. Run pattern analysis first.")


# Page: Predictions
elif page == "Predictions":
    st.header("🎯 Momentum Predictions")

    st.subheader("Predict Continuation Probability")

    col1, col2 = st.columns(2)

    with col1:
        move_pct = st.number_input("Initial Move %", value=2.5, min_value=0.1, max_value=50.0, step=0.1)
        volume_ratio = st.number_input("Volume Ratio", value=2.0, min_value=0.1, max_value=10.0, step=0.1)

    with col2:
        direction = st.selectbox("Direction", ["UP", "DOWN", "Auto"])
        entry_price = st.number_input("Entry Price", value=100.0, min_value=0.01, step=0.01)

    if st.button("Generate Prediction"):
        with st.spinner("Calculating prediction..."):
            engine = StatisticsEngine()

            prediction = engine.predict_continuation(
                symbol=symbol,
                initial_move_pct=move_pct,
                volume_ratio=volume_ratio,
                timeframe=timeframe,
                direction=direction if direction != "Auto" else None,
            )

            if "error" in prediction:
                st.error(prediction["error"])
            else:
                st.success("Prediction generated!")

                # Display metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Continuation Probability",
                        f"{prediction['continuation_probability']:.0%}",
                    )

                with col2:
                    st.metric(
                        "Expected Continuation",
                        f"{prediction.get('expected_continuation_minutes', 0):.1f} min",
                    )

                with col3:
                    st.metric(
                        "Expected Reversal",
                        f"{prediction.get('expected_reversal_pct', 0):.2f}%",
                    )

                with col4:
                    confidence = prediction['confidence']
                    st.metric("Confidence", f"{confidence:.0%}")

                # Recommendation
                recommendation = prediction['recommendation']
                if recommendation == "STRONG_ENTER":
                    st.success(f"✅ Recommendation: **{recommendation}**")
                elif recommendation == "ENTER":
                    st.info(f"👍 Recommendation: **{recommendation}**")
                elif recommendation == "WAIT":
                    st.warning(f"⏳ Recommendation: **{recommendation}**")
                else:
                    st.error(f"❌ Recommendation: **{recommendation}**")

                # Risk/Reward calculation
                st.markdown("---")
                st.subheader("Risk/Reward Analysis")

                stop_loss_pct = st.slider("Stop Loss %", 0.5, 5.0, 1.0, 0.1)

                rr = engine.calculate_risk_reward(
                    entry_price=entry_price,
                    expected_continuation_pct=prediction.get('expected_continuation_minutes', 0) * 0.1,  # Rough estimate
                    expected_reversal_pct=prediction.get('expected_reversal_pct', 0),
                    stop_loss_pct=stop_loss_pct,
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Target Price", f"${rr['target_price']:.2f}")
                    st.metric("Potential Gain", f"${rr['potential_gain']:.2f}")

                with col2:
                    st.metric("Stop Loss", f"${rr['stop_loss_price']:.2f}")
                    st.metric("Potential Loss", f"${rr['potential_loss']:.2f}")

                with col3:
                    st.metric("R:R Ratio", f"{rr['risk_reward_ratio']:.2f}")


# Page: Data Quality
elif page == "Data Quality":
    st.header("✅ Data Quality")

    if st.button("Run Data Validation"):
        with st.spinner("Validating data..."):
            validator = DataValidator()

            results = validator.validate_data(
                symbol=symbol,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time()),
                timeframe=timeframe,
            )

            validator.log_quality_check(results)

            # Display results
            quality_score = results["quality_score"]

            if quality_score >= 0.9:
                st.success(f"Quality Score: {quality_score:.1%} - Excellent")
            elif quality_score >= 0.7:
                st.info(f"Quality Score: {quality_score:.1%} - Good")
            elif quality_score >= 0.5:
                st.warning(f"Quality Score: {quality_score:.1%} - Fair")
            else:
                st.error(f"Quality Score: {quality_score:.1%} - Poor")

            # Metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Expected Periods", results["total_expected"])

            with col2:
                st.metric("Actual Periods", results["total_actual"])

            with col3:
                st.metric("Missing Periods", results["missing_periods"])

            # Issues
            if results["issues"]:
                st.subheader("Issues Found")
                for issue in results["issues"]:
                    st.warning(issue)
            else:
                st.success("No issues found!")


# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>GamblerAI Dashboard v0.1.0 | Built with Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True,
)
