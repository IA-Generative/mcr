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


def display_results_table(df: pd.DataFrame) -> None:
    """Display the raw results in a table."""
    st.subheader("Detailed Results")
    st.dataframe(df, use_container_width=True)


def display_baseline_comparison(df: pd.DataFrame, baseline_df: pd.DataFrame) -> None:
    """Display comparison between current data and baseline."""
    st.subheader("Baseline Comparison")

    # Metrics comparison
    col1, col2, col3 = st.columns(3)

    metrics = {
        "WER": "wer",
        "CER": "cer",
        "DER": "diarization_error_rate",
    }

    for col, (label, col_name) in zip([col1, col2, col3], metrics.items()):
        current_val = df[col_name].mean()
        baseline_val = baseline_df[col_name].mean()
        delta = current_val - baseline_val
        # Lower is better for error rates
        col.metric(
            label, f"{current_val:.4f}", delta=f"{delta:.4f}", delta_color="inverse"
        )

    # Comparison Plot
    st.write("### Side-by-side Comparison")
    metric_to_compare = st.selectbox(
        "Select metric to compare",
        list(metrics.values()),
        key="comparison_metric_select",
    )

    # Prepare data for Plotly
    df_plot = df[[metric_to_compare]].copy()
    df_plot["Type"] = "Selected"

    baseline_plot = baseline_df[[metric_to_compare]].copy()
    baseline_plot["Type"] = "Baseline"

    combined_df = pd.concat([df_plot, baseline_plot], axis=0)

    fig = px.histogram(
        combined_df,
        x=metric_to_compare,
        color="Type",
        barmode="overlay",
        marginal="box",  # Keeps a small box plot on top for distribution summary
        title=f"Comparison of {metric_to_compare.upper()}",
        template="plotly_white",
        color_discrete_map={"Selected": "#636EFA", "Baseline": "#EF553B"},
        opacity=0.75,
        nbins=20,
    )
    st.plotly_chart(fig, use_container_width=True)
