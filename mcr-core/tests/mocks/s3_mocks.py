from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_s3_put(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Mock S3 put_object to prevent actual S3 uploads during tests."""
    put_mock = MagicMock()
    monkeypatch.setattr(
        "mcr_meeting.app.services.s3_service.s3_client.put_object",
        put_mock,
    )
    return put_mock
