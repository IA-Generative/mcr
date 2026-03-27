from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcr_meeting.app.schemas.celery_types import (
    TranscriptionTaskArgs,
    extract_transcription_task_args,
)


class TestExtractTranscriptionTaskArgs:
    def test_extracts_from_kwargs_args(self) -> None:
        kwargs = {"args": [42, "uuid-123"]}

        result = extract_transcription_task_args(kwargs)

        assert result == TranscriptionTaskArgs(
            meeting_id=42, owner_keycloak_uuid="uuid-123"
        )

    def test_falls_back_to_sender_request_args(self) -> None:
        kwargs: dict[str, object] = {}
        sender = MagicMock()
        sender.request.args = [42, "uuid-123"]

        result = extract_transcription_task_args(kwargs, sender=sender)

        assert result == TranscriptionTaskArgs(
            meeting_id=42, owner_keycloak_uuid="uuid-123"
        )

    def test_falls_back_when_kwargs_args_empty(self) -> None:
        kwargs: dict[str, list[object]] = {"args": []}
        sender = MagicMock()
        sender.request.args = [42, "uuid-123"]

        result = extract_transcription_task_args(kwargs, sender=sender)

        assert result == TranscriptionTaskArgs(
            meeting_id=42, owner_keycloak_uuid="uuid-123"
        )

    def test_raises_when_no_args_available(self) -> None:
        kwargs: dict[str, object] = {}

        with pytest.raises(ValueError, match="Unable to extract"):
            extract_transcription_task_args(kwargs)

    def test_raises_when_args_has_fewer_than_two_elements(self) -> None:
        kwargs = {"args": [42]}

        with pytest.raises(ValueError, match="Unable to extract"):
            extract_transcription_task_args(kwargs)

    def test_raises_when_sender_has_no_request(self) -> None:
        kwargs: dict[str, object] = {}
        sender = SimpleNamespace()

        with pytest.raises(ValueError, match="Unable to extract"):
            extract_transcription_task_args(kwargs, sender=sender)
