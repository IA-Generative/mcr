import pytest

from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.user_model import User
from mcr_meeting.app.schemas.transcription_schema import TranscriptionSegment
from tests.factories import MeetingFactory, UserFactory

segment_data_list = [
    {
        "id": 0,
        "text": "Hello there.",
        "start": 1.0,
        "end": 2.0,
    },
    {
        "id": 1,
        "text": "World!",
        "start": 3.0,
        "end": 4.0,
    },
    {
        "id": 2,
        "text": "Sous-titrage ST' ST'",
        "start": 5.0,
        "end": 6.5,
    },
]


@pytest.fixture
def segment_fixture_list() -> list[TranscriptionSegment]:
    segments = [TranscriptionSegment(**data) for data in segment_data_list]  # type: ignore[arg-type]

    return segments


# --- ORCHESTRATOR TEST FIXTURES USING FACTORIES ---


@pytest.fixture
def orchestrator_user() -> User:
    """Create a user for orchestrator tests."""
    return UserFactory.create()


@pytest.fixture
def visio_meeting(orchestrator_user: User) -> Meeting:
    """Create a COMU visio meeting for orchestrator tests."""
    return MeetingFactory.create(
        owner=orchestrator_user,
        status=MeetingStatus.NONE,
        name_platform=MeetingPlatforms.COMU,
    )


@pytest.fixture
def import_meeting(orchestrator_user: User) -> Meeting:
    """Create an import meeting for orchestrator tests."""
    return MeetingFactory.create(
        import_meeting=True,
        owner=orchestrator_user,
        status=MeetingStatus.IMPORT_PENDING,
    )


@pytest.fixture
def record_meeting(orchestrator_user: User) -> Meeting:
    """Create a record meeting for orchestrator tests."""
    return MeetingFactory.create(
        record_meeting=True,
        owner=orchestrator_user,
        status=MeetingStatus.NONE,
    )
