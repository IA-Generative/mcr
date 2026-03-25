from collections.abc import Generator

import pytest

import mcr_meeting.app.services.deliverable_storage_service as deliverable_module
import mcr_meeting.app.services.redis_token_store as redis_store_module
import mcr_meeting.app.services.token_exchange_service as token_exchange_module
from tests.mocks.in_memory_drive import InMemoryDriveClient
from tests.mocks.in_memory_keycloak import InMemoryKeycloak
from tests.mocks.in_memory_redis import InMemoryRedis


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
    original = token_exchange_module._keycloak
    token_exchange_module._keycloak = mock  # type: ignore[assignment]
    yield mock
    token_exchange_module._keycloak = original


@pytest.fixture
def in_memory_drive() -> Generator[InMemoryDriveClient, None, None]:
    mock = InMemoryDriveClient()
    original = deliverable_module.upload_file
    deliverable_module.upload_file = mock  # type: ignore[assignment]
    yield mock
    deliverable_module.upload_file = original
