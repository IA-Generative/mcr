import pytest

from mcr_meeting.app.domain.deliverable_feedback import (
    ensure_deliverable_accepts_feedback,
    validate_feedback_content,
)
from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    DeliverableFeedbackValidationException,
)
from mcr_meeting.app.models.deliverable_model import Deliverable, DeliverableStatus
from mcr_meeting.app.models.feedback_model import VoteType


@pytest.mark.parametrize("comment", [None, "", "   ", "\n\t "])
def test_negative_vote_without_a_substantive_comment_is_refused(
    comment: str | None,
) -> None:
    with pytest.raises(DeliverableFeedbackValidationException):
        validate_feedback_content(vote_type=VoteType.NEGATIVE, comment=comment)


def test_negative_vote_with_a_comment_is_accepted() -> None:
    validate_feedback_content(
        vote_type=VoteType.NEGATIVE, comment="the summary invented a decision"
    )


@pytest.mark.parametrize("comment", [None, "", "   ", "well structured"])
def test_positive_vote_never_requires_a_comment(comment: str | None) -> None:
    validate_feedback_content(vote_type=VoteType.POSITIVE, comment=comment)


@pytest.mark.parametrize(
    "status",
    [
        DeliverableStatus.REQUESTED,
        DeliverableStatus.PENDING,
        DeliverableStatus.IN_PROGRESS,
        DeliverableStatus.FAILED,
    ],
)
def test_only_an_available_deliverable_can_be_rated(status: DeliverableStatus) -> None:
    with pytest.raises(BadRequestException):
        ensure_deliverable_accepts_feedback(Deliverable(status=status))


def test_an_available_deliverable_accepts_feedback() -> None:
    ensure_deliverable_accepts_feedback(Deliverable(status=DeliverableStatus.AVAILABLE))
