from statemachine.exceptions import TransitionNotAllowed

from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingEvent
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    get_state_machine_for_meeting,
)


def reset_and_start_report(meeting: Meeting) -> Meeting:
    _try_apply(meeting, MeetingEvent.RESET_REPORT)
    _apply(meeting, MeetingEvent.START_REPORT)
    return meeting


def _apply(meeting: Meeting, event: MeetingEvent) -> None:
    sm = get_state_machine_for_meeting(meeting)
    try:
        sm.send(event)
        meeting.status = MeetingStatus(sm.current_state_value)
    except TransitionNotAllowed as exc:
        raise ValueError(str(exc)) from exc


def _try_apply(meeting: Meeting, event: MeetingEvent) -> None:
    try:
        _apply(meeting, event)
    except ValueError:
        pass
