from mcr_meeting.app.domain.deliverable_feedback import visible_feedback
from mcr_meeting.app.models.deliverable_model import Deliverable
from mcr_meeting.app.schemas.deliverable_feedback_schema import (
    DeliverableFeedbackResponse,
)
from mcr_meeting.app.schemas.deliverable_schema import DeliverableResponse


def build_deliverable_response(deliverable: Deliverable) -> DeliverableResponse:
    feedback = visible_feedback(deliverable)
    return DeliverableResponse.model_validate(deliverable).model_copy(
        update={
            "feedback": (
                DeliverableFeedbackResponse.model_validate(feedback)
                if feedback is not None
                else None
            )
        }
    )
