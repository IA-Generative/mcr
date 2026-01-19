from typing import List

import pytest

from mcr_meeting.app.schemas.transcription_schema import TranscriptionSegment

segment_data_list = [
    {
        "id": 0,
        "text": "Hello there.",
        "start": 1.0,
        "end": 2.0,
        "no_speech_prob": 0.2,
        "avg_logprob": -0.35,
        "compression_ratio": 1.1,
        "seek": 0,
        "temperature": 0.0,
        "tokens": [50257, 1234, 5678],
        "words": [
            {"text": "Hello", "start": 1.0, "end": 1.5, "confidence": 0.93},
            {"text": "there.", "start": 1.6, "end": 2.0, "confidence": 0.91},
        ],
        "confidence": 0.2,
    },
    {
        "id": 1,
        "text": "World!",
        "start": 3.0,
        "end": 4.0,
        "no_speech_prob": 0.2,
        "avg_logprob": -0.4,
        "compression_ratio": 1.2,
        "seek": 150,
        "temperature": 0.2,
        "tokens": [50257, 2345, 6789, 91011],
        "words": [
            {"text": "World!", "start": 3.0, "end": 4.0, "confidence": 0.94},
        ],
        "confidence": 0.94,
    },
    {
        "id": 2,
        "text": "Sous-titrage ST' ST'",
        "start": 5.0,
        "end": 6.5,
        "no_speech_prob": 0.8,
        "avg_logprob": -0.38,
        "compression_ratio": 1.05,
        "seek": 300,
        "temperature": 0.1,
        "tokens": [50257, 3456, 7890, 11213, 1415],
        "words": [
            {"text": "Sous-titrage", "start": 5.0, "end": 5.5, "confidence": 0.96},
            {"text": "ST',", "start": 5.5, "end": 6.0, "confidence": 0.92},
            {"text": "ST'", "start": 6.0, "end": 6.5, "confidence": 0.93},
        ],
        "confidence": 0.94,
    },
]


@pytest.fixture
def segment_fixture_list() -> List[TranscriptionSegment]:
    segments = [TranscriptionSegment(**data) for data in segment_data_list]

    return segments
