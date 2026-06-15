from typing import Any

from pydantic import UUID4

from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_model import (
    MeetingEvent,
    MeetingPlatforms,
)
from mcr_meeting.app.schemas.report_generation import ReportResponse
from mcr_meeting.app.services.meeting_service import get_meeting_service
from mcr_meeting.app.state_machine.import_meeting_state_machine import (
    ImportMeetingStateMachine,
)
from mcr_meeting.app.state_machine.record_meeting_state_machine import (
    RecordMeetingStateMachine,
)
from mcr_meeting.app.state_machine.visio_meeting_state_machine import (
    VisioMeetingStateMachine,
)


def start_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.START_CAPTURE)


def fail_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.FAIL_CAPTURE)


def init_transcription(
    meeting_id: int, user_keycloak_uuid: UUID4 | None = None
) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.INIT_TRANSCRIPTION)


def start_transcription(meeting_id: int) -> Meeting:
    meeting = get_meeting_service(meeting_id=meeting_id)
    return _apply_transition(meeting, MeetingEvent.START_TRANSCRIPTION)


def fail_transcription(meeting_id: int) -> Meeting:
    meeting = get_meeting_service(meeting_id=meeting_id)
    return _apply_transition(meeting, MeetingEvent.FAIL_TRANSCRIPTION)


def update_transcription(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.UPDATE_TRANSCRIPTION)


def complete_report(meeting_id: int, report_response: ReportResponse) -> Meeting:
    meeting = get_meeting_service(meeting_id=meeting_id)

    return _apply_transition(
        meeting,
        MeetingEvent.COMPLETE_REPORT,
        report_response=report_response,
    )


def fail_report(meeting_id: int) -> Meeting:
    meeting = get_meeting_service(meeting_id=meeting_id)
    return _apply_transition(meeting, MeetingEvent.FAIL_REPORT)


def _apply_transition(  # type: ignore[explicit-any]
    meeting: Meeting,
    transition_name: MeetingEvent,
    **kwargs: Any,
) -> Meeting:
    sm = get_state_machine_for_meeting(meeting)
    try:
        sm.send(transition_name, **kwargs)
    except Exception as e:
        raise ValueError(
            f"Error applying transition {transition_name} to meeting {meeting.id}: {str(e)}"
        )

    return meeting


def get_state_machine_for_meeting(
    meeting: Meeting,
) -> VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine:
    match meeting.name_platform:
        case MeetingPlatforms.MCR_IMPORT:
            return _from_status(ImportMeetingStateMachine, meeting)
        case MeetingPlatforms.MCR_RECORD:
            return _from_status(RecordMeetingStateMachine, meeting)
        case _:
            return _from_status(VisioMeetingStateMachine, meeting)


def _from_status(
    cls: type[
        VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine
    ],
    meeting: Meeting,
) -> VisioMeetingStateMachine | RecordMeetingStateMachine | ImportMeetingStateMachine:
    sm = cls(meeting)

    for st in sm.states:
        if isinstance(st.value, str) and st.value == meeting.status:
            sm.current_state = st
            break
    else:
        raise ValueError(f"Not state found for {meeting.status}")

    return sm
