from sqlalchemy import select
from sqlalchemy.orm import joinedload

from mcr_capture_worker.db.db import get_db_session
from mcr_capture_worker.models.meeting_model import Meeting, MeetingStatus


def get_next_element_for_capture_and_mark_as_bot_is_connecting() -> Meeting | None:
    with get_db_session() as db:
        get_and_lock_statement = (
            select(Meeting)
            .where(Meeting.status == MeetingStatus.CAPTURE_PENDING)
            .order_by(Meeting.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        meeting = db.execute(get_and_lock_statement).scalars().first()
        if meeting is None:
            return None

        meeting.status = MeetingStatus.CAPTURE_BOT_IS_CONNECTING
        db.commit()
        db.refresh(meeting)

        return meeting


def get_meeting(meeting_id: int) -> Meeting:
    """
    Retrieve a meeting by its ID from the database.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The meeting object with the specified ID, or None if not found.
    """
    with get_db_session() as db:
        meeting = db.get(Meeting, meeting_id)

    if meeting is None:
        raise ValueError("Meeting not found: id={meeting_id}")

    return meeting


def get_meeting_with_owner(meeting_id: int) -> Meeting:
    with get_db_session() as db:
        meeting = (
            db.query(Meeting)
            .options(joinedload(Meeting.owner))
            .filter(Meeting.id == meeting_id)
            .one()
        )

    if meeting is None:
        raise ValueError("Meeting not found: id={meeting_id}")

    return meeting
