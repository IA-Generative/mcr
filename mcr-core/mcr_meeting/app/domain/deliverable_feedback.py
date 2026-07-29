from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    DeliverableFeedbackValidationException,
)
from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedback
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableStatus
from mcr_meeting.app.models.feedback_model import VoteType


def ensure_deliverable_accepts_feedback(deliverable: Deliverable) -> None:
    if deliverable.status != DeliverableStatus.AVAILABLE:
        raise BadRequestException(
            f"Deliverable in state {deliverable.status!r} cannot be rated: "
            "only an AVAILABLE deliverable accepts feedback"
        )


def validate_feedback_content(vote_type: VoteType, comment: str | None) -> None:
    if vote_type == VoteType.NEGATIVE and not _is_substantive(comment):
        raise DeliverableFeedbackValidationException(
            "A negative vote requires a comment explaining what went wrong"
        )


def visible_feedback(deliverable: Deliverable) -> DeliverableFeedback | None:
    feedback = deliverable.feedback
    if feedback is None or not feedback.is_active:
        return None
    return feedback


def _is_substantive(comment: str | None) -> bool:
    return comment is not None and bool(comment.strip())
