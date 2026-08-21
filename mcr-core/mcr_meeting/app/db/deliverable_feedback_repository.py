from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedback
from mcr_meeting.app.models.feedback_model import VoteType


def get_by_deliverable_id(deliverable_id: int) -> DeliverableFeedback | None:
    db = get_db_session_ctx()
    return (
        db.query(DeliverableFeedback)
        .filter(DeliverableFeedback.deliverable_id == deliverable_id)
        .one_or_none()
    )


def upsert(
    deliverable_id: int,
    vote_type: VoteType,
    comment: str | None,
    reasons: list[str],
) -> DeliverableFeedback:
    db = get_db_session_ctx()
    feedback = get_by_deliverable_id(deliverable_id)
    if feedback is None:
        feedback = DeliverableFeedback(deliverable_id=deliverable_id)
        db.add(feedback)
    feedback.vote_type = vote_type
    feedback.comment = comment
    feedback.is_active = True
    feedback.reasons = list(dict.fromkeys(reasons))
    return feedback


def deactivate(deliverable_id: int) -> None:
    feedback = get_by_deliverable_id(deliverable_id)
    if feedback is None:
        return
    feedback.is_active = False
