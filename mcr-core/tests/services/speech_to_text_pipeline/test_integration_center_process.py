"""Test integration of the shared transcribe_diarized_audio step."""

from io import BytesIO

import pytest

from mcr_meeting.app.configs.base import WhisperTranscriptionSettings
from mcr_meeting.app.exceptions.exceptions import (
    DiarizationError,
    TranscriptionError,
)
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.use_cases.transcription._shared.transcribe_diarized_audio import (
    transcribe_diarized_audio,
)
from tests.services.speech_to_text_pipeline.seams import TranscriptionSeams

transcription_settings = WhisperTranscriptionSettings()
M = transcription_settings.MAX_CHUNK_DURATION


def run_the_code_to_test(
    pre_processed_audio_bytes: BytesIO,
) -> list[DiarizedTranscriptionSegment]:
    diarization_result = DiarizationProcessor().diarize(
        audio_bytes=pre_processed_audio_bytes
    )

    if not diarization_result:
        return []

    return transcribe_diarized_audio(
        pre_processed_audio_bytes,
        diarization_result,
        TranscriptionProcessor(),
    )


@pytest.mark.parametrize(
    "diarization_fixture,transcription_fixture,expected_segments_count,expected_speakers",
    [
        (
            "diarization_result_multiple_speakers",
            "mock_transcription_segments_normal",
            7,
            [
                "Intervenant 1",
                "Intervenant 1",
                "Intervenant 2",
                "Intervenant 2",
                "Intervenant 2",
                "Intervenant 1",
                "Intervenant 2",
            ],
        ),
        (
            "diarization_result_single_speaker",
            "mock_transcription_segments_normal",
            3,
            ["Intervenant 1", "Intervenant 1", "Intervenant 1"],
        ),
    ],
)
def test_integration_center_process_normal_flow(
    transcription_seams: TranscriptionSeams,
    diarization_fixture: str,
    transcription_fixture: str,
    expected_segments_count: int,
    expected_speakers: list[str],
    pre_processed_audio_bytes: BytesIO,
    request: pytest.FixtureRequest,
) -> None:
    diarization_result = request.getfixturevalue(diarization_fixture)
    transcription_segments_list = request.getfixturevalue(transcription_fixture)

    transcription_seams.install_diarization(diarization_result)
    transcription_seams.install_transcription(transcription_segments_list)

    transcription_segments = run_the_code_to_test(pre_processed_audio_bytes)

    assert len(transcription_segments) == expected_segments_count
    assert all(
        isinstance(seg, DiarizedTranscriptionSegment) for seg in transcription_segments
    )

    speakers_succession = [seg.speaker for seg in transcription_segments]
    assert speakers_succession == expected_speakers

    assert all(seg.start >= 0 for seg in transcription_segments)
    assert all(seg.end > seg.start for seg in transcription_segments)

    assert transcription_segments[0].id == 0
    assert transcription_segments[1].id == 0
    assert transcription_segments[1].start == 1.51
    assert transcription_segments[1].end == 3.0
    assert transcription_segments[1].text == "2nd segment"
    assert transcription_segments[1].speaker == "Intervenant 1"

    if expected_segments_count >= 7:
        assert transcription_segments[3].id == 2
        assert transcription_segments[3].start == 2 * M
        assert transcription_segments[3].end == 2 * M + 2.0
        assert transcription_segments[3].text == "4th segment"
        assert transcription_segments[3].speaker == "Intervenant 2"

        assert transcription_segments[5].id == 3
        assert transcription_segments[5].text == "6th segment"
        assert transcription_segments[5].speaker == "Intervenant 1"

        assert transcription_segments[6].id == 3
        assert transcription_segments[6].text == "7th segment"
        assert transcription_segments[6].speaker == "Intervenant 2"


def test_integration_center_process_empty_diarization(
    transcription_seams: TranscriptionSeams,
    pre_processed_audio_bytes: BytesIO,
) -> None:
    """A meeting where the API detects no speaker fails instead of yielding an
    empty transcription.

    The removed local path returned no segments and the pipeline degraded to an
    empty transcription; the diarization API reports a completed job with no
    segments as an error. Pinned here so the trade-off can't change unnoticed.
    """
    transcription_seams.install_diarization([])

    with pytest.raises(DiarizationError):
        run_the_code_to_test(pre_processed_audio_bytes)


def test_a_chunk_without_speech_fails_the_transcription(
    transcription_seams: TranscriptionSeams,
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_with_empty: list[list[TranscriptionSegment]],
    pre_processed_audio_bytes: BytesIO,
) -> None:
    """A chunk the API returns no segments for aborts the whole transcription.

    The removed local path skipped such a chunk and kept the rest; the API path
    treats it as an error, so the meeting fails instead of losing a chunk
    silently. Asserted here so the trade-off can't change unnoticed.
    """
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription(mock_transcription_segments_with_empty)

    with pytest.raises(TranscriptionError):
        run_the_code_to_test(pre_processed_audio_bytes)
