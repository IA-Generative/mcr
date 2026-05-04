"""Entry point for the offline report evaluation runner.

Usage:
    uv run python -m mcr_generation.evaluation.cli.cli [--limit N]
"""

import os

# The eval runner does not need traces; it produces a local CSV.
# Users wanting traces can override this env var.
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "False")

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

from loguru import logger  # noqa: E402

from mcr_generation.evaluation.pipeline.evaluation_pipeline import (  # noqa: E402
    ReportEvaluationPipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline evaluation runner for MCR generated reports."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N items (useful for smoke tests).",
    )
    args = parser.parse_args()

    data_dir = Path(
        os.environ.get("EVALUATION_DATA_DIR", "mcr_generation/evaluation/data")
    )
    output_dir = Path(
        os.environ.get("EVALUATION_OUTPUT_DIR", str(data_dir / "outputs"))
    )

    logger.info("Data directory: {}", data_dir)
    logger.info("Output directory: {}", output_dir)

    pipeline = ReportEvaluationPipeline(data_dir=data_dir, output_dir=output_dir)
    summary = pipeline.run(limit=args.limit)
    logger.info(
        "Run {} done — {}/{} succeeded, overall mean: {}",
        summary.run_id,
        summary.n_items_succeeded,
        summary.n_items_total,
        summary.overall_mean,
    )


if __name__ == "__main__":
    main()
