"""Centralized patch seams for the transcription golden test.

Each external leaf of the transcription pipeline (diarization HTTP client,
transcription API client, feature flags, LLM client, audio source) is patched at
ONE place here. When code moves between layers during the refacto, only the
``_SEAM_*`` constants below change — never the tests that consume them.

The seams mock the *stable leaves* (clients / HTTP), never the wrapper classes
that the refacto dissolves.
"""

import re
from io import BytesIO
from threading import Lock
from types import SimpleNamespace
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from mcr_meeting.app.infrastructure import transcription as transcription_module
from mcr_meeting.app.infrastructure.llm.client import CorrectedText
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizationSegment,
    Participant,
    TranscriptionSegment,
)
from tests.mocks.in_memory_feature_flags import InMemoryFeatureFlagClient

# --- Seam targets: the single edit point per external dependency. ---
# Speech-to-text runs against remote APIs, so the leaf of each processor is its
# transport client, resolved lazily at call time.
_SEAM_DIARIZATION_HTTP = (
    "mcr_meeting.app.infrastructure.diarization.DiarizationProcessor._get_http_client"
)
_SEAM_TRANSCRIPTION_API = (
    "mcr_meeting.app.infrastructure.transcription."
    "TranscriptionProcessor._get_openai_client"
)
_SEAM_LLM_FROM_OPENAI = (
    "mcr_meeting.app.infrastructure.llm.client.instructor.from_openai"
)
_SEAM_AUDIO_SOURCE = "mcr_meeting.app.infrastructure.s3.fetch_audio_bytes"


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
    def __init__(
        self, mocker: MockerFixture, feature_flags: InMemoryFeatureFlagClient
    ) -> None:
        self._mocker = mocker
        self._feature_flags = feature_flags

    def install_feature_flags(self, **flags: bool) -> None:
        for name, enabled in flags.items():
            if enabled:
                self._feature_flags.enable(name)
            else:
                self._feature_flags.disable(name)

    def install_diarization(self, segments: list[DiarizationSegment]) -> None:
        """Fake the diarization job API: submit returns a job id, the first poll
        returns a completed job carrying ``segments``."""
        submit_response = MagicMock()
        submit_response.json.return_value = {"job_id": "job-golden"}

        status_response = MagicMock()
        status_response.json.return_value = {
            "status": "completed",
            "result": {
                "segments": [
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "speaker": segment.speaker,
                    }
                    for segment in segments
                ]
            },
        }

        client = MagicMock()
        client.post.return_value = submit_response
        client.get.return_value = status_response
        self._mocker.patch(_SEAM_DIARIZATION_HTTP, return_value=client)

    def install_transcription(
        self, segments_per_chunk: list[list[TranscriptionSegment]]
    ) -> None:
        """Fake the transcription API, one canned response per chunk.

        Chunks are dealt out in call order, so the golden test pins the pool to a
        single worker (see ``_pin_serial_chunk_transcription``). Concurrency and
        out-of-order completion are covered by test_parallel_chunk_transcription.
        """
        self._pin_serial_chunk_transcription()

        remaining = list(segments_per_chunk)
        lock = Lock()

        def create(**kwargs: object) -> SimpleNamespace:
            with lock:
                segments = remaining.pop(0)
            return SimpleNamespace(
                segments=[
                    SimpleNamespace(
                        start=segment.start, end=segment.end, text=segment.text
                    )
                    for segment in segments
                ]
            )

        client = SimpleNamespace(
            audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
        )
        self._mocker.patch(_SEAM_TRANSCRIPTION_API, return_value=client)

    def _pin_serial_chunk_transcription(self) -> None:
        self._mocker.patch.object(
            transcription_module.api_settings, "MAX_CONCURRENT_CHUNKS", 1
        )

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
        # Reset the lazy singleton so this test's client is built from the
        # patched from_openai (and the cache is restored after the test).
        self._mocker.patch(
            "mcr_meeting.app.infrastructure.llm.client._client", new=None
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
