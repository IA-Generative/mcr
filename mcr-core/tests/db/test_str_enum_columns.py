from sqlalchemy.orm import Session

from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import Meeting, MeetingStatus
from tests.factories.deliverable_factory import DeliverableFactory
from tests.factories.meeting_factory import MeetingFactory


def test_a_persisted_deliverable_type_survives_as_an_enum_member(
    db_session: Session,
) -> None:
    deliverable = DeliverableFactory.create(type=DeliverableType.DECISION_RECORD)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(Deliverable, deliverable.id)
    assert reloaded is not None
    assert isinstance(reloaded.type, DeliverableType)
    assert reloaded.type is DeliverableType.DECISION_RECORD


def test_a_persisted_deliverable_status_survives_as_an_enum_member(
    db_session: Session,
) -> None:
    deliverable = DeliverableFactory.create(status=DeliverableStatus.FAILED)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(Deliverable, deliverable.id)
    assert reloaded is not None
    assert isinstance(reloaded.status, DeliverableStatus)


def test_a_persisted_meeting_status_survives_as_an_enum_member(
    db_session: Session,
) -> None:
    meeting = MeetingFactory.create(status=MeetingStatus.TRANSCRIPTION_DONE)
    db_session.commit()
    db_session.expire_all()

    reloaded = db_session.get(Meeting, meeting.id)
    assert reloaded is not None
    assert isinstance(reloaded.status, MeetingStatus)


def test_the_stored_column_still_holds_the_plain_string_value(
    db_session: Session,
) -> None:
    deliverable = DeliverableFactory.create(type=DeliverableType.CUSTOM_REPORT)
    db_session.commit()

    stored = db_session.execute(
        Deliverable.__table__.select().where(Deliverable.id == deliverable.id)
    ).one()

    assert stored.type == "CUSTOM_REPORT"
