import pytest

from mcr_meeting.evaluation.acronyms.utils.metrics import (
    compute_audio_metrics,
    compute_global_metrics,
    score_acronym,
)

GLOSSARY = ["DGPN", "DGGN", "DGSI", "ANTS", "ANTAI"]


def _empty_predicted(glossary: list[str]) -> dict[str, int]:
    return dict.fromkeys(glossary, 0)


class TestScoreAcronym:
    @pytest.mark.parametrize(
        "expected, predicted, result",
        [
            (0, 0, (0, 0, 1, 0)),  # correctly absent -> TN
            (0, 5, (0, 5, 0, 0)),  # 5 hallucinations -> FP=5
            (1, 4, (1, 3, 0, 0)),  # correct + 3 extras -> TP=1, FP=3
            (2, 0, (0, 0, 0, 2)),  # 2 missing -> FN=2
            (3, 1, (1, 0, 0, 2)),  # 1 correct, 2 still missing -> TP=1, FN=2
            (2, 2, (2, 0, 0, 0)),  # exact match -> TP=2
        ],
    )
    def test_count_aware_scoring(
        self, expected: int, predicted: int, result: tuple[int, int, int, int]
    ) -> None:
        assert score_acronym(expected, predicted) == result


class TestComputeAudioMetrics:
    def test_perfect_audio(self) -> None:
        expected = {"DGPN": 1, "DGGN": 1, "DGSI": 1, "ANTS": 0, "ANTAI": 0}
        predicted = {"DGPN": 1, "DGGN": 1, "DGSI": 1, "ANTS": 0, "ANTAI": 0}
        m = compute_audio_metrics(expected, predicted)
        assert m.tp == 3
        assert m.fp == 0
        assert m.tn == 2
        assert m.fn == 0
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.accuracy == 1.0

    def test_all_missing(self) -> None:
        expected = dict.fromkeys(GLOSSARY, 1)
        predicted = _empty_predicted(GLOSSARY)
        m = compute_audio_metrics(expected, predicted)
        assert m.tp == 0
        assert m.fp == 0
        assert m.tn == 0
        assert m.fn == 5
        assert m.precision == 0.0  # 0/0 -> 0.0 by convention
        assert m.recall == 0.0
        assert m.accuracy == 0.0

    def test_repetitions_inflate_fp(self) -> None:
        # DGPN expected 1x, emitted 4x -> TP=1, FP=3 under count-aware model.
        expected = {"DGPN": 1, "DGGN": 0, "DGSI": 0, "ANTS": 0, "ANTAI": 0}
        predicted = {"DGPN": 4, "DGGN": 0, "DGSI": 0, "ANTS": 0, "ANTAI": 0}
        m = compute_audio_metrics(expected, predicted)
        assert m.tp == 1
        assert m.fp == 3
        assert m.tn == 4
        assert m.fn == 0
        assert m.precision == pytest.approx(1 / 4)
        assert m.recall == 1.0
        assert m.accuracy == pytest.approx(5 / 8)

    def test_missing_key_in_expected_treated_as_zero(self) -> None:
        # Common case: reference file only lists spoken acronyms.
        expected = {"DGPN": 1}  # DGGN/DGSI/ANTS/ANTAI implicit 0
        predicted = dict.fromkeys(GLOSSARY, 0)
        predicted["DGPN"] = 1
        m = compute_audio_metrics(expected, predicted)
        assert m.tp == 1
        assert m.fp == 0
        assert m.tn == 4
        assert m.fn == 0
        assert m.accuracy == 1.0


class TestComputeGlobalMetrics:
    def test_micro_average_with_mixed_errors(self) -> None:
        # audio1: 3 correct, 2 missing -> tp=3, fn=2, fp=0, tn=0
        # audio2: 0 expected, DGPN emitted 2x -> tp=0, fn=0, fp=2, tn=4
        a1_expected = {"DGPN": 1, "DGGN": 1, "DGSI": 1, "ANTS": 1, "ANTAI": 1}
        a1_predicted = {"DGPN": 1, "DGGN": 1, "DGSI": 1, "ANTS": 0, "ANTAI": 0}
        a2_expected = dict.fromkeys(GLOSSARY, 0)
        a2_predicted = {"DGPN": 2, "DGGN": 0, "DGSI": 0, "ANTS": 0, "ANTAI": 0}
        m = compute_global_metrics(
            {"a1": a1_expected, "a2": a2_expected},
            {"a1": a1_predicted, "a2": a2_predicted},
        )
        assert m.tp == 3
        assert m.fp == 2
        assert m.tn == 4
        assert m.fn == 2
        assert m.precision == pytest.approx(3 / 5)
        assert m.recall == pytest.approx(3 / 5)
        assert m.accuracy == pytest.approx(7 / 11)

    def test_empty_inputs_safe(self) -> None:
        m = compute_global_metrics({}, {})
        assert m.tp == 0
        assert m.fp == 0
        assert m.tn == 0
        assert m.fn == 0
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.accuracy == 0.0
