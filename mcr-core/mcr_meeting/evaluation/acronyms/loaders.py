"""Load the acronym glossary and per-audio reference files."""

import json
from pathlib import Path


def load_glossary(path: Path) -> list[str]:
    """Load the closed list of acronyms from a JSON file.

    The JSON file must contain a flat list of acronym strings (uppercase)::

        ["DGPN", "DGGN", "DGSI", ...]

    Order is preserved so downstream CSV columns stay stable across runs.
    """
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise ValueError(
            f"Glossary file {path} must contain a JSON list, got {type(raw).__name__}."
        )
    if not all(isinstance(item, str) for item in raw):
        raise ValueError(f"Glossary file {path} must only contain strings.")
    return list(raw)


def load_audio_reference(path: Path) -> dict[str, int]:
    """Load the expected acronym counts for one audio from a JSON file.

    The JSON file must contain a flat object mapping acronym -> expected count::

        {"DGPN": 1, "ANTS": 2, ...}

    Only acronyms actually spoken in the audio need to be listed; any acronym
    from the glossary that is absent from this file is implicitly ``expected = 0``.
    """
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(
            f"Reference file {path} must contain a JSON object, got {type(raw).__name__}."
        )
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ValueError(f"Reference file {path}: keys must be strings.")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(
                f"Reference file {path}: value for {key!r} must be a non-negative int."
            )
    return dict(raw)
