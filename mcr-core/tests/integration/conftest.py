from collections.abc import Generator

import pytest

import mcr_meeting.app.services.deliverable_storage_service as deliverable_module
from tests.mocks.in_memory_drive import InMemoryDriveClient


@pytest.fixture
def in_memory_drive() -> Generator[InMemoryDriveClient, None, None]:
    mock = InMemoryDriveClient()
    original = deliverable_module.upload_file
    deliverable_module.upload_file = mock  # type: ignore[assignment]
    yield mock
    deliverable_module.upload_file = original
