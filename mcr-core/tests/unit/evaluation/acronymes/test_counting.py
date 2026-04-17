import pytest

from mcr_meeting.evaluation.acronymes.utils.counting import (
    count_acronym_occurrences,
    evaluate_acronyms,
)

GLOSSARY = ["DGPN", "DGGN", "ANTS", "ANTAI", "DNPAF", "COMSOPGN", "MINUM"]


class TestCountAcronymOccurrences:
    @pytest.mark.parametrize(
        ("text", "acronym", "expected_count"),
        [
            pytest.param("la dgpn agit", "DGPN", 1, id="single-occurrence"),
            pytest.param("dgpn et dgpn et dgpn", "DGPN", 3, id="multiple-occurrences"),
            pytest.param("dgpnx xdgpn dgpnn", "DGPN", 0, id="word-boundary-protection"),
        ],
    )
    def test_core_counting_cases(
        self, text: str, acronym: str, expected_count: int
    ) -> None:
        assert count_acronym_occurrences(text, acronym) == expected_count


class TestEvaluateAcronyms:
    def test_returns_all_glossary_keys_with_zero_counts_on_empty_text(self) -> None:
        result = evaluate_acronyms("", GLOSSARY)
        assert set(result.keys()) == set(GLOSSARY)
        assert all(value == 0 for value in result.values())

    def test_mixed_counts(self) -> None:
        text = "dgpn dgpn ants ants ants ants dgsi"
        result = evaluate_acronyms(text, GLOSSARY)
        assert result["DGPN"] == 2
        assert result["ANTS"] == 4
        assert result["ANTAI"] == 0
        # DGSI is not in this test's glossary, so it doesn't appear in the result.
        assert "DGSI" not in result

    def test_empty_glossary(self) -> None:
        assert evaluate_acronyms("anything goes here dgpn", []) == {}
