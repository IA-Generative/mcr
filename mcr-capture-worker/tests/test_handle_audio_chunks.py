from unittest.mock import Mock

import pytest

from mcr_capture_worker.schemas.audio_capture_schema import OnDataAvailableBytesWrapper
from mcr_capture_worker.services.meeting_audio_recorder import MeetingAudioRecorder


@pytest.fixture(scope="function")
def mock_meeting_audio_recorder() -> MeetingAudioRecorder:
    bot = MeetingAudioRecorder(meeting_id=0)

    return bot


@pytest.mark.asyncio
async def test_handle_audio_chunks_success(
    mock_minio: Mock,
    mock_meeting_audio_recorder: MeetingAudioRecorder,
) -> None:
    bot = mock_meeting_audio_recorder

    data: OnDataAvailableBytesWrapper = {
        "js_bytes": [102, 97, 107, 101, 45, 100, 97, 116, 97]
    }  # This is b"fake-data"
    await bot.handle_data_available(data)
    await bot.pending_uploads.wait_for_all_to_finish()

    # Assert audio sent twice and incremented index
    assert mock_minio.put_object.call_count == 1
