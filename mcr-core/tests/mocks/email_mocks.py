from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_send_email(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Mock email service to prevent actual emails during tests."""
    send_email_mock = MagicMock()
    monkeypatch.setattr(
        "mcr_meeting.app.services.email.email_service.send_email",
        send_email_mock,
    )
    return send_email_mock
