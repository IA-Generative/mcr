"""
Evaluate the participant naming pipeline against ground-truth expected files.

Usage from mcr root:
    docker compose --env-file .env --env-file .env.local.docker exec transcription_worker python -m mcr_meeting.evaluation.participant_naming

"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from unicodedata import normalize

from loguru import logger

from mcr_meeting.app.schemas.transcription_schema import DiarizedTranscriptionSegment
from mcr_meeting.app.services.speech_to_text.participants_naming import (
    ParticipantExtraction,
)

SEGMENT_PATTERN = re.compile(r"^(LOCUTEUR_\d+)\s*:\s*(.+)$")

DEFAULT_TEST_DIR = Path(__file__).resolve().parent / "test_data"


@dataclass
class SpeakerDetail:
    speaker_id: str
    expected: str | None
    predicted: str | None
    match: bool


@dataclass
class EvalResult:
    file: str
    accuracy: float
    correct: int
    total: int
    details: list[SpeakerDetail] = field(default_factory=list)


def parse_txt_to_segments(txt_path: Path) -> list[DiarizedTranscriptionSegment]:
    segments: list[DiarizedTranscriptionSegment] = []
    idx = 0
    for line in txt_path.read_text(encoding="utf-8").splitlines():
        match = SEGMENT_PATTERN.match(line.strip())
        if not match:
            continue
        speaker, text = match.group(1), match.group(2)
        segments.append(
            DiarizedTranscriptionSegment(
                id=idx, speaker=speaker, text=text, start=float(idx), end=float(idx + 1)
            )
        )
        idx += 1
    return segments


def load_expected(json_path: Path) -> dict[str, str | None]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return {entry["speaker_id"]: entry.get("name") for entry in data}


def normalize_name(name: str | None) -> str | None:
    if name is None:
        return None
    return normalize("NFC", name.strip().lower())


def evaluate_file(
    txt_path: Path, expected_path: Path, extractor: ParticipantExtraction
) -> EvalResult:
    segments = parse_txt_to_segments(txt_path)
    expected = load_expected(expected_path)

    logger.info("Running extraction on {} ({} segments)", txt_path.name, len(segments))
    participants = extractor.extract(segments)

    predicted = {p.speaker_id: p.name for p in participants}

    all_speaker_ids = sorted(set(expected.keys()) | set(predicted.keys()))

    correct = 0
    total = 0
    details: list[SpeakerDetail] = []

    for sid in all_speaker_ids:
        exp = expected.get(sid)
        pred = predicted.get(sid)
        exp_norm = normalize_name(exp)
        pred_norm = normalize_name(pred)
        is_match = exp_norm == pred_norm
        if is_match:
            correct += 1
        total += 1
        details.append(
            SpeakerDetail(
                speaker_id=sid,
                expected=exp,
                predicted=pred,
                match=is_match,
            )
        )

    return EvalResult(
        file=txt_path.name,
        accuracy=correct / total if total else 0,
        correct=correct,
        total=total,
        details=details,
    )


def log_report(results: list[EvalResult]) -> None:
    total_correct = 0
    total_speakers = 0

    for res in results:
        logger.info("\n{}", "=" * 60)
        logger.info(
            "  {}  —  {}/{} correct ({:.0%})",
            res.file,
            res.correct,
            res.total,
            res.accuracy,
        )
        logger.info("{}", "=" * 60)
        for d in res.details:
            status = "OK" if d.match else "FAIL"
            logger.info(
                "  [{:4s}] {:15s}  expected={:20s}  predicted={}",
                status,
                d.speaker_id,
                d.expected or "",
                d.predicted or "",
            )
        total_correct += res.correct
        total_speakers += res.total

    logger.info("\n{}", "=" * 60)
    overall = total_correct / total_speakers if total_speakers else 0
    logger.info("  OVERALL: {}/{} ({:.0%})", total_correct, total_speakers, overall)
    logger.info("{}\n", "=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate participant naming pipeline")
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=DEFAULT_TEST_DIR,
        help="Directory containing .txt and .expected.json files (default: test_data/)",
    )
    args = parser.parse_args()

    txt_files = sorted(args.test_dir.glob("*.txt"))
    if not txt_files:
        logger.error("No .txt files found in {}", args.test_dir, file=sys.stderr)
        sys.exit(1)

    pairs: list[tuple[Path, Path]] = []
    for txt_path in txt_files:
        expected_path = txt_path.with_suffix("").with_suffix(".expected.json")
        if not expected_path.exists():
            logger.warning("No expected file for {}, skipping", txt_path.name)
            continue
        pairs.append((txt_path, expected_path))

    if not pairs:
        logger.info(
            "No test cases found (no matching .expected.json files)", file=sys.stderr
        )
        sys.exit(1)

    logger.info("Found {} test case(s). Initializing extractor...", len(pairs))
    extractor = ParticipantExtraction()

    results = []
    for txt_path, expected_path in pairs:
        result = evaluate_file(txt_path, expected_path, extractor)
        results.append(result)

    log_report(results)


if __name__ == "__main__":
    main()
