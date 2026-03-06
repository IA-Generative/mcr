import re
import unicodedata

from num2words import num2words

# French filler words / interjections that carry no semantic content.
# Listed in their accent-stripped form since removal is applied after
# Unicode normalization.
_FRENCH_INTERJECTIONS: frozenset[str] = frozenset(
    {
        "euh",
        "heu",
        "hein",
        "bon",
        "ben",
        "bah",
        "eh",
        "ah",
        "oh",
        "ouais",
        "voila",  # voilà (accent stripped by normalization)
        "donc",
        "alors",
        "quoi", 
    }
)

_INTERJECTION_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in sorted(_FRENCH_INTERJECTIONS)) + r")\b"
)


def _replace_numbers_with_words(text: str, lang: str = "fr") -> str:
    """Replace digit sequences with their French word equivalents.

    Example: "234 euros" → "deux cent trente-quatre euros"
    """

    def repl(match: re.Match[str]) -> str:
        return str(num2words(int(match.group()), lang=lang))

    return re.sub(r"\d+", repl, text)


def french_text_normalizer(text: str) -> str:
    """Normalize French text before metric computation.

    Applies the following transformations:
    - Lowercase
    - Numbers replaced by their French word equivalents (e.g. 234 → "deux cent trente-quatre")
    - Dataset ground-truth markers removed: ¤TAG¤ tokens (e.g. ¤P13¤)
    - Truncated words removed: tokens ending with a dash before a space or
      end-of-string (e.g. "qu-", "s-") are dropped entirely
    - Unicode normalization (é → e, ç → c, etc.)
    - French filler words / interjections removed (euh, hein, donc, voilà, …)
    - Punctuation and special characters removed (replaced by space),
      including underscore
    - Consecutive duplicate words collapsed (e.g. "le le" → "le", "de de de" → "de")
    - Multiple spaces collapsed to one
    - Leading/trailing whitespace stripped
    """
    # Lowercase
    text = text.lower()

    # Replace digit sequences with French words before accent stripping so
    # that num2words can produce proper accented French (e.g. "deuxième").
    text = _replace_numbers_with_words(text)

    # Remove ¤TAG¤ markers used in some ground-truth datasets (e.g. ¤P13¤)
    text = re.sub(r"¤[^¤\s]+¤", " ", text)

    # Remove truncated words: a word that ends with a dash right before a
    # space or end-of-string is an incomplete token and should be dropped
    # (e.g. "qu- il" → "il", "il vient s-" → "il vient")
    text = re.sub(r"\b\w+-(?=\s|$)", " ", text)

    # Unicode normalization (NFD decomposes accented chars into base + combining mark)
    text = unicodedata.normalize("NFD", text)
    # Strip combining diacritical marks (category "Mn")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Remove punctuation and special characters including underscore
    # (replace with space to avoid merging surrounding words)
    text = re.sub(r"[^\w\s]|_", " ", text)

    # Remove French filler words / interjections (applied after accent
    # stripping so the pattern matches the normalized forms, e.g. "voila")
    text = _INTERJECTION_PATTERN.sub(" ", text)

    # Remove consecutive duplicate words (e.g. "le le" → "le", "de de de" → "de").
    # Applied after punctuation removal so only clean word tokens are compared.
    text = re.sub(r"\b(\w+)(\s+\1)+\b", r"\1", text)

    # Collapse multiple spaces and strip edges
    text = re.sub(r"\s+", " ", text).strip()

    return text
