import pytest

from mcr_meeting.app.domain import meeting_transitions
from mcr_meeting.app.exceptions.exceptions import MeetingStateConflictException
from mcr_meeting.app.models import Meeting, MeetingStatus


def _meeting(status: MeetingStatus) -> Meeting:
    return Meeting(id=1, status=status)


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
