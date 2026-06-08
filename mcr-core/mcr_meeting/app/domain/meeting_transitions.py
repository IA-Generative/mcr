from statemachine.exceptions import TransitionNotAllowed

from mcr_meeting.app.exceptions.exceptions import MeetingStateConflictException
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingEvent
from mcr_meeting.app.orchestrators.meeting_transitions_orchestrator import (
    get_state_machine_for_meeting,
)

# Allowed meeting transitions handled outside the legacy state machine.
# This table grows PR after PR as routes migrate to use cases; it only covers
# the transitions already drained from the SM (see migration-plan.md).
_ALLOWED: dict[MeetingStatus, frozenset[MeetingStatus]] = {
    MeetingStatus.CAPTURE_BOT_IS_CONNECTING: frozenset(
        {
            MeetingStatus.CAPTURE_IN_PROGRESS,
            MeetingStatus.CAPTURE_BOT_CONNECTION_FAILED,
        }
    ),
}


def assert_meeting_transition(current: MeetingStatus, target: MeetingStatus) -> None:
    if target not in _ALLOWED.get(current, frozenset()):
        raise MeetingStateConflictException(
            f"Cannot transition meeting from {str(current)!r} to {str(target)!r}"
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
