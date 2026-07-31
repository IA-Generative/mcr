from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.orm import Session

from mcr_meeting.app.db import deliverable_feedback_repository as repo
from mcr_meeting.app.db import deliverable_repository
from mcr_meeting.app.models.deliverable_feedback_model import StructuredFeedbackReason
from mcr_meeting.app.models.deliverable_model import DeliverableStatus, DeliverableType
from mcr_meeting.app.models.feedback_model import VoteType
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory
from tests.factories.deliverable_feedback_factory import DeliverableFeedbackFactory


def test_retracting_a_vote_keeps_it_in_the_database(db_session: Session) -> None:
    feedback = DeliverableFeedbackFactory.create(
        vote_type=VoteType.POSITIVE, comment="still useful to the dashboards"
    )

    repo.deactivate(deliverable_id=feedback.deliverable_id)
    db_session.flush()

    db_session.refresh(feedback)
    assert feedback.is_active is False
    assert feedback.vote_type == VoteType.POSITIVE
    assert feedback.comment == "still useful to the dashboards"


def test_retracting_a_vote_keeps_the_reasons_it_was_given_for(
    db_session: Session,
) -> None:
    deliverable = DeliverableFactory.create(
        type=DeliverableType.DECISION_RECORD, status=DeliverableStatus.AVAILABLE
    )
    repo.upsert(
        deliverable_id=deliverable.id,
        vote_type=VoteType.NEGATIVE,
        comment=None,
        reasons=[StructuredFeedbackReason.OFF_TOPIC],
    )
    db_session.flush()

    repo.deactivate(deliverable_id=deliverable.id)
    db_session.flush()

    assert _stored_reasons(deliverable.id) == {StructuredFeedbackReason.OFF_TOPIC}


def test_changing_ones_mind_replaces_the_whole_set_of_reasons(
    db_session: Session,
) -> None:
    deliverable = DeliverableFactory.create(
        type=DeliverableType.DECISION_RECORD, status=DeliverableStatus.AVAILABLE
    )
    repo.upsert(
        deliverable_id=deliverable.id,
        vote_type=VoteType.NEGATIVE,
        comment=None,
        reasons=[
            StructuredFeedbackReason.OFF_TOPIC,
            StructuredFeedbackReason.TOO_LONG_OR_DETAILED,
        ],
    )
    db_session.flush()

    repo.upsert(
        deliverable_id=deliverable.id,
        vote_type=VoteType.NEGATIVE,
        comment=None,
        reasons=[StructuredFeedbackReason.FACTUAL_ERROR],
    )
    db_session.flush()

    assert _stored_reasons(deliverable.id) == {StructuredFeedbackReason.FACTUAL_ERROR}


def test_switching_to_a_thumb_up_drops_the_reasons_of_the_previous_opinion(
    db_session: Session,
) -> None:
    deliverable = DeliverableFactory.create(
        type=DeliverableType.DECISION_RECORD, status=DeliverableStatus.AVAILABLE
    )
    repo.upsert(
        deliverable_id=deliverable.id,
        vote_type=VoteType.NEGATIVE,
        comment="wrong from start to finish",
        reasons=[StructuredFeedbackReason.FACTUAL_ERROR],
    )
    db_session.flush()

    repo.upsert(
        deliverable_id=deliverable.id,
        vote_type=VoteType.POSITIVE,
        comment="regenerated, now spot on",
        reasons=[],
    )
    db_session.flush()

    assert _stored_reasons(deliverable.id) == set()


def test_the_same_reason_sent_twice_is_stored_once(db_session: Session) -> None:
    deliverable = DeliverableFactory.create(
        type=DeliverableType.DECISION_RECORD, status=DeliverableStatus.AVAILABLE
    )

    repo.upsert(
        deliverable_id=deliverable.id,
        vote_type=VoteType.NEGATIVE,
        comment=None,
        reasons=[
            StructuredFeedbackReason.OFF_TOPIC,
            StructuredFeedbackReason.OFF_TOPIC,
        ],
    )
    db_session.flush()

    feedback = repo.get_by_deliverable_id(deliverable.id)
    assert feedback is not None
    assert len(feedback.reasons) == 1


def test_reading_a_meeting_costs_the_same_whatever_the_number_of_deliverables(
    db_session: Session,
) -> None:
    one_deliverable = _meeting_with_rated_deliverables(count=1)
    four_deliverables = _meeting_with_rated_deliverables(count=4)
    db_session.expire_all()

    with _count_queries(db_session) as counter:
        _read_votes(one_deliverable)
    cost_of_one = counter["count"]

    with _count_queries(db_session) as counter:
        votes = _read_votes(four_deliverables)
    cost_of_four = counter["count"]

    assert len(votes) == 4
    assert cost_of_four == cost_of_one


def _meeting_with_rated_deliverables(count: int) -> int:
    meeting = MeetingFactory.create()
    for deliverable_type in list(DeliverableType)[:count]:
        deliverable = DeliverableFactory.create(
            meeting=meeting,
            type=deliverable_type,
            status=DeliverableStatus.AVAILABLE,
        )
        DeliverableFeedbackFactory.create(
            deliverable=deliverable,
            vote_type=VoteType.NEGATIVE,
            comment="explained at length",
            reasons=[StructuredFeedbackReason.OFF_TOPIC],
        )
    return int(meeting.id)


def _read_votes(meeting_id: int) -> list[tuple[VoteType, int]]:
    rows = deliverable_repository.list_by_meeting(meeting_id=meeting_id)
    return [
        (row.feedback.vote_type, len(row.feedback.reasons))
        for row in rows
        if row.feedback is not None
    ]


def _stored_reasons(deliverable_id: int) -> set[str]:
    feedback = repo.get_by_deliverable_id(deliverable_id)
    assert feedback is not None
    return set(feedback.reasons)


@contextmanager
def _count_queries(session: Session) -> Iterator[dict[str, int]]:
    counter = {"count": 0}
    connection = session.connection()

    def _on_execute(*_args: object, **_kwargs: object) -> None:
        counter["count"] += 1

    event.listen(connection, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(connection, "before_cursor_execute", _on_execute)
