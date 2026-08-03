from datetime import datetime, timezone

from mcr_meeting.app.models.deliverable_feedback_model import DeliverableFeedback
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.feedback_model import VoteType
from mcr_meeting.app.schemas.deliverable_schema import DeliverableResponse


def _deliverable(feedback: DeliverableFeedback | None) -> Deliverable:
    now = datetime(2026, 7, 30, tzinfo=timezone.utc)
    deliverable = Deliverable(
        id=1,
        meeting_id=1,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.AVAILABLE,
        external_url=None,
        created_at=now,
        updated_at=now,
    )
    deliverable.feedback = feedback
    return deliverable


def test_a_retracted_opinion_is_never_published() -> None:
    response = DeliverableResponse.model_validate(
        _deliverable(
            DeliverableFeedback(
                vote_type=VoteType.POSITIVE,
                comment="kept for the dashboards",
                is_active=False,
            )
        )
    )

    assert response.feedback is None


def test_a_live_opinion_is_published() -> None:
    response = DeliverableResponse.model_validate(
        _deliverable(
            DeliverableFeedback(
                vote_type=VoteType.POSITIVE, comment="clear", is_active=True
            )
        )
    )

    assert response.feedback is not None
    assert response.feedback.vote_type == VoteType.POSITIVE
    assert response.feedback.comment == "clear"


def test_a_deliverable_never_rated_publishes_nothing() -> None:
    assert DeliverableResponse.model_validate(_deliverable(None)).feedback is None


def test_the_active_flag_is_not_part_of_the_payload() -> None:
    response = DeliverableResponse.model_validate(
        _deliverable(DeliverableFeedback(vote_type=VoteType.POSITIVE, is_active=True))
    )

    assert set(response.model_dump()["feedback"]) == {"vote_type", "comment", "reasons"}


def test_a_feedback_read_back_from_json_survives_revalidation() -> None:
    response = DeliverableResponse.model_validate(
        {
            "id": 1,
            "meeting_id": 1,
            "type": "DECISION_RECORD",
            "status": "AVAILABLE",
            "external_url": None,
            "created_at": "2026-07-30T00:00:00Z",
            "updated_at": "2026-07-30T00:00:00Z",
            "feedback": {"vote_type": "POSITIVE", "comment": "clear"},
        }
    )

    assert response.feedback is not None
    assert response.feedback.comment == "clear"
