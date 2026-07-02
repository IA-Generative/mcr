"""Golden parity test — the real gate of the transcription refacto.

Asserts the full ``list[SpeakerTranscription]`` returned by the end-to-end
transcription flow (today ``transcribe_meeting``, tomorrow the composition of
the 3 phase use-cases). The invariant is that this output stays byte-identical
across every step of the refacto.

All external leaves are mocked through the centralized ``transcription_seams``
so the real domain transforms (chunking, VAD, merge, hallucination removal,
LLM text splitting/reassembly, participant reconciliation) run for real.
"""

from collections.abc import Callable
from io import BytesIO

from mcr_meeting.app.infrastructure import speech_to_text_models
from mcr_meeting.app.infrastructure.diarization import DiarizationProcessor
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    SpeakerTranscription,
    TranscriptionSegment,
)
from mcr_meeting.app.use_cases.transcription.run_diarization import run_diarization
from mcr_meeting.app.use_cases.transcription.run_finalize_transcription import (
    run_finalize_transcription,
)
from mcr_meeting.app.use_cases.transcription.run_transcribe_chunks import (
    run_transcribe_chunks,
)
from tests.services.speech_to_text_pipeline.seams import (
    TranscriptionSeams,
    make_participant,
)

MEETING_ID = 123


def _transcribe(meeting_id: int) -> list[SpeakerTranscription]:
    # Providers are read off the module at call time, after the seams patched it.
    artifact = run_diarization(
        meeting_id,
        DiarizationProcessor(speech_to_text_models.get_diarization_pipeline),
    )
    segments = run_transcribe_chunks(
        artifact,
        TranscriptionProcessor(speech_to_text_models.get_transcription_model),
    )
    return run_finalize_transcription(meeting_id, segments)


_LOCAL_MODEL_FLAGS = dict(
    audio_phase_aware_downmix=False,
    audio_noise_filtering=False,
    api_based_diarization=False,
    api_based_transcription=False,
    spelling_correction=False,
)


def test_multi_speaker_golden(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
) -> None:
    transcription_seams.install_feature_flags(**_LOCAL_MODEL_FLAGS)
    transcription_seams.install_audio_source(create_audio_buffer("wav"))
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(participants=[])

    result = _transcribe(MEETING_ID)

    assert all(isinstance(item, SpeakerTranscription) for item in result)
    assert all(item.meeting_id == MEETING_ID for item in result)
    assert [item.transcription_index for item in result] == [0, 1, 2, 3]
    assert [item.speaker for item in result] == [
        "Intervenant 1",
        "Intervenant 2",
        "Intervenant 1",
        "Intervenant 2",
    ]
    assert "1st segment" in result[0].transcription
    assert "2nd segment" in result[0].transcription
    assert "3rd segment" in result[1].transcription
    assert "6th segment" in result[2].transcription
    assert "7th segment" in result[3].transcription
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
    transcription_seams.install_feature_flags(**_LOCAL_MODEL_FLAGS)
    transcription_seams.install_audio_source(create_audio_buffer("wav"))
    transcription_seams.install_diarization(diarization_result_single_speaker)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(participants=[])

    result = _transcribe(MEETING_ID)

    assert len(result) == 1
    assert result[0].transcription_index == 0
    assert result[0].speaker == "Intervenant 1"
    assert "1st segment" in result[0].transcription
    assert "2nd segment" in result[0].transcription
    assert "3rd segment" in result[0].transcription


def test_empty_diarization_returns_empty(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_empty: list[DiarizationSegment],
) -> None:
    transcription_seams.install_feature_flags(**_LOCAL_MODEL_FLAGS)
    transcription_seams.install_audio_source(create_audio_buffer("wav"))
    transcription_seams.install_diarization(diarization_result_empty)
    transcription_seams.install_transcription([])
    transcription_seams.install_llm(participants=[])

    result = _transcribe(MEETING_ID)

    assert result == []


def test_enrich_participants_failure_keeps_raw_labels(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
) -> None:
    transcription_seams.install_feature_flags(**_LOCAL_MODEL_FLAGS)
    transcription_seams.install_audio_source(create_audio_buffer("wav"))
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(
        participants_error=RuntimeError("LLM participant extraction failed")
    )

    result = _transcribe(MEETING_ID)

    assert [item.speaker for item in result] == [
        "Intervenant 1",
        "Intervenant 2",
        "Intervenant 1",
        "Intervenant 2",
    ]


def test_participant_names_replace_speaker_labels(
    transcription_seams: TranscriptionSeams,
    create_audio_buffer: Callable[[str], BytesIO],
    diarization_result_multiple_speakers: list[DiarizationSegment],
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
) -> None:
    transcription_seams.install_feature_flags(**_LOCAL_MODEL_FLAGS)
    transcription_seams.install_audio_source(create_audio_buffer("wav"))
    transcription_seams.install_diarization(diarization_result_multiple_speakers)
    transcription_seams.install_transcription(mock_transcription_segments_normal)
    transcription_seams.install_llm(
        participants=[
            make_participant("Intervenant 1", "Alice"),
            make_participant("Intervenant 2", "Bob"),
        ]
    )

    result = _transcribe(MEETING_ID)

    assert [item.speaker for item in result] == ["Alice", "Bob", "Alice", "Bob"]
