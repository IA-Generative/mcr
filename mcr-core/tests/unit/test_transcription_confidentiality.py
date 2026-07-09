import json
from collections.abc import Iterator
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest
import sentry_sdk
from pytest_mock import MockerFixture
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from mcr_meeting.app.exceptions.exceptions import TranscriptionError
from mcr_meeting.app.infrastructure.sentry import init_sentry
from mcr_meeting.app.infrastructure.transcription import TranscriptionProcessor
from mcr_meeting.app.schemas.transcription_schema import (
    DiarizedTranscriptionSegment,
    TimeSpan,
    TranscriptionInput,
    TranscriptionSegment,
)

SECRET_TEXT = "phrase-strictement-confidentielle-de-reunion"


def test_init_sentry_disables_local_variables_capture(
    mocker: MockerFixture,
) -> None:
    sentry_init = mocker.patch("mcr_meeting.app.infrastructure.sentry.sentry_sdk.init")

    init_sentry()

    assert sentry_init.call_args.kwargs["include_local_variables"] is False


def test_transcription_segment_repr_and_str_mask_text() -> None:
    segment = TranscriptionSegment(id=0, start=0.0, end=1.0, text=SECRET_TEXT)

    assert SECRET_TEXT not in repr(segment)
    assert SECRET_TEXT not in str(segment)


def test_diarized_segment_repr_and_str_mask_text() -> None:
    segment = DiarizedTranscriptionSegment(
        id=0, start=0.0, end=1.0, text=SECRET_TEXT, speaker="Intervenant 1"
    )

    assert SECRET_TEXT not in repr(segment)
    assert SECRET_TEXT not in str(segment)


class _CapturingTransport(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        event = envelope.get_event()
        if event is not None:
            self.events.append(event)


@pytest.fixture
def sentry_capture() -> Iterator[_CapturingTransport]:
    transport = _CapturingTransport()
    # mirror the prod init_sentry() config under test: locals capture off
    sentry_sdk.init(transport=transport, include_local_variables=False)
    yield transport
    sentry_sdk.init()


def test_transcription_error_event_leaks_no_transcript_text(
    mocker: MockerFixture,
    sentry_capture: _CapturingTransport,
) -> None:
    inputs = [
        TranscriptionInput(
            audio=np.zeros(4, dtype=np.float32), span=TimeSpan(0.0, 10.0)
        )
    ]
    mocker.patch(
        "mcr_meeting.app.infrastructure.transcription.split_audio_on_timestamps",
        return_value=inputs,
    )
    mocker.patch(
        "mcr_meeting.app.infrastructure.transcription."
        "TranscriptionProcessor._is_api_transcription_enabled",
        return_value=True,
    )

    def leaky_transcribe(
        audio: np.ndarray, transcription_model: MagicMock
    ) -> list[TranscriptionSegment]:
        # transcript text held in frame locals, like the real API/whisper path
        leaked_segments = [
            TranscriptionSegment(id=0, start=0.0, end=1.0, text=SECRET_TEXT)
        ]
        raise TranscriptionError(
            f"Transcription API returned no segments ({len(leaked_segments)} local)"
        )

    mocker.patch(
        "mcr_meeting.app.infrastructure.transcription."
        "TranscriptionProcessor._transcribe_audio_chunk",
        side_effect=leaky_transcribe,
    )

    with pytest.raises(TranscriptionError) as error:
        TranscriptionProcessor(MagicMock()).transcribe(BytesIO(), [])

    sentry_sdk.capture_exception(error.value)
    sentry_sdk.flush()

    assert sentry_capture.events
    assert SECRET_TEXT not in json.dumps(sentry_capture.events, default=str)
