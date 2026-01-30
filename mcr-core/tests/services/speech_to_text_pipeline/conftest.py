"""Fixtures for speech-to-text pipeline integration tests."""

from io import BytesIO
from typing import Callable

import pytest
from pydub.generators import Sine

from mcr_meeting.app.schemas.transcription_schema import TranscriptionSegment
from mcr_meeting.app.services.speech_to_text.types import DiarizationSegment


@pytest.fixture
def diarization_result_multiple_speakers() -> list[DiarizationSegment]:
    """Mock diarization result with multiple speakers.

    Note: Segments have gaps > MAX_SILENCE_GAP to prevent VAD merging.
    """
    return [
        DiarizationSegment(start=0.0, end=3.0, speaker="Intervenant 1"),
        DiarizationSegment(start=4.0, end=6.0, speaker="Intervenant 2"),
        DiarizationSegment(start=7.0, end=10.0, speaker="Intervenant 2"),
        DiarizationSegment(start=11.0, end=12.0, speaker="Intervenant 1"),
        DiarizationSegment(start=12.01, end=13.0, speaker="Intervenant 2"),
    ]


@pytest.fixture
def diarization_result_single_speaker() -> list[DiarizationSegment]:
    """Mock diarization result with single speaker."""
    return [
        DiarizationSegment(start=0.0, end=5.0, speaker="Intervenant 1"),
        DiarizationSegment(start=6.0, end=10.0, speaker="Intervenant 1"),
    ]


@pytest.fixture
def diarization_result_empty() -> list[DiarizationSegment]:
    """Empty diarization result."""
    return []


@pytest.fixture
def mock_transcription_segments_normal() -> list[list[TranscriptionSegment]]:
    """Normal transcription segments for each chunk."""
    return [
        [
            TranscriptionSegment(id=0, start=0.0, end=1.5, text="1st segment"),
            TranscriptionSegment(id=1, start=1.5, end=3.0, text="2nd segment"),
        ],
        [
            TranscriptionSegment(id=0, start=0.0, end=2.0, text="3rd segment"),
        ],
        [
            TranscriptionSegment(id=0, start=0.0, end=2.0, text="4th segment"),
            TranscriptionSegment(id=0, start=2.0, end=3.0, text="5th segment"),
        ],
        [
            TranscriptionSegment(id=0, start=0.2, end=1.1, text="6th segment"),
            TranscriptionSegment(id=0, start=1.2, end=1.6, text="7th segment"),
        ],
    ]


@pytest.fixture
def mock_transcription_segments_with_empty() -> list[list[TranscriptionSegment]]:
    """Transcription segments with some empty chunks."""
    return [
        [TranscriptionSegment(id=0, start=0.0, end=1.0, text="1st segment")],
        [],  # Empty chunk
        [TranscriptionSegment(id=0, start=0.0, end=1.0, text="3rd segment")],
        [],  # Empty chunk
    ]


@pytest.fixture
def pre_processed_audio_bytes(create_audio_buffer: Callable[[str], BytesIO]) -> BytesIO:
    """Create pre-processed audio bytes for testing."""
    return create_audio_buffer("wav")


@pytest.fixture
def create_audio_buffer() -> Callable[[str], BytesIO]:
    """Factory fixture to create audio buffers in different formats.

    This fixture returns a factory function that creates audio test files
    in various formats (mp3, mp4, m4a, wav, mov) for testing audio processing.

    Usage:
        def test_something(create_audio_buffer):
            mp3_buffer = create_audio_buffer("mp3")
            wav_buffer = create_audio_buffer("wav")
    """

    def _create_buffer(audio_format: str) -> BytesIO:
        """Create a small test audio file in memory with the specified format.

        Args:
            audio_format: The audio format (mp3, mp4, m4a, wav, mov)

        Returns:
            BytesIO: Buffer containing the audio data
        """
        # Generate a 1-second sine wave at 440Hz (A note)
        sine_wave = Sine(440).to_audio_segment(duration=1000)

        # Export to specified format in memory
        audio_buffer = BytesIO()

        # Set format-specific parameters
        match audio_format:
            case "mp3":
                sine_wave.export(audio_buffer, format="mp3", bitrate="128k")
            case "mp4":
                sine_wave.export(audio_buffer, format="mp4", codec="aac")
            case "m4a":
                sine_wave.export(audio_buffer, format="ipod", codec="aac")
            case "mov":
                sine_wave.export(audio_buffer, format="mov", codec="aac")
            case "wav":
                sine_wave.export(audio_buffer, format=audio_format)
            case _:
                raise ValueError(f"Unsupported audio format: {audio_format}")

        audio_buffer.seek(0)
        return audio_buffer

    return _create_buffer
