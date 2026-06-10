from uuid import UUID

import pytest

from mcr_meeting.app.models.meeting_model import (
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.orchestrators import meeting_transitions_orchestrator as mts
from tests.factories import MeetingFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_keycloak_uuid(orchestrator_user: User) -> UUID:
    """Use the keycloak_uuid from the orchestrator_user fixture."""
    return orchestrator_user.keycloak_uuid


# ---------------------------------------------------------------------------
# Tests – Capture
# ---------------------------------------------------------------------------


def test_start_capture(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test starting capture transitions meeting to CAPTURE_BOT_IS_CONNECTING."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_PENDING,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.start_capture(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_BOT_IS_CONNECTING


def test_fail_capture(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test capture failure transitions to CAPTURE_FAILED."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.CAPTURE_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )

    result = mts.fail_capture(
        meeting_id=meeting.id,
        user_keycloak_uuid=user_keycloak_uuid,
    )

    assert result.status == MeetingStatus.CAPTURE_FAILED


# ---------------------------------------------------------------------------
# Tests – Report
# ---------------------------------------------------------------------------


def test_reset_report_bad_status(
    orchestrator_user: User,
    user_keycloak_uuid: UUID,
) -> None:
    """Test that reset_report raises exception when meeting is in wrong status."""
    meeting = MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(Exception):
        mts.reset_report(
            meeting_id=meeting.id,
            user_keycloak_uuid=user_keycloak_uuid,
        )


# ---------------------------------------------------------------------------
# Error case
# ---------------------------------------------------------------------------


def test_complete_transcription_from_transcription_done_fails() -> None:
    """Test that complete_transcription from TRANSCRIPTION_DONE raises exception."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(Exception):
        mts.complete_transcription(meeting_id=meeting.id)


def test_complete_transcription_from_report_done_fails() -> None:
    """Test that complete_transcription from REPORT_DONE raises exception."""
    meeting = MeetingFactory.create(
        status=MeetingStatus.REPORT_DONE,
        name_platform=MeetingPlatforms.COMU,
    )

    with pytest.raises(Exception):
        mts.complete_transcription(meeting_id=meeting.id)
