import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Lock
from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture

from mcr_meeting.app.exceptions.exceptions import TranscriptionError
from mcr_meeting.app.infrastructure.transcription import (
    TranscriptionProcessor,
    api_settings,
)
from mcr_meeting.app.schemas.transcription_schema import (
    TimeSpan,
    TranscriptionInput,
    TranscriptionSegment,
)

_SEAM_SPLIT_AUDIO = (
    "mcr_meeting.app.infrastructure.transcription.split_audio_on_timestamps"
)
_SEAM_API_MODE = (
    "mcr_meeting.app.infrastructure.transcription."
    "TranscriptionProcessor._is_api_transcription_enabled"
)
_SEAM_CHUNK_TRANSCRIBE = (
    "mcr_meeting.app.infrastructure.transcription."
    "TranscriptionProcessor._transcribe_audio_chunk"
)
_SEAM_POOL = "mcr_meeting.app.infrastructure.transcription.ThreadPoolExecutor"


def _make_transcription_inputs(chunk_count: int) -> list[TranscriptionInput]:
    # each chunk's audio is filled with its index so mocked transcription
    # can recover which chunk it received regardless of call order
    return [
        TranscriptionInput(
            audio=np.full(4, idx, dtype=np.float32),
            span=TimeSpan(start=idx * 10.0, end=(idx + 1) * 10.0),
        )
        for idx in range(chunk_count)
    ]


def _expected_sequential_output(
    inputs: list[TranscriptionInput],
    segments_per_chunk: list[list[TranscriptionSegment]],
) -> list[TranscriptionSegment]:
    return [
        TranscriptionSegment(
            id=idx,
            start=segment.start + chunk.span.start,
            end=segment.end + chunk.span.start,
            text=segment.text,
        )
        for idx, chunk in enumerate(inputs)
        for segment in segments_per_chunk[idx]
    ]


def test_output_identical_when_chunks_complete_out_of_order(
    mocker: MockerFixture,
    mock_transcription_segments_normal: list[list[TranscriptionSegment]],
) -> None:
    inputs = _make_transcription_inputs(4)
    mocker.patch(_SEAM_SPLIT_AUDIO, return_value=inputs)
    mocker.patch(_SEAM_API_MODE, return_value=True)
    mocker.patch.object(api_settings, "MAX_CONCURRENT_CHUNKS", 4)

    completion_order: list[int] = []
    completion_lock = Lock()

    def delayed_transcribe(
        audio: np.ndarray, transcription_model: MagicMock
    ) -> list[TranscriptionSegment]:
        idx = int(audio[0])
        time.sleep(0.05 * (len(inputs) - idx))
        with completion_lock:
            completion_order.append(idx)
        return mock_transcription_segments_normal[idx]

    mocker.patch(_SEAM_CHUNK_TRANSCRIBE, side_effect=delayed_transcribe)

    result = TranscriptionProcessor(MagicMock()).transcribe(BytesIO(), [])

    assert completion_order == [3, 2, 1, 0]
    assert result == _expected_sequential_output(
        inputs, mock_transcription_segments_normal
    )


@pytest.mark.parametrize(
    ("fixture_name", "chunk_count"),
    [
        ("mock_transcription_segments_normal", 2),
        ("mock_transcription_segments_normal", 4),
        ("mock_transcription_segments_with_empty", 4),
    ],
)
def test_parallel_output_matches_sequential_baseline(
    request: pytest.FixtureRequest,
    mocker: MockerFixture,
    fixture_name: str,
    chunk_count: int,
) -> None:
    segments_per_chunk = request.getfixturevalue(fixture_name)[:chunk_count]
    inputs = _make_transcription_inputs(chunk_count)
    mocker.patch(_SEAM_SPLIT_AUDIO, return_value=inputs)
    mocker.patch(_SEAM_API_MODE, return_value=True)
    mocker.patch(
        _SEAM_CHUNK_TRANSCRIBE,
        side_effect=lambda audio, transcription_model: segments_per_chunk[
            int(audio[0])
        ],
    )

    result = TranscriptionProcessor(MagicMock()).transcribe(BytesIO(), [])

    assert result == _expected_sequential_output(inputs, segments_per_chunk)


def test_pool_bounded_by_max_concurrent_chunks_in_api_mode(
    mocker: MockerFixture,
) -> None:
    mocker.patch(_SEAM_SPLIT_AUDIO, return_value=_make_transcription_inputs(2))
    mocker.patch(_SEAM_API_MODE, return_value=True)
    mocker.patch(_SEAM_CHUNK_TRANSCRIBE, return_value=[])
    pool_spy = mocker.patch(_SEAM_POOL, wraps=ThreadPoolExecutor)

    TranscriptionProcessor(MagicMock()).transcribe(BytesIO(), [])

    pool_spy.assert_called_once_with(max_workers=api_settings.MAX_CONCURRENT_CHUNKS)


def test_pool_capped_to_one_in_local_mode(mocker: MockerFixture) -> None:
    mocker.patch(_SEAM_SPLIT_AUDIO, return_value=_make_transcription_inputs(2))
    mocker.patch(_SEAM_API_MODE, return_value=False)
    mocker.patch(_SEAM_CHUNK_TRANSCRIBE, return_value=[])
    pool_spy = mocker.patch(_SEAM_POOL, wraps=ThreadPoolExecutor)

    TranscriptionProcessor(MagicMock()).transcribe(BytesIO(), [])

    pool_spy.assert_called_once_with(max_workers=1)


def test_chunk_error_propagates(mocker: MockerFixture) -> None:
    mocker.patch(_SEAM_SPLIT_AUDIO, return_value=_make_transcription_inputs(3))
    mocker.patch(_SEAM_API_MODE, return_value=True)

    def failing_transcribe(
        audio: np.ndarray, transcription_model: MagicMock
    ) -> list[TranscriptionSegment]:
        if int(audio[0]) == 1:
            raise TranscriptionError("chunk failed")
        return []

    mocker.patch(_SEAM_CHUNK_TRANSCRIBE, side_effect=failing_transcribe)

    with pytest.raises(TranscriptionError):
        TranscriptionProcessor(MagicMock()).transcribe(BytesIO(), [])
