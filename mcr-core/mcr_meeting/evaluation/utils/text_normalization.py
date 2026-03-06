import re
import unicodedata


def french_text_normalizer(text: str) -> str:
    """Normalize French text before metric computation.

    Applies the following transformations:
    - Lowercase
    - Dataset ground-truth markers removed: ¤TAG¤ tokens (e.g. ¤P13¤)
    - Truncated words removed: tokens ending with a dash before a space or
      end-of-string (e.g. "qu-", "s-") are dropped entirely
    - Unicode normalization (é → e, ç → c, etc.)
    - Punctuation and special characters removed (replaced by space),
      including underscore
    - Multiple spaces collapsed to one
    - Leading/trailing whitespace stripped
    """
    # Lowercase
    text = text.lower()

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

    # Collapse multiple spaces and strip edges
    text = re.sub(r"\s+", " ", text).strip()

    return text
