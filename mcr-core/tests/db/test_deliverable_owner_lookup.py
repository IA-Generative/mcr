import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from mcr_meeting.app.db import deliverable_repository as repo
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models.deliverable_model import DeliverableStatus, DeliverableType
from mcr_meeting.app.models.feedback_model import VoteType
from mcr_meeting.app.models.meeting_model import MeetingStatus
from mcr_meeting.app.use_cases.upsert_deliverable_feedback import (
    upsert_deliverable_feedback,
)
from tests.factories import MeetingFactory, UserFactory
from tests.factories.deliverable_factory import DeliverableFactory


def test_the_owner_of_a_deliverable_is_read_alongside_it() -> None:
    owner = UserFactory.create(keycloak_uuid=uuid.uuid4())
    deliverable = DeliverableFactory.create(meeting=MeetingFactory.create(owner=owner))

    found, owner_keycloak_uuid = repo.get_by_id_with_owner_uuid(deliverable.id)

    assert found.id == deliverable.id
    assert owner_keycloak_uuid == owner.keycloak_uuid


def test_reading_the_owner_takes_a_single_query(db_session: Session) -> None:
    deliverable = DeliverableFactory.create(meeting=MeetingFactory.create())
    deliverable_id = deliverable.id
    db_session.expire_all()

    with _count_selects(db_session) as counter:
        _, owner_keycloak_uuid = repo.get_by_id_with_owner_uuid(deliverable_id)

    assert owner_keycloak_uuid is not None
    assert counter["count"] == 1


def test_a_deleted_deliverable_has_no_owner_to_read() -> None:
    deliverable = DeliverableFactory.create(
        meeting=MeetingFactory.create(), status=DeliverableStatus.DELETED
    )

    with pytest.raises(NotFoundException):
        repo.get_by_id_with_owner_uuid(deliverable.id)


def test_a_deliverable_of_a_deleted_meeting_has_no_owner_to_read() -> None:
    deliverable = DeliverableFactory.create(
        meeting=MeetingFactory.create(status=MeetingStatus.DELETED)
    )

    with pytest.raises(NotFoundException):
        repo.get_by_id_with_owner_uuid(deliverable.id)


def test_an_unknown_deliverable_has_no_owner_to_read() -> None:
    with pytest.raises(NotFoundException):
        repo.get_by_id_with_owner_uuid(999_999)


def test_rating_a_deliverable_reads_the_database_twice_at_most(
    db_session: Session,
) -> None:
    owner = UserFactory.create(keycloak_uuid=uuid.uuid4())
    deliverable = DeliverableFactory.create(
        meeting=MeetingFactory.create(owner=owner),
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.AVAILABLE,
    )
    deliverable_id, caller = deliverable.id, owner.keycloak_uuid
    db_session.expire_all()

    with _count_selects(db_session) as counter:
        upsert_deliverable_feedback(
            deliverable_id=deliverable_id,
            user_keycloak_uuid=caller,
            vote_type=VoteType.POSITIVE,
            comment="ok",
            reasons=[],
        )

    assert counter["count"] == 2


@contextmanager
def _count_selects(session: Session) -> Iterator[dict[str, int]]:
    counter = {"count": 0}
    connection = session.connection()

    def _on_execute(
        _conn: object,
        _cursor: object,
        statement: str,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            counter["count"] += 1

    event.listen(connection, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(connection, "before_cursor_execute", _on_execute)
