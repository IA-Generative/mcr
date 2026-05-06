from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_persist_report_docx(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    persist_mock = MagicMock()
    monkeypatch.setattr(
        "mcr_meeting.app.statemachine_actions.meeting_actions.persist_report_docx",
        persist_mock,
    )
    return persist_mock
