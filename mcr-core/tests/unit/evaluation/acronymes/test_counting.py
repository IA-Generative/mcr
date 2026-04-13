from mcr_meeting.evaluation.acronymes.constants import ACRONYMES
from mcr_meeting.evaluation.acronymes.utils.counting import (
    count_acronym_occurrences,
    evaluate_acronyms,
)


class TestCountAcronymOccurrences:
    def test_zero_occurrence(self) -> None:
        assert count_acronym_occurrences("blabla", "DGPN") == 0

    def test_single_occurrence(self) -> None:
        assert count_acronym_occurrences("la dgpn agit", "DGPN") == 1

    def test_multiple_occurrences(self) -> None:
        assert count_acronym_occurrences("dgpn et dgpn et dgpn", "DGPN") == 3

    def test_word_boundary_no_substring_match(self) -> None:
        assert count_acronym_occurrences("dgpnx", "DGPN") == 0
        assert count_acronym_occurrences("xdgpn", "DGPN") == 0
        assert count_acronym_occurrences("dgpnn", "DGPN") == 0

    def test_ants_does_not_match_inside_antai(self) -> None:
        text = "antai antai antai"
        assert count_acronym_occurrences(text, "ANTS") == 0
        assert count_acronym_occurrences(text, "ANTAI") == 3

    def test_antai_does_not_match_when_only_ants_present(self) -> None:
        text = "ants ants"
        assert count_acronym_occurrences(text, "ANTAI") == 0
        assert count_acronym_occurrences(text, "ANTS") == 2

    def test_case_insensitive_via_lowercase(self) -> None:
        assert count_acronym_occurrences("la dgpn", "DGPN") == 1

    def test_empty_text(self) -> None:
        assert count_acronym_occurrences("", "DGPN") == 0

    def test_acronym_surrounded_by_spaces(self) -> None:
        assert count_acronym_occurrences("voici dgpn et dnpaf voila", "DGPN") == 1
        assert count_acronym_occurrences("voici dgpn et dnpaf voila", "DNPAF") == 1


class TestEvaluateAcronyms:
    def test_returns_all_20_keys(self) -> None:
        result = evaluate_acronyms("")
        assert set(result.keys()) == set(ACRONYMES)
        assert all(value == 0 for value in result.values())

    def test_one_of_each(self) -> None:
        text = " ".join(a.lower() for a in ACRONYMES)
        result = evaluate_acronyms(text)
        assert all(value == 1 for value in result.values())

    def test_mixed_counts(self) -> None:
        text = "dgpn dgpn ants ants ants ants dgsi"
        result = evaluate_acronyms(text)
        assert result["DGPN"] == 2
        assert result["ANTS"] == 4
        assert result["DGSI"] == 1
        assert result["ANTAI"] == 0
        for acronym in ACRONYMES:
            if acronym not in {"DGPN", "ANTS", "DGSI"}:
                assert result[acronym] == 0
