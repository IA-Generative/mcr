import pytest

from mcr_meeting.app.domain import meeting_transitions
from mcr_meeting.app.exceptions.exceptions import MeetingStateConflictException
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingPlatforms


def _meeting(
    status: MeetingStatus, name_platform: MeetingPlatforms = MeetingPlatforms.COMU
) -> Meeting:
    return Meeting(id=1, status=status, name_platform=name_platform)


_ALL_PLATFORMS = [
    MeetingPlatforms.COMU,
    MeetingPlatforms.MCR_RECORD,
    MeetingPlatforms.MCR_IMPORT,
]


class TestStartTranscription:
    def test_pending_to_in_progress(self) -> None:
        meeting = _meeting(MeetingStatus.TRANSCRIPTION_PENDING)
        meeting_transitions.start_transcription(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_IN_PROGRESS

    @pytest.mark.parametrize(
        "status",
        [
            MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            MeetingStatus.TRANSCRIPTION_DONE,
            MeetingStatus.TRANSCRIPTION_FAILED,
            MeetingStatus.CAPTURE_DONE,
        ],
    )
    def test_conflict_from_non_pending(self, status: MeetingStatus) -> None:
        meeting = _meeting(status)
        with pytest.raises(MeetingStateConflictException):
            meeting_transitions.start_transcription(meeting)
        assert meeting.status == status


class TestForcedRequeue:
    @pytest.mark.parametrize("platform", _ALL_PLATFORMS)
    @pytest.mark.parametrize(
        "status",
        [
            MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            MeetingStatus.TRANSCRIPTION_FAILED,
        ],
    )
    def test_requeueable_back_to_pending(
        self, status: MeetingStatus, platform: MeetingPlatforms
    ) -> None:
        meeting = _meeting(status, platform)
        meeting_transitions.forced_requeue(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING

    @pytest.mark.parametrize("platform", _ALL_PLATFORMS)
    def test_pending_self_loop_is_a_noop(self, platform: MeetingPlatforms) -> None:
        meeting = _meeting(MeetingStatus.TRANSCRIPTION_PENDING, platform)
        meeting_transitions.forced_requeue(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING

    @pytest.mark.parametrize("platform", _ALL_PLATFORMS)
    @pytest.mark.parametrize(
        "status",
        [
            MeetingStatus.TRANSCRIPTION_DONE,
            MeetingStatus.REPORT_PENDING,
            MeetingStatus.REPORT_DONE,
        ],
    )
    def test_conflict_from_non_requeueable(
        self, status: MeetingStatus, platform: MeetingPlatforms
    ) -> None:
        meeting = _meeting(status, platform)
        with pytest.raises(MeetingStateConflictException):
            meeting_transitions.forced_requeue(meeting)
        assert meeting.status == status


class TestInitTranscriptionAfterFailedCapture:
    @pytest.mark.parametrize(
        "platform", [MeetingPlatforms.COMU, MeetingPlatforms.MCR_RECORD]
    )
    def test_swept_capture_can_still_reach_transcription(
        self, platform: MeetingPlatforms
    ) -> None:
        meeting = _meeting(MeetingStatus.CAPTURE_FAILED, platform)
        meeting_transitions.init_transcription(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING

    def test_capture_in_progress_can_reach_transcription_for_local_records(
        self,
    ) -> None:
        meeting = _meeting(
            MeetingStatus.CAPTURE_IN_PROGRESS, MeetingPlatforms.MCR_RECORD
        )
        meeting_transitions.init_transcription(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING

    def test_sweeping_then_recovering_ends_in_transcription(self) -> None:
        meeting = _meeting(
            MeetingStatus.CAPTURE_IN_PROGRESS, MeetingPlatforms.MCR_RECORD
        )
        meeting_transitions.fail_capture(meeting)
        assert meeting.status == MeetingStatus.CAPTURE_FAILED

        meeting_transitions.init_transcription(meeting)
        assert meeting.status == MeetingStatus.TRANSCRIPTION_PENDING
