from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

import mcr_meeting.app.services.s3_service as s3_service_module


@pytest.fixture(autouse=True)
def mock_s3() -> Generator[MagicMock, None, None]:
    mock = MagicMock()
    original = s3_service_module.s3_client  # type: ignore[attr-defined]
    s3_service_module.s3_client = mock  # type: ignore[attr-defined]
    yield mock
    s3_service_module.s3_client = original  # type: ignore[attr-defined]
