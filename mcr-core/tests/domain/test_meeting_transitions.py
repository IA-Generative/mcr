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


class TestCompleteReport:
    def test_pending_to_done(self) -> None:
        meeting = _meeting(MeetingStatus.REPORT_PENDING)
        meeting_transitions.complete_report(meeting)
        assert meeting.status == MeetingStatus.REPORT_DONE

    @pytest.mark.parametrize(
        "status",
        [
            MeetingStatus.REPORT_DONE,
            MeetingStatus.REPORT_FAILED,
            MeetingStatus.TRANSCRIPTION_DONE,
        ],
    )
    def test_conflict_from_non_pending(self, status: MeetingStatus) -> None:
        meeting = _meeting(status)
        with pytest.raises(MeetingStateConflictException):
            meeting_transitions.complete_report(meeting)
        assert meeting.status == status


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


class TestFailReport:
    def test_pending_to_failed(self) -> None:
        meeting = _meeting(MeetingStatus.REPORT_PENDING)
        meeting_transitions.fail_report(meeting)
        assert meeting.status == MeetingStatus.REPORT_FAILED

    @pytest.mark.parametrize(
        "status",
        [
            MeetingStatus.REPORT_DONE,
            MeetingStatus.REPORT_FAILED,
            MeetingStatus.TRANSCRIPTION_DONE,
        ],
    )
    def test_conflict_from_non_pending(self, status: MeetingStatus) -> None:
        meeting = _meeting(status)
        with pytest.raises(MeetingStateConflictException):
            meeting_transitions.fail_report(meeting)
        assert meeting.status == status
