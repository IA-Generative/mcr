from dataclasses import dataclass
from typing import assert_never

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

OTHER_REASON = "OTHER"


@dataclass(frozen=True)
class ReasonCatalogueEntry:
    deliverable_group: DeliverableFeedbackGroup
    reasons: list[str]


def build_reason_catalogue() -> dict[DeliverableType, ReasonCatalogueEntry]:
    return {
        deliverable_type: _catalogue_entry(feedback_group_of(deliverable_type))
        for deliverable_type in DeliverableType
    }


def feedback_group_of(deliverable_type: DeliverableType) -> DeliverableFeedbackGroup:
    match deliverable_type:
        case DeliverableType.TRANSCRIPTION:
            return DeliverableFeedbackGroup.TRANSCRIPTION
        case (
            DeliverableType.DECISION_RECORD
            | DeliverableType.DETAILED_SYNTHESIS
            | DeliverableType.STRUCTURED_MINUTES
        ):
            return DeliverableFeedbackGroup.STRUCTURED
        case DeliverableType.CUSTOM_REPORT:
            return DeliverableFeedbackGroup.CUSTOM
        case _:
            assert_never(deliverable_type)


def ensure_deliverable_accepts_feedback(deliverable: Deliverable) -> None:
    if deliverable.status != DeliverableStatus.AVAILABLE:
        raise BadRequestException(
            f"Deliverable in state {deliverable.status!r} cannot be rated: "
            "only an AVAILABLE deliverable accepts feedback"
        )


def validate_feedback_content(
    vote_type: VoteType,
    comment: str | None,
    reasons: list[str],
    deliverable_type: DeliverableType,
) -> None:
    if vote_type == VoteType.POSITIVE:
        return

    group = feedback_group_of(deliverable_type)
    _ensure_reasons_belong_to_group(reasons=reasons, group=group)

    selected = set(reasons)
    spelled_out = _is_substantive(comment)
    if not selected and not spelled_out:
        raise DeliverableFeedbackValidationException(
            "A negative vote requires at least one reason or a comment "
            "explaining what went wrong"
        )
    if selected == {OTHER_REASON} and not spelled_out:
        raise DeliverableFeedbackValidationException(
            "Choosing OTHER alone requires a comment spelling out what went wrong"
        )


def _catalogue_entry(group: DeliverableFeedbackGroup) -> ReasonCatalogueEntry:
    return ReasonCatalogueEntry(
        deliverable_group=group, reasons=_offered_reasons(group)
    )


def _offered_reasons(group: DeliverableFeedbackGroup) -> list[str]:
    match group:
        case DeliverableFeedbackGroup.TRANSCRIPTION:
            group_reasons: list[str] = list(TranscriptionFeedbackReason)
        case DeliverableFeedbackGroup.STRUCTURED:
            group_reasons = list(StructuredFeedbackReason)
        case DeliverableFeedbackGroup.CUSTOM:
            group_reasons = list(CustomFeedbackReason)
        case _:
            assert_never(group)
    return [*group_reasons, OTHER_REASON]


def _ensure_reasons_belong_to_group(
    reasons: list[str], group: DeliverableFeedbackGroup
) -> None:
    trespassing = sorted(set(reasons) - set(_offered_reasons(group)))
    if trespassing:
        raise DeliverableFeedbackValidationException(
            f"Reasons {trespassing} are not offered for a {group} deliverable"
        )


def _is_substantive(comment: str | None) -> bool:
    return comment is not None and bool(comment.strip())
