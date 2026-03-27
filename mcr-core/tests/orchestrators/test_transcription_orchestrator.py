from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.orchestrators import transcription_orchestrator as to
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
from tests.factories import MeetingFactory


@pytest.fixture
def mock_generate_docx(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    generate_mock = MagicMock(return_value=BytesIO(b"fake docx content"))
    monkeypatch.setattr(
        "mcr_meeting.app.services.transcription_task_service.generate_transcription_docx",
        generate_mock,
    )
    return generate_mock


@pytest.fixture
def transcription_in_progress_meeting() -> Meeting:
    return MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )


@pytest.fixture
def sample_transcriptions(
    transcription_in_progress_meeting: Meeting,
) -> list[SpeakerTranscription]:
    meeting_id = transcription_in_progress_meeting.id
    return [
        SpeakerTranscription(
            meeting_id=meeting_id,
            speaker="Speaker 1",
            transcription_index=0,
            transcription="Bonjour à tous.",
            start=0.0,
            end=1.5,
        ),
        SpeakerTranscription(
            meeting_id=meeting_id,
            speaker="Speaker 2",
            transcription_index=1,
            transcription="Merci pour cette réunion.",
            start=1.5,
            end=3.0,
        ),
    ]


class TestHandleTranscriptionSuccess:
    def test_generates_docx_with_transcription_data(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        mock_s3_put: MagicMock,
        mock_send_email: MagicMock,
    ) -> None:
        to.finalize_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        mock_generate_docx.assert_called_once_with(
            transcription_in_progress_meeting.name,
            sample_transcriptions,
        )

    def test_saves_docx_to_s3(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        mock_s3_put: MagicMock,
        mock_send_email: MagicMock,
    ) -> None:
        to.finalize_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        mock_s3_put.assert_called_once()

    def test_updates_meeting_status_to_transcription_done(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        mock_s3_put: MagicMock,
        mock_send_email: MagicMock,
        db_session: Session,
    ) -> None:
        to.finalize_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        db_session.refresh(transcription_in_progress_meeting)
        assert (
            transcription_in_progress_meeting.status == MeetingStatus.TRANSCRIPTION_DONE
        )

    def test_sets_transcription_filename(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        mock_s3_put: MagicMock,
        mock_send_email: MagicMock,
        db_session: Session,
    ) -> None:
        to.finalize_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        db_session.refresh(transcription_in_progress_meeting)
        assert transcription_in_progress_meeting.transcription_filename == "v0.docx"

    def test_sends_success_email(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        mock_s3_put: MagicMock,
        mock_send_email: MagicMock,
    ) -> None:
        to.finalize_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        assert mock_send_email.call_count == 1
