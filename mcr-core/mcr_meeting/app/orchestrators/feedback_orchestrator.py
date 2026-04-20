from uuid import UUID

from mcr_meeting.app.exceptions.exceptions import (
    NotFoundException,
)
from mcr_meeting.app.models.feedback_model import Feedback as FeedbackModel
from mcr_meeting.app.schemas.feedback_schema import Feedback, FeedbackRequest
from mcr_meeting.app.services.feedback_service import (
    create_feedback as create_feedback_service,
)
from mcr_meeting.app.services.feedback_service import (
    extract_meeting_id_from_url,
)
from mcr_meeting.app.services.meeting_service import get_meeting_service


def create_feedback(
    feedback_request_data: FeedbackRequest,
    user_keycloak_uuid: UUID,
) -> FeedbackModel:
    feedback_create_data = Feedback(
        vote_type=feedback_request_data.vote_type, comment=feedback_request_data.comment
    )
    meeting_id = extract_meeting_id_from_url(feedback_request_data.url)
    if meeting_id is not None:
        try:
            get_meeting_service(meeting_id)
            feedback_create_data.meeting_id = meeting_id
        except NotFoundException:
            pass

    return create_feedback_service(
        feedback_data=feedback_create_data,
        user_keycloak_uuid=user_keycloak_uuid,
    )
