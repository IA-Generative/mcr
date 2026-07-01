"""Speaker-label formatting helper for the diarization processor."""

import re


def convert_to_french_speaker(speaker_label: str) -> str:
    """Convert speaker labels to French format"""
    return re.sub(r"SPEAKER_(\d+)", r"LOCUTEUR_\1", speaker_label)
