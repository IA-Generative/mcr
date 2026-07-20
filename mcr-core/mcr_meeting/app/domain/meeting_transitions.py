from statemachine.exceptions import TransitionNotAllowed

from mcr_meeting.app.domain.meeting_state_machine import get_state_machine_for_meeting
from mcr_meeting.app.exceptions.exceptions import MeetingStateConflictException
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingEvent


def init_capture(meeting: Meeting) -> None:
    _apply_or_conflict(meeting, MeetingEvent.INIT_CAPTURE)


def complete_capture(meeting: Meeting) -> None:
    _apply_or_conflict(meeting, MeetingEvent.COMPLETE_CAPTURE)


def start_capture_bot(meeting: Meeting) -> None:
    _apply_or_conflict(meeting, MeetingEvent.START_CAPTURE_BOT)


def fail_capture_bot(meeting: Meeting) -> None:
    _apply_or_conflict(meeting, MeetingEvent.FAIL_CAPTURE_BOT)


def reset_and_start_report(meeting: Meeting) -> Meeting:
    _try_apply(meeting, MeetingEvent.RESET_REPORT)
    _apply_or_conflict(meeting, MeetingEvent.START_REPORT)
    return meeting


def mark_transcription_done(meeting: Meeting) -> Meeting:
    _apply_or_conflict(meeting, MeetingEvent.COMPLETE_TRANSCRIPTION)
    return meeting


def complete_report(meeting: Meeting) -> Meeting:
    _apply_or_conflict(meeting, MeetingEvent.COMPLETE_REPORT)
    return meeting


def fail_report(meeting: Meeting) -> Meeting:
    _apply_or_conflict(meeting, MeetingEvent.FAIL_REPORT)
    return meeting


def init_transcription(meeting: Meeting) -> Meeting:
    _apply(meeting, MeetingEvent.INIT_TRANSCRIPTION)
    return meeting


def start_transcription(meeting: Meeting) -> Meeting:
    _apply_or_conflict(meeting, MeetingEvent.START_TRANSCRIPTION)
    return meeting


def forced_requeue(meeting: Meeting) -> Meeting:
    _apply_or_conflict(meeting, MeetingEvent.FORCED_REQUEUE)
    return meeting


def fail_transcription(meeting: Meeting) -> Meeting:
    _apply_or_conflict(meeting, MeetingEvent.FAIL_TRANSCRIPTION)
    return meeting


def update_transcription(meeting: Meeting) -> Meeting:
    _apply(meeting, MeetingEvent.UPDATE_TRANSCRIPTION)
    return meeting


def _apply(meeting: Meeting, event: MeetingEvent) -> None:
    sm = get_state_machine_for_meeting(meeting)
    try:
        sm.send(event)
        meeting.status = MeetingStatus(sm.current_state_value)
    except TransitionNotAllowed as exc:
        raise ValueError(str(exc)) from exc


def _apply_or_conflict(meeting: Meeting, event: MeetingEvent) -> None:
    try:
        _apply(meeting, event)
    except ValueError as exc:
        raise MeetingStateConflictException(str(exc)) from exc


def _try_apply(meeting: Meeting, event: MeetingEvent) -> None:
    try:
        _apply(meeting, event)
    except ValueError:
        pass
