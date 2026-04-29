import json
from pathlib import Path

import pytest

from mcr_meeting.evaluation.acronyms.types import AcronymEvaluationSummary
from mcr_meeting.evaluation.acronyms.utils.persistence import (
    build_results_dataframe,
    build_summary,
    save_acronym_results_csv,
    save_acronym_summary_json,
)

GLOSSARY = ["DGPN", "DGGN", "DGSI", "ANTS", "ANTAI"]


class TestBuildResultsDataframe:
    def test_columns_and_values(self) -> None:
        expected = {"text1": {"DGPN": 1, "DGGN": 1, "DGSI": 1}}
        predicted = {"text1": {"DGPN": 1, "DGGN": 0, "DGSI": 3, "ANTS": 2, "ANTAI": 0}}
        df = build_results_dataframe(GLOSSARY, expected, predicted)

        assert list(df["uid"]) == ["text1"]
        # One expected + predicted column per acronym.
        for acronym in GLOSSARY:
            assert f"{acronym}_expected" in df.columns
            assert f"{acronym}_predicted" in df.columns
        # Count-aware model on text1:
        #   DGPN:  exp=1, pred=1 -> TP=1
        #   DGGN:  exp=1, pred=0 -> FN=1
        #   DGSI:  exp=1, pred=3 -> TP=1, FP=2 (2 excess occurrences)
        #   ANTS:  exp=0, pred=2 -> FP=2 (hallucinations)
        #   ANTAI: exp=0, pred=0 -> TN=1
        # Totals: TP=2, FP=4, TN=1, FN=1
        assert df.loc[0, "DGPN_expected"] == 1
        assert df.loc[0, "DGPN_predicted"] == 1
        assert df.loc[0, "ANTAI_expected"] == 0
        assert df.loc[0, "ANTAI_predicted"] == 0
        assert df.loc[0, "tp"] == 2
        assert df.loc[0, "fp"] == 4
        assert df.loc[0, "tn"] == 1
        assert df.loc[0, "fn"] == 1
        assert df.loc[0, "precision"] == pytest.approx(round(2 / 6, 4))
        assert df.loc[0, "recall"] == pytest.approx(round(2 / 3, 4))
        assert df.loc[0, "accuracy"] == pytest.approx(round(3 / 8, 4))


class TestBuildSummary:
    def test_aggregate_counts(self) -> None:
        a1_expected = dict.fromkeys(GLOSSARY, 1)
        a2_expected = dict.fromkeys(GLOSSARY, 1)
        a1_predicted = dict.fromkeys(GLOSSARY, 1)
        a2_predicted = dict.fromkeys(GLOSSARY, 1)
        a2_predicted["DGPN"] = 4  # DGPN emitted 4 times in audio 2
        summary = build_summary(
            GLOSSARY,
            {"a1": a1_expected, "a2": a2_expected},
            {"a1": a1_predicted, "a2": a2_predicted},
        )
        assert isinstance(summary, AcronymEvaluationSummary)
        assert summary.total_files == 2
        assert set(summary.per_audio.keys()) == {"a1", "a2"}
        # Aggregate expected = sum of expected counts per acronym.
        assert summary.aggregate_expected["DGPN"] == 2
        # Aggregate predicted = sum of predicted counts per acronym.
        assert summary.aggregate_predicted["DGPN"] == 5
        # Count-aware: DGPN in a2 has exp=1, pred=4 -> TP=1, FP=3.
        # a1 and other a2 acronyms all contribute TP only -> global FP=3.
        assert summary.global_metrics.fp == 3
        assert summary.global_metrics.tp == 10


class TestPersistence:
    def test_save_acronym_results_csv_writes_file(self, tmp_path: Path) -> None:
        expected = {"text1": dict.fromkeys(GLOSSARY, 1)}
        predicted = {"text1": dict.fromkeys(GLOSSARY, 1)}
        out_path = save_acronym_results_csv(
            GLOSSARY, expected, predicted, tmp_path, "2026-04-15_18-00-00"
        )
        assert out_path.exists()
        assert out_path.name == "2026-04-15_18-00-00_acronyms_results.csv"
        content = out_path.read_text()
        assert "uid" in content
        assert "DGPN_expected" in content
        assert "DGPN_predicted" in content
        assert "accuracy" in content
        assert "text1" in content

    def test_save_acronym_summary_json_writes_file(self, tmp_path: Path) -> None:
        expected = {"text1": dict.fromkeys(GLOSSARY, 1)}
        predicted = {"text1": dict.fromkeys(GLOSSARY, 1)}
        summary = build_summary(GLOSSARY, expected, predicted)
        out_path = save_acronym_summary_json(summary, tmp_path, "2026-04-15_18-00-00")
        assert out_path.exists()
        assert out_path.name == "2026-04-15_18-00-00_acronyms_summary.json"
        loaded = json.loads(out_path.read_text())
        assert loaded["total_files"] == 1
        assert loaded["global_metrics"]["precision"] == 1.0
        assert loaded["global_metrics"]["accuracy"] == 1.0
        assert loaded["per_audio"]["text1"]["metrics"]["tp"] == 5
