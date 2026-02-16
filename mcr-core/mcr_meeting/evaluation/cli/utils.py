from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_meeting.evaluation.asr_evaluation_pipeline import MetricsPipeline
from mcr_meeting.evaluation.eval_types import (
    EvaluationInput,
    MetricsPipelineInput,
    TranscriptionOutput,
)

SUPPORTED_AUDIO_FORMATS = ("mp3", "wav")


def load_audio_inputs(audio_dir: Path, ref_dir: Path) -> list[EvaluationInput]:
    evaluation_inputs = []
    audio_files = [
        f for fmt in SUPPORTED_AUDIO_FORMATS for f in audio_dir.glob(f"*.{fmt}")
    ]
    for audio_file in audio_files:
        uid = audio_file.stem
        ref_path = ref_dir / f"{uid}.json"
        if not ref_path.exists():
            logger.warning("Missing reference for {}, skipping.", uid)
            continue

        try:
            reference = TranscriptionOutput.model_validate_json(ref_path.read_text())
        except Exception as e:
            logger.warning("Error parsing reference for {}: {}, skipping.", uid, e)
            continue
        evaluation_inputs.append(
            EvaluationInput(
                uid=uid,
                audio_path=audio_file,
                audio_bytes=BytesIO(audio_file.read_bytes()),
                reference_transcription=reference,
            )
        )
    return evaluation_inputs


def load_hypothesis_inputs(
    ref_dir: Path, hyp_dir: Path, audio_dir: Path
) -> list[MetricsPipelineInput]:
    metrics_pipeline_inputs = []
    for reference_transcript in ref_dir.glob("*.json"):
        uid = reference_transcript.stem
        hypothese_transcript_path = hyp_dir / f"{uid}.json"
        audio_path = audio_dir / f"{uid}.mp3"

        if not hypothese_transcript_path.exists():
            logger.warning("Missing hypothesis transcript for {}, skipping.", uid)
            continue

        reference = TranscriptionOutput.model_validate_json(
            reference_transcript.read_text()
        )
        generated = TranscriptionOutput.model_validate_json(
            hypothese_transcript_path.read_text()
        )

        metrics_pipeline_inputs.append(
            MetricsPipelineInput(
                uid=uid,
                audio_path=audio_path,
                audio_bytes=BytesIO(audio_path.read_bytes())
                if audio_path.exists()
                else BytesIO(b""),
                reference_transcription=reference,
                generated_transcription=generated,
            )
        )
    return metrics_pipeline_inputs


def run_evaluation(
    metrics_pipeline_inputs: list[MetricsPipelineInput], output_dir: Path
) -> None:
    if not metrics_pipeline_inputs:
        logger.error("No evaluation inputs found → nothing to do.")
        exit(1)

    pipeline = MetricsPipeline()
    summary = pipeline.calculate_and_save_metrics(
        metrics_pipeline_inputs=metrics_pipeline_inputs, output_dir=output_dir
    )
    logger.info("\n=== Evaluation Metrics ===")
    logger.info("\n=== Averages ===")
    logger.info("SUMMARY DETAILS   : {}", summary)
