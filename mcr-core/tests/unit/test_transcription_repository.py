from typing import List
from unittest.mock import MagicMock, patch

import pytest

from mcr_meeting.app.db.transcription_repository import save_transcription
from mcr_meeting.app.models import Transcription
from mcr_meeting.app.schemas.transcription_schema import SpeakerTranscription


@pytest.fixture
def sample_input() -> List[SpeakerTranscription]:
    return [
        SpeakerTranscription(
            meeting_id=1,
            speaker="speaker-xyz",
            transcription="Hello world",
            transcription_index=0,
            start=0.0,
            end=1.0,
        )
    ]


def test_save_transcription_happy_path(
    sample_input: List[SpeakerTranscription],
) -> None:
    db_mock = MagicMock()

    # db.query(...).filter_by(...).first() should return None (happy path)
    query_mock = db_mock.query.return_value.filter_by.return_value
    query_mock.first.return_value = None

    with (
        patch(
            "mcr_meeting.app.db.unit_of_work.get_db_session_ctx",
            return_value=db_mock,
        ),
        patch(
            "mcr_meeting.app.db.transcription_repository.get_db_session_ctx",
            return_value=db_mock,
        ),
    ):
        result = save_transcription(sample_input)

    # ensure one transcription created
    assert len(result) == 1
    created = result[0]
    assert isinstance(created, Transcription)

    # ensure DB operations were called correctly
    db_mock.add.assert_called_once_with(created)
    # With UnitOfWork, commit is called by the context manager
    db_mock.commit.assert_called_once()

    # ensure query was executed with correct filter
    db_mock.query.assert_called_once_with(Transcription)
    db_mock.query.return_value.filter_by.assert_called_once_with(
        meeting_id=1,
        transcription_index=0,
    )
