"""Persistence of acronym evaluation results (CSV + JSON)."""

import json
from pathlib import Path

import pandas as pd

from mcr_meeting.evaluation.acronymes.constants import ACRONYMES
from mcr_meeting.evaluation.acronymes.types import (
    AcronymEvaluationSummary,
    AcronymPerAudioEntry,
)
from mcr_meeting.evaluation.acronymes.utils.metrics import (
    compute_audio_metrics,
    compute_global_metrics,
)


def build_results_dataframe(
    per_audio_counts: dict[str, dict[str, int]],
) -> pd.DataFrame:
    """Build a DataFrame with one row per audio.

    Columns: ``uid``, ``<ACRONYM>_count`` x20, ``tp``, ``fp``, ``fn``,
    ``precision``, ``recall``.
    """
    rows: list[dict[str, str | int | float]] = []
    for uid, counts in per_audio_counts.items():
        metrics = compute_audio_metrics(counts)
        row: dict[str, str | int | float] = {"uid": uid}
        for acronym in ACRONYMES:
            row[f"{acronym}_count"] = counts.get(acronym, 0)
        row["tp"] = metrics.tp
        row["fp"] = metrics.fp
        row["fn"] = metrics.fn
        row["precision"] = round(metrics.precision, 4)
        row["recall"] = round(metrics.recall, 4)
        rows.append(row)
    return pd.DataFrame(rows)


def save_acronym_results_csv(
    per_audio_counts: dict[str, dict[str, int]],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """Write ``{timestamp}_acronymes_results.csv`` to ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    df = build_results_dataframe(per_audio_counts)
    output_path = output_dir / f"{timestamp}_acronymes_results.csv"
    df.to_csv(output_path, index=False)
    return output_path


def build_summary(
    per_audio_counts: dict[str, dict[str, int]],
) -> AcronymEvaluationSummary:
    """Build the global summary with per-audio detail and micro-avg metrics."""
    per_audio_entries: dict[str, AcronymPerAudioEntry] = {}
    aggregate_counts: dict[str, int] = {acronym: 0 for acronym in ACRONYMES}

    for uid, counts in per_audio_counts.items():
        per_audio_entries[uid] = AcronymPerAudioEntry(
            counts=counts,
            metrics=compute_audio_metrics(counts),
        )
        for acronym, count in counts.items():
            aggregate_counts[acronym] = aggregate_counts.get(acronym, 0) + count

    return AcronymEvaluationSummary(
        total_files=len(per_audio_counts),
        per_audio=per_audio_entries,
        global_metrics=compute_global_metrics(per_audio_counts),
        aggregate_counts=aggregate_counts,
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
