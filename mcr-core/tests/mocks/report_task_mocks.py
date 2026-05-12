from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_persist_report_docx(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    persist_mock = MagicMock(return_value=BytesIO(b"docx"))
    # Patched at both import sites: the SM handler (via meeting_actions) and the
    # orchestrator path call it independently.
    monkeypatch.setattr(
        "mcr_meeting.app.statemachine_actions.meeting_actions.persist_report_docx",
        persist_mock,
    )
    monkeypatch.setattr(
        "mcr_meeting.app.orchestrators.deliverable_orchestrator.persist_report_docx",
        persist_mock,
    )
    return persist_mock


@pytest.fixture
def mock_upload_authenticated_for_user(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    upload_mock = MagicMock(
        return_value="https://drive.example.com/explorer/items/files/fake-id"
    )
    monkeypatch.setattr(
        "mcr_meeting.app.services.drive_upload_service.upload_authenticated_for_user",
        upload_mock,
    )
    return upload_mock
