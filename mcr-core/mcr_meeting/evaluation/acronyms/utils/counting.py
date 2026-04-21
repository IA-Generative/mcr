"""Regex-based acronym counting in normalized text."""

import re
from collections.abc import Iterable


def count_acronym_occurrences(normalized_text: str, acronym: str) -> int:
    """Count occurrences of an acronym in already-normalized text.

    The project's ``french_text_normalizer`` lowercases and strips accents, so
    the acronym is lowercased before matching. Word-boundaries ``\\b`` prevent
    capturing an acronym inside another word (e.g. "ANTS" must not match inside
    "antai").
    """
    pattern = rf"\b{re.escape(acronym.lower())}\b"
    return len(re.findall(pattern, normalized_text))


def evaluate_acronyms(normalized_text: str, glossary: Iterable[str]) -> dict[str, int]:
    """Return ``{acronym -> count}`` for every acronym in ``glossary``."""
    return {
        acronym: count_acronym_occurrences(normalized_text, acronym)
        for acronym in glossary
    }
