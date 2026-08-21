from datetime import datetime, timezone

from pydantic import UUID4

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.meeting_repository import update_meeting as update_meeting_in_db
from mcr_meeting.app.db.meeting_transition_record_repository import (
    save_meeting_transition_record,
)
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_access
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import Meeting
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord


def delete_meetings(meeting_ids: list[int], user_keycloak_uuid: UUID4) -> None:
    # A meeting already gone is what a client retrying its cleanup looks like, so
    # unknown ids are skipped. Every access is authorized before the first write,
    # so one meeting owned by someone else deletes nothing at all.
    meetings = [
        meeting for meeting in map(_find_meeting, meeting_ids) if meeting is not None
    ]
    for meeting in meetings:
        authorize_meeting_access(meeting, user_keycloak_uuid)

    if not meetings:
        return

    with UnitOfWork():
        for meeting in meetings:
            meeting.status = MeetingStatus.DELETED
            update_meeting_in_db(meeting)
            save_meeting_transition_record(
                MeetingTransitionRecord(
                    meeting_id=meeting.id,
                    timestamp=datetime.now(timezone.utc),
                    status=MeetingStatus.DELETED,
                )
            )


def _find_meeting(meeting_id: int) -> Meeting | None:
    try:
        return get_meeting_by_id(meeting_id, with_deliverables=True)
    except NotFoundException:
        return None
