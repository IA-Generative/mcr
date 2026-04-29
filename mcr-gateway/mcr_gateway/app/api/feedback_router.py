from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from loguru import logger

from mcr_gateway.app.schemas.feedback_schema import Feedback, FeedbackRequest
from mcr_gateway.app.schemas.user_schema import Role, TokenUser
from mcr_gateway.app.services.authentification_service import authorize_user
from mcr_gateway.app.services.feedback_service import create_feedback_service

router = APIRouter()


@router.post(
    "/feedbacks",
    response_model=Feedback,
    tags=["Feedbacks"],
)
async def create_feedback(
    feedback_data: FeedbackRequest,
    current_user: TokenUser = Depends(authorize_user(Role.USER.value)),
) -> Feedback:
    """
    Endpoint to create a new feedback.

    Args:
        feedback_data (FeedbackRequest): The meeting details provided by the frontend.

    Returns:
        Feedback: The created feedback object.
    """
    try:
        result = await create_feedback_service(
            feedback_data, user_keycloak_uuid=current_user.keycloak_uuid
        )
        if result is None:
            raise HTTPException(
                status_code=500, detail="Service did not return a valid response"
            )
        return result
    except HTTPException as e:
        logger.error("HTTPException occurred: {}", e.detail)
        raise e
