import re
import unicodedata


def french_text_normalizer(text: str) -> str:
    """Normalize French text before metric computation.

    Applies the following transformations:
    - Lowercase
    - Unicode normalization (é → e, ç → c, etc.)
    - Punctuation removal (replaced by space)
    - Multiple spaces collapsed to one
    - Leading/trailing whitespace stripped
    """
    # Lowercase
    text = text.lower()

    # Unicode normalization (NFD decomposes accented chars into base + combining mark)
    text = unicodedata.normalize("NFD", text)
    # Strip combining diacritical marks (category "Mn")
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Remove punctuation (replace with space to avoid merging surrounding words)
    text = re.sub(r"[^\w\s]", " ", text)

    # Collapse multiple spaces and strip edges
    text = re.sub(r"\s+", " ", text).strip()

    return text
