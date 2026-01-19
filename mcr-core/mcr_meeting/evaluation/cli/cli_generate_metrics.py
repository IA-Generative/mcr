import os
from pathlib import Path

from loguru import logger

from mcr_meeting.evaluation.cli.utils import (
    load_audio_inputs,
    load_hypothesis_inputs,
    run_evaluation,
)


def main() -> None:
    data_dir = Path(os.environ.get("EVALUATION_DATA_DIR", "data"))
    out_dir = Path(os.environ.get("EVALUATION_OUTPUT_DIR", data_dir / "outputs"))

    audio_dir = data_dir / "inputs" / "raw_audios"

    ref_dir = data_dir / "inputs" / "reference_transcripts"
    hyp_dir = out_dir / "hypothesis_transcripts"
    metrics_dir = out_dir / "metrics"
    logger.info("Starting evaluation with data directory: {}", data_dir)
    logger.info("Output directory for metrics: {}", out_dir)

    evaluation_inputs = []

    evaluation_inputs.extend(load_audio_inputs(audio_dir, ref_dir))
    evaluation_inputs.extend(load_hypothesis_inputs(ref_dir, hyp_dir, audio_dir))

    run_evaluation(evaluation_inputs, output_dir=metrics_dir)


if __name__ == "__main__":
    main()
