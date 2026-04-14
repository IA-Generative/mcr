import pytest

from mcr_meeting.evaluation.acronymes.constants import ACRONYMES
from mcr_meeting.evaluation.acronymes.types import AcronymMetrics
from mcr_meeting.evaluation.acronymes.utils.metrics import (
    acronym_fn,
    acronym_fp,
    acronym_tp,
    compute_audio_metrics,
    compute_global_metrics,
)


class TestAcronymTpFpFn:
    @pytest.mark.parametrize(
        "count, expected_tp, expected_fp, expected_fn",
        [
            (0, 0, 0, 1),
            (1, 1, 0, 0),
            (2, 1, 1, 0),
            (3, 1, 2, 0),
            (4, 1, 3, 0),
            (10, 1, 9, 0),
        ],
    )
    def test_metric_table(
        self, count: int, expected_tp: int, expected_fp: int, expected_fn: int
    ) -> None:
        assert acronym_tp(count) == expected_tp
        assert acronym_fp(count) == expected_fp
        assert acronym_fn(count) == expected_fn


class TestComputeAudioMetrics:
    def test_perfect_audio(self) -> None:
        counts = dict.fromkeys(ACRONYMES, 1)
        m = compute_audio_metrics(counts)
        assert m.tp == 20
        assert m.fp == 0
        assert m.fn == 0
        assert m.precision == 1.0
        assert m.recall == 1.0

    def test_all_missing(self) -> None:
        counts = dict.fromkeys(ACRONYMES, 0)
        m = compute_audio_metrics(counts)
        assert m.tp == 0
        assert m.fp == 0
        assert m.fn == 20
        assert m.precision == 0.0
        assert m.recall == 0.0

    def test_with_repetitions(self) -> None:
        counts = dict.fromkeys(ACRONYMES, 1)
        counts["ANTS"] = 4
        m = compute_audio_metrics(counts)
        assert m.tp == 20
        assert m.fp == 3
        assert m.fn == 0
        assert m.precision == pytest.approx(20 / 23)
        assert m.recall == 1.0

    def test_with_missing_and_extras(self) -> None:
        counts = dict.fromkeys(ACRONYMES, 1)
        counts["ANTS"] = 4
        counts["DGSI"] = 0
        m = compute_audio_metrics(counts)
        assert m.tp == 19
        assert m.fp == 3
        assert m.fn == 1
        assert m.precision == pytest.approx(19 / 22)
        assert m.recall == pytest.approx(19 / 20)


class TestComputeGlobalMetrics:
    def test_micro_average_two_audios(self) -> None:
        audio1 = dict.fromkeys(ACRONYMES, 1)
        audio2 = {a: (1 if i < 10 else 0) for i, a in enumerate(ACRONYMES)}
        m = compute_global_metrics({"a1": audio1, "a2": audio2})
        assert m.tp == 30
        assert m.fp == 0
        assert m.fn == 10
        assert m.precision == 1.0
        assert m.recall == pytest.approx(30 / 40)

    def test_micro_average_with_fp(self) -> None:
        audio1 = dict.fromkeys(ACRONYMES, 1)
        audio1["ANTS"] = 4
        audio2 = dict.fromkeys(ACRONYMES, 1)
        m = compute_global_metrics({"a1": audio1, "a2": audio2})
        assert m.tp == 40
        assert m.fp == 3
        assert m.fn == 0
        assert m.precision == pytest.approx(40 / 43)
        assert m.recall == 1.0

    def test_empty_inputs_safe(self) -> None:
        m = compute_global_metrics({})
        assert m.tp == 0
        assert m.fp == 0
        assert m.fn == 0
        assert m.precision == 0.0
        assert m.recall == 0.0


class TestAcronymMetricsModel:
    def test_serialization_roundtrip(self) -> None:
        m = AcronymMetrics(tp=10, fp=2, fn=8, precision=0.83, recall=0.55)
        dumped = m.model_dump()
        assert dumped == {"tp": 10, "fp": 2, "fn": 8, "precision": 0.83, "recall": 0.55}
        rebuilt = AcronymMetrics.model_validate(dumped)
        assert rebuilt == m
