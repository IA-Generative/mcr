"""Write the per-item CSV and the run summary JSON."""

import csv
import json
from pathlib import Path

from mcr_generation.evaluation.pipeline.types import (
    Criterion,
    ItemRunResult,
    RunSummary,
)


def _mean(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _format_cell(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def write_csv(
    csv_path: Path,
    criteria: list[Criterion],
    results: list[ItemRunResult],
) -> dict[str, float | None]:
    """Write the per-item CSV and return the per-criterion means.

    Columns: uid, <criterion_1>, ..., <criterion_n>. A final `MEAN` row
    aggregates each criterion column over the dataset (ignoring empty cells).
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    criterion_names = [c.name for c in criteria]
    header = ["uid", *criterion_names]

    rows: list[list[str]] = []
    per_criterion_values: dict[str, list[int]] = {name: [] for name in criterion_names}

    for result in results:
        scores: dict[str, int | None] = {
            name: (
                result.scores[name].value
                if name in result.scores and result.scores[name].value is not None
                else None
            )
            for name in criterion_names
        }
        for name, score_value in scores.items():
            if score_value is not None:
                per_criterion_values[name].append(score_value)
        rows.append(
            [
                result.uid,
                *(_format_cell(scores[name]) for name in criterion_names),
            ]
        )

    criteria_means: dict[str, float | None] = {
        name: _mean(values) for name, values in per_criterion_values.items()
    }

    mean_row = [
        "MEAN",
        *(_format_cell(criteria_means[name]) for name in criterion_names),
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
        writer.writerow(mean_row)

    return criteria_means


def write_summary(summary_path: Path, summary: RunSummary) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary.model_dump(mode="json"), fh, ensure_ascii=False, indent=2)
