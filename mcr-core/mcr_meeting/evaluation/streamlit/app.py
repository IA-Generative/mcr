import streamlit as st

from mcr_meeting.evaluation.streamlit.components.metrics_view import (
    display_metrics_charts,
    display_metrics_summary,
    display_results_table,
)
from mcr_meeting.evaluation.streamlit.services.eval_s3_service import EvalS3Service

# Page configuration
st.set_page_config(page_title="MCR Evaluation Dashboard", page_icon="📊", layout="wide")


def main() -> None:
    st.title("📊 MCR Evaluation Dashboard")
    st.markdown("---")

    # Initialize service
    eval_service = EvalS3Service()

    # Sidebar for data selection
    st.sidebar.header("Data Selection")

    with st.sidebar:
        if st.button("🔄 Refresh Data"):
            st.rerun()

        # S3 Configuration
        s3_bucket = st.text_input("S3 Bucket", value="mirai-mcr-data")
        s3_prefix = st.text_input("S3 Prefix", value="evaluation")

        results_files = eval_service.list_evaluation_results(
            bucket=s3_bucket, prefix=s3_prefix
        )

        if not results_files:
            st.warning(f"No evaluation results found in s3://{s3_bucket}/{s3_prefix}")
            return

        selected_file = st.selectbox(
            "Select Evaluation Result",
            options=results_files,
            format_func=lambda x: x.split("/")[-1],
        )

    if selected_file:
        with st.spinner(f"Downloading {selected_file}..."):
            df = eval_service.download_csv_as_df(selected_file, bucket=s3_bucket)

        if df is not None:
            # Main content
            display_metrics_summary(df)
            st.markdown("---")

            # Interactive charts
            display_metrics_charts(df)
            st.markdown("---")

            # Raw data table
            display_results_table(df)
        else:
            st.error(f"Failed to load data from {selected_file}")


if __name__ == "__main__":
    main()
