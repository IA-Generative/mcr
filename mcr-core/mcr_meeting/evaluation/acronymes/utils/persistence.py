"""Persistence of acronym evaluation results (CSV + JSON)."""

import json
from pathlib import Path

import pandas as pd

from mcr_meeting.evaluation.acronymes.types import (
    AcronymEvaluationSummary,
    AcronymPerAudioEntry,
)
from mcr_meeting.evaluation.acronymes.utils.metrics import (
    compute_audio_metrics,
    compute_global_metrics,
)


def build_results_dataframe(
    glossary: list[str],
    per_audio_expected: dict[str, dict[str, int]],
    per_audio_predicted: dict[str, dict[str, int]],
) -> pd.DataFrame:
    """Build a DataFrame with one row per audio.

    Columns: ``uid``, ``<ACRONYM>_expected`` x N, ``<ACRONYM>_predicted`` x N,
    ``tp``, ``fp``, ``tn``, ``fn``, ``precision``, ``recall``, ``accuracy``.
    """
    rows: list[dict[str, str | int | float]] = []
    for uid, predicted in per_audio_predicted.items():
        expected = per_audio_expected.get(uid, {})
        metrics = compute_audio_metrics(expected, predicted)
        row: dict[str, str | int | float] = {"uid": uid}
        for acronym in glossary:
            row[f"{acronym}_expected"] = expected.get(acronym, 0)
            row[f"{acronym}_predicted"] = predicted.get(acronym, 0)
        row["tp"] = metrics.tp
        row["fp"] = metrics.fp
        row["tn"] = metrics.tn
        row["fn"] = metrics.fn
        row["precision"] = round(metrics.precision, 4)
        row["recall"] = round(metrics.recall, 4)
        row["accuracy"] = round(metrics.accuracy, 4)
        rows.append(row)
    return pd.DataFrame(rows)


def save_acronym_results_csv(
    glossary: list[str],
    per_audio_expected: dict[str, dict[str, int]],
    per_audio_predicted: dict[str, dict[str, int]],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """Write ``{timestamp}_acronymes_results.csv`` to ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    df = build_results_dataframe(glossary, per_audio_expected, per_audio_predicted)
    output_path = output_dir / f"{timestamp}_acronymes_results.csv"
    df.to_csv(output_path, index=False)
    return output_path


def build_summary(
    glossary: list[str],
    per_audio_expected: dict[str, dict[str, int]],
    per_audio_predicted: dict[str, dict[str, int]],
) -> AcronymEvaluationSummary:
    """Build the global summary with per-audio detail and micro-avg metrics."""
    per_audio_entries: dict[str, AcronymPerAudioEntry] = {}
    aggregate_expected: dict[str, int] = {acronym: 0 for acronym in glossary}
    aggregate_predicted: dict[str, int] = {acronym: 0 for acronym in glossary}

    for uid, predicted in per_audio_predicted.items():
        expected = per_audio_expected.get(uid, {})
        per_audio_entries[uid] = AcronymPerAudioEntry(
            expected=expected,
            predicted=predicted,
            metrics=compute_audio_metrics(expected, predicted),
        )
        for acronym in glossary:
            aggregate_expected[acronym] += expected.get(acronym, 0)
            aggregate_predicted[acronym] += predicted.get(acronym, 0)

    return AcronymEvaluationSummary(
        total_files=len(per_audio_predicted),
        per_audio=per_audio_entries,
        global_metrics=compute_global_metrics(per_audio_expected, per_audio_predicted),
        aggregate_expected=aggregate_expected,
        aggregate_predicted=aggregate_predicted,
    )


def save_acronym_summary_json(
    summary: AcronymEvaluationSummary,
    output_dir: Path,
    timestamp: str,
) -> Path:
    """Write ``{timestamp}_acronymes_summary.json`` to ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{timestamp}_acronymes_summary.json"
    output_path.write_text(
        json.dumps(summary.model_dump(), indent=2, ensure_ascii=False)
    )
    return output_path
