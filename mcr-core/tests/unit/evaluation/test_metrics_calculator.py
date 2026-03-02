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


class TestMetricsCalculatorNormalization:
    def test_punctuation_difference_does_not_affect_score(self):
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="Bonjour.",
            hypothesis_text="bonjour",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_accent_difference_does_not_affect_score(self):
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="C'est très bien",
            hypothesis_text="c est tres bien",
        )
        assert result.wer == 0.0
        assert result.cer == 0.0

    def test_case_difference_does_not_affect_score(self):
        result = MetricsCalculator.calculate_transcription_metrics(
            reference_text="Bonjour Monde",
            hypothesis_text="bonjour monde",
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
