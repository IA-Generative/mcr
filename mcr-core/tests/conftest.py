import os
import tempfile
from collections.abc import Generator, Iterator
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import mcr_meeting.app.infrastructure.email as email_infra_module
import mcr_meeting.app.infrastructure.keycloak as keycloak_module
import mcr_meeting.app.infrastructure.redis as redis_store_module
import mcr_meeting.app.infrastructure.s3 as s3_module
import mcr_meeting.app.use_cases._shared.drive_upload as drive_upload_module
from mcr_meeting.app.db.db import (
    Base,
    db_session_ctx,
    router_db_session_context_manager,
)
from mcr_meeting.app.infrastructure.unleash import FeatureFlagSingleton
from mcr_meeting.app.schemas.S3_types import S3Object
from mcr_meeting.main import app
from tests.mocks.in_memory_drive import InMemoryDriveClient
from tests.mocks.in_memory_email import InMemoryEmailClient
from tests.mocks.in_memory_feature_flags import InMemoryFeatureFlagClient
from tests.mocks.in_memory_keycloak import InMemoryKeycloak
from tests.mocks.in_memory_redis import InMemoryRedis
from tests.mocks.in_memory_s3 import InMemoryS3
from tests.mocks.report_task_mocks import (
    mock_persist_report_docx as mock_persist_report_docx,  # noqa: F401
)

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


@pytest.fixture(autouse=True)
def in_memory_redis() -> Generator[InMemoryRedis, None, None]:
    mock = InMemoryRedis()
    original = redis_store_module._client
    redis_store_module._client = mock  # type: ignore[assignment]
    yield mock
    redis_store_module._client = original


@pytest.fixture(autouse=True)
def in_memory_keycloak() -> Generator[InMemoryKeycloak, None, None]:
    mock = InMemoryKeycloak()
    original = keycloak_module._keycloak
    keycloak_module._keycloak = mock  # type: ignore[assignment]
    yield mock
    keycloak_module._keycloak = original


@pytest.fixture
def in_memory_drive() -> Generator[InMemoryDriveClient, None, None]:
    mock = InMemoryDriveClient()
    original = drive_upload_module.upload_file
    drive_upload_module.upload_file = mock  # type: ignore[assignment]
    yield mock
    drive_upload_module.upload_file = original


@pytest.fixture(autouse=True)
def _no_retry_sleep() -> None:
    for fn in (
        s3_module.get_file_from_s3,
        s3_module.put_file_to_s3,
        s3_module._list_objects_under_prefix,
    ):
        fn.retry.sleep = lambda _: None  # type: ignore[attr-defined]


@pytest.fixture
def in_memory_s3() -> Generator[InMemoryS3, None, None]:
    fake = InMemoryS3()
    original = s3_module.s3_client
    s3_module.s3_client = fake  # type: ignore[assignment]
    yield fake
    s3_module.s3_client = original


@pytest.fixture
def in_memory_email() -> Generator[InMemoryEmailClient, None, None]:
    fake = InMemoryEmailClient()
    original = email_infra_module.send_email
    email_infra_module.send_email = fake  # type: ignore[assignment]
    yield fake
    email_infra_module.send_email = original


@pytest.fixture
def mock_minio(request: pytest.FixtureRequest, mocker: MockerFixture) -> Mock:
    bucket_name = "my_bucket"
    should_error_on_delete = getattr(request, "param", "default")
    mock_minio = mocker.patch("mcr_meeting.app.infrastructure.s3.s3_client")
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


def mock_s3_delete_return(return_type: str) -> dict[str, Any]:  # type: ignore[explicit-any]
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
        "mcr_meeting.app.infrastructure.celery.celery_producer_app"
    )

    return_value = getattr(request, "param", None)
    if isinstance(return_value, Exception):
        mock_celery_producer_app.send_task.side_effect = return_value
    elif return_value is not None:
        mock_celery_producer_app.send_task.return_value = return_value
    else:
        mock_celery_producer_app.send_task.return_value = Mock()

    return mock_celery_producer_app


@pytest.fixture(autouse=True)
def feature_flags() -> Generator[InMemoryFeatureFlagClient, None, None]:
    """Replace Unleash with an in-memory client, all flags disabled by default.

    Installed on the singleton rather than on each module-level import of
    ``get_feature_flag_client``, so every call site sees the same client:

        def test_something(feature_flags):
            feature_flags.enable(FeatureFlag.AUDIO_NOISE_FILTERING)
            ...
            assert FeatureFlag.AUDIO_NOISE_FILTERING in feature_flags.calls
    """
    client = InMemoryFeatureFlagClient()
    singleton = FeatureFlagSingleton.__new__(FeatureFlagSingleton)
    singleton._feature_flag_client = client
    original = FeatureFlagSingleton._instance
    FeatureFlagSingleton._instance = singleton
    yield client
    FeatureFlagSingleton._instance = original
