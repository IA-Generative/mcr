from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.models.meeting_model import MeetingEvent, MeetingPlatforms
from mcr_meeting.app.state_machine.import_meeting_state_machine import (
    ImportMeetingStateMachine,
)
from mcr_meeting.app.state_machine.record_meeting_state_machine import (
    RecordMeetingStateMachine,
)
from mcr_meeting.app.state_machine.visio_meeting_state_machine import (
    VisioMeetingStateMachine,
)

_MeetingStateMachine = (
    VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine
)


def validate_transition(meeting: Meeting, event: MeetingEvent) -> MeetingStatus:
    """Resolve the target status for a transition without triggering it.

    Inspects the meeting's state machine to confirm ``event`` is a legal
    transition from ``meeting.status`` and returns the target status. No
    ``sm.send()`` call is made, so ``after_*`` / ``before_*`` handlers do not
    fire — the use case caller owns side effects and persistence.

    Raises ``ValueError`` if the transition is not legal from the current
    status, mirroring the error semantics of the existing orchestrator path.
    """
    sm = _build_state_machine(meeting)
    current_state = sm.current_state

    for transition in current_state.transitions:
        if transition.match(event.value):
            target_status_value = transition.target.value
            return MeetingStatus(target_status_value)

    raise ValueError(
        f"Transition {event.value} is not allowed from state {meeting.status} "
        f"for meeting {meeting.id}"
    )


def _build_state_machine(meeting: Meeting) -> _MeetingStateMachine:
    match meeting.name_platform:
        case MeetingPlatforms.MCR_IMPORT:
            return _from_status(ImportMeetingStateMachine, meeting)
        case MeetingPlatforms.MCR_RECORD:
            return _from_status(RecordMeetingStateMachine, meeting)
        case _:
            return _from_status(VisioMeetingStateMachine, meeting)


def _from_status(
    cls: type[_MeetingStateMachine],
    meeting: Meeting,
) -> _MeetingStateMachine:
    sm = cls(meeting)
    for st in sm.states:
        if isinstance(st.value, str) and st.value == meeting.status:
            sm.current_state = st
            return sm
    raise ValueError(f"No state found for {meeting.status}")
