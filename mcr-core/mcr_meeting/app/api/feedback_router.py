from fastapi import APIRouter, Depends, Header, status
from pydantic import UUID4

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import router_db_session_context_manager
from mcr_meeting.app.orchestrators.feedback_orchestrator import (
    create_feedback as create_feedback_orchestrator,
)
from mcr_meeting.app.schemas.feedback_schema import (
    FeedbackRequest,
    FeedbackResponse,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.FEEDBACK_API_PREFIX,
    dependencies=[Depends(router_db_session_context_manager)],
    tags=["Feedbacks"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_feedback(
    feedback_request_data: FeedbackRequest,
    x_user_keycloak_uuid: UUID4 = Header(),
) -> FeedbackResponse:
    """
    Create a new feedback.

    Args:
        feedback_data (FeedbackCreate): The feedback data to create.

    Returns:
        Meeting: The created meeting object.
    """
    feedback = create_feedback_orchestrator(
        feedback_request_data=feedback_request_data,
        user_keycloak_uuid=x_user_keycloak_uuid,
    )
    return FeedbackResponse.model_validate(feedback)
