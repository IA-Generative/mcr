import os
from functools import partial
from pathlib import Path

from loguru import logger

from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.speech_to_text_models import (
    get_diarization_pipeline,
    get_transcription_model,
)
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.use_cases.transcription.run_speech_to_text import (
    run_speech_to_text,
)
from mcr_meeting.evaluation.asr.evaluation_pipeline import ASREvaluationPipeline
from mcr_meeting.evaluation.cli.utils import load_evaluation_inputs


def main() -> None:
    data_dir = Path(os.environ.get("EVALUATION_DATA_DIR", "data"))
    out_dir = Path(os.environ.get("EVALUATION_OUTPUT_DIR", data_dir / "outputs"))

    audio_dir = data_dir / "inputs" / "raw_audios"
    ref_dir = data_dir / "inputs" / "reference_transcripts"

    logger.info("Starting evaluation with data directory: {}", data_dir)
    logger.info("Output directory for metrics: {}", out_dir)
    logger.info("AUDIO DIRECTORY: {}", audio_dir)

    evaluation_inputs = load_evaluation_inputs(audio_dir, ref_dir)

    if not evaluation_inputs:
        logger.error("No audio files → nothing to do.")
        exit(1)

    pipeline = ASREvaluationPipeline(
        inputs=evaluation_inputs,
        transcribe_audio=partial(
            run_speech_to_text,
            diarization_processor=DiarizationProcessor(get_diarization_pipeline),
            transcription_processor=TranscriptionProcessor(get_transcription_model),
        ),
    )
    summary = pipeline.run_evaluation(output_dir=out_dir)

    logger.info("\n=== Evaluation Metrics ===")
    logger.info("\n=== Averages ===")
    logger.info("SUMMARY DETAILS   : {}", summary)


if __name__ == "__main__":
    main()
