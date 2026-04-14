"""Evaluate the STT pipeline on acronym recognition.

For each audio in the `data/acronymes/audio/` dataset, this script:
1. generates a transcription via ``SpeechToTextPipeline``,
2. saves it as ``{timestamp}_{uid}.json`` (same convention as the existing
   evaluation pipeline, via ``ResultsManager``),
3. normalizes the text with ``french_text_normalizer`` (same function used by
   ``MetricsCalculator`` on the hypothesis side),
4. counts occurrences of the 20 expected acronyms via regex,
5. computes TP/FP/FN/precision/recall for that audio.

Once all audios are processed, results are aggregated (micro-average) and two
summary files are written:
- ``{timestamp}_acronymes_results.csv`` — per-audio detail
- ``{timestamp}_acronymes_summary.json`` — global summary + detail

Usage::

    uv run mcr-core/mcr_meeting/evaluation/acronymes/evaluation_script.py
"""

import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_meeting.app.configs.base import EvaluationSettings
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline
from mcr_meeting.evaluation.acronymes.constants import ACRONYMES
from mcr_meeting.evaluation.acronymes.utils import (
    build_summary,
    compute_audio_metrics,
    evaluate_acronyms,
    save_acronym_results_csv,
    save_acronym_summary_json,
)
from mcr_meeting.evaluation.asr.types import TranscriptionOutput
from mcr_meeting.evaluation.utils import ResultsManager
from mcr_meeting.evaluation.utils.text_normalization import french_text_normalizer

# Paths resolved relative to this file so they don't depend on the cwd.
THIS_FILE = Path(__file__).resolve()
EVALUATION_DIR = THIS_FILE.parent.parent
AUDIO_DIR = EVALUATION_DIR / "data" / "acronymes" / "audio"
OUTPUT_DIR = EVALUATION_DIR / "data" / "outputs" / "acronymes_outputs"


def discover_audio_files(audio_dir: Path) -> list[Path]:
    """Discover audio files in the acronym dataset (same formats as ``cli/utils.py``)."""
    supported_formats = EvaluationSettings().SUPPORTED_AUDIO_FORMATS
    return sorted(f for fmt in supported_formats for f in audio_dir.glob(f"*.{fmt}"))


def process_single_audio(
    audio_path: Path,
    pipeline: SpeechToTextPipeline,
    results_manager: ResultsManager,
    timestamp: str,
) -> tuple[str, dict[str, int]] | None:
    """Process a single audio: STT, save, normalize, count acronyms.

    Returns ``(uid, counts)`` on success, or ``None`` if the audio failed
    (the error is logged but does not stop the overall run, same as
    ``ASREvaluationPipeline.process_single_sample``).
    """
    uid = audio_path.stem
    try:
        logger.info("Processing acronym sample {}...", uid)
        audio_bytes = BytesIO(audio_path.read_bytes())

        segments = pipeline.run(audio_bytes)
        transcription = TranscriptionOutput(segments=segments)
        logger.info(
            "Generated transcription for {}: {}...",
            uid,
            transcription.text[:80],
        )

        # Save as {timestamp}_{uid}.json — same function as the existing
        # evaluation pipeline.
        results_manager.save_generated_transcription(transcription, uid, timestamp)

        # Same normalization used on the hypothesis side for WER/CER
        # (see metrics_calculator.py:43-45).
        normalized_text = french_text_normalizer(
            transcription.text, remove_repetitions=False
        )

        counts = evaluate_acronyms(normalized_text)
        metrics = compute_audio_metrics(counts)
        logger.info(
            "Sample {} -> TP={}, FP={}, FN={}, precision={:.3f}, recall={:.3f}",
            uid,
            metrics.tp,
            metrics.fp,
            metrics.fn,
            metrics.precision,
            metrics.recall,
        )
        for acronym in ACRONYMES:
            count = counts[acronym]
            if count != 1:
                logger.debug("  {} -> count={}", acronym, count)
        return uid, counts
    except Exception as e:
        logger.exception(
            "Error processing {}. Skipping the evaluation for this sample. "
            "The error raised is: {}",
            uid,
            str(e),
        )
        return None


def main() -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logger.info("Starting acronym evaluation. Timestamp: {}", timestamp)
    logger.info("Audio dir : {}", AUDIO_DIR)
    logger.info("Output dir: {}", OUTPUT_DIR)

    if not AUDIO_DIR.exists():
        logger.error("Audio directory does not exist: {}", AUDIO_DIR)
        sys.exit(1)

    audio_files = discover_audio_files(AUDIO_DIR)
    if not audio_files:
        logger.error("No audio files found in {}", AUDIO_DIR)
        sys.exit(1)
    logger.info("Discovered {} audio files.", len(audio_files))

    pipeline = SpeechToTextPipeline()
    results_manager = ResultsManager(OUTPUT_DIR, dev=True)

    per_audio_counts: dict[str, dict[str, int]] = {}
    for audio_file in audio_files:
        result = process_single_audio(audio_file, pipeline, results_manager, timestamp)
        if result is not None:
            uid, counts = result
            per_audio_counts[uid] = counts

    if not per_audio_counts:
        logger.error("No audio files were successfully processed.")
        sys.exit(1)

    csv_path = save_acronym_results_csv(per_audio_counts, OUTPUT_DIR, timestamp)
    logger.info("Saved per-audio results CSV to: {}", csv_path)

    summary = build_summary(per_audio_counts)
    summary_path = save_acronym_summary_json(summary, OUTPUT_DIR, timestamp)
    logger.info("Saved summary JSON to: {}", summary_path)

    logger.info("=== Acronym Evaluation Summary ===")
    logger.info("Total files     : {}", summary.total_files)
    logger.info(
        "Global TP/FP/FN : {}/{}/{}",
        summary.global_metrics.tp,
        summary.global_metrics.fp,
        summary.global_metrics.fn,
    )
    logger.info("Global precision: {:.3f}", summary.global_metrics.precision)
    logger.info("Global recall   : {:.3f}", summary.global_metrics.recall)


if __name__ == "__main__":
    main()
