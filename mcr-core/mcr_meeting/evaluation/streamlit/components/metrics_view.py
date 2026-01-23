import pandas as pd
import plotly.express as px
import streamlit as st


def display_metrics_summary(df: pd.DataFrame) -> None:
    """Display a summary of metrics using Streamlit metrics cards."""
    st.subheader("Summary Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Mean WER", f"{df['wer'].mean():.4f}")
    with col2:
        st.metric("Mean CER", f"{df['cer'].mean():.4f}")
    with col3:
        st.metric("Mean DER", f"{df['diarization_error_rate'].mean():.4f}")
    with col4:
        st.metric("Total Files", len(df))


def display_metrics_charts(df: pd.DataFrame) -> None:
    """Display charts for the metrics."""
    st.subheader("Visualizations")

    metric_to_plot = st.selectbox(
        "Select metric to visualize",
        [
            "wer",
            "cer",
            "diarization_error_rate",
            "diarization_coverage",
            "diarization_completeness",
        ],
    )

    fig = px.histogram(
        df,
        x=metric_to_plot,
        nbins=20,
        title=f"Distribution of {metric_to_plot.upper()}",
        labels={metric_to_plot: metric_to_plot.upper()},
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Box plot for comparisons if needed
    fig_box = px.box(
        df,
        y=metric_to_plot,
        points="all",
        title=f"Box Plot of {metric_to_plot.upper()}",
        template="plotly_white",
    )
    st.plotly_chart(fig_box, use_container_width=True)


def display_results_table(df: pd.DataFrame) -> None:
    """Display the raw results in a table."""
    st.subheader("Detailed Results")
    st.dataframe(df, use_container_width=True)
