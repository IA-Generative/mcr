"""Fixtures for speech-to-text pipeline integration tests."""

from io import BytesIO

import pytest
from pydub.generators import Sine


@pytest.fixture
def create_audio_buffer():
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
        if audio_format == "mp3":
            sine_wave.export(audio_buffer, format="mp3", bitrate="128k")
        elif audio_format == "mp4":
            sine_wave.export(audio_buffer, format="mp4", codec="aac")
        elif audio_format == "m4a":
            sine_wave.export(audio_buffer, format="ipod", codec="aac")
        elif audio_format == "mov":
            sine_wave.export(audio_buffer, format="mov", codec="aac")
        else:
            # For wav - use default settings
            sine_wave.export(audio_buffer, format=audio_format)

        audio_buffer.seek(0)
        return audio_buffer

    return _create_buffer
