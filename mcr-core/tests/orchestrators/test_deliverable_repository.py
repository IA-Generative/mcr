import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.db import deliverable_repository as repo
from mcr_meeting.app.exceptions.exceptions import NotFoundException
from mcr_meeting.app.models.deliverable_model import (
    DeliverableStatus,
    DeliverableType,
)
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory


def test_list_by_meeting_filters_deleted_status() -> None:
    meeting = MeetingFactory.create()
    kept_a = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.AVAILABLE,
    )
    kept_b = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.PENDING,
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DETAILED_SYNTHESIS,
        status=DeliverableStatus.DELETED,
    )

    rows = repo.list_by_meeting(meeting_id=meeting.id)

    assert {row.id for row in rows} == {kept_a.id, kept_b.id}


def test_list_by_meeting_excludes_other_meetings() -> None:
    meeting = MeetingFactory.create()
    other_meeting = MeetingFactory.create()
    mine = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.AVAILABLE,
    )
    DeliverableFactory.create(
        meeting=other_meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.AVAILABLE,
    )

    rows = repo.list_by_meeting(meeting_id=meeting.id)

    assert [row.id for row in rows] == [mine.id]


def test_get_by_id_raises_not_found_for_deleted_rows() -> None:
    meeting = MeetingFactory.create()
    deleted = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.DELETED,
    )

    with pytest.raises(NotFoundException):
        repo.get_by_id(deliverable_id=deleted.id)


def test_get_by_id_raises_not_found_for_unknown_id() -> None:
    with pytest.raises(NotFoundException):
        repo.get_by_id(deliverable_id=999_999)


def test_get_by_id_returns_pending_or_available_rows() -> None:
    meeting = MeetingFactory.create()
    pending = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.PENDING,
    )

    found = repo.get_by_id(deliverable_id=pending.id)

    assert found.id == pending.id


def test_set_status_updates_status_field(db_session: Session) -> None:
    meeting = MeetingFactory.create()
    pending = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.PENDING,
    )

    repo.set_status(deliverable_id=pending.id, status=DeliverableStatus.AVAILABLE)

    db_session.refresh(pending)
    assert pending.status == DeliverableStatus.AVAILABLE


def test_set_external_url_updates_url(db_session: Session) -> None:
    meeting = MeetingFactory.create()
    pending = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.PENDING,
        external_url=None,
    )

    repo.set_external_url(
        deliverable_id=pending.id,
        external_url="https://drive.example.com/xyz",
    )

    db_session.refresh(pending)
    assert pending.external_url == "https://drive.example.com/xyz"


def test_soft_delete_by_id_marks_status_deleted(db_session: Session) -> None:
    meeting = MeetingFactory.create()
    available = DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.DECISION_RECORD,
        status=DeliverableStatus.AVAILABLE,
    )

    repo.soft_delete_by_id(deliverable_id=available.id)

    db_session.refresh(available)
    assert available.status == DeliverableStatus.DELETED
