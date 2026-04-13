import json
from pathlib import Path

import pytest

from mcr_meeting.evaluation.acronymes.constants import ACRONYMES
from mcr_meeting.evaluation.acronymes.types import AcronymEvaluationSummary
from mcr_meeting.evaluation.acronymes.utils.persistence import (
    build_results_dataframe,
    build_summary,
    save_acronym_results_csv,
    save_acronym_summary_json,
)


class TestBuildResultsDataframe:
    def test_columns_and_values(self) -> None:
        counts = dict.fromkeys(ACRONYMES, 1)
        counts["ANTS"] = 4
        counts["DGSI"] = 0
        df = build_results_dataframe({"text1": counts})
        assert list(df["uid"]) == ["text1"]
        for acronym in ACRONYMES:
            assert f"{acronym}_count" in df.columns
        assert df.loc[0, "ANTS_count"] == 4
        assert df.loc[0, "DGSI_count"] == 0
        assert df.loc[0, "tp"] == 19
        assert df.loc[0, "fp"] == 3
        assert df.loc[0, "fn"] == 1
        assert df.loc[0, "precision"] == pytest.approx(round(19 / 22, 4))
        assert df.loc[0, "recall"] == pytest.approx(round(19 / 20, 4))

    def test_one_row_per_audio(self) -> None:
        per_audio = {
            "a1": dict.fromkeys(ACRONYMES, 1),
            "a2": dict.fromkeys(ACRONYMES, 0),
        }
        df = build_results_dataframe(per_audio)
        assert len(df) == 2
        assert set(df["uid"]) == {"a1", "a2"}


class TestBuildSummary:
    def test_summary_structure_and_values(self) -> None:
        per_audio = {"a1": dict.fromkeys(ACRONYMES, 1)}
        summary = build_summary(per_audio)
        assert isinstance(summary, AcronymEvaluationSummary)
        assert summary.total_files == 1
        assert "a1" in summary.per_audio
        assert summary.per_audio["a1"].metrics.tp == 20
        assert summary.global_metrics.precision == 1.0
        assert summary.global_metrics.recall == 1.0
        assert summary.aggregate_counts["DGPN"] == 1

    def test_aggregate_counts_sum(self) -> None:
        a1 = dict.fromkeys(ACRONYMES, 1)
        a2 = dict.fromkeys(ACRONYMES, 1)
        a2["ANTS"] = 4
        summary = build_summary({"a1": a1, "a2": a2})
        assert summary.total_files == 2
        assert summary.aggregate_counts["ANTS"] == 5
        assert summary.aggregate_counts["DGPN"] == 2
        assert summary.global_metrics.fp == 3


class TestPersistence:
    def test_save_acronym_results_csv_writes_file(self, tmp_path: Path) -> None:
        per_audio = {"text1": dict.fromkeys(ACRONYMES, 1)}
        out_path = save_acronym_results_csv(per_audio, tmp_path, "2026-04-10_18-00-00")
        assert out_path.exists()
        assert out_path.name == "2026-04-10_18-00-00_acronymes_results.csv"
        content = out_path.read_text()
        assert "uid" in content
        assert "DGPN_count" in content
        assert "precision" in content
        assert "text1" in content

    def test_save_acronym_summary_json_writes_file(self, tmp_path: Path) -> None:
        per_audio = {"text1": dict.fromkeys(ACRONYMES, 1)}
        summary = build_summary(per_audio)
        out_path = save_acronym_summary_json(summary, tmp_path, "2026-04-10_18-00-00")
        assert out_path.exists()
        assert out_path.name == "2026-04-10_18-00-00_acronymes_summary.json"
        loaded = json.loads(out_path.read_text())
        assert loaded["total_files"] == 1
        assert loaded["global_metrics"]["precision"] == 1.0
        assert loaded["per_audio"]["text1"]["metrics"]["tp"] == 20

    def test_save_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        nested = tmp_path / "does" / "not" / "exist"
        per_audio = {"text1": dict.fromkeys(ACRONYMES, 1)}
        out_path = save_acronym_results_csv(per_audio, nested, "T")
        assert out_path.exists()
        assert out_path.parent == nested
