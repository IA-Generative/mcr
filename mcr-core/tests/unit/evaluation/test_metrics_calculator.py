from mcr_meeting.evaluation.utils import MetricsCalculator
from mcr_meeting.evaluation.utils.text_normalization import french_text_normalizer


class TestFrenchTextNormalizer:
    def test_lowercase(self):
        assert french_text_normalizer("Bonjour") == "bonjour"

    def test_accent_stripping(self):
        assert french_text_normalizer("éàèêùç") == "eaeeuc"

    def test_punctuation_removal(self):
        assert french_text_normalizer("bonjour, monde!") == "bonjour monde"

    def test_double_spaces_collapsed(self):
        assert french_text_normalizer("a  b") == "a b"

    def test_leading_trailing_whitespace_stripped(self):
        assert french_text_normalizer("  bonjour  ") == "bonjour"

    def test_combined(self):
        assert (
            french_text_normalizer("Ça s'est passé, très bien.")
            == "ca s est passe tres bien"
        )

    def test_apostrophe_becomes_space(self):
        assert french_text_normalizer("c'est") == "c est"

    def test_hyphen_becomes_space(self):
        assert french_text_normalizer("vingt-trois") == "vingt trois"

    def test_empty_string(self):
        assert french_text_normalizer("") == ""

    def test_already_normalized(self):
        assert french_text_normalizer("bonjour monde") == "bonjour monde"

    # --- dataset-specific ground-truth characters ---

    def test_underscore_becomes_space(self):
        assert french_text_normalizer("hello_world") == "hello world"

    def test_double_quote_removal(self):
        assert french_text_normalizer('say "hello"') == "say hello"

    def test_parentheses_removal(self):
        assert french_text_normalizer("(bonjour)") == "bonjour"

    def test_bracket_removal(self):
        assert french_text_normalizer("[bonjour]") == "bonjour"

    def test_at_symbol_removal(self):
        assert french_text_normalizer("user@domain") == "user domain"

    def test_plus_hash_equals_removal(self):
        assert french_text_normalizer("a+b#c=d") == "a b c d"

    def test_slash_angle_brackets_removal(self):
        assert french_text_normalizer("a/b <c> d") == "a b c d"

    def test_p13_marker_removal(self):
        assert french_text_normalizer("¤P13¤ bonjour") == "bonjour"

    def test_p13_marker_inline_removal(self):
        assert french_text_normalizer("bonjour ¤P13¤ monde") == "bonjour monde"

    def test_truncated_word_before_space_removed(self):
        assert french_text_normalizer("qu- il vient") == "il vient"

    def test_truncated_word_at_end_removed(self):
        assert french_text_normalizer("il vient s-") == "il vient"

    def test_normal_hyphenated_word_split(self):
        # vingt-trois: hyphen between two words → two tokens (existing behaviour)
        assert french_text_normalizer("vingt-trois") == "vingt trois"


class TestMetricsCalculatorNormalization:
    def test_normalization_is_applied_before_scoring(self):
        """A dirty reference with markers, accents, brackets and truncated words
        should score 0 against its clean equivalent."""
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="¤P13¤ Ça s'est [très] bien passé, n'est-ce pas?",
            hypothesis_text="ca s est tres bien passe n est ce pas",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_genuinely_different_words_produce_nonzero_wer(self):
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="bonjour monde",
            hypothesis_text="au revoir monde",
        )
        assert result.wer > 0.0

    def test_genuinely_different_chars_produce_nonzero_cer(self):
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="abc",
            hypothesis_text="xyz",
        )
        assert result.cer > 0.0

    def test_missing_words_in_hypothesis_produce_nonzero_wer(self):
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="je vais bien merci",
            hypothesis_text="je vais",
        )
        assert result.wer > 0.0
