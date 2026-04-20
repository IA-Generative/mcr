import re
from urllib.parse import urlparse
from uuid import UUID

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.db.feedback_repository import save_feedback
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.feedback_model import Feedback as FeedbackModel
from mcr_meeting.app.schemas.feedback_schema import Feedback
from mcr_meeting.app.services.user_service import get_user_by_keycloak_uuid_service


def extract_meeting_id_from_url(url: str) -> int | None:
    path = urlparse(url).path
    match = re.search(r"/meetings/(\d+)", path)
    if match:
        return int(match.group(1))
    return None


def create_feedback(feedback_data: Feedback, user_keycloak_uuid: UUID) -> FeedbackModel:
    user = get_user_by_keycloak_uuid_service(user_keycloak_uuid)
    with UnitOfWork():
        feedback = save_feedback(
            feedback=FeedbackModel(
                user_id=user.id,
                meeting_id=feedback_data.meeting_id,
                vote_type=feedback_data.vote_type,
                comment=feedback_data.comment,
            )
        )
        get_db_session_ctx().flush()
    return feedback
