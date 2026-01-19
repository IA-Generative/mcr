from fastapi import HTTPException, status

from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.models.user_model import User


def check_meeting_ownership(meeting_id: int, current_user: User) -> None:
    """
    Check if the current user is the owner of the meeting.
    """
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {meeting_id} not found.",
        )

    if meeting_id not in [user_meeting.id for user_meeting in current_user.meetings]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized for this meeting",
        )
