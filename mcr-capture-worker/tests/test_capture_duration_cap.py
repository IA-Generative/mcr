import time
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_mock import MockerFixture

from mcr_capture_worker.models.meeting_model import MeetingStatus
from mcr_capture_worker.services import meeting_audio_recorder as recorder_module
from mcr_capture_worker.services.meeting_audio_recorder import MeetingAudioRecorder


def _meeting(status: MeetingStatus) -> Mock:
    meeting = Mock()
    meeting.status = status
    return meeting


@pytest.fixture
def bot(mocker: MockerFixture) -> MeetingAudioRecorder:
    bot = MeetingAudioRecorder(meeting_id=0)
    bot.meeting_monitor = Mock()
    bot.meeting_monitor.enforce_bot_muted = AsyncMock()
    mocker.patch.object(bot, "stop_recording", AsyncMock())
    mocker.patch.object(recorder_module.asyncio, "sleep", AsyncMock())
    return bot


@pytest.mark.asyncio
async def test_capture_stops_once_it_outlives_the_max_duration_even_if_meeting_is_still_in_progress(
    mocker: MockerFixture, bot: MeetingAudioRecorder
) -> None:
    get_meeting = mocker.patch.object(
        recorder_module,
        "get_meeting",
        return_value=_meeting(MeetingStatus.CAPTURE_IN_PROGRESS),
    )
    bot._connected_at = (
        time.monotonic() - recorder_module.capture_settings.MAX_CAPTURE_DURATION_S - 1
    )

    await bot.wait_for_data_or_meeting_end(page=Mock())

    bot.stop_recording.assert_awaited_once()  # type: ignore[attr-defined]
    assert get_meeting.call_count == 1


@pytest.mark.asyncio
async def test_capture_keeps_running_until_meeting_leaves_in_progress_when_under_max_duration(
    mocker: MockerFixture, bot: MeetingAudioRecorder
) -> None:
    get_meeting = mocker.patch.object(
        recorder_module,
        "get_meeting",
        side_effect=[
            _meeting(MeetingStatus.CAPTURE_IN_PROGRESS),
            _meeting(MeetingStatus.CAPTURE_IN_PROGRESS),
            _meeting(MeetingStatus.CAPTURE_DONE),
        ],
    )
    bot._connected_at = time.monotonic()

    await bot.wait_for_data_or_meeting_end(page=Mock())

    bot.stop_recording.assert_awaited_once()  # type: ignore[attr-defined]
    assert get_meeting.call_count == 3
