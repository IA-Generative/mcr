from typing import Any, Optional

from pydantic import UUID4

from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.meeting_model import (
    MeetingEvent,
    MeetingPlatforms,
)
from mcr_meeting.app.schemas.report_generation import ReportGenerationResponse
from mcr_meeting.app.services.meeting_service import get_meeting_service
from mcr_meeting.app.services.transcription_task_service import (
    create_formatted_docx_transcription,
)
from mcr_meeting.app.state_machine.import_meeting_state_machine import (
    ImportMeetingStateMachine,
)
from mcr_meeting.app.state_machine.record_meeting_state_machine import (
    RecordMeetingStateMachine,
)
from mcr_meeting.app.state_machine.visio_meeting_state_machine import (
    VisioMeetingStateMachine,
)


def init_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.INIT_CAPTURE)


def start_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.START_CAPTURE)


def start_capture_bot(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.START_CAPTURE_BOT)


def fail_capture_bot(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.FAIL_CAPTURE_BOT)


def fail_capture(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.FAIL_CAPTURE)


def complete_capture(
    meeting_id: int, user_keycloak_uuid: Optional[UUID4] = None
) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )
    return _apply_transition(meeting, MeetingEvent.COMPLETE_CAPTURE)


def init_transcription(
    meeting_id: int, user_keycloak_uuid: Optional[UUID4] = None
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


def complete_transcription(meeting_id: int) -> Meeting:
    meeting = get_meeting_service(meeting_id=meeting_id)
    return _apply_transition(meeting, MeetingEvent.COMPLETE_TRANSCRIPTION)


def start_report(meeting_id: int, user_keycloak_uuid: UUID4) -> Meeting:
    meeting = get_meeting_service(
        meeting_id=meeting_id, current_user_keycloak_uuid=user_keycloak_uuid
    )

    if meeting.transcription_filename is None:
        create_formatted_docx_transcription(meeting=meeting)

    return _apply_transition(meeting, MeetingEvent.START_REPORT)


def complete_report(
    meeting_id: int, report_response: ReportGenerationResponse
) -> Meeting:
    meeting = get_meeting_service(meeting_id=meeting_id)

    return _apply_transition(
        meeting,
        MeetingEvent.COMPLETE_REPORT,
        report_response=report_response,
    )


def _apply_transition(  # type: ignore[explicit-any]
    meeting: Meeting,
    transition_name: MeetingEvent,
    **kwargs: Any,
) -> Meeting:
    sm = _get_state_machine(meeting)
    try:
        sm.send(transition_name, **kwargs)
    except Exception as e:
        raise ValueError(
            f"Error applying transition {transition_name} to meeting {meeting.id}: {str(e)}"
        )

    return meeting


def _get_state_machine(
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
        if isinstance(st.value, str) and st.value == meeting.status.value:
            sm.current_state = st
            break
    else:
        raise ValueError(f"Not state found for {meeting.status}")

    return sm
