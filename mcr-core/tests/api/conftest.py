import os
import tempfile
import uuid
from contextvars import Token
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

    def _expire_session(self) -> None:
        """Expire all objects in the current session to force fresh DB queries."""
        try:
            session = db_session_ctx.get()
            if session:
                session.expire_all()
        except LookupError:
            # No session in context, that's okay
            pass

    def get(self, path: str, **kwargs: Any) -> Response:
        self._expire_session()
        return self.client.get(f"{self.prefix}{path}", **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        self._expire_session()
        return self.client.post(f"{self.prefix}{path}", **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        self._expire_session()
        return self.client.put(f"{self.prefix}{path}", **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        self._expire_session()
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

    # Store the context token at the fixture level to manage across threads
    context_tokens: list[Token[Session | None]] = []

    # Override get_db_session to create a new session per request (like production)
    # but bound to the same connection/transaction (for test isolation)
    def override_get_db_session() -> Generator[Session, None, None]:
        # Create a fresh session for each request, bound to the test connection
        request_session = TestingSessionLocal(bind=connection)
        token = db_session_ctx.set(request_session)
        context_tokens.append(token)
        try:
            yield request_session
        finally:
            # Don't reset here due to thread issues - will clean up at fixture teardown
            request_session.close()

    app.dependency_overrides[router_db_session_context_manager] = (
        override_get_db_session
    )

    # Create a session for fixture usage (creating test data)
    fixture_session = TestingSessionLocal(bind=connection)
    fixture_token = db_session_ctx.set(fixture_session)

    yield fixture_session

    # Clean up: reset all context tokens, rollback transaction, and close connection
    for token in context_tokens:
        try:
            db_session_ctx.reset(token)
        except ValueError:
            # Token was created in a different context (thread), safe to ignore
            pass
    try:
        db_session_ctx.reset(fixture_token)
    except ValueError:
        pass
    fixture_session.close()
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
def mock_feature_flag_client(mocker: MockerFixture) -> Generator[Mock, None, None]:
    """Mock the feature flag client for testing."""
    mock_feature_flag_client = Mock()

    app.dependency_overrides[get_feature_flag_client] = lambda: mock_feature_flag_client

    yield mock_feature_flag_client

    # Clean up dependency override
    app.dependency_overrides.clear()
