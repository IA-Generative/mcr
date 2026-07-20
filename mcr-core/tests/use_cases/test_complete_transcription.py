import json
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import (
    MeetingStateConflictException,
    NotFoundException,
)
from mcr_meeting.app.infrastructure.redis import save_refresh_token
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.models.meeting_model import (
    Meeting,
    MeetingPlatforms,
    MeetingStatus,
)
from mcr_meeting.app.models.meeting_transition_record import MeetingTransitionRecord
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription
from mcr_meeting.app.use_cases.complete_transcription import complete_transcription
from tests.factories import MeetingFactory
from tests.factories.deliverable_factory import DeliverableFactory
from tests.mocks.in_memory_drive import InMemoryDriveClient
from tests.mocks.in_memory_email import InMemoryEmailClient
from tests.mocks.in_memory_s3 import InMemoryS3


@pytest.fixture
def mock_generate_docx(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    generate_mock = MagicMock(return_value=BytesIO(b"fake docx content"))
    monkeypatch.setattr(
        "mcr_meeting.app.use_cases.complete_transcription.render_transcription_docx",
        generate_mock,
    )
    return generate_mock


@pytest.fixture
def transcription_in_progress_meeting() -> Meeting:
    meeting = MeetingFactory.create(
        status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
        name_platform=MeetingPlatforms.COMU,
    )
    DeliverableFactory.create(
        meeting=meeting,
        type=DeliverableType.TRANSCRIPTION,
        status=DeliverableStatus.IN_PROGRESS,
        external_url=None,
    )
    return meeting


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


def _transcription_deliverables(meeting_id: int) -> list[Deliverable]:
    return list(
        get_db_session_ctx()
        .query(Deliverable)
        .filter(
            Deliverable.meeting_id == meeting_id,
            Deliverable.type == DeliverableType.TRANSCRIPTION,
        )
        .all()
    )


def _transcription_done_records(meeting_id: int) -> list[MeetingTransitionRecord]:
    return list(
        get_db_session_ctx()
        .query(MeetingTransitionRecord)
        .filter(
            MeetingTransitionRecord.meeting_id == meeting_id,
            MeetingTransitionRecord.status == MeetingStatus.TRANSCRIPTION_DONE,
        )
        .all()
    )


class TestCompleteTranscription:
    def test_generates_docx_with_transcription_data(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        complete_transcription(
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
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        assert len(in_memory_s3.objects) == 1

    def test_updates_meeting_status_to_transcription_done(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        db_session: Session,
    ) -> None:
        complete_transcription(
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
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        db_session: Session,
    ) -> None:
        complete_transcription(
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
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        assert len(in_memory_email.sent) == 1

    def test_creates_transcription_deliverable(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        deliverables = _transcription_deliverables(transcription_in_progress_meeting.id)
        assert len(deliverables) == 1
        assert deliverables[0].status == DeliverableStatus.AVAILABLE

    def test_updates_early_deliverable_instead_of_creating_a_second(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
    ) -> None:
        early_deliverable = _transcription_deliverables(
            transcription_in_progress_meeting.id
        )[0]
        save_refresh_token(
            str(transcription_in_progress_meeting.owner.keycloak_uuid),
            "refresh-token",
        )

        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        deliverables = _transcription_deliverables(transcription_in_progress_meeting.id)
        assert len(deliverables) == 1
        assert deliverables[0].id == early_deliverable.id
        assert deliverables[0].status == DeliverableStatus.AVAILABLE
        assert deliverables[0].external_url == in_memory_drive.url

    def test_uploads_to_drive_and_persists_external_url(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
        in_memory_drive: InMemoryDriveClient,
    ) -> None:
        save_refresh_token(
            str(transcription_in_progress_meeting.owner.keycloak_uuid),
            "refresh-token",
        )

        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        deliverables = _transcription_deliverables(transcription_in_progress_meeting.id)
        assert len(deliverables) == 1
        assert deliverables[0].external_url == in_memory_drive.url

    def test_records_single_transcription_done_transition(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=sample_transcriptions,
        )

        # The state machine no longer records this transition; the use-case does it
        # exactly once.
        assert (
            len(_transcription_done_records(transcription_in_progress_meeting.id)) == 1
        )

    def test_renders_docx_from_s3_full_transcript_when_payload_is_absent(
        self,
        transcription_in_progress_meeting: Meeting,
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        # Chemin de la route /transcription/complete (pipeline split) : la
        # source de la transcription est le full_transcript.json écrit en S3.
        meeting_id = transcription_in_progress_meeting.id
        in_memory_s3.objects[f"transcription/{meeting_id}/full_transcript.json"] = (
            json.dumps(
                {
                    "meeting_id": meeting_id,
                    "version": 0,
                    "segments": [
                        {
                            "speaker": "LOCUTEUR_00",
                            "transcription_index": 0,
                            "transcription": "Bonjour à tous.",
                            "start": 0.0,
                            "end": 1.5,
                        }
                    ],
                }
            ).encode()
        )

        complete_transcription(meeting_id=meeting_id)

        (name, segments), _ = mock_generate_docx.call_args
        assert name == transcription_in_progress_meeting.name
        assert [(s.speaker, s.transcription) for s in segments] == [
            ("LOCUTEUR_00", "Bonjour à tous.")
        ]

    def test_uses_the_payload_when_provided_even_empty(
        self,
        transcription_in_progress_meeting: Meeting,
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        # Payload fourni (pipeline legacy) : pas de lecture S3 — un S3 vide
        # ferait échouer ce test si le use-case tentait d'y lire le transcript.
        complete_transcription(
            meeting_id=transcription_in_progress_meeting.id,
            transcriptions=[],
        )

        mock_generate_docx.assert_called_once_with(
            transcription_in_progress_meeting.name, []
        )

    def test_conflicts_on_completion_from_invalid_status(
        self,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_PENDING,
            name_platform=MeetingPlatforms.COMU,
        )

        with pytest.raises(MeetingStateConflictException):
            complete_transcription(
                meeting_id=meeting.id,
                transcriptions=sample_transcriptions,
            )

        assert _transcription_deliverables(meeting.id) == []
        assert _transcription_done_records(meeting.id) == []

    def test_raises_when_deliverable_missing(
        self,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting = MeetingFactory.create(
            status=MeetingStatus.TRANSCRIPTION_IN_PROGRESS,
            name_platform=MeetingPlatforms.COMU,
        )

        with pytest.raises(NotFoundException):
            complete_transcription(
                meeting_id=meeting.id,
                transcriptions=sample_transcriptions,
            )

        assert _transcription_deliverables(meeting.id) == []
        assert len(in_memory_email.sent) == 0

    def test_replayed_completion_conflicts_without_duplicating_deliverables(
        self,
        transcription_in_progress_meeting: Meeting,
        sample_transcriptions: list[SpeakerTranscription],
        mock_generate_docx: MagicMock,
        in_memory_s3: InMemoryS3,
        in_memory_email: InMemoryEmailClient,
    ) -> None:
        meeting_id = transcription_in_progress_meeting.id
        complete_transcription(
            meeting_id=meeting_id, transcriptions=sample_transcriptions
        )

        with pytest.raises(MeetingStateConflictException):
            complete_transcription(
                meeting_id=meeting_id, transcriptions=sample_transcriptions
            )

        assert len(_transcription_deliverables(meeting_id)) == 1
        assert len(_transcription_done_records(meeting_id)) == 1
        assert len(in_memory_email.sent) == 1
