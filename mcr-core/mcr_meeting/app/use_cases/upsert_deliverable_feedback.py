from pydantic import UUID4

from mcr_meeting.app.db import deliverable_feedback_repository, deliverable_repository
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.domain.authorize_meeting_access import authorize_meeting_owner
from mcr_meeting.app.domain.deliverable_feedback import (
    ensure_deliverable_accepts_feedback,
    validate_feedback_content,
)
from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedback
from mcr_meeting.app.models.feedback_model import VoteType


def upsert_deliverable_feedback(
    deliverable_id: int,
    user_keycloak_uuid: UUID4,
    vote_type: VoteType,
    comment: str | None,
) -> DeliverableFeedback:
    deliverable, owner_keycloak_uuid = deliverable_repository.get_by_id_with_owner_uuid(
        deliverable_id
    )
    authorize_meeting_owner(owner_keycloak_uuid, user_keycloak_uuid)
    ensure_deliverable_accepts_feedback(deliverable)
    validate_feedback_content(vote_type=vote_type, comment=comment)

    with UnitOfWork():
        feedback = deliverable_feedback_repository.upsert(
            deliverable_id=deliverable_id, vote_type=vote_type, comment=comment
        )
    return feedback
