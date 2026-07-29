from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.orm import Session

from mcr_meeting.app.db import deliverable_feedback_repository as repo
from mcr_meeting.app.db import deliverable_repository
from mcr_meeting.app.models.deliverable_model import DeliverableStatus, DeliverableType
from mcr_meeting.app.models.feedback_model import VoteType
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory
from tests.factories.deliverable_feedback_factory import DeliverableFeedbackFactory

REPORT_TYPES = (
    DeliverableType.TRANSCRIPTION,
    DeliverableType.DECISION_RECORD,
    DeliverableType.DETAILED_SYNTHESIS,
    DeliverableType.CUSTOM_REPORT,
)


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
    for deliverable_type in REPORT_TYPES[:count]:
        DeliverableFeedbackFactory.create(
            deliverable=DeliverableFactory.create(
                meeting=meeting,
                type=deliverable_type,
                status=DeliverableStatus.AVAILABLE,
            )
        )
    return int(meeting.id)


def _read_votes(meeting_id: int) -> list[VoteType]:
    rows = deliverable_repository.list_by_meeting(meeting_id=meeting_id)
    return [row.feedback.vote_type for row in rows if row.feedback is not None]


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
