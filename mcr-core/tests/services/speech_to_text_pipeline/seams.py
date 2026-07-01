"""Centralized patch seams for the transcription golden test.

Each external leaf of the transcription pipeline (diarization loader, whisper
model, feature flags, LLM client, audio source) is patched at ONE place here.
When code moves between layers during the refacto, only the ``_SEAM_*``
constants below change — never the tests that consume them.

The seams mock the *stable leaves* (loaders / clients / HTTP), never the
wrapper classes that the refacto dissolves.
"""

import re
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from mcr_meeting.app.infrastructure.llm.client import CorrectedText
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    Participant,
    TranscriptionSegment,
)

# --- Seam targets: the single edit point per external dependency. ---
_SEAM_DIARIZATION_PIPELINE = (
    "mcr_meeting.app.infrastructure.diarization.get_diarization_pipeline"
)
_SEAM_DIARIZATION_FF = (
    "mcr_meeting.app.infrastructure.diarization.get_feature_flag_client"
)
_SEAM_TRANSCRIPTION_MODEL = (
    "mcr_meeting.app.infrastructure.transcription.get_transcription_model"
)
_SEAM_TRANSCRIPTION_FF = (
    "mcr_meeting.app.infrastructure.transcription.get_feature_flag_client"
)
_SEAM_PIPELINE_FF = (
    "mcr_meeting.app.services.speech_to_text.speech_to_text.get_feature_flag_client"
)
_SEAM_LLM_FROM_OPENAI = (
    "mcr_meeting.app.infrastructure.llm.client.instructor.from_openai"
)
_SEAM_AUDIO_SOURCE = (
    "mcr_meeting.app.use_cases.transcription.run_diarization.fetch_audio_bytes"
)


class _FakeFeatureFlagClient:
    def __init__(self, enabled: dict[str, bool]) -> None:
        self._enabled = enabled

    def is_enabled(self, feature_flag_name: str) -> bool:
        return self._enabled.get(str(feature_flag_name), False)


class _FakeLLMCompletions:
    def __init__(
        self,
        participants: list[Participant],
        participants_error: Exception | None,
    ) -> None:
        self._participants = participants
        self._participants_error = participants_error

    def create(self, *, response_model, messages, **kwargs):  # type: ignore[no-untyped-def]
        content = messages[-1]["content"]
        if response_model is CorrectedText:
            return CorrectedText(corrected_text=_last_delimited_block(content))
        if self._participants_error is not None:
            raise self._participants_error
        return list(self._participants)


def _last_delimited_block(content: str) -> str:
    blocks = re.findall(r"<<<(.*?)>>>", content, re.DOTALL)
    return blocks[-1].strip() if blocks else content


class TranscriptionSeams:
    def __init__(self, mocker: MockerFixture) -> None:
        self._mocker = mocker
        self._flags: dict[str, bool] = {}

    def install_feature_flags(self, **flags: bool) -> None:
        self._flags = {str(name): value for name, value in flags.items()}
        client = _FakeFeatureFlagClient(self._flags)
        for target in (_SEAM_PIPELINE_FF, _SEAM_DIARIZATION_FF, _SEAM_TRANSCRIPTION_FF):
            self._mocker.patch(target, return_value=client)

    def install_diarization(self, segments: list[DiarizationSegment]) -> None:
        pipeline = MagicMock()
        pipeline.return_value = MagicMock(
            itertracks=lambda yield_label: [
                (MagicMock(start=segment.start, end=segment.end), None, segment.speaker)
                for segment in segments
            ]
        )
        self._mocker.patch(_SEAM_DIARIZATION_PIPELINE, return_value=pipeline)

    def install_transcription(
        self, segments_per_chunk: list[list[TranscriptionSegment]]
    ) -> None:
        model = MagicMock()
        model.transcribe.side_effect = [
            (iter(segments), MagicMock()) for segments in segments_per_chunk
        ]
        self._mocker.patch(_SEAM_TRANSCRIPTION_MODEL, return_value=model)

    def install_llm(
        self,
        participants: list[Participant] | None = None,
        participants_error: Exception | None = None,
    ) -> None:
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=_FakeLLMCompletions(participants or [], participants_error)
            )
        )
        self._mocker.patch(_SEAM_LLM_FROM_OPENAI, return_value=fake_client)

    def install_audio_source(self, audio_bytes: BytesIO) -> None:
        self._mocker.patch(_SEAM_AUDIO_SOURCE, return_value=audio_bytes)


def make_participant(speaker_id: str, name: str | None) -> Participant:
    return Participant(
        speaker_id=speaker_id,
        name=name,
        role=None,
        confidence=0.9,
        association_justification="golden-test",
    )
