from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_meeting.evaluation.asr_evaluation_pipeline import MetricsPipeline
from mcr_meeting.evaluation.eval_types import EvaluationInput, TranscriptionOutput


def load_audio_inputs(audio_dir: Path, ref_dir: Path) -> list[EvaluationInput]:
    evaluation_inputs = []
    for audio_file in audio_dir.glob("*.mp3"):
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
                generated_transcription=None,
            )
        )
    return evaluation_inputs


def load_hypothesis_inputs(
    ref_dir: Path, hyp_dir: Path, audio_dir: Path
) -> list[EvaluationInput]:
    evaluation_inputs = []
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

        evaluation_inputs.append(
            EvaluationInput(
                uid=uid,
                audio_path=audio_path,
                audio_bytes=BytesIO(audio_path.read_bytes())
                if audio_path.exists()
                else BytesIO(b""),
                reference_transcription=reference,
                generated_transcription=generated,
            )
        )
    return evaluation_inputs


def run_evaluation(evaluation_inputs: list[EvaluationInput], output_dir: Path) -> None:
    if not evaluation_inputs:
        logger.error("No evaluation inputs found → nothing to do.")
        exit(1)

    pipeline = MetricsPipeline()
    summary = pipeline.calculate_and_save_metrics(
        evaluation_inputs=evaluation_inputs, output_dir=output_dir
    )
    logger.info("\n=== Evaluation Metrics ===")
    logger.info("\n=== Averages ===")
    logger.info("SUMMARY DETAILS   : {}", summary)
