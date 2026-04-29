from pathlib import Path

from mcr_generation.evaluation.criteria import CRITERIA
from mcr_generation.evaluation.pipeline.csv_writer import write_csv
from mcr_generation.evaluation.pipeline.types import ItemRunResult, ScoreResult


def _build_result(uid: str, scores: dict[str, int | None]) -> ItemRunResult:
    return ItemRunResult(
        uid=uid,
        scores={name: ScoreResult(value=value) for name, value in scores.items()},
    )


class TestWriteCsv:
    def test_writes_header_rows_and_mean(self, tmp_path: Path) -> None:
        criterion_names = [c.name for c in CRITERIA]
        scores_a = dict.fromkeys(criterion_names, 5)
        scores_b = dict.fromkeys(criterion_names, 3)
        results = [
            _build_result("a", scores_a),
            _build_result("b", scores_b),
        ]
        csv_path = tmp_path / "metrics.csv"

        criteria_means = write_csv(csv_path, list(CRITERIA), results)

        lines = csv_path.read_text().splitlines()
        assert lines[0].split(",")[:2] == ["uid", criterion_names[0]]
        assert lines[1].startswith("a,")
        assert lines[2].startswith("b,")
        assert lines[3].startswith("MEAN,")

        for name in criterion_names:
            assert criteria_means[name] == 4.00

    def test_skips_none_cells_in_mean(self, tmp_path: Path) -> None:
        criterion_names = [c.name for c in CRITERIA]
        # First row has only the first criterion scored; second row scores all.
        scores_partial = {name: None for name in criterion_names}
        scores_partial[criterion_names[0]] = 4
        scores_full = dict.fromkeys(criterion_names, 2)

        results = [
            _build_result("partial", scores_partial),
            _build_result("full", scores_full),
        ]
        csv_path = tmp_path / "metrics.csv"

        criteria_means = write_csv(csv_path, list(CRITERIA), results)

        # First criterion: average of (4, 2) = 3.0
        assert criteria_means[criterion_names[0]] == 3.0
        # Other criteria: only one value (2), so mean is 2.0
        for name in criterion_names[1:]:
            assert criteria_means[name] == 2.0

        # The "partial" row must leave empty cells where scores are None.
        partial_line = csv_path.read_text().splitlines()[1]
        cells = partial_line.split(",")
        assert cells[0] == "partial"
        assert cells[1] == "4"
        for cell in cells[2 : 1 + len(criterion_names)]:
            assert cell == ""

    def test_row_has_only_uid_and_criterion_columns(self, tmp_path: Path) -> None:
        criterion_names = [c.name for c in CRITERIA]
        scores = dict.fromkeys(criterion_names, 4)
        results = [_build_result("a", scores)]
        csv_path = tmp_path / "metrics.csv"

        write_csv(csv_path, list(CRITERIA), results)

        header = csv_path.read_text().splitlines()[0].split(",")
        assert header == ["uid", *criterion_names]
        row = csv_path.read_text().splitlines()[1].split(",")
        assert len(row) == len(header)
