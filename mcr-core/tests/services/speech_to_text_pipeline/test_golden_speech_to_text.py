from collections.abc import Callable
from io import BytesIO

import pytest
from pytest_mock import MockerFixture

from mcr_meeting.app.exceptions.exceptions import (
    DiarizationError,
    InvalidAudioFileError,
    TranscriptionError,
)
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    DiarizedTranscriptionSegment,
    TranscriptionSegment,
)
from mcr_meeting.app.use_cases.transcription.run_speech_to_text import (
    run_speech_to_text,
)
from tests.services.speech_to_text_pipeline.seams import TranscriptionSeams


def _transcribe(audio_bytes: BytesIO) -> list[DiarizedTranscriptionSegment]:
    return run_speech_to_text(
        audio_bytes,
        DiarizationProcessor(),
        TranscriptionProcessor(),
    )


_BASE_FLAGS = dict(
    audio_phase_aware_downmix=False,
    audio_noise_filtering=False,
    spelling_correction=False,
)


@pytest.mark.parametrize("spelling_correction", [False, True])
def test_multi_speaker_golden(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
    spelling_correction: bool,
) -> None:
    transcription_seams.install_feature_flags(
        **{**_BASE_FLAGS, "spelling_correction": spelling_correction}
    )
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(participants=[])

    result = _transcribe(create_audio_buffer("wav"))

    assert all(isinstance(item, DiarizedTranscriptionSegment) for item in result)
    assert [item.speaker for item in result] == [
        "Intervenant 1",
        "Intervenant 2",
        "Intervenant 1",
        "Intervenant 2",
    ]
    assert "1st segment" in result[0].text
    assert "2nd segment" in result[0].text
    assert "3rd segment" in result[1].text
    assert "6th segment" in result[2].text
    assert "7th segment" in result[3].text
    assert result[0].start == 0.0
    assert all(item.end > item.start for item in result)
    for previous, current in zip(result, result[1:]):
        assert previous.start <= current.start


def test_single_speaker_golden(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_single_speaker: list[DiarizationSegment],
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
) -> None:
    transcription_seams.install_feature_flags(**_BASE_FLAGS)
    transcription_seams.install_diarization(diarization_result_single_speaker)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(participants=[])

    result = _transcribe(create_audio_buffer("wav"))

    assert len(result) == 1
    assert result[0].speaker == "Intervenant 1"
    assert "1st segment" in result[0].text
    assert "2nd segment" in result[0].text
    assert "3rd segment" in result[0].text


def test_empty_diarization_fails_the_transcription(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_empty: list[DiarizationSegment],
) -> None:
    """A meeting where the API detects no speaker fails instead of yielding an
    empty transcription.

    The removed local path returned no segments and the pipeline degraded to an
    empty transcription; the diarization API reports a completed job with no
    segments as an error. Pinned here so the trade-off can't change unnoticed.
    """
    transcription_seams.install_feature_flags(**_BASE_FLAGS)
    transcription_seams.install_diarization(diarization_result_empty)
    transcription_seams.install_transcription([])
    transcription_seams.install_llm(participants=[])

    with pytest.raises(DiarizationError):
        _transcribe(create_audio_buffer("wav"))


def test_audio_without_any_speech_fails_the_transcription(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_multiple_speakers: list[DiarizationSegment],
) -> None:
    """Audio the API transcribes to nothing fails, as TranscriptionError.

    The removed local path let every chunk come back empty and surfaced the
    emptiness later as InvalidAudioFileError; the API rejects the first empty
    chunk. Only the exception type changes — the transcription still fails.
    """
    transcription_seams.install_feature_flags(**_BASE_FLAGS)
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription([[], [], [], []])
    transcription_seams.install_llm(participants=[])

    with pytest.raises(TranscriptionError):
        _transcribe(create_audio_buffer("wav"))


def test_invalid_audio_when_vad_attributes_no_segment_to_a_speaker(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
    mocker: MockerFixture,
) -> None:
    """The InvalidAudioFileError guard stays reachable: the API can return
    segments that VAD then attributes to no speaker at all."""
    transcription_seams.install_feature_flags(**_BASE_FLAGS)
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(participants=[])
    mocker.patch(
        "mcr_meeting.app.use_cases.transcription._shared."
        "transcribe_diarized_audio.diarize_vad_transcription_segments",
        return_value=[],
    )

    with pytest.raises(InvalidAudioFileError):
        _transcribe(create_audio_buffer("wav"))
