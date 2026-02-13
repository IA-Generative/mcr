# mypy: ignore-errors
import os
from pathlib import Path

from faster_whisper import WhisperModel  # type: ignore[import]
from loguru import logger

from mcr_meeting.evaluation.asr_evaluation_pipeline import ASREvaluationPipeline
from mcr_meeting.evaluation.cli.utils import load_audio_inputs


def main() -> None:
    data_dir = Path(os.environ.get("EVALUATION_DATA_DIR", "data"))
    out_dir = Path(os.environ.get("EVALUATION_OUTPUT_DIR", data_dir / "outputs"))
    model_name = os.environ.get("MODEL", "tiny")

    audio_dir = data_dir / "inputs" / "raw_audios"
    ref_dir = data_dir / "inputs" / "reference_transcripts"

    logger.info("Starting evaluation with data directory: {}", data_dir)
    logger.info("Output directory for metrics: {}", out_dir)
    logger.info("AUDIO DIRECTORY: {}", audio_dir)

    evaluation_inputs = load_audio_inputs(audio_dir, ref_dir)

    if not evaluation_inputs:
        logger.error("No audio files → nothing to do.")
        exit(1)

    model = WhisperModel(model_name)
    pipeline = ASREvaluationPipeline(inputs=evaluation_inputs, model=model)
    summary = pipeline.run_evaluation(output_dir=out_dir)

    logger.info("\n=== Evaluation Metrics ===")
    logger.info("\n=== Averages ===")
    logger.info("SUMMARY DETAILS   : {}", summary)


if __name__ == "__main__":
    main()
