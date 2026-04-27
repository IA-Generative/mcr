"""Evaluate the STT pipeline on acronym recognition.

For each audio in the `data/acronyms/audio/` dataset, this script:
1. generates a transcription via ``SpeechToTextPipeline``,
2. saves it as ``{timestamp}_{uid}.json`` (same convention as the existing
   evaluation pipeline, via ``ResultsManager``),
3. normalizes the text with ``french_text_normalizer`` (same function used by
   ``MetricsCalculator`` on the hypothesis side),
4. counts occurrences of the glossary acronyms via regex,
5. compares against the per-audio reference file (expected counts) to compute
   TP/FP/TN/FN + precision/recall/accuracy as a binary classification over the
   full glossary.

Once all audios are processed, results are aggregated (micro-average) and two
summary files are written:
- ``{timestamp}_acronyms_results.csv`` — per-audio detail
- ``{timestamp}_acronyms_summary.json`` — global summary + detail

Usage::

    uv run mcr-core/mcr_meeting/evaluation/acronyms/evaluation_script.py
"""

import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_meeting.app.configs.base import EvaluationSettings
from mcr_meeting.app.services.speech_to_text.speech_to_text import SpeechToTextPipeline
from mcr_meeting.evaluation.acronyms.loaders import (
    load_audio_reference,
    load_glossary,
)
from mcr_meeting.evaluation.acronyms.utils import (
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
DATA_DIR = EVALUATION_DIR / "data" / "acronyms"
AUDIO_DIR = DATA_DIR / "audio"
REFERENCE_DIR = DATA_DIR / "references"
GLOSSARY_PATH = DATA_DIR / "in_glossary.json"
NOT_IN_GLOSSARY_PATH = DATA_DIR / "not_in_glossary.json"
NOT_EVALUATED_PATH = DATA_DIR / "acronyms_not_evaluated.json"
OUTPUT_DIR = EVALUATION_DIR / "data" / "outputs" / "acronyms_outputs"


def discover_audio_files(audio_dir: Path) -> list[Path]:
    """Discover audio files in the acronym dataset (same formats as ``cli/utils.py``)."""
    supported_formats = EvaluationSettings().SUPPORTED_AUDIO_FORMATS
    return sorted(f for fmt in supported_formats for f in audio_dir.glob(f"*.{fmt}"))


def process_single_audio(
    audio_path: Path,
    reference_dir: Path,
    glossary: list[str],
    pipeline: SpeechToTextPipeline,
    results_manager: ResultsManager,
    timestamp: str,
) -> tuple[str, dict[str, int], dict[str, int]] | None:
    """Process a single audio: STT, save, normalize, count acronyms.

    Returns ``(uid, expected, predicted)`` on success, or ``None`` if the audio
    failed or its reference file is missing (logged, does not stop the run).
    """
    uid = audio_path.stem
    reference_path = reference_dir / f"{uid}.json"
    if not reference_path.exists():
        logger.warning("Missing reference for {}, skipping.", uid)
        return None

    try:
        logger.info("Processing acronym sample {}...", uid)
        expected = load_audio_reference(reference_path)

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

        predicted = evaluate_acronyms(normalized_text, glossary)
        metrics = compute_audio_metrics(expected, predicted)
        logger.info(
            "Sample {} -> TP={}, FP={}, TN={}, FN={}, "
            "precision={:.3f}, recall={:.3f}, accuracy={:.3f}",
            uid,
            metrics.tp,
            metrics.fp,
            metrics.tn,
            metrics.fn,
            metrics.precision,
            metrics.recall,
            metrics.accuracy,
        )
        return uid, expected, predicted
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
    logger.info("Audio dir     : {}", AUDIO_DIR)
    logger.info("Reference dir : {}", REFERENCE_DIR)
    logger.info("Glossary path : {}", GLOSSARY_PATH)
    logger.info("Output dir    : {}", OUTPUT_DIR)

    if not AUDIO_DIR.exists():
        logger.error("Audio directory does not exist: {}", AUDIO_DIR)
        sys.exit(1)
    if not GLOSSARY_PATH.exists():
        logger.error("Glossary file does not exist: {}", GLOSSARY_PATH)
        sys.exit(1)
    if not REFERENCE_DIR.exists():
        logger.error("Reference directory does not exist: {}", REFERENCE_DIR)
        sys.exit(1)

    glossary = load_glossary(GLOSSARY_PATH)
    if NOT_IN_GLOSSARY_PATH.exists():
        not_in_glossary = load_glossary(NOT_IN_GLOSSARY_PATH)
        glossary = glossary + not_in_glossary
    if NOT_EVALUATED_PATH.exists():
        not_evaluated = set(load_glossary(NOT_EVALUATED_PATH))
        glossary = [a for a in glossary if a not in not_evaluated]
    logger.info("Loaded glossary with {} acronyms.", len(glossary))

    audio_files = discover_audio_files(AUDIO_DIR)
    if not audio_files:
        logger.error("No audio files found in {}", AUDIO_DIR)
        sys.exit(1)
    logger.info("Discovered {} audio files.", len(audio_files))

    pipeline = SpeechToTextPipeline()
    results_manager = ResultsManager(OUTPUT_DIR, dev=True)

    per_audio_expected: dict[str, dict[str, int]] = {}
    per_audio_predicted: dict[str, dict[str, int]] = {}
    for audio_file in audio_files:
        result = process_single_audio(
            audio_file, REFERENCE_DIR, glossary, pipeline, results_manager, timestamp
        )
        if result is not None:
            uid, expected, predicted = result
            per_audio_expected[uid] = expected
            per_audio_predicted[uid] = predicted

    if not per_audio_predicted:
        logger.error("No audio files were successfully processed.")
        sys.exit(1)

    csv_path = save_acronym_results_csv(
        glossary, per_audio_expected, per_audio_predicted, OUTPUT_DIR, timestamp
    )
    logger.info("Saved per-audio results CSV to: {}", csv_path)

    summary = build_summary(glossary, per_audio_expected, per_audio_predicted)
    summary_path = save_acronym_summary_json(summary, OUTPUT_DIR, timestamp)
    logger.info("Saved summary JSON to: {}", summary_path)

    logger.info("=== Acronym Evaluation Summary ===")
    logger.info("Total files        : {}", summary.total_files)
    logger.info(
        "Global TP/FP/TN/FN : {}/{}/{}/{}",
        summary.global_metrics.tp,
        summary.global_metrics.fp,
        summary.global_metrics.tn,
        summary.global_metrics.fn,
    )
    logger.info("Global precision   : {:.3f}", summary.global_metrics.precision)
    logger.info("Global recall      : {:.3f}", summary.global_metrics.recall)
    logger.info("Global accuracy    : {:.3f}", summary.global_metrics.accuracy)


if __name__ == "__main__":
    main()
