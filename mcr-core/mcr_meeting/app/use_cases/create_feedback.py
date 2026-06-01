from pydantic import UUID4

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.db.feedback_repository import save_feedback
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.db.user_repository import get_user_by_keycloak_uuid
from mcr_meeting.app.domain.feedback import extract_meeting_id_from_url
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models.feedback_model import Feedback as FeedbackModel
from mcr_meeting.app.schemas.feedback_schema import FeedbackRequest


def create_feedback(
    feedback_request_data: FeedbackRequest,
    user_keycloak_uuid: UUID4,
) -> FeedbackModel:
    user = get_user_by_keycloak_uuid(user_keycloak_uuid)
    meeting_id = _resolve_meeting_id(feedback_request_data.url)

    with UnitOfWork():
        feedback = save_feedback(
            feedback=FeedbackModel(
                user_id=user.id,
                meeting_id=meeting_id,
                vote_type=feedback_request_data.vote_type,
                comment=feedback_request_data.comment,
            )
        )
        get_db_session_ctx().flush()
    return feedback


def _resolve_meeting_id(url: str) -> int | None:
    meeting_id = extract_meeting_id_from_url(url)
    if meeting_id is None:
        return None
    try:
        get_meeting_by_id(meeting_id)
    except NotFoundException:
        return None
    return meeting_id
