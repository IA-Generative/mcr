import pytest

from mcr_meeting.app.domain.deliverable_feedback import (
    OTHER_REASON,
    build_reason_catalogue,
    ensure_deliverable_accepts_feedback,
    validate_feedback_content,
)
from mcr_meeting.app.exceptions.exceptions import (
    BadRequestException,
    DeliverableFeedbackValidationException,
)
from mcr_meeting.app.models.deliverable_feedback_model import (
    CustomFeedbackReason,
    DeliverableFeedbackGroup,
    StructuredFeedbackReason,
    TranscriptionFeedbackReason,
)
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.feedback_model import VoteType

BLANK_COMMENTS = [None, "", "   ", "\n\t "]


@pytest.mark.parametrize("comment", BLANK_COMMENTS)
def test_a_negative_vote_carrying_neither_reason_nor_comment_is_refused(
    comment: str | None,
) -> None:
    with pytest.raises(DeliverableFeedbackValidationException):
        validate_feedback_content(
            vote_type=VoteType.NEGATIVE,
            comment=comment,
            reasons=[],
            deliverable_type=DeliverableType.DECISION_RECORD,
        )


@pytest.mark.parametrize("comment", BLANK_COMMENTS)
def test_a_reason_alone_explains_a_negative_vote(comment: str | None) -> None:
    validate_feedback_content(
        vote_type=VoteType.NEGATIVE,
        comment=comment,
        reasons=[StructuredFeedbackReason.FACTUAL_ERROR],
        deliverable_type=DeliverableType.DECISION_RECORD,
    )


def test_a_comment_alone_explains_a_negative_vote() -> None:
    validate_feedback_content(
        vote_type=VoteType.NEGATIVE,
        comment="the summary invented a decision",
        reasons=[],
        deliverable_type=DeliverableType.DECISION_RECORD,
    )


@pytest.mark.parametrize("comment", BLANK_COMMENTS)
def test_other_on_its_own_carries_no_signal_without_a_comment(
    comment: str | None,
) -> None:
    with pytest.raises(DeliverableFeedbackValidationException):
        validate_feedback_content(
            vote_type=VoteType.NEGATIVE,
            comment=comment,
            reasons=[OTHER_REASON],
            deliverable_type=DeliverableType.DECISION_RECORD,
        )


def test_other_on_its_own_is_accepted_once_spelled_out() -> None:
    validate_feedback_content(
        vote_type=VoteType.NEGATIVE,
        comment="the tables lost their header row",
        reasons=[OTHER_REASON],
        deliverable_type=DeliverableType.DECISION_RECORD,
    )


@pytest.mark.parametrize("comment", BLANK_COMMENTS)
def test_other_beside_another_reason_needs_no_comment(comment: str | None) -> None:
    validate_feedback_content(
        vote_type=VoteType.NEGATIVE,
        comment=comment,
        reasons=[StructuredFeedbackReason.OFF_TOPIC, OTHER_REASON],
        deliverable_type=DeliverableType.DECISION_RECORD,
    )


def test_a_reason_belonging_to_another_deliverable_group_is_refused() -> None:
    with pytest.raises(DeliverableFeedbackValidationException):
        validate_feedback_content(
            vote_type=VoteType.NEGATIVE,
            comment=None,
            reasons=[TranscriptionFeedbackReason.MISIDENTIFIED_SPEAKERS],
            deliverable_type=DeliverableType.DECISION_RECORD,
        )


def test_an_unknown_reason_is_refused() -> None:
    with pytest.raises(DeliverableFeedbackValidationException):
        validate_feedback_content(
            vote_type=VoteType.NEGATIVE,
            comment=None,
            reasons=["ROBOT_UPRISING"],
            deliverable_type=DeliverableType.DECISION_RECORD,
        )


def test_a_reason_shared_by_two_groups_is_legal_in_both() -> None:
    for deliverable_type in (
        DeliverableType.DECISION_RECORD,
        DeliverableType.CUSTOM_REPORT,
    ):
        validate_feedback_content(
            vote_type=VoteType.NEGATIVE,
            comment=None,
            reasons=["MISSING_INFORMATION"],
            deliverable_type=deliverable_type,
        )


@pytest.mark.parametrize("comment", [None, "", "   ", "well structured"])
def test_a_positive_vote_never_requires_a_comment(comment: str | None) -> None:
    validate_feedback_content(
        vote_type=VoteType.POSITIVE,
        comment=comment,
        reasons=[],
        deliverable_type=DeliverableType.DECISION_RECORD,
    )


def test_every_deliverable_type_offers_reasons_ending_with_other() -> None:
    catalogue = build_reason_catalogue()

    assert set(catalogue) == set(DeliverableType)
    for deliverable_type, entry in catalogue.items():
        assert entry.reasons[-1] == OTHER_REASON, deliverable_type
        assert len(entry.reasons) > 1, deliverable_type


def test_the_three_report_flavours_share_one_list_and_the_others_do_not() -> None:
    catalogue = build_reason_catalogue()

    assert catalogue[DeliverableType.TRANSCRIPTION].deliverable_group == (
        DeliverableFeedbackGroup.TRANSCRIPTION
    )
    assert catalogue[DeliverableType.CUSTOM_REPORT].deliverable_group == (
        DeliverableFeedbackGroup.CUSTOM
    )
    for structured_type in (
        DeliverableType.DECISION_RECORD,
        DeliverableType.DETAILED_SYNTHESIS,
        DeliverableType.STRUCTURED_MINUTES,
    ):
        assert catalogue[structured_type].deliverable_group == (
            DeliverableFeedbackGroup.STRUCTURED
        )
        assert (
            catalogue[structured_type].reasons
            == catalogue[DeliverableType.DECISION_RECORD].reasons
        )

    assert (
        catalogue[DeliverableType.TRANSCRIPTION].reasons
        != catalogue[DeliverableType.DECISION_RECORD].reasons
    )


def test_a_deliverable_only_offers_the_reasons_its_own_group_accepts() -> None:
    catalogue = build_reason_catalogue()

    for deliverable_type, entry in catalogue.items():
        for reason in entry.reasons:
            validate_feedback_content(
                vote_type=VoteType.NEGATIVE,
                comment="spelled out so OTHER passes too",
                reasons=[reason],
                deliverable_type=deliverable_type,
            )

    assert set(catalogue[DeliverableType.CUSTOM_REPORT].reasons) == {
        *CustomFeedbackReason,
        OTHER_REASON,
    }


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
