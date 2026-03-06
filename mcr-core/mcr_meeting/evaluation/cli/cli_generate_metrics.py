# mypy: ignore-errors
import os
from pathlib import Path

from loguru import logger

from mcr_meeting.evaluation.cli.utils import (
    load_metrics_inputs,
    run_metrics_calculation,
)


def main() -> None:
    data_dir = Path(os.environ.get("EVALUATION_DATA_DIR", "data"))
    out_dir = Path(os.environ.get("EVALUATION_OUTPUT_DIR", data_dir / "outputs"))

    ref_dir = data_dir / "inputs" / "reference_transcripts"
    hyp_dir = out_dir / "make_metrics" / "hypothesis_transcripts"
    metrics_dir = out_dir / "make_metrics" / "metrics"

    logger.info("Starting evaluation with data directory: {}", data_dir)
    logger.info("Output directory for metrics: {}", out_dir)

    evaluation_inputs = load_metrics_inputs(ref_dir, hyp_dir)

    run_metrics_calculation(evaluation_inputs, output_dir=metrics_dir)


if __name__ == "__main__":
    main()
