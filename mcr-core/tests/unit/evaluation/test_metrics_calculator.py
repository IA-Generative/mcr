import pytest

from mcr_meeting.evaluation.utils import MetricsCalculator
from mcr_meeting.evaluation.utils.text_normalization import french_text_normalizer


class TestFrenchTextNormalizer:
    def test_lowercase(self) -> None:
        assert french_text_normalizer("Bonjour") == "bonjour"

    def test_accent_stripping(self) -> None:
        assert french_text_normalizer("éàèêùç") == "eaeeuc"

    def test_punctuation_removal(self) -> None:
        assert french_text_normalizer("bonjour, monde!") == "bonjour monde"

    def test_double_spaces_collapsed(self) -> None:
        assert french_text_normalizer("a  b") == "a b"

    def test_leading_trailing_whitespace_stripped(self) -> None:
        assert french_text_normalizer("  bonjour  ") == "bonjour"

    def test_combined(self) -> None:
        assert (
            french_text_normalizer("Ça s'est passé, très bien.")
            == "ca s est passe tres bien"
        )

    def test_apostrophe_becomes_space(self) -> None:
        assert french_text_normalizer("c'est") == "c est"

    def test_hyphen_becomes_space(self) -> None:
        assert french_text_normalizer("vingt-trois") == "vingt trois"

    def test_empty_string(self) -> None:
        assert french_text_normalizer("") == ""

    def test_already_normalized(self) -> None:
        assert french_text_normalizer("bonjour monde") == "bonjour monde"

    # --- dataset-specific ground-truth characters ---

    def test_underscore_becomes_space(self) -> None:
        assert french_text_normalizer("hello_world") == "hello world"

    def test_double_quote_removal(self) -> None:
        assert french_text_normalizer('say "hello"') == "say hello"

    def test_parentheses_removal(self) -> None:
        assert french_text_normalizer("(bonjour)") == "bonjour"

    def test_bracket_removal(self) -> None:
        assert french_text_normalizer("[bonjour]") == "bonjour"

    def test_at_symbol_removal(self) -> None:
        assert french_text_normalizer("user@domain") == "user domain"

    def test_plus_hash_equals_removal(self) -> None:
        assert french_text_normalizer("a+b#c=d") == "a b c d"

    def test_slash_angle_brackets_removal(self) -> None:
        assert french_text_normalizer("a/b <c> d") == "a b c d"

    def test_p13_marker_removal(self) -> None:
        assert french_text_normalizer("¤P13¤ bonjour") == "bonjour"

    def test_p13_marker_inline_removal(self) -> None:
        assert french_text_normalizer("bonjour ¤P13¤ monde") == "bonjour monde"

    def test_truncated_word_before_space_removed(self) -> None:
        assert french_text_normalizer("qu- il vient") == "il vient"

    def test_truncated_word_at_end_removed(self) -> None:
        assert french_text_normalizer("il vient s-") == "il vient"

    def test_normal_hyphenated_word_split(self) -> None:
        # vingt-trois: hyphen between two words → two tokens (existing behaviour)
        assert french_text_normalizer("vingt-trois") == "vingt trois"

    # --- number-to-words conversion ---

    def test_integer_replaced_by_words(self) -> None:
        assert french_text_normalizer("234") == "deux cent trente quatre"

    def test_number_inline(self) -> None:
        assert french_text_normalizer("il y a 3 chats") == "il y a trois chats"

    def test_zero(self) -> None:
        assert french_text_normalizer("0") == "zero"

    # --- interjection removal ---

    def test_euh_removed(self) -> None:
        assert french_text_normalizer("euh bonjour") == "bonjour"

    def test_hein_removed(self) -> None:
        assert french_text_normalizer("c'est bien hein") == "c est bien"

    def test_donc_removed(self) -> None:
        assert french_text_normalizer("donc on y va") == "on y va"

    def test_voila_removed(self) -> None:
        assert french_text_normalizer("voilà c'est fait") == "c est fait"

    def test_multiple_interjections_removed(self) -> None:
        assert french_text_normalizer("euh donc bonjour hein") == "bonjour"

    def test_interjection_not_removed_as_substring(self) -> None:
        # "alors" should not be removed from inside a longer word
        assert "elabor" in french_text_normalizer("elaboration")

    # --- consecutive duplicate removal ---

    def test_two_consecutive_duplicates_collapsed(self) -> None:
        assert french_text_normalizer("le le probleme") == "le probleme"

    def test_three_consecutive_duplicates_collapsed(self) -> None:
        assert french_text_normalizer("de de de cette") == "de cette"

    def test_non_consecutive_duplicates_kept(self) -> None:
        # Same word repeated but not consecutively should be preserved
        assert french_text_normalizer("le probleme le") == "le probleme le"

    def test_sentence_with_mixed_duplicates(self) -> None:
        # Multiple consecutive duplicates should be collapsed
        assert (
            french_text_normalizer("le le problème du du de de de cette")
            == "le probleme du de cette"
        )


class TestMetricsCalculatorNormalization:
    def test_normalization_is_applied_before_scoring(self) -> None:
        """A dirty reference with markers, accents, brackets, truncated words,
        interjections and numbers should score 0 against its clean equivalent."""
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="¤P13¤ euh Ça s'est [très] bien passé, n'est-ce pas? hein",
            hypothesis_text="ca s est tres bien passe n est ce pas",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_interjections_ignored_in_scoring(self) -> None:
        """Reference cluttered with filler words should score 0 against the
        clean transcript."""
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="euh donc je vais hein bien merci euh",
            hypothesis_text="je vais bien merci",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_numbers_converted_to_words_for_scoring(self) -> None:
        """A reference with digits should score 0 against its fully-written
        French equivalent."""
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="il y a 3 chats et 20 chiens",
            hypothesis_text="il y a trois chats et vingt chiens",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_consecutive_duplicates_ignored_in_scoring(self) -> None:
        """A reference with repeated words should score 0 against
        the deduplicated transcript."""
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="le le problème du du alors de de de cette question",
            hypothesis_text="le probleme du de cette question",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_consecutive_duplicates_in_prediction_not_ignored_in_scoring(self) -> None:
        """A prediction with repeated words should be penalized."""
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="le problème du du alors de de de cette question",
            hypothesis_text="le le probleme du de cette question",
        )
        assert result.wer > 0.0
        assert result.cer > 0.0

    def test_genuinely_different_words_produce_nonzero_wer(self) -> None:
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="bonjour monde",
            hypothesis_text="au revoir monde",
        )
        assert result.wer > 0.0

    def test_genuinely_different_chars_produce_nonzero_cer(self) -> None:
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="abc",
            hypothesis_text="xyz",
        )
        assert result.cer > 0.0

    def test_missing_words_in_hypothesis_produce_nonzero_wer(self) -> None:
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="je vais bien merci",
            hypothesis_text="je vais",
        )
        assert result.wer > 0.0


@pytest.mark.parametrize(
    "reference_text, hypothesis_text",
    [
        pytest.param(
            "euh ben bonjour à tous_les trois + euh nous sommes ici pour une réunion"
            " qui va durer vingt minutes euh est-ce_que vous voulez vous présenter",
            "Bonjour à tous les trois. Nous sommes ici pour une réunion qui va durer"
            " 20 minutes. Est-ce que vous voulez vous présenter ?",
            id="greeting_with_fillers",
        ),
        pytest.param(
            "oui bien sûr euh bastien euh donc euh nous sommes donc dans l' association euh"
            " pour un changement culturel important et euh du_coup euh je pense que faire"
            " cette réunion est intéressante pour euh pour voir un petit peu ce qu' on peut faire",
            "Oui, bien sûr. Bastien, nous sommes dans l'association pour un changement"
            " culturel important et du coup, je pense que faire cette réunion est"
            " intéressante pour voir un petit peu ce qu'on peut faire.",
            id="introduction_with_fillers",
        ),
        pytest.param(
            "éventuellement @ puisqu' on va essayer aussi de leur vendre nos produits donc euh @",
            "Éventuellement, puisqu'on va essayer aussi de leur vendre nos produits.",
            id="eventually_with_markers",
        ),
        pytest.param(
            "merci très bien + ensuite euh + jean-marc + * + ca ca ca va",
            "Merci.  Très bien. Ensuite, Jean-Marc, ça va ?",
            id="repeated_merci_collapsed",
        ),
        pytest.param(
            "il faudrait penser aux intelligences artificielles parce_que je vois qu' il_y a"
            " quand même des grosses pertes de mémoire parmi nos membres et ça ça pourrait être"
            " utile de les intégrer parce_que",
            "il faudrait penser aux intelligences artificielles,  parce que je vois qu'il y a"
            " quand même des grosses pertes de mémoire parmi nos membres. Et  Ça pourrait être"
            " utile de les intégrer, parce que",
            id="ai_memory_with_fillers",
        ),
    ],
)
def test_real_examples(reference_text: str, hypothesis_text: str) -> None:
    result = MetricsCalculator.calculate_transcription_metrics(
        reference_text=reference_text,
        hypothesis_text=hypothesis_text,
    )
    assert result.wer == 0.0
    assert result.cer == 0.0
