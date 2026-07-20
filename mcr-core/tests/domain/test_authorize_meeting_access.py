import uuid

import pytest

from mcr_meeting.app.domain.authorize_meeting_access import (
    authorize_meeting_owner_or_admin,
)
from mcr_meeting.app.exceptions.exceptions import ForbiddenAccessException
from mcr_meeting.app.schemas.caller_schema import Caller


def _caller(user_id: int, is_admin: bool) -> Caller:
    return Caller(user_id=user_id, keycloak_uuid=uuid.uuid4(), is_admin=is_admin)


def test_owner_is_allowed() -> None:
    authorize_meeting_owner_or_admin(42, _caller(user_id=42, is_admin=False))


def test_admin_non_owner_is_allowed() -> None:
    authorize_meeting_owner_or_admin(42, _caller(user_id=99, is_admin=True))


def test_non_owner_non_admin_is_rejected() -> None:
    with pytest.raises(ForbiddenAccessException):
        authorize_meeting_owner_or_admin(42, _caller(user_id=99, is_admin=False))
