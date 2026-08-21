import pytest

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.db.meeting_repository import get_meeting_by_id
from mcr_meeting.app.exceptions.exceptions import (
    ForbiddenAccessException,
    NotFoundException,
)
from mcr_meeting.app.models import MeetingStatus
from mcr_meeting.app.models.meeting_model import Meeting, MeetingPlatforms
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.use_cases.delete_meetings import delete_meetings
from tests.factories.meeting_factory import MeetingFactory
from tests.factories.user_factory import UserFactory


@pytest.fixture
def user_fixture() -> User:
    return UserFactory.create()


def a_meeting(owner: User | None = None) -> Meeting:
    return MeetingFactory.create(
        **({"owner": owner} if owner else {}),
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )


def deleted_transition_records(meeting_id: int) -> list[MeetingTransitionRecord]:
    return (
        get_db_session_ctx()
        .query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == MeetingStatus.DELETED,
        )
        .all()
    )


def test_delete_meetings_deletes_every_meeting_of_the_list(user_fixture: User) -> None:
    first, second = a_meeting(user_fixture), a_meeting(user_fixture)

    delete_meetings(
        meeting_ids=[first.id, second.id],
        user_keycloak_uuid=user_fixture.keycloak_uuid,
    )

    for meeting in (first, second):
        assert meeting.status == MeetingStatus.DELETED
        with pytest.raises(NotFoundException):
            get_meeting_by_id(meeting.id)
        assert len(deleted_transition_records(meeting.id)) == 1


def test_delete_meetings_deletes_the_others_when_one_is_unknown(
    user_fixture: User,
) -> None:
    first, second = a_meeting(user_fixture), a_meeting(user_fixture)

    delete_meetings(
        meeting_ids=[first.id, 999_999, second.id],
        user_keycloak_uuid=user_fixture.keycloak_uuid,
    )

    assert first.status == MeetingStatus.DELETED
    assert second.status == MeetingStatus.DELETED


def test_delete_meetings_spares_every_meeting_when_one_belongs_to_someone_else(
    user_fixture: User,
) -> None:
    own = a_meeting(user_fixture)
    someone_elses = a_meeting()

    with pytest.raises(ForbiddenAccessException):
        delete_meetings(
            meeting_ids=[own.id, someone_elses.id],
            user_keycloak_uuid=user_fixture.keycloak_uuid,
        )

    assert own.status != MeetingStatus.DELETED
    assert someone_elses.status != MeetingStatus.DELETED
    assert deleted_transition_records(own.id) == []


def test_delete_meetings_deletes_nothing_when_the_list_is_empty(
    user_fixture: User,
) -> None:
    untouched = a_meeting(user_fixture)

    delete_meetings(meeting_ids=[], user_keycloak_uuid=user_fixture.keycloak_uuid)

    assert untouched.status != MeetingStatus.DELETED
