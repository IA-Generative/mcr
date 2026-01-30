import os
import tempfile
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Generator, Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_mock import MockerFixture
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.db.db import (
    Base,
    db_session_ctx,
    router_db_session_context_manager,
)
from mcr_meeting.app.models import Meeting, MeetingStatus, Role, User
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.app.services.feature_flag_service import get_feature_flag_client
from mcr_meeting.main import app

api_settings = ApiSettings()


class PrefixedTestClient:
    def __init__(self, client: TestClient, prefix: str) -> None:
        self.client = client
        self.prefix = prefix

    def get(self, path: str, **kwargs: Any) -> Response:
        return self.client.get(f"{self.prefix}{path}", **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        return self.client.post(f"{self.prefix}{path}", **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        return self.client.put(f"{self.prefix}{path}", **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        return self.client.delete(f"{self.prefix}{path}", **kwargs)


@pytest.fixture
def user_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.USER_API_PREFIX)


@pytest.fixture
def member_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.MEMBER_API_PREFIX)


@pytest.fixture
def meeting_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.MEETING_API_PREFIX)


@pytest.fixture
def participants_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.PARTICIPANTS_API_PREFIX)


@pytest.fixture
def transcription_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.TRANSCRIPTION_API_PREFIX)


@pytest.fixture
def feature_flag_client() -> PrefixedTestClient:
    return PrefixedTestClient(TestClient(app), api_settings.FEATURE_FLAG_API_PREFIX)


# --- TEST DB SETUP ---
# Use a temporary SQLite file for the test DB
TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp()
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create all tables before tests
@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    os.close(TEST_DB_FD)
    os.unlink(TEST_DB_PATH)


@pytest.fixture(autouse=True)
def db_session() -> Generator[Session, None, None]:
    # Start a new connection and transaction
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Set the session in the actual context variable used by the application
    context_token = db_session_ctx.set(session)

    # Override get_db_session to use this session
    def override_get_db_session() -> Generator[Session, None, None]:
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[router_db_session_context_manager] = (
        override_get_db_session
    )

    yield session

    # Clean up: reset the context variable, rollback transaction, and close connection
    db_session_ctx.reset(context_token)
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def user_fixture(db_session: Session) -> User:
    user = User(
        first_name="Wade",
        last_name="Wilson",
        entity_name="X-Force",
        email="wade.wilson@x-force.com",
        role=Role.USER,
        keycloak_uuid=uuid.uuid4(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_2_fixture(db_session: Session) -> User:
    user = User(
        first_name="John",
        last_name="Doe",
        entity_name="Acme",
        email="john.doe@acme.com",
        role=Role.USER,
        keycloak_uuid=uuid.uuid4(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def meeting_fixture(db_session: Session) -> Meeting:
    meeting = Meeting(
        id=1,
        user_id=1,
        name="Team Meeting",
        creation_date=datetime(2024, 9, 29, 10, 0, tzinfo=timezone.utc),
        status="NONE",
        name_platform="COMU",
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        meeting_password="123456",
        meeting_platform_id="123",
    )

    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


@pytest.fixture
def meeting_2_fixture(db_session: Session) -> Meeting:
    meeting = Meeting(
        id=2,
        user_id=1,
        name="Project Kickoff",
        creation_date=datetime(2024, 10, 1, 12, 0, tzinfo=timezone.utc),
        status="NONE",
        name_platform="COMU",
        url="https://webconf.comu.gouv.fr/meeting/306356457?secret=GF2e74BjOcDR1Bq6nvv5wA",
        meeting_password="123456",
        meeting_platform_id="123",
    )

    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


@pytest.fixture
def meeting_factory(db_session, user_fixture):
    def _create_meeting(status=MeetingStatus.NONE, **kwargs):
        meeting = Meeting(
            user_id=user_fixture.id,
            name="Dynamic meeting",
            status=status,
            name_platform="COMU",
            creation_date=datetime.now(timezone.utc),
            **kwargs,
        )
        db_session.add(meeting)
        db_session.commit()
        db_session.refresh(meeting)
        return meeting

    return _create_meeting


@pytest.fixture
def mock_minio(request: pytest.FixtureRequest, mocker: MockerFixture) -> Mock:
    bucket_name = "my_bucket"
    should_error_on_delete = getattr(request, "param", "default")
    mock_minio = mocker.patch("mcr_meeting.app.services.s3_service.s3_client")
    mock_minio.put_object.return_value = SimpleNamespace(
        bucket_name=bucket_name,
        object_name="my/super/file",
    )

    mock_minio.list_objects.return_value = mock_s3_object_iterator(bucket_name)
    mock_minio.delete_objects.return_value = mock_s3_delete_return(
        should_error_on_delete
    )

    return mock_minio


def mock_s3_object_iterator(bucket_name: str) -> Iterator[S3Object]:
    for i in range(3):
        yield S3Object(
            bucket_name=bucket_name,
            object_name=f"file{i}.txt",
            last_modified=datetime(2025, 1, i + 1),
        )


def mock_s3_delete_return(return_type: str):
    match return_type:
        case "delete_error":
            return {
                "Errors": [
                    {
                        "Key": "audio.mp3",
                        "Code": "InternalError",
                        "Message": "Simulated delete failure",
                    }
                ]
            }
        case _:
            return {"Deleted": [{"Key": "audio.mp3"}]}


@pytest.fixture
def mock_celery_producer_app(
    request: pytest.FixtureRequest, mocker: MockerFixture
) -> Mock:
    """Mock the celery broker send_task method."""

    mock_celery_producer_app = mocker.patch(
        "mcr_meeting.app.statemachine_actions.meeting_actions.celery_producer_app"
    )

    return_value = getattr(request, "param", None)
    if isinstance(return_value, Exception):
        mock_celery_producer_app.send_task.side_effect = return_value
    elif return_value is not None:
        mock_celery_producer_app.send_task.return_value = return_value
    else:
        mock_celery_producer_app.send_task.return_value = Mock()

    return mock_celery_producer_app


@pytest.fixture
def create_mock_feature_flag_client(mocker: MockerFixture):
    """Mock the feature flag client factory for testing.

    Returns a factory function that creates mock feature flag clients
    with configurable enabled/disabled states for specific flags.

    Usage:
        def test_something(create_mock_feature_flag_client):
            mock_feature_flag_client = create_mock_feature_flag_client("audio_noise_filtering", enabled=True)
            # Will return True only for "audio_noise_filtering", False for other flags
            assert mock_feature_flag_client.is_enabled("audio_noise_filtering") == True
            assert mock_feature_flag_client.is_enabled("other_flag") == False
            # Can also verify the flag was called
            mock_feature_flag_client.is_enabled.assert_called_with("audio_noise_filtering")
    """

    def _create_mock(flag_name: str, enabled: bool) -> Mock:
        mock_client = Mock()

        # Create a side_effect that returns enabled only for the specified flag
        def is_enabled_side_effect(name: str) -> bool:
            return enabled if name == flag_name else False

        mock_client.is_enabled.side_effect = is_enabled_side_effect
        app.dependency_overrides[get_feature_flag_client] = lambda: mock_client
        return mock_client

    yield _create_mock

    # Clean up dependency override
    app.dependency_overrides.clear()
