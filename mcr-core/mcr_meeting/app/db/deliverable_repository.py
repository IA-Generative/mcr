from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
)
from mcr_meeting.app.models.deliverable_model import Deliverable


def save_deliverable(deliverable: Deliverable) -> Deliverable:
    db = get_db_session_ctx()
    db.add(deliverable)
    db.flush()
    return deliverable


def update_deliverable(deliverable: Deliverable) -> Deliverable:
    db = get_db_session_ctx()
    db.merge(deliverable)
    return deliverable


def get_deliverable_by_meeting_id_and_file_type(
    meeting_id: int, file_type: str
) -> Deliverable:
    db = get_db_session_ctx()
    query = db.query(Deliverable).filter_by(meeting_id=meeting_id, file_type=file_type)
    deliverable = query.first()
    if deliverable is None:
        raise NotFoundException(f"Deliverable not found: meeting id={meeting_id}")
    return deliverable
