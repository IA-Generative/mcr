from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models import Meeting, MeetingStatus
from mcr_meeting.app.services.meeting_service import (
    update_meeting_status,
)
from mcr_meeting.app.services.meeting_transition_record_service import (
    create_transition_record_service,
)


def update_status_handler(meeting: Meeting, next_status: MeetingStatus) -> None:
    with UnitOfWork():
        update_meeting_status(meeting, next_status)


def after_transition_handler(meeting_id: int, next_status: MeetingStatus) -> None:
    create_transition_record_service(meeting_id, next_status)
